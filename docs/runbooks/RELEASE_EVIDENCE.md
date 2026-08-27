# Release Evidence Bundle — ARUORA IELTS (TV/14 §Release evidence bundle)

One bundle per release candidate. The release decision must be reproducible
from this evidence alone — not from intuition or a screenshot walkthrough.
Copy the template below for each RC and store under
`docs/validation/releases/<date>-<sha>.md` (or the release tracker issue).

Collection helper (staging host, optional):

```bash
tests/load/../../ops/collect_release_evidence.sh > release-evidence.txt
```

*(helper to be added by WS11/WS15 with the deployment pipeline; the template
is the contract)*

---

## Template

```markdown
# Release candidate — <DATE>

- Build: git SHA <sha> · api image digest <sha256:...> · web image digest <sha256:...>
- Environment: <staging host / compose profile> · deployed by <operator>
- Migration revision at deploy: <alembic head id> (upgrade path tested: empty→head, prev→head)

## CI results (links)
- API + web CI: <run URL> (pass/fail)
- Migrations (PostgreSQL 18) job: <run URL>
- CodeQL / security scans: <run URL>

## Test summary
- pytest: <passed/failed/skipped> (command: cd api && python -m pytest -q)
- web: tsc clean? <yes/no> · vitest <passed/failed> · build <ok/fail>
- E2E (Playwright journey): <result, link>

## Load test (TV-07)
- Scenario set: <files> · concurrency: <VUs/rate> · duration: <duration>
- P50/P95/P99 non-AI: <...> · error rate: <...> · verdict: <PASS/NO-GO>
- Log entry: docs/validation/LOAD_TEST_LOG.md#<row>

## Resilience drills (TV-08)
- Drills run this cycle: <DR-1..DR-7> · findings: <link/log>

## Security (TV-09)
- Secret scan: <pass> · CodeQL: <pass/alerts triaged>
- Manual DAST/pen-test items covered: <list or "scheduled pre-GA">

## AI scoring calibration (TV-10)
- Calibration set: <frozen set id/version> · model+prompt version: <ids>
- Thresholds (set BEFORE eval): MAE ≤ <x>, ±0.5 agreement ≥ <x>
- Results: writing <...> · speaking text-only <...> · audio-supported <...>

## Backup / DR (TV-06)
- Newest backup age at release: <hours> (freshness ≤ 26 h)
- Last restore drill: <date> · RPO/RTO: <...> (docs/runbooks/DATABASE_BACKUP_RESTORE.md)

## Product evidence (TV-12/13/14 as applicable)
- Cohort/funnel integrity checks: <result>
- Brand/claim regression: <result or WS23 status>
- UAT protocol artifacts for this cohort: <link per 22 §TV-14>

## Known accepted risks (this release)
- <risk 1 — owner, mitigation>
- <risk 2 — owner, mitigation>

## Decision
- [ ] GO  — approver: <name/date>
- [ ] NO-GO — reason: <...>
```
