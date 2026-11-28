#!/usr/bin/env bash
#
# Backup the cabici PostgreSQL database to DigitalOcean Spaces (S3-compatible).
#
# Usage:
#   ./deploy/scripts/backup-postgres-to-s3.sh
#
# Prerequisites:
#   - awscli (apt-get install awscli) or s3cmd
#   - Environment variables set (see below) or an AWS config profile
#
# This is designed to run from inside the Django Droplet via cron.
#

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration — override via environment variables or source a .env file
# ---------------------------------------------------------------------------

# Database connection (these match the Docker Compose env file)
DB_NAME="${DB_NAME:-cabici}"
DB_USER="${DB_USER:-cabici}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

# DO Spaces (S3-compatible) settings
S3_ENDPOINT="${S3_ENDPOINT:-https://syd1.digitaloceanspaces.com}"
S3_BUCKET="${S3_BUCKET:-}"           # e.g. cabici-backups
S3_PREFIX="${S3_PREFIX:-postgres}"
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"

# Backup retention: how many daily backups to keep locally (optional)
LOCAL_RETENTION_DAYS="${LOCAL_RETENTION_DAYS:-7}"
BACKUP_DIR="${BACKUP_DIR:-/mnt/cabici-data/backups}"

# Timestamped filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DUMP_FILE="${DB_NAME}_${TIMESTAMP}.sql.gz"
LOCAL_PATH="${BACKUP_DIR}/${DUMP_FILE}"
S3_KEY="${S3_PREFIX}/${DUMP_FILE}"

# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------

if [[ -z "${S3_BUCKET}" ]]; then
  echo "ERROR: S3_BUCKET must be set." >&2
  exit 1
fi

if [[ -z "${AWS_ACCESS_KEY_ID}" || -z "${AWS_SECRET_ACCESS_KEY}" ]]; then
  echo "ERROR: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY must be set." >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

# ---------------------------------------------------------------------------
# Dump and compress
# ---------------------------------------------------------------------------

echo "[BACKUP] Creating PostgreSQL dump: ${LOCAL_PATH}"

docker compose -f /opt/cabici/deploy/docker-compose.production.yml exec -T db \
  pg_dump -U "${DB_USER}" -d "${DB_NAME}" --no-owner --no-privileges \
  | gzip > "${LOCAL_PATH}"

BACKUP_SIZE=$(du -h "${LOCAL_PATH}" | cut -f1)
echo "[BACKUP] Dump complete: ${BACKUP_SIZE}"

# ---------------------------------------------------------------------------
# Upload to DO Spaces
# ---------------------------------------------------------------------------

echo "[UPLOAD] Pushing to s3://${S3_BUCKET}/${S3_KEY}"

export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY

aws --endpoint-url="${S3_ENDPOINT}" \
    s3 cp "${LOCAL_PATH}" "s3://${S3_BUCKET}/${S3_KEY}"

echo "[UPLOAD] Complete."

# ---------------------------------------------------------------------------
# Local cleanup (optional — keeps disk usage bounded)
# ---------------------------------------------------------------------------

echo "[CLEANUP] Pruning local backups older than ${LOCAL_RETENTION_DAYS} days"
find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql.gz" -mtime +"${LOCAL_RETENTION_DAYS}" -delete

# ---------------------------------------------------------------------------
# Remote retention (optional — delete old S3 objects)
# ---------------------------------------------------------------------------
# Uncomment and adjust to prune S3 backups older than N days automatically.
# Requires `jq` and the AWS CLI with delete-object privileges.
#
# S3_RETENTION_DAYS="${S3_RETENTION_DAYS:-30}"
# CUTOFF_DATE=$(date -d "${S3_RETENTION_DAYS} days ago" +%Y%m%d)
# aws --endpoint-url="${S3_ENDPOINT}" s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" | \
#   awk '{print $4}' | \
#   while read -r key; do
#     KEY_DATE=$(echo "$key" | grep -oP '^\d{8}')
#     if [[ "$KEY_DATE" < "$CUTOFF_DATE" ]]; then
#       aws --endpoint-url="${S3_ENDPOINT}" s3 rm "s3://${S3_BUCKET}/${S3_PREFIX}/${key}"
#     fi
#   done

echo "[DONE] Backup finished."
