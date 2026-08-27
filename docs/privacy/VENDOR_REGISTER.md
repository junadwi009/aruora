# ARUORA IELTS — Vendor / Subprocessor Register (WS12-09)

Living register. Update **per release wave**; the provider technical review
lives in `docs/production-readiness/PROVIDER_PRIVACY_REVIEW.md` (WS05-07) and
gates live deployment. The published public notice summarises only the rows
marked `public: yes`.

Legend: PD = personal data; LC = learner content (essays/transcripts/generated
task inputs); A = raw audio.

| Vendor / role | Service | Data categories | Region | Retention | Training on our data? | Transfer basis / notes | DPA status | Public |
|---|---|---|---|---|---|---|---|---|
| [HOSTING PROVIDER] | app/db/redis hosting | all hosted data | [region] | per contract | n/a | [TODO at first deployment] | [PENDING] | yes |
| OpenRouter, Inc. | LLM router | LC (task payloads only — no email/name/user_id) | US (+ upstream routes) | per router account settings; strictest opt-outs to be enabled + recorded at release | disabled to the extent offered (record at release) | SCC-equivalent via DPA where applicable; cross-border disclosure in notice | [PENDING — before public wave] | yes |
| Anthropic (upstream, via OpenRouter) | `MODEL_GENERATE` | LC | [record at release] | [PENDING LIVE CHECK] | [PENDING] | via OpenRouter routing | covered via router DPA where offered | yes |
| DeepSeek (upstream, via OpenRouter) | `MODEL_SCORE` | LC | [record at release] | [PENDING LIVE CHECK] | [PENDING] | via OpenRouter routing | covered via router DPA where offered | yes |
| local faster-whisper (self-hosted) | speech-to-text | A | on-host | ephemeral ≤ 30 min (WS06-07) | no — no data leaves host | n/a | n/a (no third party) | yes |
| [SMTP PROVIDER] | transactional email (reset/verify/reminders) | email address, message content | [region] | [PENDING selection] | [PENDING] | [PENDING] | [PENDING] | yes |
| [OBSERVABILITY VENDOR] | logs/metrics/traces (if adopted, WS10) | operational telemetry only — **never** learner payloads (WS12-05B) | [region] | [PENDING] | [PENDING] | [PENDING] | [PENDING] | no |
| [ANALYTICS/PRODUCT VENDOR] | product analytics (if adopted beyond self-hosted DB) | content-free events only | [region] | [PENDING] | [PENDING] | [PENDING] | [PENDING] | no |

## Rules

1. A vendor that would receive LC/A may not be added to the live path before
   its row is completed **and** the WS05-07 release-time verification passes.
2. Observability/error-reporting vendors must not ingest learner payloads
   (WS12-05B); any payload-capture capability requires an explicit
   short-lived incident mode (see `docs/runbooks/INCIDENT_RESPONSE.md`).
3. The register is reviewed at every release wave alongside the privacy
   notice; removal of a vendor does not remove its historical row — mark it
   `RETIRED <date>`.
4. Deletion-on-termination: where the vendor stores PD, record deletion
   evidence at contract end.
