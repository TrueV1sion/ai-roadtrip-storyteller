# Backup and Restore Procedures

**Last Updated:** December 13, 2024  
**Document Version:** 1.0  
**Critical Document - Required for Production Operations**

## Overview

This document provides step-by-step procedures for backing up and restoring critical data for the AI Road Trip Storyteller application. All procedures have been tested and verified.

## Table of Contents

1. [PostgreSQL Database](#postgresql-database)
2. [Redis Cache](#redis-cache)
3. [Application Secrets](#application-secrets)
4. [User-Generated Content](#user-generated-content)
5. [Disaster Recovery](#disaster-recovery)
6. [Monitoring & Alerts](#monitoring--alerts)

## PostgreSQL Database

### Automated Backups

PostgreSQL backups are automatically configured via Cloud SQL with the following settings:
- **Schedule**: Daily at 3:00 AM UTC
- **Retention**: 30 days
- **Point-in-Time Recovery**: 7 days of transaction logs
- **Location**: Multi-regional storage

### Manual Backup Procedure

```bash
# 1. Create on-demand backup
gcloud sql backups create \
  --instance=roadtrip-db-prod \
  --description="Manual backup $(date +%Y%m%d_%H%M%S)"

# 2. Verify backup creation
gcloud sql backups list --instance=roadtrip-db-prod

# 3. Export to GCS (optional, for long-term storage)
gcloud sql export sql roadtrip-db-prod \
  gs://roadtrip-sql-backups/manual/backup_$(date +%Y%m%d_%H%M%S).sql \
  --database=roadtrip
```

### Restore Procedures

#### Scenario 1: Point-in-Time Recovery (Data Corruption)

**Use when**: Need to restore to a specific moment within the last 7 days

```bash
# 1. Identify the target timestamp
TARGET_TIMESTAMP="2024-12-12T15:30:00Z"

# 2. Create new instance from point-in-time
gcloud sql instances clone roadtrip-db-prod roadtrip-db-recovery \
  --point-in-time="${TARGET_TIMESTAMP}"

# 3. Verify data integrity
psql -h <RECOVERY_INSTANCE_IP> -U roadtrip -d roadtrip \
  -c "SELECT COUNT(*) FROM users;"

# 4. Switch application to recovery instance
# Update DATABASE_URL in Secret Manager
python scripts/migrate_secrets.py update DATABASE_URL \
  "postgresql://roadtrip:${DB_PASSWORD}@${RECOVERY_IP}:5432/roadtrip"

# 5. After verification, promote recovery instance
gcloud sql instances patch roadtrip-db-recovery \
  --rename=roadtrip-db-prod
```

**Time to Recovery**: 15-30 minutes

#### Scenario 2: Full Backup Restore (Complete Loss)

**Use when**: Instance is completely lost or corrupted beyond point-in-time recovery

```bash
# 1. List available backups
gcloud sql backups list --instance=roadtrip-db-prod

# 2. Create new instance from backup
BACKUP_ID="1234567890"
gcloud sql backups restore $BACKUP_ID \
  --restore-instance=roadtrip-db-prod-restored

# 3. Verify restoration
gcloud sql instances describe roadtrip-db-prod-restored

# 4. Run verification script
python scripts/verify_backup.py \
  --instance roadtrip-db-prod-restored \
  --test-queries
```

**Time to Recovery**: 30-60 minutes

#### Scenario 3: Cross-Region Disaster Recovery

**Use when**: Entire region is unavailable

```bash
# 1. Create instance in backup region
gcloud sql instances create roadtrip-db-dr \
  --database-version=POSTGRES_15 \
  --tier=db-g1-small \
  --region=us-east1 \
  --network=roadtrip-vpc

# 2. Restore from GCS backup
gcloud sql import sql roadtrip-db-dr \
  gs://roadtrip-sql-backups/daily/latest.sql \
  --database=roadtrip

# 3. Update application configuration
kubectl set env deployment/roadtrip-api \
  DATABASE_URL="postgresql://roadtrip:${DB_PASSWORD}@${DR_IP}:5432/roadtrip"
```

**Time to Recovery**: 45-90 minutes

## Redis Cache

### Automated Backups

Redis backups run via scheduled job:
- **Schedule**: Every 6 hours
- **Retention**: 7 days
- **Storage**: Google Cloud Storage
- **Compression**: gzip

### Manual Backup Procedure

```bash
# 1. Trigger manual backup
python scripts/redis_backup.py backup \
  --redis-url "${REDIS_URL}" \
  --name "manual_$(date +%Y%m%d_%H%M%S)"

# 2. Verify backup
python scripts/redis_backup.py list --days 1

# 3. Download backup locally (optional)
gsutil cp gs://roadtrip-redis-backups/redis_backup_*.rdb.gz ./
```

### Restore Procedures

#### Scenario 1: Cache Corruption

**Use when**: Redis data is corrupted but instance is running

```bash
# 1. List recent backups
python scripts/redis_backup.py list

# 2. Clear existing data
redis-cli -h redis.roadtrip.internal FLUSHALL

# 3. Restore from backup
python scripts/redis_backup.py restore redis_backup_20241213_030000

# 4. Verify restoration
redis-cli -h redis.roadtrip.internal INFO keyspace
```

**Time to Recovery**: 5-10 minutes

#### Scenario 2: Complete Redis Loss

**Use when**: Redis instance is completely unavailable

```bash
# 1. Deploy new Redis instance
kubectl apply -f infrastructure/k8s/redis.yaml

# 2. Wait for instance to be ready
kubectl wait --for=condition=ready pod -l app=redis

# 3. Restore latest backup
LATEST_BACKUP=$(python scripts/redis_backup.py list --days 1 | head -1)
python scripts/redis_backup.py restore "${LATEST_BACKUP}" \
  --target-redis "redis://new-redis:6379"

# 4. Update service endpoints
kubectl patch service redis -p '{"spec":{"selector":{"version":"new"}}}'
```

**Time to Recovery**: 10-15 minutes

## Application Secrets

### Backup Procedure

Secrets are versioned in Google Secret Manager, but additional backup is recommended:

```bash
# 1. Export all secrets
python scripts/export_secrets.py \
  --project roadtrip-prod \
  --output secrets_backup_$(date +%Y%m%d).json \
  --encrypt

# 2. Store encrypted backup
gsutil cp secrets_backup_*.json \
  gs://roadtrip-disaster-recovery/secrets/

# 3. Store encryption key separately (HSM or secure vault)
```

### Restore Procedure

```bash
# 1. Decrypt backup
python scripts/decrypt_secrets.py \
  --input secrets_backup_20241213.json \
  --key-file /secure/encryption.key

# 2. Import to Secret Manager
python scripts/import_secrets.py \
  --project roadtrip-prod \
  --input decrypted_secrets.json

# 3. Restart applications to pick up new secrets
kubectl rollout restart deployment/roadtrip-api
```

**Time to Recovery**: 10-15 minutes

## User-Generated Content

### Photo Backups

Photos are stored in Google Cloud Storage with versioning enabled:

```bash
# 1. Enable versioning (already configured)
gsutil versioning set on gs://roadtrip-user-photos

# 2. List versions of a specific file
gsutil ls -a gs://roadtrip-user-photos/users/123/photo.jpg

# 3. Restore previous version
gsutil cp gs://roadtrip-user-photos/users/123/photo.jpg#1234567890 \
  gs://roadtrip-user-photos/users/123/photo.jpg
```

### Story Content Backup

```bash
# 1. Export stories from database
psql -h $DB_HOST -U roadtrip -d roadtrip \
  -c "\COPY stories TO '/tmp/stories_backup.csv' CSV HEADER"

# 2. Backup to GCS
gsutil cp /tmp/stories_backup.csv \
  gs://roadtrip-content-backup/stories/$(date +%Y%m%d)/
```

## Disaster Recovery

### Full System Recovery Procedure

**Scenario**: Complete regional outage or catastrophic failure

1. **Activate DR Plan** (5 minutes)
   ```bash
   ./scripts/activate_dr.sh --region us-east1
   ```

2. **Database Recovery** (30 minutes)
   - Follow Cross-Region Disaster Recovery procedure above

3. **Redis Recovery** (10 minutes)
   - Deploy fresh Redis instance
   - Application will rebuild cache automatically

4. **Application Deployment** (15 minutes)
   ```bash
   # Deploy to DR region
   kubectl config use-context gke_roadtrip-prod_us-east1_roadtrip-dr
   kubectl apply -f infrastructure/k8s/
   ```

5. **DNS Failover** (5-15 minutes)
   ```bash
   gcloud dns record-sets transaction start --zone=roadtrip-zone
   gcloud dns record-sets transaction remove \
     --name=api.roadtrip.app --ttl=300 --type=A --zone=roadtrip-zone \
     --rrdatas=PRIMARY_IP
   gcloud dns record-sets transaction add \
     --name=api.roadtrip.app --ttl=60 --type=A --zone=roadtrip-zone \
     --rrdatas=DR_IP
   gcloud dns record-sets transaction execute --zone=roadtrip-zone
   ```

6. **Verification** (10 minutes)
   ```bash
   ./scripts/verify_dr.sh --comprehensive
   ```

**Total Time to Recovery**: 60-90 minutes

### Recovery Priority Order

1. **Critical** (First 30 minutes)
   - Database restoration
   - Authentication services
   - Core API endpoints

2. **High** (30-60 minutes)
   - Voice services
   - Booking integrations
   - User sessions

3. **Medium** (60-90 minutes)
   - Analytics
   - Background jobs
   - Email notifications

4. **Low** (Post-recovery)
   - Historical metrics
   - Development environments
   - Non-essential features

## Monitoring & Alerts

### Backup Monitoring

All backup jobs are monitored with alerts for:
- Backup failure
- Backup duration > 2 hours
- Storage quota exceeded
- Verification failure

### Alert Responses

| Alert | Response Time | Action |
|-------|--------------|--------|
| Backup Failed | 15 min | Run manual backup |
| Restore Test Failed | 1 hour | Investigate and fix |
| Storage Quota Warning | 4 hours | Cleanup old backups |
| Verification Failed | 30 min | Re-run verification |

### Regular Testing

- **Weekly**: Automated restore test (Sundays 6 AM)
- **Monthly**: Manual DR drill (First Tuesday)
- **Quarterly**: Full system recovery test

## Appendix

### Useful Commands

```bash
# Check backup status
./scripts/backup_status.sh --all

# Verify all backups
./scripts/verify_all_backups.sh

# Generate backup report
./scripts/backup_report.sh --email ops@roadtrip.app
```

### Contact Information

- **On-Call**: Available in PagerDuty
- **Escalation**: CTO (30 min), CEO (60 min)
- **External Support**: Google Cloud Support (Premium)

### Related Documents

- [PRODUCTION_LAUNCH_CHECKLIST.md](../PRODUCTION_LAUNCH_CHECKLIST.md)
- [SECURITY_INCIDENT_RESPONSE.md](../SECURITY_INCIDENT_RESPONSE.md)
- [scripts/verify_backup.py](../scripts/verify_backup.py)
- [scripts/redis_backup.py](../scripts/redis_backup.py)

---

**Remember**: Practice makes perfect. Regular drills ensure smooth recovery when it matters.