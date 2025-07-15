#!/bin/bash
#
# Database Backup Script for Cloud SQL
# Runs automated backups with retention policy
#

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-roadtrip-prod}"
INSTANCE_ID="${CLOUD_SQL_INSTANCE:-roadtrip-db}"
BACKUP_BUCKET="${BACKUP_BUCKET:-gs://roadtrip-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
BACKUP_PREFIX="roadtrip-backup"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="${BACKUP_PREFIX}-${TIMESTAMP}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI not found. Please install Google Cloud SDK."
        exit 1
    fi
    
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        error "Not authenticated with gcloud. Run 'gcloud auth login'"
        exit 1
    fi
    
    # Check if Cloud SQL instance exists
    if ! gcloud sql instances describe ${INSTANCE_ID} --project=${PROJECT_ID} &> /dev/null; then
        error "Cloud SQL instance ${INSTANCE_ID} not found in project ${PROJECT_ID}"
        exit 1
    fi
    
    # Check if backup bucket exists
    if ! gsutil ls ${BACKUP_BUCKET} &> /dev/null; then
        warning "Backup bucket ${BACKUP_BUCKET} not found. Creating..."
        gsutil mb -p ${PROJECT_ID} ${BACKUP_BUCKET}
        gsutil lifecycle set backup_lifecycle.json ${BACKUP_BUCKET}
    fi
}

# Create automated Cloud SQL backup
create_sql_backup() {
    log "Creating Cloud SQL backup: ${BACKUP_NAME}"
    
    gcloud sql backups create \
        --instance=${INSTANCE_ID} \
        --description="Automated backup ${TIMESTAMP}" \
        --project=${PROJECT_ID}
    
    # Wait for backup to complete
    log "Waiting for backup to complete..."
    local backup_id=$(gcloud sql backups list \
        --instance=${INSTANCE_ID} \
        --project=${PROJECT_ID} \
        --limit=1 \
        --format="value(id)")
    
    while true; do
        local status=$(gcloud sql backups describe ${backup_id} \
            --instance=${INSTANCE_ID} \
            --project=${PROJECT_ID} \
            --format="value(status)")
        
        if [[ "${status}" == "SUCCESSFUL" ]]; then
            log "Backup completed successfully"
            break
        elif [[ "${status}" == "FAILED" ]]; then
            error "Backup failed"
            exit 1
        else
            echo -n "."
            sleep 10
        fi
    done
}

# Export backup to Cloud Storage
export_to_storage() {
    log "Exporting backup to Cloud Storage..."
    
    local export_uri="${BACKUP_BUCKET}/${BACKUP_NAME}.sql.gz"
    
    gcloud sql export sql ${INSTANCE_ID} ${export_uri} \
        --database=roadtrip_prod \
        --project=${PROJECT_ID} \
        --offload
    
    log "Backup exported to: ${export_uri}"
}

# Create backup metadata
create_backup_metadata() {
    log "Creating backup metadata..."
    
    local metadata_file="/tmp/${BACKUP_NAME}-metadata.json"
    local db_version=$(gcloud sql instances describe ${INSTANCE_ID} \
        --project=${PROJECT_ID} \
        --format="value(databaseVersion)")
    
    cat > ${metadata_file} << EOF
{
    "backup_name": "${BACKUP_NAME}",
    "timestamp": "${TIMESTAMP}",
    "instance_id": "${INSTANCE_ID}",
    "project_id": "${PROJECT_ID}",
    "database_version": "${db_version}",
    "backup_type": "automated",
    "retention_days": ${RETENTION_DAYS},
    "backup_size_bytes": 0,
    "checksum": ""
}
EOF
    
    # Upload metadata
    gsutil cp ${metadata_file} ${BACKUP_BUCKET}/${BACKUP_NAME}-metadata.json
    rm ${metadata_file}
}

# Clean up old backups
cleanup_old_backups() {
    log "Cleaning up backups older than ${RETENTION_DAYS} days..."
    
    # List and delete old backups
    local cutoff_date=$(date -d "${RETENTION_DAYS} days ago" +%Y%m%d)
    
    gsutil ls ${BACKUP_BUCKET}/${BACKUP_PREFIX}-*.sql.gz | while read backup_file; do
        local backup_date=$(echo ${backup_file} | sed -E 's/.*-([0-9]{8})-[0-9]{6}\.sql\.gz/\1/')
        
        if [[ ${backup_date} -lt ${cutoff_date} ]]; then
            warning "Deleting old backup: ${backup_file}"
            gsutil rm ${backup_file}
            gsutil rm ${backup_file%.sql.gz}-metadata.json 2>/dev/null || true
        fi
    done
}

# Verify backup integrity
verify_backup() {
    log "Verifying backup integrity..."
    
    local backup_file="${BACKUP_BUCKET}/${BACKUP_NAME}.sql.gz"
    
    # Download first few KB to verify it's a valid gzip
    gsutil cp -r 0-1024 ${backup_file} - | gunzip -t 2>/dev/null
    
    if [[ $? -eq 0 ]]; then
        log "Backup file integrity verified"
    else
        error "Backup file appears to be corrupted"
        exit 1
    fi
}

# Send notification
send_notification() {
    local status=$1
    local message=$2
    
    # Send to monitoring webhook if configured
    if [[ -n "${MONITORING_WEBHOOK:-}" ]]; then
        curl -X POST ${MONITORING_WEBHOOK} \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"Database Backup ${status}\",
                \"backup_name\": \"${BACKUP_NAME}\",
                \"message\": \"${message}\"
            }" 2>/dev/null || true
    fi
    
    # Log to Cloud Logging
    gcloud logging write database-backups \
        "${message}" \
        --severity=$([ "$status" == "SUCCESS" ] && echo "INFO" || echo "ERROR") \
        --project=${PROJECT_ID}
}

# Main execution
main() {
    log "Starting database backup process..."
    
    # Trap errors
    trap 'error "Backup failed at line $LINENO"' ERR
    
    # Execute backup steps
    check_prerequisites
    create_sql_backup
    export_to_storage
    create_backup_metadata
    verify_backup
    cleanup_old_backups
    
    log "Backup completed successfully!"
    send_notification "SUCCESS" "Database backup ${BACKUP_NAME} completed successfully"
}

# Run main function
main "$@"