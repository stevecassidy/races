#!/usr/bin/env bash
#
# Restore the cabici PostgreSQL database from a backup in DigitalOcean Spaces.
#
# Usage:
#   ./deploy/scripts/restore-postgres-from-s3.sh [backup-filename]
#
# If no filename is given, lists available backups and prompts for selection.
# WARNING: This drops the existing database and recreates it. All current data
# will be lost.
#

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_NAME="${DB_NAME:-cabici}"
DB_USER="${DB_USER:-cabici}"
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"

S3_ENDPOINT="${S3_ENDPOINT:-https://syd1.digitaloceanspaces.com}"
S3_BUCKET="${S3_BUCKET:-}"
S3_PREFIX="${S3_PREFIX:-postgres}"
AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"

BACKUP_DIR="${BACKUP_DIR:-/mnt/cabici-data/backups}"
COMPOSE_FILE="${COMPOSE_FILE:-/opt/cabici/deploy/docker-compose.production.yml}"

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
# List backups
# ---------------------------------------------------------------------------

export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY

echo "Fetching backup list from s3://${S3_BUCKET}/${S3_PREFIX}/ ..."
BACKUPS=$(aws --endpoint-url="${S3_ENDPOINT}" s3 ls "s3://${S3_BUCKET}/${S3_PREFIX}/" | awk '{print $4}')

if [[ -z "${BACKUPS}" ]]; then
  echo "ERROR: No backups found in s3://${S3_BUCKET}/${S3_PREFIX}/" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Select backup
# ---------------------------------------------------------------------------

SELECTED_FILE="${1:-}"

if [[ -z "${SELECTED_FILE}" ]]; then
  echo ""
  echo "Available backups:"
  echo "${BACKUPS}" | nl -ba -w2 -s'. '
  echo ""
  read -rp "Enter the number of the backup to restore: " CHOICE
  SELECTED_FILE=$(echo "${BACKUPS}" | sed -n "${CHOICE}p")
fi

if [[ -z "${SELECTED_FILE}" ]]; then
  echo "ERROR: Invalid selection." >&2
  exit 1
fi

S3_KEY="${S3_PREFIX}/${SELECTED_FILE}"
LOCAL_PATH="${BACKUP_DIR}/${SELECTED_FILE}"

echo ""
echo "Selected backup: ${SELECTED_FILE}"

# ---------------------------------------------------------------------------
# Confirmation
# ---------------------------------------------------------------------------

echo ""
echo "WARNING: This will DROP the existing '${DB_NAME}' database"
echo "and replace it with the contents of ${SELECTED_FILE}."
echo "All current data will be lost."
echo ""
read -rp "Type the database name '${DB_NAME}' to confirm: " CONFIRM

if [[ "${CONFIRM}" != "${DB_NAME}" ]]; then
  echo "Aborting."
  exit 1
fi

# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

echo ""
echo "[DOWNLOAD] s3://${S3_BUCKET}/${S3_KEY} -> ${LOCAL_PATH}"

if [[ -f "${LOCAL_PATH}" ]]; then
  echo "Backup already exists locally."
else
  aws --endpoint-url="${S3_ENDPOINT}" s3 cp "s3://${S3_BUCKET}/${S3_KEY}" "${LOCAL_PATH}"
fi

# ---------------------------------------------------------------------------
# Restore
# ---------------------------------------------------------------------------

echo ""
echo "[RESTORE] Stopping web service to prevent writes..."
docker compose -f "${COMPOSE_FILE}" stop web

echo "[RESTORE] Dropping and recreating database..."
docker compose -f "${COMPOSE_FILE}" exec -T db dropdb -U "${DB_USER}" --if-exists "${DB_NAME}"
docker compose -f "${COMPOSE_FILE}" exec -T db createdb -U "${DB_USER}" -O "${DB_USER}" "${DB_NAME}"

echo "[RESTORE] Loading data from ${SELECTED_FILE}..."
if [[ "${SELECTED_FILE}" == *.gz ]]; then
  gunzip -c "${LOCAL_PATH}" | docker compose -f "${COMPOSE_FILE}" exec -T db psql -U "${DB_USER}" -d "${DB_NAME}"
else
  docker compose -f "${COMPOSE_FILE}" exec -T db psql -U "${DB_USER}" -d "${DB_NAME}" < "${LOCAL_PATH}"
fi

echo ""
echo "[RESTORE] Starting web service..."
docker compose -f "${COMPOSE_FILE}" start web

echo ""
echo "[DONE] Database restored from ${SELECTED_FILE}."
