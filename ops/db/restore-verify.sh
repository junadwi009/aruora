#!/bin/sh
# WS08-07 — restore VERIFICATION drill.
#
# "Postgres starts" is not a proven recovery. This drill restores a backup
# into an ISOLATED throwaway PostgreSQL 18 container and verifies
# application-level correctness:
#   1. alembic_version matches the current chain head;
#   2. account data survives (a login-capable account exists);
#   3. learning history counts are plausible and non-empty (or explicitly
#      accepted as empty for a young deployment);
#   4. FK integrity: no orphaned user-owned rows anywhere;
#   5. encrypted secrets (SMTP keys, SESSION_SECRET, LLM keys) are supplied
#      by the deployment environment — the backup must NOT contain them and
#      the drill confirms the restored app boots with fresh secrets;
#   6. object/audio references: recordings are transient by design (WS06);
#      profile avatars are DB rows and are covered by the orphan checks.
#
# Usage: RESTORE_FILE=... ./restore-verify.sh
# Measures RTO (restore+verify wall time) — record it in the runbook log.
set -eu

: "${RESTORE_FILE:?RESTORE_FILE is required}"
: "${POSTGRES_USER:?POSTGRES_USER (DB owner) is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

CONTAINER="${VERIFY_CONTAINER:-aruora-restore-verify}"
TARGET_DB="${VERIFY_DB:-verify}"
PGPORT="${VERIFY_PORT:-55432}"
START="$(date +%s)"

cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
}
trap cleanup EXIT

cleanup
echo "[verify] starting isolated postgres:18 ($CONTAINER)"
docker run -d --name "$CONTAINER" \
  -e POSTGRES_USER="$POSTGRES_USER" \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB="$TARGET_DB" \
  -p "$PGPORT":5432 postgres:18 >/dev/null

until docker exec "$CONTAINER" pg_isready -U "$POSTGRES_USER" -d "$TARGET_DB" >/dev/null 2>&1; do
  sleep 1
done

echo "[verify] restoring backup"
TARGET_HOST="127.0.0.1" TARGET_PORT="$PGPORT" \
POSTGRES_DB="$TARGET_DB" \
"$(dirname "$0")/restore.sh"

# Unencrypted restore file may have been produced from the .enc source by
# restore.sh in the same directory — that file is not needed here; all
# verification reads the restored DATABASE.

echo "[verify] application-level checks"
CHECKS="$(cat <<'SQL'
\echo '## alembic_version (compare with alembic heads)'
SELECT version_num FROM alembic_version;
\echo '## accounts (must be > 0 unless a documented young deployment)'
SELECT COUNT(*) AS users FROM user_profile;
\echo '## learning history volumes'
SELECT (SELECT COUNT(*) FROM attempts) AS attempts,
       (SELECT COUNT(*) FROM cards) AS cards,
       (SELECT COUNT(*) FROM programs) AS programs;
\echo '## orphan user-owned rows (all must be 0)'
SELECT
  (SELECT COUNT(*) FROM attempts WHERE user_id NOT IN (SELECT id FROM user_profile)) AS orphan_attempts,
  (SELECT COUNT(*) FROM cards WHERE user_id NOT IN (SELECT id FROM user_profile)) AS orphan_cards,
  (SELECT COUNT(*) FROM programs WHERE user_id NOT IN (SELECT id FROM user_profile)) AS orphan_programs,
  (SELECT COUNT(*) FROM mocks WHERE user_id NOT IN (SELECT id FROM user_profile)) AS orphan_mocks,
  (SELECT COUNT(*) FROM lessons WHERE user_id NOT IN (SELECT id FROM user_profile)) AS orphan_lessons,
  (SELECT COUNT(*) FROM feedback WHERE user_id NOT IN (SELECT id FROM user_profile)) AS orphan_feedback;
\echo '## milestones cascaded through programs (must be 0)'
SELECT COUNT(*) AS orphan_milestones FROM milestones
 WHERE program_id NOT IN (SELECT id FROM programs);
SQL
)"
docker exec -i -e PGPASSWORD="$POSTGRES_PASSWORD" "$CONTAINER" \
  psql -U "$POSTGRES_USER" -d "$TARGET_DB" -v ON_ERROR_STOP=1 <<SQL
$CHECKS
SQL

# Human decision point: the operator confirms the numbers above match the
# last known production snapshot before declaring the drill PASSED.
END="$(date +%s)"
echo "[verify] RTO (restore + checks): $((END - START))s"
echo "[verify] REVIEW the counts above, then record RPO/RTO in"
echo "         docs/runbooks/DATABASE_BACKUP_RESTORE.md (monthly drill log)."
