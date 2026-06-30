# deploy-config — 2026-06-29

Phase 2d-7: production deployment **configuration** (not a live deploy — go-live needs the owner's hosting decision + secrets).

## What changed
- **`web/Dockerfile.prod`** — multi-stage: `npm ci && npm run build` → nginx serving `dist/`. Build arg `VITE_API_BASE=""` so the client calls relative `/api/*`.
- **`web/nginx.conf`** — serves the SPA (try_files fallback), reverse-proxies `/api/` → `api:5050` (180s read timeout for live LLM/ASR; 25m body for audio), gzip + immutable caching for hashed assets. Uses the Docker embedded DNS resolver (`127.0.0.11`) + a variable upstream so nginx boots even before `api` resolves.
- **`docker-compose.prod.yml`** — db + api (gunicorn, internal) + web (prod image, publishes `${WEB_PORT:-80}`). `restart: unless-stopped`; parameterised `POSTGRES_*`. Only web is published.
- **`README.md`** — "Production deploy" section with the quickstart + the decisions left to the host (TLS, access gate, secrets, DB creds) + the `--build web` reminder.

## Decisions
- **Same-origin via nginx proxy** over split hosting — no CORS, no API host baked into the JS bundle, one published port. Aligns with the existing Docker-first setup.
- **No auth/TLS in the stack** — these are host/platform concerns; documented rather than hard-coded so the owner can pick (Caddy/Traefik/platform LB + basic-auth).

## Verify
- `docker build -f web/Dockerfile.prod` → builds. Standalone run → `/` 200, `/vocab` 200 (SPA fallback), `<title>IELTS Coach`.

## ⚠️ Needs owner decision before go-live
Not deployed. To ship, the owner must choose: **host** (single VPS via this compose vs. split Vercel+Render vs. other), **domain + TLS**, **access gate** (passcode/basic-auth — none yet), and provide **production secrets** (OpenRouter key, DB password). Then: `docker compose -f docker-compose.prod.yml up -d --build`.

## Commits
- `e0c0d66` build(deploy): production compose (nginx static + /api proxy)
