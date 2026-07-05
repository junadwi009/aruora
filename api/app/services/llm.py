"""
LLM Gateway — the SINGLE entry point for all language-model access.

Phase 1 (stub mode):
  Responses are served from ``fixtures/stub_responses.json`` via
  ``app.data.seed.load_fixture``. No network calls are made and no
  API key is ever included in the return value.

Phase 2 (live mode):
  OpenRouter via the OpenAI Python SDK.
  Generation tasks use MODEL_GENERATE (cheap, high-volume).
  Scoring tasks use MODEL_SCORE (strong, Writing/Speaking evaluation).

Rules enforced here:
  - NEVER return an API key in any output dict.
  - NEVER call the LLM SDK outside this class.
  - ALL prompt templates live in app.services.prompts, not here.
"""

from __future__ import annotations

import json
import re

from app.data.seed import load_fixture
from app.errors import ApiError

# SYSTEM addendum appended to every live call to enforce JSON-only output
_JSON_ONLY = "\n\nReturn ONLY strict JSON — no markdown fences, no prose outside the JSON object."


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
        """
        Remove any key that could be an API credential from *payload*.

        This is a defence-in-depth measure — the gateway should never
        construct a response that includes a key in the first place, but
        we strip known sensitive key names before returning.
        """
        sensitive = {"api_key", "OPENROUTER_API_KEY", "ANTHROPIC_API_KEY"}
        return {k: v for k, v in payload.items() if k not in sensitive}

    def _client(self):
        """Lazily build and cache the OpenAI client pointed at OpenRouter."""
        if self._openai_client is None:
            from openai import OpenAI  # lazy import so stub mode needs no openai install
            cfg = self._config
            if not cfg.OPENROUTER_API_KEY:
                raise ApiError("LLM_UNAVAILABLE", "OPENROUTER_API_KEY not set", 502)
            self._openai_client = OpenAI(
                base_url=cfg.OPENROUTER_BASE_URL,
                api_key=cfg.OPENROUTER_API_KEY,
            )
        return self._openai_client

    @staticmethod
    def _extract_json(text: str) -> dict:
        """
        Parse JSON from model output, handling ```json fences and surrounding prose.
        """
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

    def _chat(self, model: str, system: str, user: str) -> dict:
        """
        Make a single chat completion call and return a sanitised dict.
        Generation uses MODEL_GENERATE; scoring uses MODEL_SCORE (SC-006).
        """
        try:
            resp = self._client().chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
            )
            content = resp.choices[0].message.content
        except ApiError:
            raise
        except Exception as e:  # network / provider / auth errors
            raise ApiError("LLM_UNAVAILABLE", f"LLM call failed: {type(e).__name__}", 502)
        out = self._extract_json(content)
        return self._sanitise(out)   # never leak a key; do NOT add stub:True in live mode

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
        Generate content (passage, transcript, vocab list, or lesson).

        Parameters
        ----------
        task  : str   Task name, e.g. ``"generate"``.
        skill : str   Skill name, e.g. ``"reading"``, ``"listening"``.
        band  : str   CEFR band, e.g. ``"B2"``.
        **kw  :       Extra keyword arguments forwarded to the prompt template.

        Returns
        -------
        dict
            Fixture payload merged with ``{"stub": True}`` in stub mode.
            Live payload (no ``stub`` key) in live mode.

        Raises
        ------
        ApiError
            - ``LLM_UNAVAILABLE`` (502) if the stub has no matching entry.
            - ``LLM_UNAVAILABLE`` (502) if no prompt template is found.
            - ``LLM_UNAVAILABLE`` (502) on network/provider/parse failure.
        """
        if self._config.LLM_MODE == "stub":
            return self._stub_generate(task, skill, band)

        # ---- Live path (Phase 2) ----
        return self._live_generate(task, skill, band, lang=lang, **kw)

    def score(self, task: str, lang: str = "en", **kw) -> dict:
        """
        Score a learner's written or spoken response.

        Parameters
        ----------
        task : str   Task name, e.g. ``"writing"`` or ``"speaking"``.
        **kw :       Extra keyword arguments forwarded to the prompt template
                     (e.g. ``essay=``, ``transcript=``).

        Returns
        -------
        dict
            Fixture payload merged with ``{"stub": True}`` in stub mode.
            Live payload (no ``stub`` key) in live mode.

        Raises
        ------
        ApiError
            - ``LLM_UNAVAILABLE`` (502) if the stub has no matching entry.
            - ``LLM_UNAVAILABLE`` (502) if no prompt template is found.
            - ``LLM_UNAVAILABLE`` (502) on network/provider/parse failure.
        """
        if self._config.LLM_MODE == "stub":
            return self._stub_score(task)

        # ---- Live path (Phase 2) ----
        return self._live_score(task, lang=lang, **kw)

    # ------------------------------------------------------------------
    # Live-mode resolution
    # ------------------------------------------------------------------

    def _live_generate(
        self,
        task: str,
        skill: str | None,
        band: str | None,
        lang: str = "en",
        **kw,
    ) -> dict:
        """Build prompt, call MODEL_GENERATE, return parsed result."""
        from app.services.prompts import GENERATE_PROMPTS, lang_note
        from app.domain.leveling import band_params

        # Pick template: try skill first, fall back to task name
        tmpl = GENERATE_PROMPTS.get(skill) or GENERATE_PROMPTS.get(task)
        if tmpl is None:
            raise ApiError(
                "LLM_UNAVAILABLE",
                f"no generate prompt for {skill!r}",
                502,
            )

        # Build params dict for template formatting. langNote is always present
        # so templates carrying the {langNote} placeholder never KeyError.
        fmt_kw: dict = dict(kw)
        fmt_kw["langNote"] = lang_note(lang)
        if band:
            fmt_kw["band"] = band
            # Include difficulty params if skill is provided
            if skill:
                try:
                    params = band_params(skill, band)
                    fmt_kw["params"] = params
                except Exception:
                    fmt_kw["params"] = {}

        # Format the template; fall back gracefully on missing placeholders
        try:
            system_prompt = tmpl.format(**fmt_kw) + _JSON_ONLY
        except KeyError:
            # Template has placeholders we don't have — append info as user msg
            system_prompt = tmpl + _JSON_ONLY

        user_msg = f"Band/level: {band or 'B2'}."
        if kw:
            extras = "; ".join(f"{k}={v}" for k, v in kw.items())
            user_msg += f" {extras}"

        return self._chat(self._config.MODEL_GENERATE, system=system_prompt, user=user_msg)

    def _live_score(self, task: str, lang: str = "en", **kw) -> dict:
        """Build scoring prompt, call MODEL_SCORE, return parsed result."""
        from app.services.prompts import SCORE_PROMPTS, lang_note

        tmpl = SCORE_PROMPTS.get(task)
        if tmpl is None:
            raise ApiError(
                "LLM_UNAVAILABLE",
                f"no score prompt for {task!r}",
                502,
            )

        # langNote always present so templates with {langNote} never KeyError.
        kw["langNote"] = lang_note(lang)

        # Format the template with provided kwargs
        # str.format(**kw) only fails if a placeholder in the template is MISSING
        # (extra keys are silently ignored), so we guard only for missing keys.
        try:
            system_prompt = tmpl.format(**kw) + _JSON_ONLY
            user_msg = "Please evaluate and return the JSON result as instructed."
        except KeyError as missing:
            # A required placeholder is absent — append kwargs as context instead
            system_prompt = tmpl + _JSON_ONLY
            user_msg = (
                "Context: "
                + "; ".join(f"{k}={v}" for k, v in kw.items())
                + "\nPlease evaluate and return the JSON result as instructed."
            )

        return self._chat(self._config.MODEL_SCORE, system=system_prompt, user=user_msg)

    # ------------------------------------------------------------------
    # Stub-mode resolution
    # ------------------------------------------------------------------

    def _stub_generate(self, task: str, skill: str | None, band: str | None) -> dict:
        """
        Look up a generate stub.

        Key strategy:
          1. Exact key: ``"{task}:{skill}:{band}"``
          2. Band fallback: first key matching ``"{task}:{skill}:"``
          3. Raise ApiError if nothing found.
        """
        stubs = self._stubs()
        exact_key = f"{task}:{skill}:{band}"

        if exact_key in stubs:
            payload = self._sanitise(dict(stubs[exact_key]))
            payload["stub"] = True
            return payload

        # Fallback: any entry with matching task+skill regardless of band
        prefix = f"{task}:{skill}:"
        for key, value in stubs.items():
            if key.startswith(prefix):
                payload = self._sanitise(dict(value))
                payload["stub"] = True
                return payload

        raise ApiError(
            "LLM_UNAVAILABLE",
            f"no stub for {exact_key}",
            502,
        )

    def _stub_score(self, task: str) -> dict:
        """
        Look up a score stub.

        Key: ``"score:{task}"``
        Raise ApiError if not found.
        """
        stubs = self._stubs()
        key = f"score:{task}"

        if key in stubs:
            payload = self._sanitise(dict(stubs[key]))
            payload["stub"] = True
            return payload

        raise ApiError(
            "LLM_UNAVAILABLE",
            f"no stub for {key}",
            502,
        )
