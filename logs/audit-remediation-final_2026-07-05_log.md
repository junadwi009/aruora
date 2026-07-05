# Audit remediation — final review & verification (FASE 5) — 2026-07-05

End-to-end security + a11y audit of IELTS Coach v3 and remediation of all findings,
executed in phases with owner approval at each gate. This log closes the engagement.

## Batches delivered (all committed, none pushed/merged)
| Batch | Findings | Commit(s) |
|---|---|---|
| Fase 0 docs | README v3 drift (D1–D5); CLAUDE.md refreshed (git-ignored) | `a1a396c` |
| 1 — LLM/ASR auth | H1 roleplay, M1 transcribe, M2 evaluate ordering | `ba98aa2` |
| 2 — a11y | H2 contrast, H3 dialog focus, M3 radio arrow-keys | `f5ed993` |
| 3 — cleanups | M4 card button, L1 i18n, L2 endonym, L3 dead code, L4 except, L5 google email_verified | `9a1ba2c` |
| hash logs | — | `f11f0d8` |

(Prior session, context for reviewers: `40e537c` first security hardening —
SESSION_SECRET guard, cookie flags, rate limiter, headers, generate-endpoint auth.)

## Verification (all green)
- `cd api && .venv/Scripts/python -m pytest -q` → **177 passed**.
- `cd web && npm test` → **66 passed**; `npx tsc --noEmit` → clean.
- `bash tests/secret_scan.sh` → clean (no key in `web/dist`).
- Docker end-to-end (live-tolerant smoke): stack builds & becomes healthy, `/api/health`
  `ok:true`, `placement/start` + `tips` OK, security headers present, and
  `POST /api/speaking/roleplay` unauthenticated → **401**. Tear-down clean.

## Whole-diff review verdict
- **Security:** no new issues introduced. Auth guards are additive; Google email is
  now only trusted when verified; ASR/LLM endpoints all require a session and are
  rate-limited; no secrets in code or bundle. SQLi/IDOR remain absent (ORM + ownership
  scoping unchanged).
- **Quality:** diffs small and reviewable (~+419/−38 across 18 files this engagement);
  behavioural changes are test-pinned; dead code removed; i18n coverage complete.

## Residual risk / accepted
- **Register enumeration** (L5b): left as-is by decision (UX affordance; rate-limited 5/min).
- **Live keys in `.env`**: owner deferred rotation (local install). Rotate + vault the
  OpenRouter key and remove the unused mis-spelled Google secret before any public deploy.
- **Rate limiter is in-process** (per gunicorn worker) — front with Redis for exact
  global limits on multi-worker/multi-node.
- Contrast verified by computation; a full axe-core sweep is an optional follow-up.

## Manual steps for the owner (before public deploy)
1. Set `COOKIE_SECURE=1` once served over HTTPS.
2. Rotate the OpenRouter key; move secrets to a secret manager.
3. `LLM_MODE=live` requires a valid `OPENROUTER_API_KEY`; the stock `tests/smoke.sh`
   asserts `stub` — run it with `LLM_MODE=stub` or use the live-tolerant checks above.
4. Nothing was merged or deployed — that remains the owner's call.

## Commit
- Docs/logs commit for hashes: this file + cleanups-log hash. (recorded on commit)
