# WS12 — Privacy & Compliance Status Register

Task-by-task mapping of `docs/production-readiness/12_PRIVACY_COMPLIANCE.md`
to implementation evidence, with owner workstreams and open gaps. Update at
each release wave. Not legal advice; see the doc's own caveat.

| Task | Status | Evidence / location | Gaps |
|---|---|---|---|
| WS12-01 Data inventory & classification | **COVERED (split)** | Ownership/lifecycle/scoping: `docs/production-readiness/DATA_OWNERSHIP_INVENTORY.md` (WS04-01, updated per migration). Sensitivity/processor/retention view: `PRIVACY_NOTICE.md` §2/§4 + `VENDOR_REGISTER.md` | keep both tables in sync when WS20+ product fields land (destination, deadlines, previous score → inventory "Future ARUORA data classes") |
| WS12-02 Data minimization | **VERIFIED in code** | Payload builders send task fields only — no email/name/user_id (WS05-01; PROVIDER_PRIVACY_REVIEW §4 requires recorded request dump at UAT). Profile fields optional. Analytics reject PII-shaped values (WS21) | UAT-time recorded request dump (WS05-07 gate) |
| WS12-03 Privacy notice | **DRAFTED** | Canonical: `PRIVACY_NOTICE.md`; public page: `web/public/legal/privacy.html`; linked from `index.html` footer | [OPERATOR CONTACT] placeholders + legal sign-off before public signup |
| WS12-04 Terms + AI disclaimer | **DRAFTED** | Canonical: `TERMS_OF_SERVICE.md`; public page: `web/public/legal/terms.html` | legal sign-off; in-app re-consent UX at acceptance-capture time (WS23) |
| WS12-05 IELTS trademark/copyright | **PARTIAL — audit clean so far** | Automated scan (2026-08-27): no `ielts.org`/logo/Cambridge/BritishCouncil/IDP references in `api/app`, `web/src`, `fixtures/`. Product naming = ARUORA IELTS with disclaimer framing ("preparation focus", no official-looking identity). Descriptor rubrics are original summaries, not long verbatim official text | final naming/copy legal approval; re-scan at each release; permission records if any official material is ever licensed |
| WS12-05B Logs/analytics/AI-payload minimization | **VERIFIED in code** | Mailer: outcome + `recipient_ref` only, body/links never logged (`services/mailer.py` logging contract). ASR: model/status logs only (`services/asr.py`). Unhandled errors log path/method only (`errors.py`). Analytics events content-free by construction (WS21). No request-body logging anywhere (`grep logging/logger/print` audit 2026-08-27) | WS10 must keep this policy when vendors are added (`VENDOR_REGISTER.md` rule 2); incident payload-capture mode defined in `INCIDENT_RESPONSE.md` |
| WS12-06 Data-subject requests | **COVERED (engineering)** | Authenticated export `/api/account/export` (excludes password_hash/google_sub), profile correction, deletion `/api/account` with schema CASCADE (no orphans — migration-tested), admin actions audited (`admin_audit`), IP hashed everywhere | external-blob deletion N/A today (audio ephemeral, no object store); SLA statement to fill with legal ([PRIVACY@CONTACT]) |
| WS12-07 Audio & biometric caution | **VERIFIED in design** | `services/audio_store.py`: private non-served dir, unguessable keys, TTL ≤ 30 min purge, worker-only access, **no HTTP read interface**; deleted on immediate processing failure (routes/speaking.py). No speaker ID/voiceprint/matching anywhere | keep no-biometric stance; separate legal review required before ANY voice-identity feature |
| WS12-08 Children/minors | **POLICY (adult-only beta)** | Terms §3 adult-only eligibility (self-declaration) | enforcement: registration age attestation (server-validated flag) — needs coordinated WS03 change + test updates; minor-consent flow deferred until product decision |
| WS12-09 Vendor register / DPAs | **DRAFTED** | `VENDOR_REGISTER.md` (all rows for current stack; DPA statuses PENDING) | complete before first public wave (gates via WS05-07 + WS16) |
| WS12-10 Breach response | **READY (runbook)** | `docs/runbooks/INCIDENT_RESPONSE.md`: T0 clock rules (3×24 h / 72 h), roles, exposure-assessment data map keyed to real tables | fill role owners; tabletop rehearsal per release wave |
| WS12-11 RAG source/privacy governance | **GATED (no RAG active)** | WS28 READY_FOR_DESIGN; no vector index/shared knowledge store exists yet. Requirements inherited by WS28 via `28_AUTO_RAG_KNOWLEDGE_PIPELINE.md` (namespace/ACL-pre-filter/provenance/no learner state in indexes) | none while inactive — revisit at WS28 design acceptance |

## Exit criteria snapshot (12 §Exit criteria)

- [x] Data inventory + retention policy documented (WS04 inventory + notice §4)
- [x] Raw audio minimized (ephemeral by design, WS06)
- [x] Export/delete end-to-end (WS04/WS12-06)
- [x] Vendor AI processing disclosed/reviewed (register + WS05-07 gate) — sign-off pending
- [ ] Public branding/IP final legal approval (WS12-05)
- [ ] Incident response roles filled + one tabletop done (WS12-10)

## Change log

| Date | Note |
|---|---|
| 2026-08-27 | Initial register created; code audits run (logging, brand scan, audio store review) |
