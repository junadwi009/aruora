#!/bin/sh
# WS08-06 — encrypted PostgreSQL backup for ARUORA IELTS.
#
# Produces a timestamped pg_dump (custom format) in $BACKUP_DIR, optionally
# AES-256 encrypted, with local retention pruning. The copy to OFF-HOST
# storage (rclone/scp/object storage) is the operator's scheduled step — a
# backup that lives on the database host is not a recovery mechanism.
#
# Schedule daily (cron):
#   15 3 * * * /opt/aruora/ops/db/backup.sh >> /var/log/aruora-backup.log 2>&1
#
# Required env (or environment file sourced by cron):
#   POSTGRES_USER / POSTGRES_PASSWORD / POSTGRES_DB
#   BACKUP_DIR        local staging dir (e.g. /var/backups/aruora)
# Optional:
#   POSTGRES_HOST=127.0.0.1  POSTGRES_PORT=5432
#   BACKUP_RETENTION_DAYS=14 (local retention; off-host retention per policy)
#   BACKUP_ENCRYPTION_KEY    AES-256-CBC + PBKDF2 when set (ALWAYS set in prod)
#
# Monitoring: cron mail on failure + check the newest mtime from a separate
# host; an absent fresh backup is an incident (see the runbook).
set -eu

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${BACKUP_DIR:?BACKUP_DIR is required}"

HOST="${POSTGRES_HOST:-127.0.0.1}"
PORT="${POSTGRES_PORT:-5432}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
ENCRYPT_KEY="${BACKUP_ENCRYPTION_KEY:-}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/aruora_${POSTGRES_DB}_${STAMP}.dump"

mkdir -p "$BACKUP_DIR"
export PGPASSWORD="$POSTGRES_PASSWORD"

echo "[backup] pg_dump $HOST:$PORT/$POSTGRES_DB -> $OUT"
pg_dump -h "$HOST" -p "$PORT" -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" -f "$OUT"

if [ -n "$ENCRYPT_KEY" ]; then
  openssl enc -aes-256-cbc -pbkdf2 -salt -in "$OUT" -out "$OUT.enc" -pass "pass:$ENCRYPT_KEY"
  rm -f "$OUT"
  OUT="$OUT.enc"
fi

# Integrity reference for the restore drill (verify before trusting).
sha256sum "$OUT" > "$OUT.sha256"

# Local retention prune (off-host copies follow the documented policy).
find "$BACKUP_DIR" -name "aruora_${POSTGRES_DB}_*.dump*" -mtime +"$RETENTION_DAYS" -delete

echo "[backup] complete: $OUT"
echo "[backup] NEXT STEP (operator): copy off-host, e.g. rclone copy \"$OUT\" remote:aruora-backups/"
