# UAT repair validation boundary — PR 18

Implementation checkpoint: `8a107ce5d813690cfc1bd4b0fd01f4afcae4823e`.
This checkpoint is not a production release. Main and deployed data remain unchanged.

## Verification policy

Inspect the exact current PR head's CI, Security, CodeQL, UAT browser regressions and Jobs integration results. Results from an earlier SHA do not close new changes.

The Jobs integration workflow exercises real PostgreSQL, Redis and a separate Celery process using synthetic accounts and stub inference. It tests queued submission, normal completion, duplicate delivery, interrupted publication recovery and concurrent database claims. It does not certify nginx/TLS, live provider billing, email delivery, Google sign-in, real-device UX, backup/restore or deployed images.

The browser workflow exercises the React application with synthetic intercepted API responses, including recovery of a queued evaluation after reload. It is not full-stack browser acceptance.

## Dependency evidence

Candidate frontend dependency resolution and tests passed in run `37278450637`. The resulting lockfile SHA-256 is `7115428eb19bea3d2d39f41265269eb7cf53ec5be1ea2cee8fd9fa1fdd99cd09`. Its npm audit report contained zero findings. This must be rechecked by normal Security CI on the committed lockfile.

Python's NLTK advisory `GHSA-8mgp-746c-j5xp` / `PYSEC-2026-3740` remains an unresolved gate; no suppression or fabricated fixed version is used. Upstream lists no patched version at the time checked. Removing/replacing metric dependencies requires measured scoring compatibility; do not silently change scoring merely to make the scanner green.

## Operational constraints

Read `docs/UAT_REPAIR_RUNTIME.md` before attempting an isolated staging deployment. Apply migration `b26c20261005` before starting new workers. Pair the new frontend with the asynchronous API contract. Stop obsolete worker services; never run migrations concurrently with uncontrolled consumers.

Do not automatically replay jobs marked `JOB_OUTCOME_UNCERTAIN`: the provider may have processed a request before the worker lost its result. Idempotency prevents duplicate application execution for ordinary retries, not a universal exactly-once billing guarantee.

No real secrets, learner data, email delivery or paid model calls were used during repair. Temporary transfer workflows and payload files are removed from the branch tip.
