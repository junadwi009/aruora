#!/bin/bash
# WS08-02 — least-privilege runtime role provisioning.
#
# Runs once, on FIRST initialization of an empty data volume
# (/docker-entrypoint-initdb.d semantics). Creates a non-superuser runtime
# role for the application/workers and grants it DML-only rights on the
# public schema (including future objects created by the DDL/owner role that
# runs Alembic migrations). The runtime role can never DDL, create roles, or
# bypass RLS-style protections.
#
# Activation (docker-compose.prod.yml env):
#   POSTGRES_RUNTIME_USER=aruora_app
#   POSTGRES_RUNTIME_PASSWORD=<strong random>
#   DATABASE_URL=postgresql+psycopg://aruora_app:<same>@db:5432/<db>
#   MIGRATION_DATABASE_URL=postgresql+psycopg://<owner>:<owner>@db:5432/<db>
#
# If the runtime variables are absent the script is a no-op and the stack
# keeps the documented single-owner self-host profile (app still refuses to
# boot with default credentials in production — WS08-04B).
set -euo pipefail

: "${POSTGRES_DB:?POSTGRES_DB must be set}"
: "${POSTGRES_USER:?POSTGRES_USER must be set}"

if [ -z "${POSTGRES_RUNTIME_USER:-}" ] || [ -z "${POSTGRES_RUNTIME_PASSWORD:-}" ]; then
  echo "[ws08-init] POSTGRES_RUNTIME_USER/PASSWORD not set - keeping single-owner profile (dev/self-host convenience)."
  exit 0
fi

echo "[ws08-init] creating least-privilege runtime role '${POSTGRES_RUNTIME_USER}'"

psql -v ON_ERROR_STOP=1 \
     --username "$POSTGRES_USER" \
     --dbname "$POSTGRES_DB" \
     -v rt_user="$POSTGRES_RUNTIME_USER" \
     -v rt_pass="$POSTGRES_RUNTIME_PASSWORD" \
     -v owner="$POSTGRES_USER" \
     -v pgdb="$POSTGRES_DB" <<-'EOSQL'
  -- Idempotent role creation (volume may be re-initialised into a snapshot).
  SELECT format(
      'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT',
      :'rt_user', :'rt_pass')
  WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'rt_user') \gexec

  GRANT CONNECT ON DATABASE :"pgdb" TO :"rt_user";
  GRANT USAGE ON SCHEMA public TO :"rt_user";
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"rt_user";
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO :"rt_user";

  -- Future objects created by the migration/DDL owner (alembic upgrade head
  -- runs as the owner in the api container) get runtime grants automatically.
  ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public
      GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"rt_user";
  ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public
      GRANT USAGE, SELECT ON SEQUENCES TO :"rt_user";
EOSQL

echo "[ws08-init] runtime role ready (DML only; DDL stays with '${POSTGRES_USER}')"
