# 11 — CI/CD and Software Supply-Chain Security

## Goal
Turn the existing unit/build CI into a release gate that tests PostgreSQL behavior, browser journeys, migrations, dependencies, containers, and deployment artifacts.

## Current strength
The reviewed workflow already runs API pytest, TypeScript checking, Vitest, production build, and a browser-bundle secret check. Preserve these checks.

## Gaps
- Playwright E2E is local-only.
- secret scan is intentionally focused on the web bundle rather than repository history/source.
- no PostgreSQL migration job.
- no dependency/code/container security scan.
- no staging deployment gate/rollback verification.

## WS11 ownership
Expected areas:
- `.github/workflows/*`
- dependency update config
- container build metadata
- test scripts
- staging/prod deployment workflows

## Task WS11-01 — Required CI jobs
PR gate should include:
1. API unit/integration tests.
2. Web typecheck/unit/build.
3. PostgreSQL migration integration test.
4. Playwright E2E against built stack.
5. lint/format checks once configured.
6. LLM stub contract/adversarial tests (no live provider spend on every PR).
7. secret scanning.
8. dependency vulnerability scanning.
9. static/code scanning.
10. container/image scan.

Run slower full calibration/load suites on scheduled/manual/release workflows rather than every small PR.

## Task WS11-02 — Real PostgreSQL in CI
Use a service container or Compose to run the API integration/migration tests against the production major version.

Required:
- fresh DB → Alembic head;
- seed/test data;
- representative route tests;
- account cascade deletion;
- ownership constraints;
- production SQL types/behavior.

Keep SQLite fast unit tests if useful, but do not treat them as full DB evidence.

## Task WS11-03 — Playwright in CI
Run at least the critical journey:
- register/verify fixture or controlled auth;
- login;
- onboarding/placement stub path;
- writing submission stub;
- progress/history;
- logout/session expiry;
- account delete in isolated test data;
- mobile viewport smoke.

Capture screenshots/traces only as CI artifacts; never run E2E with real production user data.

## Task WS11-04 — Secrets
Enable GitHub Secret Protection features available to the public repository, including secret scanning/push protection where possible.

Keep the existing “no secret in browser bundle” check as a separate defense.

Also scan source/history with an appropriate tool/policy. Never intentionally commit fake strings that match live credential formats without allow-listing test fixtures safely.

## Task WS11-05 — Code/dependency/container scanning
Recommended controls:
- CodeQL for supported languages;
- Dependabot or equivalent update PRs;
- Python dependency vulnerability audit;
- npm dependency audit/advisory scan;
- container image scan (e.g. Trivy/Grype class tool);
- base-image update policy.

A vulnerability finding needs severity/impact triage; do not blindly merge breaking major updates.

## Task WS11-06 — Pin build inputs
For production workflows:
- lock Python/Node dependencies reproducibly (introduce a lock/constraints strategy for Python rather than only loose runtime installs from mutable ecosystem state);
- keep `package-lock.json` with `npm ci`;
- pin Docker major/base intentionally;
- pin critical GitHub Actions to trusted versions, and for higher assurance pin third-party actions to full commit SHAs.

## Task WS11-07 — SBOM and provenance
For release images/artifacts:
- produce an SBOM;
- record git SHA/image digest;
- generate GitHub artifact attestations/provenance where applicable;
- deploy by immutable digest/tag derived from commit, not `latest`.

GitHub documents artifact attestations as a way to establish build provenance and support SLSA-oriented assurance.

## Task WS11-08 — Branch/release protection
Protect the release branch:
- PR required;
- required status checks;
- no force push;
- code-owner/review policy when team size allows;
- production environment requires explicit approval;
- secrets stored in environment/secret manager, not workflow YAML.

For a solo developer, still use PR/self-review checkpoints for production-critical migrations and deployment manifests.

## Task WS11-09 — Staging deploy
On merge/release candidate:
1. build immutable images;
2. deploy to staging;
3. run migrations;
4. run smoke/E2E/security-header checks;
5. run selected live-provider smoke with strict cost cap if desired;
6. record artifact digests;
7. require approval for production.

## Task WS11-10 — Production workflow
- preflight backup freshness;
- database migration plan classified safe/risky;
- deploy immutable artifact;
- readiness check;
- smoke test;
- monitor error/latency during rollout;
- rollback app automatically/manually on threshold breach;
- database rollback uses planned forward/backward migration strategy, not blind downgrade.

## Task WS11-09 — Repository and dependency licensing
The reviewed public GitHub repository currently reports no repository license metadata. Before treating the codebase as a public product or accepting outside contributions, make the intended legal posture explicit.

Required decisions/checks:
- choose and add the repository license if open-source distribution is intended, or document that source availability does not grant reuse rights if that is the intended posture;
- inventory runtime/build dependency licenses and flag incompatible/restrictive licenses in CI or release review;
- maintain third-party notices where required;
- do not copy IELTS copyrighted test material or rubric text into fixtures/prompts merely because it is publicly viewable;
- define contribution terms/CLA/DCO only if external contributions will be accepted.

This is separate from IELTS trademark/copyright review in `12_PRIVACY_COMPLIANCE.md`.

## ARUORA product/brand CI checks

Add lightweight automated checks where practical:
- production build contains approved product naming and no legacy secret/API-key values;
- route/E2E coverage includes destination → placement → result → Journey flow;
- axe/accessibility checks on critical ARUORA screens;
- design token file parses and generated CSS/theme artifacts stay synchronized if code generation is used;
- score/disclaimer copy regression tests for critical result surfaces.

Do not turn brand copy into brittle snapshot tests for every sentence; protect only non-negotiable claims and critical hierarchy.

## Exit criteria
A merge cannot bypass unit/build/migration/E2E/security checks, release artifacts are immutable and traceable to source, staging is exercised before production, and repository/provider secrets have automated leak protection.
