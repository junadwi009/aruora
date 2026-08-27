#!/bin/sh
# WS08-07 — restore a ARUORA backup into a TARGET database.
#
# Restores are performed into an ISOLATED environment first (see
# restore-verify.sh); restoring directly over production is a last-resort
# runbook step and must be preceded by a fresh backup of the current state.
#
# Usage:
#   POSTGRES_USER=owner POSTGRES_PASSWORD=... POSTGRES_DB=aruora \
#   TARGET_HOST=127.0.0.1 TARGET_PORT=5432 RESTORE_FILE=/path/aruora_...dump[.enc] \
#   ./restore.sh
#
# For .enc files BACKUP_ENCRYPTION_KEY must be set (secrets are injected by
# the deployment mechanism — they are NEVER part of the backup itself).
set -eu

: "${POSTGRES_USER:?POSTGRES_USER (DB owner) is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB (target) is required}"
: "${RESTORE_FILE:?RESTORE_FILE is required}"

TARGET_HOST="${TARGET_HOST:-127.0.0.1}"
TARGET_PORT="${TARGET_PORT:-5432}"
ENCRYPT_KEY="${BACKUP_ENCRYPTION_KEY:-}"

FILE="$RESTORE_FILE"
if printf '%s' "$FILE" | grep -q '\.enc$'; then
  : "${ENCRYPT_KEY:?BACKUP_ENCRYPTION_KEY is required for .enc backups}"
  PLAIN="${FILE%.enc}"
  openssl enc -d -aes-256-cbc -pbkdf2 -in "$FILE" -out "$PLAIN" -pass "pass:$ENCRYPT_KEY"
  FILE="$PLAIN"
fi

# Verify integrity when a checksum is available (fail closed).
if [ -f "$RESTORE_FILE.sha256" ]; then
  (cd "$(dirname "$RESTORE_FILE")" && sha256sum -c "$(basename "$RESTORE_FILE").sha256")
fi

export PGPASSWORD="$POSTGRES_PASSWORD"
echo "[restore] pg_restore $FILE -> $TARGET_HOST:$TARGET_PORT/$POSTGRES_DB"
# --clean --if-exists: re-runnable restore into an existing (empty or stale)
# target. Objects are restored with the owner role; the least-privilege
# runtime role regains DML via its default privileges (WS08-02).
pg_restore -h "$TARGET_HOST" -p "$TARGET_PORT" -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" --clean --if-exists --no-privileges "$FILE"

echo "[restore] done. Run restore-verify.sh against this database before use."
