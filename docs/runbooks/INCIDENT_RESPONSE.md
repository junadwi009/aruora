# Runbook — ARUORA IELTS Security Incident & Breach Response (WS12-10)

Companion runbooks: `DATABASE_BACKUP_RESTORE.md` (recovery), privacy policy
pack under `docs/privacy/`. This runbook is engineering-owned; legal wording
and jurisdiction calls belong to legal counsel.

## 0. Clock rules (read before anything else)

- Indonesia PDP Law (UU 27/2022) Art. 46: **written notification no later than
  3×24 hours** to the data subject and the institution, for failures to
  protect personal data.
- GDPR (if/when applicable): **72 h** to the supervisory authority where
  required.
- The clock starts at **T0 = when the incident is classified as a suspected
  personal-data breach** — not when the root cause is found. Start the timer
  and the log immediately; assessment happens in parallel, not first.
- If in doubt whether something qualifies → treat it as a breach and start
  the clock. False alarms are cheap; late notification is not.

## 1. Roles (small-team mode)

| Role | Default owner | Duty |
|---|---|---|
| Incident Lead | [ON-CALL OWNER] | owns T0, triage, comms cadence |
| Legal/Compliance | [OWNER] | notification duty call, regulator/subject notices |
| Engineering Lead | [OWNER] | containment, evidence preservation, fix |
| Comms | [OWNER] | user-facing message drafts |

## 2. Severity classification (T0 + 1 h)

| Class | Examples | Clock |
|---|---|---|
| S1 suspected PD breach | DB dump/exposure, credential store leak, provider-side learner-content exposure, audio exposure | 3×24 h clock starts NOW |
| S2 security event without confirmed PD impact | XSS/CSRF patched pre-exploit, targeted abuse contained | no statutory clock; log + review |
| S3 operational | provider outage, queue backlog | status page only |

## 3. First hour (S1)

1. Open the incident log (timestamped, append-only, no learner content in it).
2. Contain: rotate exposed secrets (deployment secret store), revoke sessions
   (`auth_session` mass revoke for affected users), block the vector, snapshot
   volumes for forensics **before** destructive fixes when feasible.
3. Preserve evidence: logs (outcome-only), request IDs, ledger/audit rows.
4. Estimate exposure using data we can actually query:
   affected accounts (created_at/email-domain ranges), row counts by table
   (`DATA_OWNERSHIP_INVENTORY.md` classes), time window.
5. Notify Legal/Compliance role — even partially-informed, immediately.

## 4. Notification data (3×24 h target)

The notice to subjects/institution must be able to state:

- what data was exposed (map to inventory classes: account data / learning
  content / audio / security metadata — audio is high-impact, say so);
- when and how (window, vector class);
- affected-user estimate + how individuals can check/protect themselves;
- containment/recovery status and next steps;
- contact for follow-up.

Draft templates live with the comms role; the runbook guarantees the FACTS
above can be produced within hours from DB queries + audit rows.

## 5. Data-source map for exposure assessment

| Question | Source |
|---|---|
| Which accounts affected? | `user_profile` (created_at/email), `auth_session.ip_hash/device` |
| Learner content exposed? | `attempts` (essays/transcripts), `lessons`, `cards`, export blobs |
| Audio exposed? | audio store TTL audit (≤ 30 min by design — confirm store contents) |
| Provider-side exposure? | `ai_usage_ledger` (provider/model/status/time), provider incident notices |
| What actions were taken? | `admin_audit` (append-only), deployment secret rotation logs |
| Cost/abuse anomalies? | `ai_usage_ledger` aggregates per `cost_center` |

## 6. Post-incident (≤ 7 days)

- Blameless post-mortem: timeline, root cause, detection gap, fix owner+date.
- Update this runbook + detection (WS10 hooks) + vendor register rows if a
  sub-processor was involved (its incident-notification terms apply).
- Record the drill/real-incident one-liner in the restore-drill log if a
  restore was part of recovery.

## 7. Rehearsal

Tabletop once per release wave before public scale: walk a S1 (leaked DB
backup) end-to-end; verify the 3×24 h notification data can actually be
produced. Log date + findings below.

| Date | Scenario | Gaps found | Fixed |
|---|---|---|---|
