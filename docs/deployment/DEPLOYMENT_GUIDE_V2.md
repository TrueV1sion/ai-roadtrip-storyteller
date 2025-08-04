# AI Road Trip Storyteller - Deployment Guide V2

## Overview

This guide covers the deployment of the enhanced AI Road Trip Storyteller application with new features including journey tracking, story timing, AR/spatial audio, and comprehensive security improvements.

## Architecture Updates

### New Services
1. **Knowledge Graph Service** - Code intelligence and impact analysis
2. **Journey Tracking** - Real-time trip monitoring
3. **Story Queue Manager** - Dynamic story delivery
4. **Spatial Audio Engine** - 3D audio processing
5. **AR Service** - Augmented reality features

### Infrastructure Changes
- Backend: 4Gi RAM, 4 CPU (increased from 2Gi/2)
- Database: Upgraded to n1-standard-2
- Redis: 2GB (increased from 1GB)
- New storage buckets for audio/AR content

## Pre-Deployment Checklist

### 1. Environment Setup
- [ ] GCP Project configured
- [ ] Service accounts created
- [ ] VPC connector established
- [ ] SSL certificates ready
- [ ] Domain DNS configured

### 2. Secrets Management
```bash
# Create required secrets
gcloud secrets create roadtrip-2fa-secret --data-file=2fa_secret.txt
gcloud secrets create roadtrip-audio-encryption-key --data-file=audio_key.txt
gcloud secrets create roadtrip-ar-api-key --data-file=ar_key.txt
```

### 3. Database Preparation
```bash
# Run migrations
./scripts/deployment/run-migrations.sh
```

## Deployment Steps

### Step 1: Deploy Knowledge Graph

```bash
# Deploy Knowledge Graph service first
./scripts/deployment/deploy-knowledge-graph.sh

# Verify deployment
curl https://roadtrip-knowledge-graph-*.run.app/api/health
```

### Step 2: Deploy Backend

```bash
# Submit to Cloud Build
gcloud builds submit --config=backend/cloudbuild.yaml .

# Monitor deployment
gcloud builds log [BUILD_ID]
```

### Step 3: Deploy Monitoring Stack

```bash
# Deploy monitoring infrastructure
docker-compose -f infrastructure/docker/docker-compose.monitoring.yml up -d

# Access dashboards
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000
# AlertManager: http://localhost:9093
```

### Step 4: Mobile App Deployment

```bash
# Build and deploy mobile apps
cd mobile
./scripts/deployment/build-mobile-production.sh all production

# Monitor builds at https://expo.dev
```

## Configuration Reference

### Environment Variables

#### Backend
```env
# Core
ENVIRONMENT=production
PORT=8080
LOG_LEVEL=INFO

# Features
ENABLE_JOURNEY_TRACKING=true
ENABLE_AR_FEATURES=true
ENABLE_SPATIAL_AUDIO=true
ENABLE_2FA=true

# Story Timing
STORY_CHECK_INTERVAL=300
MIN_STORY_GAP_MINUTES=10
MAX_STORIES_PER_HOUR=4

# Audio
AUDIO_SAMPLE_RATE=48000
BINAURAL_PROCESSING=true

# Knowledge Graph
KNOWLEDGE_GRAPH_URL=https://roadtrip-knowledge-graph-*.run.app
```

#### Mobile
```env
EXPO_PUBLIC_API_URL=https://roadtrip-backend-*.run.app
EXPO_PUBLIC_ENVIRONMENT=production
EXPO_PUBLIC_SENTRY_DSN=your-sentry-dsn
EXPO_PUBLIC_ENABLE_JOURNEY_TRACKING=true
EXPO_PUBLIC_ENABLE_AR=true
EXPO_PUBLIC_ENABLE_SPATIAL_AUDIO=true
EXPO_PUBLIC_ENABLE_2FA=true
```

## Monitoring & Alerts

### Key Metrics
1. **API Performance**
   - Response time (p50, p95, p99)
   - Error rate
   - Request volume

2. **Journey Tracking**
   - Active journeys
   - Story delivery rate
   - Engagement scores

3. **AI Services**
   - API costs
   - Cache hit rates
   - Processing latency

4. **Infrastructure**
   - CPU/Memory usage
   - Database connections
   - Disk space

### Alert Thresholds
- Error rate > 1%: Critical
- P95 latency > 2s: Warning
- AI costs > $100/hour: Warning
- Memory > 90%: Critical

## Rollback Procedures

### Backend Rollback
```bash
# List revisions
gcloud run revisions list --service roadtrip-backend

# Rollback to previous
gcloud run services update-traffic roadtrip-backend \
  --to-revisions=PREVIOUS_REVISION=100
```

### Database Rollback
```bash
# Restore from backup
gcloud sql backups restore [BACKUP_ID] \
  --restore-instance=roadtrip-postgres
```

### Mobile Rollback
- iOS: Submit new build with previous version
- Android: Use staged rollout controls in Play Console

## Security Considerations

### Backend Security
- [x] JWT with RS256
- [x] CSRF protection
- [x] Rate limiting
- [x] Security headers
- [x] Two-factor authentication
- [x] Request signing

### Mobile Security
- [x] Certificate pinning
- [x] Secure token storage
- [x] Code obfuscation
- [x] Biometric authentication
- [x] Anti-tampering
- [x] No console.log in production

## Performance Optimization

### Caching Strategy
1. AI responses: 48-hour TTL
2. Static assets: CDN with 30-day cache
3. API responses: Redis with smart invalidation
4. Database: Query result caching

### Scaling Configuration
- Min instances: 2
- Max instances: 200
- Target CPU: 60%
- Target memory: 70%

## Troubleshooting

### Common Issues

1. **Knowledge Graph Connection Failed**
   ```bash
   # Check service status
   gcloud run services describe roadtrip-knowledge-graph
   
   # Verify network connectivity
   curl https://roadtrip-knowledge-graph-*.run.app/api/health
   ```

2. **Story Timing Not Working**
   ```bash
   # Check Celery workers
   kubectl logs -l app=celery-worker
   
   # Verify Redis connection
   redis-cli ping
   ```

3. **Mobile Build Failures**
   ```bash
   # Check EAS status
   eas build:list --platform=all
   
   # View build logs
   eas build:view [BUILD_ID]
   ```

## Post-Deployment Tasks

### 1. Verification
- [ ] All health checks passing
- [ ] Critical user journeys tested
- [ ] Monitoring dashboards active
- [ ] Alerts configured

### 2. Performance Testing
```bash
# Run load tests
k6 run scripts/load-tests/production.js

# Benchmark AI performance
python scripts/benchmark-ai-performance.py
```

### 3. Security Audit
```bash
# Run security scan
./scripts/security/production-audit.sh

# Check SSL configuration
ssl-checker roadtrip-backend-*.run.app
```

## Maintenance

### Daily Tasks
- Review error logs
- Check AI costs
- Monitor performance metrics
- Verify backups

### Weekly Tasks
- Security updates
- Performance optimization
- Cost analysis
- User feedback review

### Monthly Tasks
- Full security audit
- Disaster recovery test
- Capacity planning
- Feature usage analysis

## Support

### Escalation Path
1. On-call engineer
2. Team lead
3. CTO
4. External support (GCP, etc.)

### Contact Information
- On-call: +1-XXX-XXX-XXXX
- Slack: #roadtrip-alerts
- Email: ops@roadtripapp.com

## Appendix

### Useful Commands
```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision"

# SSH to container
gcloud run services proxy roadtrip-backend

# Database console
gcloud sql connect roadtrip-postgres --user=postgres

# Clear cache
redis-cli FLUSHALL
```

### Resource Links
- [GCP Console](https://console.cloud.google.com)
- [Monitoring Dashboard](https://roadtrip-grafana.app)
- [API Documentation](https://roadtrip-backend-*.run.app/docs)
- [Knowledge Graph](https://roadtrip-knowledge-graph-*.run.app)