# 16 — Public Release Gates

Use this file as a **go/no-go** checklist. “Mostly done” is not a pass for MUST items.

## Gate A — Public Beta MUST
### Product/legal positioning
- [ ] Public name/domain/copy reviewed for IELTS trademark confusion.
- [ ] No IELTS logo or protected material shipped without permission/licence.
- [ ] AI results visibly labeled estimated/practice/non-official.
- [ ] Privacy notice and Terms published.
- [ ] Target user age/minor policy defined.

### Scoring integrity
- [ ] `.25`/`.75` official overall rounding regression tests pass.
- [ ] CEFR shown as approximate alignment, not exact equivalence.
- [ ] Transcript-only Speaking does not pretend pronunciation is fully assessed.
- [ ] Model/prompt/rubric/scoring versions stored with AI attempts.

### Tenant security
- [ ] All persistent learner resources have unambiguous `user_id` ownership.
- [ ] BOLA cross-user matrix passes for every ID endpoint.
- [ ] Account deletion succeeds with all owned child records and blobs/jobs policy.
- [ ] Admin endpoints have explicit function-level authorization.

### Identity/request security
- [ ] Sessions are revocable server-side.
- [ ] Session rotates on login/reset/privilege changes.
- [ ] Unsafe cookie-authenticated methods have CSRF protection.
- [ ] Password reset token is single-use/expiring.
- [ ] Login/register/recovery distributed rate limits work across replicas.
- [ ] Production cookie flags are `Secure`, `HttpOnly`, appropriate `SameSite`.
- [ ] Trusted Host/proxy configuration tested.

### AI/resource security
- [ ] Auto-RAG source registry is allowlist-first; no unrestricted crawler is enabled.
- [ ] RAG namespace/authorization filters run before retrieval and cross-user retrieval tests are green.
- [ ] Retrieved chunks are treated as untrusted data and indirect prompt-injection regression tests pass.
- [ ] Active RAG sources have provenance/trust/allowed-use/license metadata and staged activation.
- [ ] RAG retrieval benchmark and rollback/disable path exist.
- [ ] Normal Task Pool serving does not invoke RAG, and dynamic RAG is not part of calibrated scoring by default.
- [ ] Learner content is never interpolated into LLM system messages.
- [ ] Every LLM response validated by server schema.
- [ ] Per-user AI quotas and global emergency spend stop exist.
- [ ] Standard practice is pool-first; Next/Try another does not normally cause a fresh LLM generation.
- [ ] Pool serves, fresh generation, scoring, Aura, retries/cache hits, and ASR are separately accountable.
- [ ] Provider token/cost metadata is persisted in an auditable usage ledger where available.
- [ ] Shared generated tasks pass lifecycle validation/deduplication before ACTIVE.
- [ ] Per-user task exposure/anti-repeat logic and pool-depletion behavior are tested.
- [ ] System-owned pool replenishment does not consume an arbitrary learner's personal generation entitlement.
- [ ] Heavy jobs are idempotent.
- [ ] ASR cannot starve web workers.
- [ ] Request/upload/token/output bounds enforced.

### Data/recovery
- [ ] PostgreSQL 18 volume/storage config correct for chosen deployment.
- [ ] Alembic upgrade tested on PostgreSQL.
- [ ] Off-host encrypted backup enabled.
- [ ] At least one restore drill completed successfully.
- [ ] DB/Redis not publicly reachable.

### Operations
- [ ] Production structured logs exclude secrets/raw learner content.
- [ ] Error/latency/DB/Redis/queue/AI-cost dashboards exist.
- [ ] Alerts for DB, Redis/session impact, 5xx, queue age, backup failure, spend spike.
- [ ] Deployment and rollback runbook exercised in staging.

### CI/CD
- [ ] API tests, web tests/typecheck/build required.
- [ ] PostgreSQL migration CI required.
- [ ] Critical Playwright E2E required.
- [ ] repository secret scanning/push protection enabled where available.
- [ ] dependency/code/container scans run and findings triaged.
- [ ] production image/tag traceable to commit SHA.

### ARUORA product readiness
- [ ] Product is branded ARUORA/ARUORA IELTS according to approved identity or intentionally remains in a documented transitional state.
- [ ] Home/result flows prioritize Destination, Target, Current Estimate/Gap, and Next Action over gamification.
- [ ] No unsupported Readiness percentage is presented as scientific precision.
- [ ] Aura follows approved non-authoritative, evidence-aware language.
- [ ] Cohort/acquisition and meaningful-learning telemetry is reliable before external UAT.
- [ ] Study Pool is either disabled or explicit opt-in with privacy controls.
- [ ] WhatsApp is not required for the core learning journey.

### Product validation before cohort expansion
- [ ] Internal QA P0/P1 = 0 before lecturer UAT.
- [ ] Lecturer UAT results are not presented as organic PMF evidence.
- [ ] LinkedIn/voluntary market cohort is measured separately.
- [ ] Founding Beta expansion has an explicit evidence memo using `22_UAT_FOUNDING_BETA_RELEASE_PLAN.md`.

## Gate B — GA / broader production SHOULD→MUST
- [ ] Managed PostgreSQL with PITR or equivalent tested recovery.
- [ ] Production-standard RPO/RTO measured and approved.
- [ ] Admin MFA mandatory.
- [ ] Independent security review/penetration test completed where feasible.
- [ ] Full Writing calibration thresholds defined and met on licensed/consented human-rated set.
- [ ] Any full Speaking estimate validated with audio evidence and human ratings.
- [ ] Vendor/subprocessor register and required DPAs/contracts complete.
- [ ] Privacy request operational SLA tested.
- [ ] WCAG 2.2 AA manual + automated critical-journey review completed.
- [ ] SBOM and artifact provenance/attestation produced for release artifacts.
- [ ] Capacity/load test against realistic traffic model completed.
- [ ] Incident/breach tabletop exercise completed.

## Automatic NO-GO conditions
- unauthorized RAG namespace/tenant retrieval;
- unreviewed/unclassified source auto-activated into production RAG;
Do not launch or continue rollout if any is known:
- cross-user data access possible;
- scoring rounding known wrong;
- auth/session bypass or CSRF on sensitive operations;
- reset token reusable;
- production DB has no restorable backup;
- unbounded paid LLM/ASR consumption;
- standard pooled practice accidentally performs a fresh LLM generation on each Next/Try another request;
- AI spend cannot be reconciled by operation/model/provider because only a raw generation count exists;
- raw secret in repository/browser bundle/log;
- LLM output bypasses server validation;
- public branding materially implies official IELTS ownership/endorsement without permission;
- a “full” Speaking score includes pronunciation with no audio evidence and no explicit limitation.

## Accepted-risk process
A P2/P3 issue may be accepted only with:
- owner;
- rationale;
- impact;
- compensating control;
- expiry/review date;
- tracking issue.

P0/P1 items that affect tenant isolation, auth bypass, data loss, official scoring correctness, or uncontrolled spend are not normal beta risk acceptances.
