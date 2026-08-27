"""
LLM Gateway — the SINGLE entry point for all language-model access.

Phase 1 (stub mode):
  Responses are served from ``fixtures/stub_responses.json`` via
  app.data.seed.load_fixture and validated against the same output contracts
  as live calls. No network calls, no API key ever included.

Phase 2 (live mode):
  OpenRouter via the OpenAI Python SDK.

WS05 rules enforced here:
  - STRICT ROLE SEPARATION (WS05-01): the SYSTEM message carries only policy,
    internally authored rubric, schema contract, and safety rules. Every
    request-specific value — including learner essays/transcripts, topics,
    scenarios and history — travels in the USER message as a strict JSON
    payload built by the private ``_payload_*`` builders below. Raw learner
    text is never formatted into a system template.
  - SERVER-SIDE OUTPUT VALIDATION (WS05-02): every response is checked
    against an explicit Pydantic contract (app.services.llm_output) before it
    leaves this class. Invalid output raises controlled LLM_BAD_OUTPUT;
    nothing partial is persisted downstream.
  - INPUT/COST BOUNDS (WS05-05): untrusted strings are truncated at
    config-defined ceilings before leaving the process; requests carry a
    timeout and output-token ceiling; the SDK applies bounded retries
    (transient 429/5xx/network only) with exponential backoff+jitter.
  - AUDIT METADATA (WS05-08): each call returns ``_meta_llm`` describing
    provider, requested/resolved model, latency and token usage where the
    provider reports it — without mixing billing concerns into prompts.
"""

from __future__ import annotations

import json
import re
import time

from app.data.seed import load_fixture
from app.errors import ApiError


class LlmGateway:
    """
    Central gateway for LLM calls.

    Parameters
    ----------
    config : app.config.Config
        Application configuration object.  ``config.LLM_MODE`` controls
        whether stub or live mode is used.
    """

    def __init__(self, config) -> None:
        self._config = config
        self._stub_data: dict | None = None  # lazily loaded on first access
        self._openai_client = None           # lazily built on first live call

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _stubs(self) -> dict:
        """Return the stub fixture, loading it exactly once per instance."""
        if self._stub_data is None:
            self._stub_data = load_fixture("stub_responses")
        return self._stub_data

    @staticmethod
    def _sanitise(payload: dict) -> dict:
        """Remove any key that could be an API credential from *payload*."""
        sensitive = {"api_key", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"}
        return {k: v for k, v in payload.items() if k not in sensitive}

    def _client(self):
        """Lazily build and cache the OpenAI client pointed at the provider."""
        if self._openai_client is None:
            from openai import OpenAI  # lazy import so stub mode needs no openai install
            cfg = self._config
            if not cfg.OPENROUTER_API_KEY:
                raise ApiError("LLM_UNAVAILABLE", "OPENROUTER_API_KEY not set", 502)
            self._openai_client = OpenAI(
                base_url=cfg.OPENROUTER_BASE_URL,
                api_key=cfg.OPENROUTER_API_KEY,
                timeout=max(1, int(getattr(cfg, "LLM_TIMEOUT_S", 60))),
                # WS05-06: SDK-level bounded retry for transient failures only
                # (connection errors, 408/409/429, >=500) with backoff+jitter.
                max_retries=max(0, min(int(getattr(cfg, "LLM_MAX_RETRIES", 2)), 5)),
            )
        return self._openai_client

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Parse JSON from model output, handling ```json fences and prose."""
        t = text.strip()
        if t.startswith("```"):
            t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
            t = re.sub(r"\n?```$", "", t).strip()
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", t, re.DOTALL)  # first {...} span
            if m:
                return json.loads(m.group(0))
            raise ApiError("LLM_UNAVAILABLE", "model did not return valid JSON", 502)

    @staticmethod
    def _cap(value, limit: int) -> str:
        """Defence-in-depth truncation of any untrusted string."""
        if value is None:
            return ""
        s = str(value)
        return s[:limit]

    def _payload(self, fields: dict) -> str:
        """Serialise the strict user-message payload."""
        clean = {k: v for k, v in fields.items() if v is not None}
        return json.dumps(clean, ensure_ascii=False)

    def _chat(self, model: str, system: str, user_payload_json: str,
              *, max_tokens: int):
        """
        One chat completion call: privileged system text + structured user
        payload. Returns (parsed_output_dict, audit_metadata_dict).

        Raises ApiError(LLM_UNAVAILABLE) on network/provider errors and
        ApiError(LLM_BAD_OUTPUT, via the caller's validator) on schema misses.
        """
        started = time.monotonic()
        try:
            resp = self._client().chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_payload_json},
                ],
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content
            resolved_model = getattr(resp, "model", None)
            usage = getattr(resp, "usage", None)
        except ApiError:
            raise
        except Exception as e:  # network / provider / auth errors
            raise ApiError("LLM_UNAVAILABLE", f"LLM call failed: {type(e).__name__}", 502)
        latency_ms = int((time.monotonic() - started) * 1000)
        out = self._extract_json(content)
        # WS05→WS07/WS27 contract: expose full provider usage metadata so the
        # append-only cost ledger can record real token/cost figures without
        # any billing concern leaking into prompt construction. All fields
        # are optional — providers that don't report them stay None.
        prompt_details = getattr(usage, "prompt_tokens_details", None)
        completion_details = getattr(usage, "completion_tokens_details", None)
        meta = {
            "provider": getattr(self._config, "LLM_PROVIDER", "openrouter"),
            "requestedModel": model,
            "resolvedModel": resolved_model,
            "latencyMs": latency_ms,
            "promptTokens": getattr(usage, "prompt_tokens", None),
            "completionTokens": getattr(usage, "completion_tokens", None),
            "cachedTokens": getattr(prompt_details, "cached_tokens", None),
            "reasoningTokens": getattr(completion_details, "reasoning_tokens", None),
            "costUsd": getattr(usage, "cost", None),
        }
        return self._sanitise(out), meta

    # ------------------------------------------------------------------
    # Structured user-message payload builders (WS05-01)
    #
    # One builder per task. Everything routed through here is UNTRUSTED data;
    # bounds come from config so no code path can bypass the ceilings.
    # ------------------------------------------------------------------

    def _cfg(self):
        return self._config

    def _gen_payload(self, skill: str, band: str | None, **kw) -> str:
        cfg = self._cfg()
        band = (band or "B2")[:6]
        base: dict = {"band": band}
        if skill == "vocab":
            base["topic"] = self._cap(kw.get("topic"), getattr(cfg, "MAX_TOPIC_CHARS", 160))
        elif skill == "lesson":
            lc = getattr(cfg, "MAX_LESSON_FIELD_CHARS", 160)
            base.update({
                "day": self._cap(kw.get("day"), lc),
                "focus": self._cap(kw.get("focus"), lc),
                "tasks": self._cap(kw.get("tasks"), lc),
            })
        return self._payload(base)

    def _score_payload(self, task: str, **kw) -> str:
        cfg = self._cfg()
        if task == "writing":
            return self._payload({
                "task_type": self._cap(kw.get("taskType"), 20),
                "task_prompt": self._cap(kw.get("prompt"), 4000),
                "learner_response": self._cap(kw.get("essay"), getattr(cfg, "MAX_ESSAY_CHARS", 30000)),
                "deterministic_metrics": self._cap(kw.get("metricsSummary"), 600),
            })
        if task == "speaking":
            return self._payload({
                "part": self._cap(kw.get("part"), 20),
                "question": self._cap(kw.get("question"), 2000),
                "learner_transcript": self._cap(kw.get("transcript"), getattr(cfg, "MAX_TRANSCRIPT_CHARS", 12000)),
            })
        if task == "roleplay":
            return self._payload({
                "scenario": self._cap(kw.get("scenario"), getattr(cfg, "MAX_SCENARIO_CHARS", 160)),
                "history": self._cap(kw.get("history"), getattr(cfg, "MAX_ROLEPLAY_HISTORY_CHARS", 4000)),
                "user_utterance": self._cap(kw.get("userText"), getattr(cfg, "MAX_ROLEPLAY_TURN_CHARS", 1200)),
            })
        if task == "pronounce":
            try:
                acc = float(kw.get("accuracy") or 0)
            except (TypeError, ValueError):
                acc = 0.0
            return self._payload({
                "target_sentence": self._cap(kw.get("target"), 240),
                "recogniser_transcript": self._cap(kw.get("transcript"), 2400),
                "word_match_accuracy_pct": round(acc, 1),
                "missed_words": self._cap(kw.get("missed"), 400),
            })
        raise ApiError("LLM_UNAVAILABLE", f"no payload contract for task {task!r}", 502)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(
        self,
        task: str,
        skill: str | None = None,
        band: str | None = None,
        lang: str = "en",
        **kw,
    ) -> dict:
        """
        Generate content (passage, transcript, vocab list, lesson, or
        pronunciation target).

        Returns the validated, cleaned payload dict. In both modes the dict
        carries ``"_meta_llm"`` audit metadata for the call.
        """
        if self._config.LLM_MODE == "stub":
            return self._stub_generate(task, skill, band)

        from app.services.prompts import GENERATE_PROMPTS, lang_note
        from app.services.llm_output import validate_llm_output

        # One resolution for BOTH template and schema. An explicit generation
        # task name ("lesson") wins; otherwise the skill selects the content
        # generator ("reading"/"listening"/"vocab"/"pronounce"). Focus skills
        # like speaking/writing that share names with SCORE tasks resolve to
        # the correct schema because the task key already carried "lesson".
        if task in GENERATE_PROMPTS:
            gen_key = task
        elif skill in GENERATE_PROMPTS:
            gen_key = skill
        else:
            gen_key = None
        tmpl = GENERATE_PROMPTS.get(gen_key) if gen_key else None
        if tmpl is None:
            raise ApiError("LLM_UNAVAILABLE", f"no generate prompt for {skill!r}", 502)

        # System template formats ONLY trusted server-authored values.
        system_prompt = tmpl.format(langNote=self._lang_policy(lang))

        payload_json = self._gen_payload(gen_key, band, **kw)
        raw, meta = self._chat(
            self._config.MODEL_GENERATE, system_prompt, payload_json,
            max_tokens=int(getattr(self._config, "LLM_MAX_OUTPUT_TOKENS_GEN", 2000)),
        )
        schema_task = {"pronounce": "pronounce_target"}.get(gen_key, gen_key)
        result = validate_llm_output(schema_task, raw)
        result["_meta_llm"] = meta
        return result

    def score(self, task: str, lang: str = "en", **kw) -> dict:
        """
        Score a learner's written or spoken response (practice estimate).

        Returns the validated, cleaned payload dict including
        ``score_metadata`` (estimate transparency envelope) and
        ``_meta_llm`` (audit metadata).
        """
        if self._config.LLM_MODE == "stub":
            return self._stub_score(task)

        from app.services.prompts import SCORE_PROMPTS, lang_note
        from app.services.llm_output import validate_llm_output

        tmpl = SCORE_PROMPTS.get(task)
        if tmpl is None:
            raise ApiError("LLM_UNAVAILABLE", f"no score prompt for {task!r}", 502)

        system_prompt = tmpl.format(langNote=self.__class__._lang_policy(lang))
        payload_json = self._score_payload(task, **kw)
        raw, meta = self._chat(
            self._config.MODEL_SCORE, system_prompt, payload_json,
            max_tokens=int(getattr(self._config, "LLM_MAX_OUTPUT_TOKENS_SCORE", 2000)),
        )
        result = validate_llm_output(task, raw)
        ws_meta = {
            "score_method": "llm_estimate",
            "score_version": "1.0",
            "model_provider": meta.get("provider"),
            "model_id": meta.get("requestedModel"),
            "prompt_version": "ws05-1",
            "rubric_version": "internal-v1",
            "calibration_version": "cal-v1",
        }
        result["score_metadata"] = ws_meta
        result["_meta_llm"] = meta
        return result

    @staticmethod
    def _lang_policy(lang: str) -> str:
        """Trusted enum-derived policy text (the ONLY dynamic system input)."""
        from app.services.prompts import lang_note
        return lang_note(lang)

    # ------------------------------------------------------------------
    # Stub-mode resolution
    # ------------------------------------------------------------------

    def _stub_generate(self, task: str, skill: str | None, band: str | None) -> dict:
        """Look up a generate stub; exact key then band fallback."""
        from app.services.prompts import GENERATE_PROMPTS
        from app.services.llm_output import validate_llm_output

        # Same precedence as the live path (task name first, then skill).
        if task in GENERATE_PROMPTS:
            gen_key = task
        elif skill in GENERATE_PROMPTS:
            gen_key = skill
        else:
            gen_key = None
        stubs = self._stubs()
        exact_key = f"{task}:{skill}:{band}"
        prefix = f"{task}:{skill}:"
        chosen = None
        if exact_key in stubs:
            chosen = stubs[exact_key]
        else:
            for key, value in stubs.items():
                if key.startswith(prefix):
                    chosen = value
                    break
        if chosen is None:
            raise ApiError("LLM_UNAVAILABLE", f"no stub for {exact_key}", 502)

        payload = self._sanitise(dict(chosen))
        schema_task = {"pronounce": "pronounce_target"}.get(gen_key, gen_key)
        result = validate_llm_output(schema_task, payload)
        result["stub"] = True
        result["_meta_llm"] = {
            "provider": "stub", "requestedModel": "stub",
            "resolvedModel": None, "latencyMs": 0,
            "promptTokens": None, "completionTokens": None,
            "cachedTokens": None, "reasoningTokens": None, "costUsd": None,
        }
        return result

    def _stub_score(self, task: str) -> dict:
        """Look up a score stub by \"score:{task}\"; validated like live."""
        from app.services.llm_output import validate_llm_output

        stubs = self._stubs()
        key = f"score:{task}"
        if key not in stubs:
            raise ApiError("LLM_UNAVAILABLE", f"no stub for {key}", 502)

        payload = self._sanitise(dict(stubs[key]))
        result = validate_llm_output(task, payload)
        result["stub"] = True
        result["score_metadata"] = {
            "score_method": "llm_estimate",
            "score_version": "1.0",
            "model_provider": "stub",
            "model_id": "stub",
            "prompt_version": "ws05-1",
            "rubric_version": "internal-v1",
            "calibration_version": "cal-v1",
        }
        result["_meta_llm"] = {
            "provider": "stub", "requestedModel": "stub",
            "resolvedModel": None, "latencyMs": 0,
            "promptTokens": None, "completionTokens": None,
            "cachedTokens": None, "reasoningTokens": None, "costUsd": None,
        }
        return result
