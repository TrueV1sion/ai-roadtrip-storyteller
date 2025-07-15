# Database Backup and Recovery Guide

This guide covers the automated backup system for the AI Road Trip Storyteller PostgreSQL database.

## Overview

The backup system provides:
- **Automated daily backups** with configurable retention
- **Compressed storage** to minimize costs
- **Google Cloud Storage** integration for durability
- **Point-in-time recovery** capabilities
- **Monitoring and alerting** for backup failures

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   PostgreSQL    │────▶│  Backup Script   │────▶│ Google Cloud    │
│   Database      │     │  (pg_dump)       │     │ Storage         │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │ Local Backup     │
                        │ (Compressed)     │
                        └──────────────────┘
```

## Setup Instructions

### 1. Create GCS Bucket

```bash
# Create backup bucket with lifecycle rules
gsutil mb -p YOUR_PROJECT_ID -c STANDARD -l us-central1 gs://roadtrip-db-backups/

# Set lifecycle policy (delete backups older than 90 days)
cat > lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["postgres/"]
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set lifecycle.json gs://roadtrip-db-backups/
```

### 2. Create Service Account

```bash
# Create backup service account
gcloud iam service-accounts create roadtrip-backup \
    --display-name="Database Backup Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:roadtrip-backup@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Grant access to secrets
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:roadtrip-backup@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 3. Build Backup Container

```bash
# Build and push backup container
cd infrastructure/backup
docker build -f Dockerfile.backup -t gcr.io/YOUR_PROJECT_ID/roadtrip-backup:latest ../..
docker push gcr.io/YOUR_PROJECT_ID/roadtrip-backup:latest
```

### 4. Deploy Backup Job

#### Option A: Kubernetes CronJob

```bash
# Apply CronJob configuration
kubectl apply -f infrastructure/backup/backup-cronjob.yaml
```

#### Option B: Cloud Scheduler + Cloud Run

```bash
# Create Cloud Run job
gcloud run jobs replace infrastructure/backup/cloud-run-backup-job.yaml \
    --region=us-central1

# Create Cloud Scheduler job
gcloud scheduler jobs create http roadtrip-db-backup \
    --location=us-central1 \
    --schedule="0 2 * * *" \
    --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/YOUR_PROJECT_ID/jobs/roadtrip-db-backup:run" \
    --http-method=POST \
    --oidc-service-account-email=roadtrip-backup@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

## Backup Operations

### Manual Backup

```bash
# Run backup manually
python scripts/database_backup.py backup

# Skip compression (faster but larger)
python scripts/database_backup.py backup --no-compress

# Local backup only (no GCS upload)
python scripts/database_backup.py backup --no-upload
```

### List Backups

```bash
# List all available backups
python scripts/database_backup.py list

# Output example:
# Available backups (15 total):
# Name                                    Location   Size (MB)  Created
# roadtrip_backup_20240115_020000.sql.gz gcs        45.23      2024-01-15 02:00:00
# roadtrip_backup_20240114_020000.sql.gz gcs        44.89      2024-01-14 02:00:00
```

### Restore Backup

```bash
# Restore latest backup
python scripts/database_backup.py restore --backup-name roadtrip_backup_20240115_020000.sql.gz

# Restore to different database
python scripts/database_backup.py restore \
    --backup-name roadtrip_backup_20240115_020000.sql.gz \
    --target-database roadtrip_staging
```

### Cleanup Old Backups

```bash
# Remove backups older than 30 days
python scripts/database_backup.py cleanup --retention-days 30
```

## Monitoring

### Backup Success Metrics

Create an alert for backup failures:

```yaml
# monitoring/backup-failure-alert.yaml
displayName: Database Backup Failure
conditions:
  - displayName: Backup job failed
    conditionThreshold:
      filter: |
        resource.type="k8s_job"
        resource.labels.job_name="postgres-backup-*"
        jsonPayload.severity="ERROR"
      comparison: COMPARISON_GT
      thresholdValue: 0
      duration: 0s
```

### Backup Size Monitoring

Monitor backup sizes to detect issues:

```yaml
# monitoring/backup-size-alert.yaml
displayName: Abnormal Backup Size
conditions:
  - displayName: Backup too small
    conditionThreshold:
      filter: |
        metric.type="storage.googleapis.com/storage/object/size"
        resource.type="gcs_bucket"
        resource.label.bucket_name="roadtrip-db-backups"
      comparison: COMPARISON_LT
      thresholdValue: 10485760  # 10MB
```

## Recovery Procedures

### Disaster Recovery

1. **Identify Recovery Point**
   ```bash
   # List available backups
   python scripts/database_backup.py list
   ```

2. **Create New Database Instance** (if needed)
   ```bash
   gcloud sql instances create roadtrip-recovery \
       --database-version=POSTGRES_15 \
       --tier=db-g1-small \
       --region=us-central1
   ```

3. **Restore Backup**
   ```bash
   # Download and restore
   python scripts/database_backup.py restore \
       --backup-name roadtrip_backup_20240115_020000.sql.gz \
       --target-database postgresql://user:pass@new-host/roadtrip
   ```

4. **Verify Data Integrity**
   ```sql
   -- Check record counts
   SELECT 'users' as table_name, COUNT(*) as count FROM users
   UNION ALL
   SELECT 'stories', COUNT(*) FROM stories
   UNION ALL
   SELECT 'bookings', COUNT(*) FROM bookings;
   ```

5. **Update Application Configuration**
   ```bash
   # Update Secret Manager with new database URL
   gcloud secrets versions add roadtrip-database-url \
       --data-file=- <<< "postgresql://user:pass@new-host/roadtrip"
   ```

### Point-in-Time Recovery

For Cloud SQL instances with point-in-time recovery:

```bash
# Restore to specific timestamp
gcloud sql instances restore-backup roadtrip-prod \
    --backup-id=BACKUP_ID \
    --backup-instance=roadtrip-prod
```

## Best Practices

### 1. Backup Verification

Always verify backups after creation:
- Check file size is reasonable
- Test restore to staging environment monthly
- Monitor backup completion metrics

### 2. Security

- Encrypt backups at rest (GCS default)
- Use service accounts with minimal permissions
- Rotate database passwords after restore operations
- Audit backup access logs

### 3. Retention Policy

Recommended retention:
- Daily backups: 7 days
- Weekly backups: 4 weeks  
- Monthly backups: 12 months
- Yearly backups: 7 years (compliance)

### 4. Testing

Regular recovery drills:
```bash
# Monthly recovery test
./scripts/disaster_recovery_drill.sh
```

## Troubleshooting

### Common Issues

1. **pg_dump: command not found**
   - Install PostgreSQL client tools
   - Check PATH environment variable

2. **Permission denied accessing GCS**
   - Verify service account permissions
   - Check GOOGLE_APPLICATION_CREDENTIALS

3. **Backup too large**
   - Enable compression
   - Increase retention cleanup frequency
   - Consider incremental backups

4. **Restore fails with errors**
   - Check target database exists
   - Verify user permissions
   - Review error logs for constraints

### Debug Mode

Enable verbose logging:
```bash
export LOG_LEVEL=DEBUG
python scripts/database_backup.py backup
```

## Cost Optimization

### Storage Costs

- Compressed backups: ~80% size reduction
- Lifecycle policies: Auto-delete old backups
- Storage class: Use STANDARD for recent, NEARLINE for archives

### Estimate Monthly Costs

```
Database size: 10GB
Compression ratio: 80%
Daily backup size: 2GB
Monthly storage: 60GB (30 days retention)
Cost: ~$1.20/month (STANDARD storage)
```

## Advanced Configuration

### Incremental Backups

For large databases, consider WAL archiving:

```bash
# Enable WAL archiving in postgresql.conf
archive_mode = on
archive_command = 'gsutil cp %p gs://roadtrip-wal-archive/%f'
```

### Parallel Backup

For faster backups of large databases:

```bash
pg_dump -j 4  # Use 4 parallel jobs
```

### Custom Retention

Implement custom retention in backup script:

```python
# Keep daily for 7 days, weekly for 4 weeks, monthly forever
def should_keep_backup(backup_date):
    age = datetime.now() - backup_date
    if age.days <= 7:
        return True  # Keep all recent
    elif age.days <= 28 and backup_date.weekday() == 0:
        return True  # Keep Mondays
    elif backup_date.day == 1:
        return True  # Keep first of month
    return False
```

## Integration with CI/CD

### Pre-deployment Backup

Add to deployment pipeline:

```yaml
# .github/workflows/deploy.yml
- name: Backup database
  run: |
    python scripts/database_backup.py backup
  env:
    DATABASE_URL: ${{ secrets.DATABASE_URL }}
```

### Post-deployment Verification

```yaml
- name: Verify deployment
  run: |
    # Check database connectivity
    python scripts/health_check.py database
```