# AI Road Trip Storyteller - Operational Runbook

## Table of Contents

1. [System Overview](#system-overview)
2. [Critical Components](#critical-components)
3. [Standard Operating Procedures](#standard-operating-procedures)
4. [Incident Response](#incident-response)
5. [Monitoring and Alerts](#monitoring-and-alerts)
6. [Deployment Procedures](#deployment-procedures)
7. [Database Operations](#database-operations)
8. [Emergency Procedures](#emergency-procedures)
9. [Contact Information](#contact-information)

## System Overview

### Architecture Summary
- **Frontend**: React Native mobile app (iOS/Android)
- **Backend**: FastAPI Python application
- **Infrastructure**: Google Cloud Platform
  - Cloud Run (containerized backend)
  - Cloud SQL (PostgreSQL)
  - Memorystore (Redis)
  - Vertex AI (Gemini 1.5)
  - Cloud Storage (media files)

### Key Services
1. **API Service**: `roadtrip-api` on Cloud Run
2. **Database**: `roadtrip-db` on Cloud SQL
3. **Cache**: `roadtrip-redis` on Memorystore
4. **CDN**: Cloud CDN with Cloud Armor WAF

## Critical Components

### 1. Master Orchestration Agent
- **Location**: `/backend/app/services/master_orchestration_agent.py`
- **Purpose**: Routes all AI requests to specialized sub-agents
- **Sub-agents**:
  - Navigation Agent
  - Booking Agent
  - Storytelling Agent
  - Voice Agent
  - Emergency Agent

### 2. Database
- **Type**: PostgreSQL 14
- **Connection Pool**: Max 100 connections
- **Critical Tables**:
  - `users` - User accounts
  - `trips` - Trip data
  - `stories` - Generated stories
  - `bookings` - Reservations

### 3. External APIs
- Google Maps API (location services)
- OpenWeatherMap API (weather data)
- Ticketmaster API (event bookings)
- Viator API (activity bookings)

## Standard Operating Procedures

### Daily Health Checks

```bash
# 1. Check service health
curl https://api.roadtripstoryteller.com/health

# 2. Check detailed health
curl https://api.roadtripstoryteller.com/health/detailed

# 3. Check database connections
gcloud sql operations list --instance=roadtrip-db --limit=5

# 4. Check Redis memory usage
gcloud redis instances describe roadtrip-redis --region=us-central1

# 5. Review error logs
gcloud logging read "severity>=ERROR" --limit=50 --format=json
```

### Weekly Maintenance

1. **Review Metrics**
   ```bash
   # Check Prometheus metrics
   kubectl port-forward -n monitoring prometheus-0 9090:9090
   # Open http://localhost:9090
   ```

2. **Database Maintenance**
   ```bash
   # Analyze database performance
   gcloud sql operations list --instance=roadtrip-db
   
   # Check slow queries
   psql -h /cloudsql/PROJECT:REGION:roadtrip-db -U postgres -c "
   SELECT query, calls, mean_exec_time
   FROM pg_stat_statements
   ORDER BY mean_exec_time DESC
   LIMIT 10;"
   ```

3. **Security Review**
   ```bash
   # Check WAF blocked requests
   gcloud compute security-policies describe roadtrip-waf-policy
   
   # Review authentication failures
   gcloud logging read 'jsonPayload.event_type="authentication_failed"' --limit=100
   ```

### Monthly Tasks

1. **Secret Rotation**
   ```bash
   cd /scripts/security
   ./secret-rotation.sh --dry-run
   # Review output, then run without --dry-run
   ./secret-rotation.sh
   ```

2. **Backup Verification**
   ```bash
   # List recent backups
   gsutil ls gs://roadtrip-backups/roadtrip-backup-*
   
   # Test restore procedure (on staging)
   ./scripts/restore_backup.sh --backup-id=BACKUP_ID --target=staging
   ```

3. **Dependency Updates**
   ```bash
   # Backend dependencies
   cd backend
   pip list --outdated
   
   # Mobile dependencies
   cd mobile
   npm outdated
   ```

## Incident Response

### Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| P1 | Complete outage | 15 minutes | API down, database failure |
| P2 | Major degradation | 30 minutes | Booking failures, AI errors |
| P3 | Minor issues | 2 hours | Slow responses, UI bugs |
| P4 | Non-critical | Next business day | Feature requests |

### P1 Incident Response Playbook

1. **Acknowledge Alert** (0-5 min)
   - Respond in #oncall-alerts
   - Create incident channel #inc-YYYYMMDD-description

2. **Initial Assessment** (5-15 min)
   ```bash
   # Check service status
   gcloud run services describe roadtrip-api --region=us-central1
   
   # Check recent deployments
   gcloud run revisions list --service=roadtrip-api --region=us-central1
   
   # Check database
   gcloud sql instances describe roadtrip-db
   ```

3. **Mitigation Actions**
   
   **If API is down:**
   ```bash
   # Rollback to previous version
   gcloud run services update-traffic roadtrip-api \
     --to-revisions=PREV_REVISION=100 \
     --region=us-central1
   ```
   
   **If database is down:**
   ```bash
   # Failover to replica
   gcloud sql instances failover roadtrip-db-replica
   ```
   
   **If overwhelmed by traffic:**
   ```bash
   # Scale up instances
   gcloud run services update roadtrip-api \
     --max-instances=100 \
     --region=us-central1
   ```

4. **Communication**
   - Update status page
   - Post in #incidents channel
   - Email stakeholders if > 30 min

5. **Resolution & Post-mortem**
   - Document timeline
   - Identify root cause
   - Create action items
   - Schedule retrospective

### Common Issues and Solutions

#### High Memory Usage
```bash
# Check memory metrics
gcloud monitoring time-series list \
  --filter='metric.type="run.googleapis.com/container/memory/utilizations"'

# Solution: Restart service
gcloud run services update roadtrip-api --no-traffic --region=us-central1
```

#### Database Connection Pool Exhausted
```bash
# Check active connections
psql -c "SELECT count(*) FROM pg_stat_activity;"

# Solution: Kill idle connections
psql -c "SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' AND state_change < now() - interval '10 minutes';"
```

#### Redis Memory Full
```bash
# Check memory usage
gcloud redis instances describe roadtrip-redis --region=us-central1

# Solution: Flush old cache
redis-cli -h REDIS_IP FLUSHDB
```

#### AI Service Errors
```bash
# Check Vertex AI quota
gcloud compute project-info describe --project=PROJECT_ID

# Solution: Implement fallback
# Enable cache-only mode in app config
```

## Monitoring and Alerts

### Key Metrics to Monitor

1. **API Health**
   - Request rate: > 1000 req/min warning
   - Error rate: > 5% critical
   - P95 latency: > 2s warning
   - P99 latency: > 5s critical

2. **Database**
   - CPU usage: > 80% warning
   - Connection pool: > 90% critical
   - Replication lag: > 5s warning
   - Storage: > 85% warning

3. **AI Services**
   - Token usage: > 80% quota warning
   - API errors: > 10/min critical
   - Response time: > 10s warning

### Alert Channels
- **PagerDuty**: P1/P2 incidents
- **Slack**: #alerts channel
- **Email**: ops-team@roadtripstoryteller.com

### Dashboards
- **Grafana**: http://monitoring.roadtripstoryteller.com
  - System Overview
  - API Performance
  - Database Metrics
  - AI Usage
- **Google Cloud Console**: 
  - Cloud Run metrics
  - Cloud SQL insights
  - Error Reporting

## Deployment Procedures

### Standard Deployment

1. **Pre-deployment Checks**
   ```bash
   # Run tests
   pytest
   
   # Build and test Docker image
   docker build -t roadtrip-api:test .
   docker run --rm roadtrip-api:test pytest
   ```

2. **Deploy to Staging**
   ```bash
   # Deploy to staging
   gcloud run deploy roadtrip-api-staging \
     --image gcr.io/PROJECT/roadtrip-api:TAG \
     --region us-central1
   
   # Run smoke tests
   ./scripts/smoke_tests.sh staging
   ```

3. **Production Deployment**
   ```bash
   # Canary deployment (10%)
   gcloud run services update-traffic roadtrip-api \
     --to-tags=canary=10 \
     --region=us-central1
   
   # Monitor for 30 minutes
   ./scripts/monitor_canary.sh
   
   # Full deployment
   gcloud run services update-traffic roadtrip-api \
     --to-latest=100 \
     --region=us-central1
   ```

### Rollback Procedure

```bash
# List recent revisions
gcloud run revisions list --service=roadtrip-api

# Rollback to specific revision
gcloud run services update-traffic roadtrip-api \
  --to-revisions=roadtrip-api-00123=100 \
  --region=us-central1
```

## Database Operations

### Backup Procedures

**Automated Backups** (via cron job):
```bash
0 2 * * * /scripts/database_backup.sh
```

**Manual Backup**:
```bash
# Create on-demand backup
gcloud sql backups create \
  --instance=roadtrip-db \
  --description="Manual backup before migration"

# Export to Cloud Storage
gcloud sql export sql roadtrip-db \
  gs://roadtrip-backups/manual-$(date +%Y%m%d-%H%M%S).sql \
  --database=roadtrip_prod
```

### Restore Procedures

```bash
# From automated backup
gcloud sql backups restore BACKUP_ID \
  --restore-instance=roadtrip-db

# From Cloud Storage export
gcloud sql import sql roadtrip-db \
  gs://roadtrip-backups/backup-file.sql \
  --database=roadtrip_prod
```

### Schema Migrations

```bash
# Generate migration
cd backend
alembic revision --autogenerate -m "Description"

# Review migration
cat alembic/versions/latest_migration.py

# Apply migration (staging first)
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

## Emergency Procedures

### Complete Outage Recovery

1. **Assess Damage**
   ```bash
   # Check all services
   ./scripts/health_check_all.sh
   ```

2. **Start Core Services**
   ```bash
   # 1. Database
   gcloud sql instances describe roadtrip-db
   
   # 2. Redis
   gcloud redis instances describe roadtrip-redis
   
   # 3. API
   gcloud run services describe roadtrip-api
   ```

3. **Verify Data Integrity**
   ```bash
   # Check database
   psql -c "SELECT COUNT(*) FROM users;"
   psql -c "SELECT COUNT(*) FROM trips;"
   ```

### Data Breach Response

1. **Immediate Actions**
   - Disable affected user accounts
   - Rotate all secrets
   - Enable enhanced logging

2. **Investigation**
   ```bash
   # Check access logs
   gcloud logging read "protoPayload.authenticationInfo.principalEmail!=null" \
     --limit=1000 --format=json
   ```

3. **Communication**
   - Legal team notification
   - Prepare user communication
   - Update security measures

### DDoS Attack Response

1. **Enable Enhanced Protection**
   ```bash
   # Update Cloud Armor policy
   gcloud compute security-policies update roadtrip-waf-policy \
     --enable-layer7-ddos-defense
   ```

2. **Scale Resources**
   ```bash
   # Increase Cloud Run instances
   gcloud run services update roadtrip-api \
     --max-instances=200 \
     --region=us-central1
   ```

3. **Block Suspicious IPs**
   ```bash
   # Add IP to blocklist
   gcloud compute security-policies rules create 9999 \
     --security-policy=roadtrip-waf-policy \
     --action=deny-403 \
     --src-ip-ranges=ATTACKER_IP
   ```

## Contact Information

### Escalation Matrix

| Role | Name | Contact | When to Contact |
|------|------|---------|----------------|
| On-Call Engineer | Rotation | PagerDuty | First response |
| Engineering Lead | John Smith | john@company.com | P1 incidents |
| VP Engineering | Jane Doe | jane@company.com | P1 > 1 hour |
| CTO | Bob Wilson | bob@company.com | Data breach |

### External Contacts

| Service | Support Level | Contact | Account # |
|---------|--------------|---------|-----------|
| Google Cloud | Premium | 1-855-817-1444 | 12345 |
| Vertex AI | Included | GCP Support | - |
| Ticketmaster | Partner | partner@ticketmaster.com | RT-789 |
| Viator | API Support | api@viator.com | RT-456 |

### Key Slack Channels
- `#oncall-alerts` - Automated alerts
- `#incidents` - Incident coordination
- `#engineering` - General engineering
- `#deployments` - Deployment notifications

## Appendix

### Useful Commands Cheatsheet

```bash
# Get API logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=roadtrip-api" --limit=100

# SSH to Cloud SQL
gcloud sql connect roadtrip-db --user=postgres

# Port forward to Redis
gcloud compute ssh redis-forwarder -- -N -L 6379:REDIS_IP:6379

# Check SSL certificate
openssl s_client -connect api.roadtripstoryteller.com:443 -servername api.roadtripstoryteller.com

# Test API endpoint
curl -X POST https://api.roadtripstoryteller.com/api/health \
  -H "Authorization: Bearer $TOKEN"

# Monitor real-time logs
gcloud logging tail "resource.type=cloud_run_revision"
```

### Environment Variables Reference
See `/backend/.env.example` for complete list

### Migration History
See `/docs/MIGRATION_HISTORY.md` for database schema changes