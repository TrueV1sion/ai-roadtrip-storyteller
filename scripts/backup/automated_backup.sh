#!/bin/bash
# Automated backup script for AI Road Trip Storyteller
# This script performs database and Redis backups with verification

set -euo pipefail

# Configuration
PROJECT_ID="${1:-roadtrip-460720}"
BUCKET_NAME="${2:-roadtrip-backups}"
ENVIRONMENT="${ENVIRONMENT:-production}"
BACKUP_PREFIX="backups/${ENVIRONMENT}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Log function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to perform PostgreSQL backup
backup_postgres() {
    log "Starting PostgreSQL backup..."
    
    local db_host="${DB_HOST:-localhost}"
    local db_port="${DB_PORT:-5432}"
    local db_name="${DB_NAME:-roadtrip}"
    local db_user="${DB_USER:-roadtrip}"
    local backup_file="postgres_${ENVIRONMENT}_${TIMESTAMP}.sql"
    local backup_path="/tmp/${backup_file}"
    
    # Create backup with custom format for better compression
    PGPASSWORD="${DB_PASSWORD}" pg_dump \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${db_user}" \
        -d "${db_name}" \
        --verbose \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        --format=custom \
        --compress=9 \
        --file="${backup_path}.gz"
    
    if [ $? -eq 0 ]; then
        log "PostgreSQL backup completed: ${backup_path}.gz"
        
        # Calculate checksum
        local checksum=$(sha256sum "${backup_path}.gz" | awk '{print $1}')
        echo "${checksum}" > "${backup_path}.gz.sha256"
        
        # Upload to GCS
        gsutil -o GSUtil:parallel_composite_upload_threshold=150M \
            cp "${backup_path}.gz" "gs://${BUCKET_NAME}/${BACKUP_PREFIX}/postgres/${backup_file}.gz"
        
        gsutil cp "${backup_path}.gz.sha256" \
            "gs://${BUCKET_NAME}/${BACKUP_PREFIX}/postgres/${backup_file}.gz.sha256"
        
        log "PostgreSQL backup uploaded to GCS"
        
        # Clean up local files
        rm -f "${backup_path}.gz" "${backup_path}.gz.sha256"
        
        return 0
    else
        error "PostgreSQL backup failed"
        return 1
    fi
}

# Function to perform Redis backup
backup_redis() {
    log "Starting Redis backup..."
    
    local redis_host="${REDIS_HOST:-localhost}"
    local redis_port="${REDIS_PORT:-6379}"
    local redis_password="${REDIS_PASSWORD:-}"
    local backup_file="redis_${ENVIRONMENT}_${TIMESTAMP}.rdb"
    local backup_path="/tmp/${backup_file}"
    
    # Trigger Redis BGSAVE
    if [ -n "${redis_password}" ]; then
        redis-cli -h "${redis_host}" -p "${redis_port}" -a "${redis_password}" BGSAVE
    else
        redis-cli -h "${redis_host}" -p "${redis_port}" BGSAVE
    fi
    
    # Wait for background save to complete
    log "Waiting for Redis background save to complete..."
    while true; do
        if [ -n "${redis_password}" ]; then
            lastsave=$(redis-cli -h "${redis_host}" -p "${redis_port}" -a "${redis_password}" LASTSAVE)
        else
            lastsave=$(redis-cli -h "${redis_host}" -p "${redis_port}" LASTSAVE)
        fi
        
        sleep 2
        
        if [ -n "${redis_password}" ]; then
            newsave=$(redis-cli -h "${redis_host}" -p "${redis_port}" -a "${redis_password}" LASTSAVE)
        else
            newsave=$(redis-cli -h "${redis_host}" -p "${redis_port}" LASTSAVE)
        fi
        
        if [ "${newsave}" != "${lastsave}" ]; then
            break
        fi
    done
    
    log "Redis background save completed"
    
    # Get Redis data directory
    if [ -n "${redis_password}" ]; then
        redis_dir=$(redis-cli -h "${redis_host}" -p "${redis_port}" -a "${redis_password}" CONFIG GET dir | tail -1)
    else
        redis_dir=$(redis-cli -h "${redis_host}" -p "${redis_port}" CONFIG GET dir | tail -1)
    fi
    
    # Copy RDB file
    cp "${redis_dir}/dump.rdb" "${backup_path}"
    
    # Compress
    gzip -9 "${backup_path}"
    
    # Calculate checksum
    local checksum=$(sha256sum "${backup_path}.gz" | awk '{print $1}')
    echo "${checksum}" > "${backup_path}.gz.sha256"
    
    # Upload to GCS
    gsutil cp "${backup_path}.gz" \
        "gs://${BUCKET_NAME}/${BACKUP_PREFIX}/redis/${backup_file}.gz"
    
    gsutil cp "${backup_path}.gz.sha256" \
        "gs://${BUCKET_NAME}/${BACKUP_PREFIX}/redis/${backup_file}.gz.sha256"
    
    log "Redis backup uploaded to GCS"
    
    # Clean up
    rm -f "${backup_path}.gz" "${backup_path}.gz.sha256"
    
    return 0
}

# Function to clean old backups
cleanup_old_backups() {
    log "Cleaning up old backups..."
    
    local retention_days="${BACKUP_RETENTION_DAYS:-30}"
    local cutoff_date=$(date -d "${retention_days} days ago" +%Y%m%d)
    
    # List and delete old PostgreSQL backups
    gsutil ls "gs://${BUCKET_NAME}/${BACKUP_PREFIX}/postgres/" | while read -r file; do
        if [[ $file =~ postgres_${ENVIRONMENT}_([0-9]{8})_.*\.gz$ ]]; then
            backup_date="${BASH_REMATCH[1]}"
            if [[ "${backup_date}" < "${cutoff_date}" ]]; then
                warning "Deleting old backup: ${file}"
                gsutil rm "${file}" "${file}.sha256" 2>/dev/null || true
            fi
        fi
    done
    
    # List and delete old Redis backups
    gsutil ls "gs://${BUCKET_NAME}/${BACKUP_PREFIX}/redis/" | while read -r file; do
        if [[ $file =~ redis_${ENVIRONMENT}_([0-9]{8})_.*\.gz$ ]]; then
            backup_date="${BASH_REMATCH[1]}"
            if [[ "${backup_date}" < "${cutoff_date}" ]]; then
                warning "Deleting old backup: ${file}"
                gsutil rm "${file}" "${file}.sha256" 2>/dev/null || true
            fi
        fi
    done
    
    log "Old backup cleanup completed"
}

# Function to verify backups
verify_backups() {
    log "Verifying recent backups..."
    
    python3 /app/scripts/backup/verify_backups.py \
        --project-id "${PROJECT_ID}" \
        --bucket-name "${BUCKET_NAME}" \
        --backup-type all \
        --days 1 \
        --output "/tmp/backup_verification_${TIMESTAMP}.md"
    
    if [ $? -eq 0 ]; then
        log "Backup verification passed"
        
        # Upload verification report
        gsutil cp "/tmp/backup_verification_${TIMESTAMP}.md" \
            "gs://${BUCKET_NAME}/${BACKUP_PREFIX}/verification/report_${TIMESTAMP}.md"
        
        rm -f "/tmp/backup_verification_${TIMESTAMP}.md"
        return 0
    else
        error "Backup verification failed"
        return 1
    fi
}

# Function to send notification
send_notification() {
    local status="$1"
    local message="$2"
    
    # Send to monitoring webhook if configured
    if [ -n "${MONITORING_WEBHOOK_URL:-}" ]; then
        curl -X POST "${MONITORING_WEBHOOK_URL}" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"Backup ${status} for ${ENVIRONMENT}\",
                \"attachments\": [{
                    \"color\": \"$([ \"${status}\" = \"SUCCESS\" ] && echo \"good\" || echo \"danger\")\",
                    \"text\": \"${message}\",
                    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
                }]
            }" 2>/dev/null || true
    fi
}

# Main backup process
main() {
    log "Starting automated backup for environment: ${ENVIRONMENT}"
    
    # Check prerequisites
    for cmd in pg_dump redis-cli gsutil python3; do
        if ! command_exists "$cmd"; then
            error "Required command '$cmd' not found"
            exit 1
        fi
    done
    
    # Create GCS bucket if it doesn't exist
    if ! gsutil ls -b "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
        log "Creating GCS bucket: ${BUCKET_NAME}"
        gsutil mb -p "${PROJECT_ID}" -c STANDARD -l US "gs://${BUCKET_NAME}"
        
        # Set lifecycle rules
        cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["backups/"]
        }
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {
          "age": 30,
          "matchesPrefix": ["backups/"]
        }
      }
    ]
  }
}
EOF
        gsutil lifecycle set /tmp/lifecycle.json "gs://${BUCKET_NAME}"
        rm -f /tmp/lifecycle.json
    fi
    
    # Perform backups
    backup_status="SUCCESS"
    backup_message=""
    
    # PostgreSQL backup
    if backup_postgres; then
        backup_message+="PostgreSQL backup: SUCCESS\n"
    else
        backup_status="FAILED"
        backup_message+="PostgreSQL backup: FAILED\n"
    fi
    
    # Redis backup
    if backup_redis; then
        backup_message+="Redis backup: SUCCESS\n"
    else
        backup_status="FAILED"
        backup_message+="Redis backup: FAILED\n"
    fi
    
    # Clean up old backups
    cleanup_old_backups
    
    # Verify backups
    if [ "${SKIP_VERIFICATION:-false}" != "true" ]; then
        if verify_backups; then
            backup_message+="Verification: PASSED\n"
        else
            backup_status="FAILED"
            backup_message+="Verification: FAILED\n"
        fi
    fi
    
    # Send notification
    send_notification "${backup_status}" "${backup_message}"
    
    if [ "${backup_status}" = "SUCCESS" ]; then
        log "Backup process completed successfully"
        exit 0
    else
        error "Backup process completed with errors"
        exit 1
    fi
}

# Run main function
main "$@"