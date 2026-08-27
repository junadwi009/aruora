# Provider / Router Privacy Review — WS05-07 (live-verification gate)

Status: **BLOCKED until a live verification pass is completed and signed off**
immediately before any public deployment wave. Provider terms change; this
review is time-stamped per release, not one-off.

## Who receives learner content today

| Layer | Component | Receives | Notes |
|---|---|---|---|
| API | `app/services/llm.py` → OpenRouter router (`OPENROUTER_BASE_URL`) | writing essays, speaking transcripts, vocab topics, roleplay text, pronunciation recognizer output, lesson focus | Single governed path for ALL model traffic |
| ASR | local faster-whisper (`asr.py`) | raw practice audio | On-device/on-server inference — no third-party call |

Sub-processors that MAY see content when a model is routed through OpenRouter
are whatever upstream providers serve the selected model IDs
(`MODEL_GENERATE`, `MODEL_SCORE`). The currently configured defaults are:
`MODEL_GENERATE=anthropic/claude-haiku-4-5`,
`MODEL_SCORE=deepseek/deepseek-chat-v3.1:free` (check `.env` per deployment).

## Verification checklist (execute at release time)

1. Record the exact date + source URL of the provider policy pages reviewed.
2. Router settings: enable the strictest retention/logging/training opt-outs
   available on the account AND per-request if supported by the SDK header set.
3. For every model ID in active use (including regional/route variants),
   record the upstream provider's training/retention stance in the table below.
4. Confirm no prompts include user identity: current payload builders send
   only task fields (essay/transcript/topic/scenario/history) — no email,
   name, or user_id is ever sent to the provider (verify with a recorded
   request dump during UAT).
5. Note cross-border processing implications of chosen routes/regions in the
   privacy records required by 12_PRIVACY_COMPLIANCE.md.

## Upstream provider table (fill in at verification)

| Model ID (config) | Upstream provider | Policy URL + date seen | Trains on inputs? | Retention window | Zero-retention mode available? |
|---|---|---|---|---|---|
| anthropic/claude-haiku-4-5 | Anthropic via OpenRouter | _PENDING LIVE CHECK_ | _PENDING_ | _PENDING_ | _PENDING_ |
| deepseek/deepseek-chat-v3.1:free | DeepSeek via OpenRouter | _PENDING LIVE CHECK_ | _PENDING_ | _PENDING_ | _PENDING_ |

## Standing engineering guarantees (already enforced in code)

- Learner text enters ONLY through the structured USER-message payload
  builders; system templates contain zero request data (WS05-01).
- Untrusted strings are truncated to config ceilings before transport (WS05-05).
- Calls carry an explicit timeout and output-token ceiling; retries are bounded
  and apply only to transient failures (WS05-06).
- Every response is schema-validated locally before persistence/rendering;
  invalid output never reaches learners or the database (WS05-02).
- Audit metadata (provider/model ids, latency, token counts) is captured per
  call without mixing billing into prompt construction (WS05-08).
