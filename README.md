# IELTS Coach v3

A self-hosted IELTS preparation app with AI-powered placement, Writing, Speaking, Listening, and Reading practice.

## Quickstart

```bash
cp .env.example .env
docker compose up --build
```

Open **http://localhost:5173** in your browser.

The API runs on **http://localhost:5050** by default.

## Journey overview

1. **Placement** — A short adaptive test (Reading, Listening, Writing, Speaking) estimates your starting CEFR level and IELTS band per skill.
2. **Results** — See your estimated band per skill (e.g. Reading C1, Listening B1) and your gap to target.
3. **Program** — Choose a study program (Intensive, Balanced, or Self-directed) tailored to your weaker skills.
4. **Practice** — Targeted exercises auto-generated for each skill, prioritising the skills with the biggest gaps.
5. **Progress** — Track improvement over time across all four skills.

## Honesty note

Band scores and CEFR levels shown in this app are **estimates only** — they are NOT official IELTS scores. They are calibrated approximations based on task performance; for an official score, sit a real exam from British Council or IDP.

## Phase 1 scope

**Phase 1 = offline stub journey.** The default `LLM_MODE=stub` runs fully **offline** using static fixture data — no API key required. Ideal for development and testing.

Live OpenRouter LLM calls, faster-whisper ASR (real speech scoring), and essay-metric scoring (lexical density, coherence) come in **later phases**.

## Architecture

| Service | Path | Description |
|---------|------|-------------|
| `api`   | `./api` | Python FastAPI backend (SQLAlchemy, Alembic, PostgreSQL) |
| `web`   | `./web` | React 19 + Vite + TypeScript frontend |
| `db`    | Docker  | PostgreSQL 18 |

### Environment variables

Copy `.env.example` to `.env` and fill in your values:

| Variable | Default | Purpose |
|----------|---------|---------|
| `LLM_MODE` | `stub` | `stub` = offline fixtures; `openrouter` = live LLM |
| `OPENROUTER_API_KEY` | — | Required only when `LLM_MODE=openrouter` |
| `DATABASE_URL` | set by Compose | PostgreSQL connection string |

## Development

```bash
# API (Python 3.11+)
cd api
python -m venv .venv
.venv/Scripts/activate     # Windows
# or: source .venv/bin/activate  (macOS/Linux)
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 5050

# Web (Node 18+)
cd web
npm install
npm run dev        # http://localhost:5173
npm test           # vitest
npx tsc --noEmit   # type-check
```

## Tests

```bash
# API tests
cd api && .venv/Scripts/python -m pytest -q

# Web tests
cd web && npm test

# Type-check
cd web && npx tsc --noEmit

# Secret scan (ensures no API keys are baked into built assets)
bash tests/secret_scan.sh

# Full compose smoke test (requires Docker)
bash tests/smoke.sh
```

## Production deploy

The dev `docker-compose.yml` runs the Vite dev server and publishes the API. For a
real deployment use **`docker-compose.prod.yml`**, which builds the SPA to static
files and serves them with nginx, reverse-proxying `/api/*` to gunicorn (same
origin → no CORS, no API host baked into the bundle). Only the web port is
published; `api` and `db` stay on the internal network.

```bash
cp .env.example .env          # set LLM_MODE + keys; CHANGE POSTGRES_PASSWORD
docker compose -f docker-compose.prod.yml up -d --build
# open http://<host>:${WEB_PORT:-80}
```

Env (in `.env`): `LLM_MODE` (`stub` offline / `live`), `OPENROUTER_API_KEY`,
`MODEL_GENERATE`/`MODEL_SCORE`, `ASR_ENABLED`, `POSTGRES_USER/PASSWORD/DB`,
`WEB_PORT`.

**Before exposing publicly — not included, decide per host:**
- **TLS**: terminate HTTPS at a front proxy (Caddy/Traefik/nginx) or the platform's
  load balancer; this stack speaks plain HTTP on the web port.
- **Access gate**: the app has no auth. Add a passcode/basic-auth at the proxy, e.g.
  nginx `auth_basic` in front, or a platform access rule. (App-level passcode is a
  future enhancement.)
- **Secrets**: keep real keys in the host's secret store / env, never committed.
- **DB**: change the default `ielts/ielts` credentials; back up the `ielts_pgdata`
  volume.

> ⚠️ The `web` image **copies source at build time** — always `--build` the web
> service after frontend changes (a stale container serves old UI).

### Email + study reminders (optional)

Password reset and study reminders send email when **SMTP** is configured
(`SMTP_HOST/PORT/USER/PASSWORD/FROM` + `APP_BASE_URL`). Without SMTP, the message
(including any reset link) is **logged to the api container** instead of sent.

Reminders are driven by an external scheduler hitting a token-protected endpoint
hourly. Set `REMINDER_TOKEN`, then add a cron entry (host or platform scheduler):

```cron
0 * * * * curl -fsS -X POST -H "X-Reminder-Token: $REMINDER_TOKEN" \
  http://localhost:5050/api/internal/reminders/run >/dev/null
```

Each run emails users whose chosen reminder hour matches and who haven't been
emailed that day.

See `CLAUDE.md` for full architecture, conventions, and roadmap.
