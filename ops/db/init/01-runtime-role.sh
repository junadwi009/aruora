#!/bin/bash
# WS08-02 — least-privilege runtime role provisioning.
# Runs once during FIRST initialization of an empty PostgreSQL data volume.
# Runtime roles receive DML, never superuser/role-creation privileges.
# The migration owner retains DDL and grants access to future objects.
# Both runtime variables absent retains the documented single-owner profile.
# A partially configured role must fail rather than silently use the owner.
#
# The official PostgreSQL entrypoint SOURCES non-executable .sh init files.
# Isolate shell options and early exit from that parent in both invocation modes.
(
set -euo pipefail

: "${POSTGRES_DB:?POSTGRES_DB must be set}"
: "${POSTGRES_USER:?POSTGRES_USER must be set}"

if { [ -n "${POSTGRES_RUNTIME_USER:-}" ] && [ -z "${POSTGRES_RUNTIME_PASSWORD:-}" ]; } ||
   { [ -z "${POSTGRES_RUNTIME_USER:-}" ] && [ -n "${POSTGRES_RUNTIME_PASSWORD:-}" ]; }; then
  echo "[ws08-init] both runtime-role variables must be configured together." >&2
  exit 1
fi

if [ -z "${POSTGRES_RUNTIME_USER:-}" ]; then
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
  SELECT format(
      'CREATE ROLE %I LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT',
      :'rt_user', :'rt_pass')
  WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'rt_user') \gexec

  GRANT CONNECT ON DATABASE :"pgdb" TO :"rt_user";
  GRANT USAGE ON SCHEMA public TO :"rt_user";
  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"rt_user";
  GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO :"rt_user";

  ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public
      GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"rt_user";
  ALTER DEFAULT PRIVILEGES FOR ROLE :"owner" IN SCHEMA public
      GRANT USAGE, SELECT ON SEQUENCES TO :"rt_user";
EOSQL

echo "[ws08-init] runtime role ready (DML only; DDL stays with '${POSTGRES_USER}')"
)
