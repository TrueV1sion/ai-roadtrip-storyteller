#!/bin/bash
# Redis backup script for Docker environment

set -euo pipefail

# Configuration
REDIS_URL="${REDIS_URL:-redis://localhost:6379}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="redis_backup_${TIMESTAMP}"

echo "Starting Redis backup: ${BACKUP_NAME}"

# Create backup directory
mkdir -p "${BACKUP_DIR}"

# Parse Redis URL
REDIS_HOST=$(echo $REDIS_URL | sed -e 's/redis:\/\///' -e 's/:.*$//')
REDIS_PORT=$(echo $REDIS_URL | sed -e 's/.*://' -e 's/\/.*//')

# Create RDB backup using redis-cli
echo "Creating Redis snapshot..."
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" --rdb "${BACKUP_DIR}/${BACKUP_NAME}.rdb"

# Compress the backup
echo "Compressing backup..."
gzip -9 "${BACKUP_DIR}/${BACKUP_NAME}.rdb"

# Upload to GCS using Python script
echo "Uploading to GCS..."
python /app/redis_backup.py backup --name "${BACKUP_NAME}"

# Clean up local files older than 1 day
echo "Cleaning up old local backups..."
find "${BACKUP_DIR}" -name "*.rdb.gz" -mtime +1 -delete

# Run cleanup for old GCS backups
echo "Cleaning up old GCS backups..."
python /app/redis_backup.py cleanup

echo "Backup completed successfully!"

# Send success metric
curl -X POST "http://localhost:9090/metrics/job/redis_backup/instance/${HOSTNAME}" \
  --data-binary @- <<EOF
redis_backup_success{backup="${BACKUP_NAME}"} 1
redis_backup_timestamp{backup="${BACKUP_NAME}"} $(date +%s)
EOF