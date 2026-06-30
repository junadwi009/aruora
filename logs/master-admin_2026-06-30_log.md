# master-admin — 2026-06-30

Added a **master-admin** tier (owner-requested: "make me master admin account").
Scope chosen by the owner: **Manage users** (list accounts, global stats, delete a
user + their data, trigger a password-reset email). Designated admin email:
`junadwi009@gmail.com`.

## Design decision — env-only designation (no DB column)
A request is admin **iff the signed-in account's email is in `ADMIN_EMAILS`** (a
comma-separated env var). There is deliberately **no `is_admin` DB column**:

- Admin can't be granted by a DB write, a registration bug, or any in-app path —
  only by deployment config (a Secret / env var). It can't be self-claimed.
- Trivially revocable and auditable (it lives in one env var).
- No schema migration needed → respects the "Alembic owns the schema, no data
  loss" rule established in the previous change.

Privacy: admin manages the **account list** (who exists, usage counts) and can
remove / password-reset a user. It does **not** expose other users' essays,
answers, or feedback.

## What changed

### Backend (`a` commit)
- `api/app/config.py` — `Config.ADMIN_EMAILS` parsed to a lowercased `frozenset`
  via new `_email_set()` (accepts a CSV string or any iterable; tolerant of
  whitespace/empties). Empty by default → admin panel disabled.
- `api/app/routes/admin.py` (NEW) — blueprint, all endpoints gated by
  `_require_admin()` (401 if not signed in, 403 if email not in `ADMIN_EMAILS`):
  - `GET  /api/admin/users` — every registered account + usage counts
  - `GET  /api/admin/stats` — instance totals
  - `DELETE /api/admin/users/<id>` — delete a user + all their rows (reuses
    `repo.delete_account`); **400 if you target your own admin id** (use
    Settings → Data for that), 404 if absent
  - `POST /api/admin/users/<id>/reset-password` — emails a reset link using the
    SAME serializer salt as `/api/account/forgot`, so it's consumable by
    `/api/account/reset`
- `api/app/data/repositories.py` — `list_accounts()` (accounts only, i.e.
  `email IS NOT NULL`, with per-user attempt counts) and `admin_stats()`
  (accounts / profiles / anonymous / attempts / mocks / cards). Imported `func`.
- `api/app/routes/account.py` — `_public()` now returns `isAdmin` (computed from
  `ADMIN_EMAILS`), so every `/account/me|login|register` response tells the
  client whether to show the panel. New `_is_admin()` helper.
- `api/app/__init__.py` — register the `admin` blueprint. (Admin paths sit under
  `/api/`, so the existing passcode + idle-timeout gates already apply.)

### Frontend (`b` commit)
- `web/src/lib/types.ts` — `AccountUser.isAdmin?`, new `AdminUser` / `AdminStats`.
- `web/src/lib/api/client.ts` — `adminUsers / adminStats / adminDeleteUser /
  adminResetUser`.
- `web/src/components/settings/AdminSection.tsx` (NEW) — stats tiles + account
  list; per-row **Send reset link** (key icon) and **Delete user** (trash) with a
  `confirm()` guard; a **YOU** badge on your own row, which hides its delete
  button (you can't delete yourself here). Reloads after a delete.
- `web/src/components/settings/Settings.tsx` — fetch the account once, render
  `<AdminSection selfId={account.id} />` only when `account.isAdmin`.
- `web/src/lib/i18n.tsx` — admin keys (EN + ID).

### Config / docs
- `.env.example` documents `ADMIN_EMAILS` (the file is gitignored in this repo, so
  the canonical doc is this log + the example). The live `.env` sets
  `ADMIN_EMAILS=junadwi009@gmail.com`.

## How to test / verify
- API unit: `cd api && .venv/Scripts/python -m pytest tests/test_admin.py -q`
  → 10 passed. Full api suite **136 passed**.
- Web unit: `cd web && npx vitest run` → **55 passed** (admin.test.tsx: lists
  accounts, self-badge hides self-delete, delete-after-confirm calls the API,
  reset calls the API, Settings shows the panel only for admins). `tsc` clean.
- Live (docker compose up --build): signed in as `junadwi009@gmail.com` →
  `me.isAdmin=true`, `GET /api/admin/users`→200, `/stats`→200; a normal account →
  403; anonymous → 401; admin delete of another user → 200 (gone from list);
  delete-self → 400; reset-password → 200. Verified the panel in Chrome
  (Settings → Master admin): stats + account list + YOU badge + no self-delete.

## Caveats / notes
- The admin account was created with a **temporary password `adminpass123`** so
  the panel is usable immediately — **change it** in Settings → Security (or via
  the forgot-password flow).
- `ADMIN_EMAILS` must be set in the deploy environment (it's an env var, so
  changing who is admin needs no code change and no migration).
- In dev with no SMTP configured, the reset email is **logged by the api**, not
  actually sent (existing mailer behaviour).
- Pre-existing accounts (`m@ex.com`, `e2e@example.com`) are leftovers from earlier
  test/e2e runs, not created here.

## Commits
- (backend) feat(admin): master-admin endpoints + ADMIN_EMAILS gating
- (frontend) feat(admin): Master admin panel in Settings (manage users)
- (log) docs: master-admin log
