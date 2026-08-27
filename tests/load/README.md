# Load Tests (TV-07) — ARUORA IELTS

k6 scenario pack for the five TV-07 initial scenarios. **Staging only** —
run against a production-like `docker-compose.prod.yml` stack with
`LLM_MODE=stub` (no provider spend, deterministic latency) unless a scenario
explicitly targets live AI behaviour.

Install k6: https://k6.io/docs/get-started/installation/

## Scenarios

| File | TV-07 scenario | What it proves |
|---|---|---|
| `scenarios/login_profile_history.js` | 1. login/profile/history mix | non-AI P95 < 500 ms; session writes hold up |
| `scenarios/writing_jobs.js` | 2. concurrent writing submissions under per-user limits | per-user AI concurrency + queue backpressure activate before starvation |
| `scenarios/asr_burst.js` | 3. ASR queue burst | ASR stays low-concurrency; queue depth bounded (`QUEUE_MAX_DEPTH`) |
| `scenarios/rate_limit_contention.js` | 4. Redis rate-limit contention | shared limiter: 429s are exact across replicas, no limiter unwind |
| `scenarios/progress_realistic_rows.js` | 5. progress/history with realistic row counts | indexed history queries hold P95 with seeded volumes |

## Running

```bash
# 1. Bring up the production-like stack (staging host)
cp .env.example .env   # LLM_MODE=stub, set POSTGRES_PASSWORD
docker compose -f docker-compose.prod.yml up -d --build

# 2. Seed users once (each VU logs in as its own seeded user):
BASE_URL=http://localhost:80 k6 run tests/load/seed_users.js   # N=50 by default

# 3. Run a scenario (env: BASE_URL, VUS, DURATION):
BASE_URL=http://localhost:80 VUS=20 DURATION=2m \
  k6 run tests/load/scenarios/login_profile_history.js
```

## Provisional beta acceptance thresholds (set BEFORE the run — 14 §TV-07)

- non-AI endpoints P95 **< 500 ms**, P99 < 1.5 s, at the agreed expected
  concurrency (record the number in the release evidence bundle);
- **zero** cross-user data leakage (scenario 1 asserts isolation responses);
- no uncontrolled 5xx growth (error rate < 1% for non-AI routes);
- queue backpressure: submission 429/503 (`RATE_LIMITED`/backpressure)
  activates **before** API worker starvation (no timeout cascade);
- DB connections stay under the configured budget
  (`processes × (DB_POOL_SIZE + DB_MAX_OVERFLOW) < max_connections − headroom`);
- cost/quota counters exact across replicas: post-run ledger sum equals the
  injected stub-call count (scenario 2 prints the check query).

If a threshold fails, the result is a NO-GO for the release candidate until
re-run green at the same concurrency. Do not move thresholds after a run.

## Recording results

Append one row per run to `docs/validation/LOAD_TEST_LOG.md`:
date, build SHA, scenario, VUs, duration, P50/P95/P99, error rate, queue
depth max, DB connection peak, verdict. Link the run from the release
evidence bundle (`docs/runbooks/RELEASE_EVIDENCE.md`).
