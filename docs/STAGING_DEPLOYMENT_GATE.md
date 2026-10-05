# Persistent staging deployment gate

## Current boundary

The repair has been built/tested in disposable GitHub Actions infrastructure.
It has NOT been installed on a persistent user-controlled staging server.
No confirmed ARUORA staging hostname and no authorized remote terminal were
available to this execution. Do not substitute another project's server, invent
a URL, open a public tunnel, or provision paid infrastructure to fill that gap.

Required before a remote write: the intended staging host/domain, an authorized
terminal connection, and confirmation that this is an isolated staging target.
Use a secure connection or deployment secret store; never paste private keys,
server passwords, database credentials or application secrets into this chat,
repository, issue, or workflow logs.

## Operator preflight on the confirmed host

Check the approved PR SHA and all seven workflow groups: CI, Security, CodeQL,
Jobs integration, Metric compatibility, UAT browser regressions and Production
image smoke. Do not replace a failed check with a success badge from an older SHA.

Inspect existing services, available RAM/disk, Docker/Compose, bound ports,
firewall and the site's current TLS termination before changing anything. On a
HestiaCP-managed host, use the existing managed virtual-host/proxy/TLS mechanism.
Do not install a competing control panel, nginx/Caddy service or certbot daemon,
and do not overwrite global Hestia nginx configuration. The CI-only TLS overlay
and self-signed localhost certificate must NEVER be deployed to that host.

Prepare a separate checkout and Compose project (for example `aruora-staging`)
with separate PostgreSQL/Redis/audio volumes and separate accounts/secrets.
Check that the chosen loopback web port is free; the example port 8080 is not a
claim that it is free on Hestia. Never point DATABASE_URL or a volume at production.

Copy `ops/uat.env.example` to the staging checkout's `.env` only when that file
does not already exist; configure it without logging values and use mode 0600.
Use strong independent session/database secrets, APP_BASE_URL with the exact
HTTPS origin, TRUSTED_HOSTS for that host, and trusted proxy hop counts matching
the actual topology. Keep web bound to loopback; never publish PostgreSQL or
Redis ports. Secure cookies and production-mode checks must stay enabled.

Start with `LLM_MODE=stub`; restrict the edge to authorized testers/VPN/IP rules
before startup. Public/external UAT keeps email verification and fail-closed mail
delivery enabled with a configured SMTP service. The isolated image test's
mail-disabled settings are NOT an external UAT configuration. Configure Google
sign-in only for the confirmed origin/client and test it before enabling the UI.

## Deployment after preflight passes

Record the approved source revision and build image IDs. The prior CI's images
are ephemeral, not published release artifacts; a staging rebuild must be
identified and smoke-tested rather than assumed byte-identical to the CI image.

Validate Compose without printing resolved secrets:

```sh
docker compose -p aruora-staging -f docker-compose.prod.yml config --quiet
```

With the isolated staging configuration confirmed, build, then start the stack:

```sh
docker compose -p aruora-staging -f docker-compose.prod.yml build
docker compose -p aruora-staging -f docker-compose.prod.yml up -d --wait --wait-timeout 240
```

The one-shot migrate service must complete before new API/workers. Migration
`b26c20261005` belongs to the reliable-jobs repair; this NLTK removal introduces
no further migration. Do not mix old and new consumers on shared queues.

## Remote acceptance, distinct from CI

Verify external DNS and the real certificate chain/hostname/expiry, proxy header
handling, secure/HttpOnly cookies, no cross-origin leakage, protected DB/Redis
ports, dependency-aware readiness, and every intended worker's availability.
Then exercise real register/verify/reset/login, MFA where configured, placement,
all four learning skills, audio permission/upload/transcription, job reload
recovery, progress persistence, settings and logout on the target domain.

Use synthetic accounts first and check cross-account denials. Confirm delivery
of verification/reset messages and Google login rather than assuming configured
values prove they work. Test backup/restore in a separate staging restore target;
a successful CI restore is not proof the host's scheduled backups are working.
Record monitoring/worker alerts, resource use and capacity before inviting a
larger cohort. Live provider scoring needs a separate budgeted calibration gate;
stub results are explicitly not assessed scores.

Stop and record failures rather than weakening controls or opening production.
Before rollback, stop producers/consumers, inspect pending jobs and preserve a
verified backup. Do not run destructive volume removal or automatic schema
rollback on an existing user database. No remote command in this document was
executed against a user-controlled staging or production host during this repair.
