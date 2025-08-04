# AI Road Trip Storyteller - Deployment Guide

## Overview

This guide covers deploying the AI Road Trip Storyteller application. **The backend is already deployed to production** at `https://roadtrip-mvp-792001900150.us-central1.run.app`. This guide covers updating the deployment and preparing the mobile app for release.

## Prerequisites

- Docker and Docker Compose installed
- Google Cloud Project configured (see `google_cloud_setup.md`)
- Google Secret Manager configured (see `google_secret_manager_setup.md`)
- Domain name (for HTTPS)
- SSL certificates
- Production database (PostgreSQL)
- Redis instance (for caching)

## Environment Setup

### 1. Production Secrets Management

**IMPORTANT**: In production, sensitive credentials are stored in Google Secret Manager, not in `.env` files.

#### Setup Secret Manager:
```bash
# Migrate secrets from .env to Secret Manager
python scripts/migrate_to_secret_manager.py

# Verify secrets are accessible
python scripts/test_secret_manager.py
```

#### Minimal Production Environment Variables:
```bash
# Only non-sensitive configuration in .env
APP_VERSION=1.0.0
ENVIRONMENT=production
GOOGLE_CLOUD_PROJECT_ID=your-prod-project-id
GOOGLE_AI_LOCATION=us-central1
GOOGLE_AI_MODEL=gemini-1.5-pro

# All sensitive values (API keys, passwords) are in Secret Manager
```

See `production_secrets_guide.md` for detailed Secret Manager setup.

### 2. SSL Certificates

Place your SSL certificates in `config/ssl/`:
- `cert.pem` - SSL certificate
- `key.pem` - Private key

For testing, you can generate self-signed certificates:
```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout config/ssl/key.pem \
  -out config/ssl/cert.pem
```

## Current Production Deployment

### Backend (Already Deployed)

**Production URL**: `https://roadtrip-mvp-792001900150.us-central1.run.app`

**Check deployment status**:
```bash
# Health check
curl https://roadtrip-mvp-792001900150.us-central1.run.app/health

# View API docs
open https://roadtrip-mvp-792001900150.us-central1.run.app/docs

# Check current revision
gcloud run services describe roadtrip-backend --region=us-central1
```

### Option 2: Kubernetes (GKE)

See `infrastructure/k8s/` directory for Kubernetes manifests.

1. Create namespace:
```bash
kubectl create namespace roadtrip-prod
```

2. Create secrets:
```bash
kubectl create secret generic roadtrip-secrets \
  --from-env-file=.env \
  -n roadtrip-prod
```

3. Apply manifests:
```bash
kubectl apply -f infrastructure/k8s/ -n roadtrip-prod
```

### Updating Backend Deployment

1. **Make code changes and test locally**:
```bash
# Run tests
pytest

# Test with Docker
docker-compose up
```

2. **Deploy updates to Cloud Run**:
```bash
# Use the deployment script
./scripts/deployment/deploy.sh --project-id roadtrip-mvp

# Or manually:
gcloud builds submit --tag gcr.io/roadtrip-mvp/roadtrip-backend:latest
gcloud run deploy roadtrip-backend \
  --image gcr.io/roadtrip-mvp/roadtrip-backend:latest \
  --region us-central1
```

3. **Verify deployment**:
```bash
# Check new revision is serving traffic
gcloud run services describe roadtrip-backend --region=us-central1

# Test endpoints
curl https://roadtrip-mvp-792001900150.us-central1.run.app/health
```

## Mobile App Deployment

### Prerequisites for Mobile Release

**Critical Security Fixes Required (4-5 weeks)**:
1. Remove 200+ console.log statements
2. Replace hardcoded API keys
3. Implement crash reporting (Sentry)
4. Add certificate pinning
5. Fix token storage security

### iOS Deployment Process

1. **Configure production environment**:
```bash
# Update app.json
{
  "expo": {
    "extra": {
      "apiUrl": "https://roadtrip-mvp-792001900150.us-central1.run.app"
    }
  }
}
```

2. **Build for iOS**:
```bash
cd mobile
eas build --platform ios --profile production
```

3. **Submit to App Store**:
```bash
eas submit --platform ios
```

### Android Deployment Process

1. **Enable obfuscation**:
```bash
# android/app/build.gradle
release {
    minifyEnabled true
    proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
}
```

2. **Build and submit**:
```bash
eas build --platform android --profile production
eas submit --platform android
```

2. Create database and user:
```sql
CREATE DATABASE roadtrip_prod;
CREATE USER roadtrip_app WITH ENCRYPTED PASSWORD 'strong-password';
GRANT ALL PRIVILEGES ON DATABASE roadtrip_prod TO roadtrip_app;
```

3. Run migrations:
```bash
DATABASE_URL=<prod-database-url> alembic upgrade head
```

## Monitoring Setup

### 1. Application Metrics

The application exposes Prometheus metrics at `/metrics`.

### 2. Google Cloud Monitoring

Enable Cloud Monitoring for comprehensive observability:

```bash
# Install monitoring agent on VMs
curl -sSO https://dl.google.com/cloudagents/add-google-cloud-ops-agent-repo.sh
sudo bash add-google-cloud-ops-agent-repo.sh --also-install
```

### 3. Alerts

Set up alerts for:
- High error rates
- Slow response times
- Database connection issues
- Memory/CPU usage
- API quota limits

## Security Checklist

- [ ] Strong SECRET_KEY generated
- [ ] Database credentials secured
- [ ] SSL certificates valid
- [ ] API keys restricted by IP/referrer
- [ ] CORS origins properly configured
- [ ] Rate limiting enabled
- [ ] Security headers configured
- [ ] Monitoring alerts set up
- [ ] Backup strategy implemented
- [ ] Incident response plan ready

## Performance Optimization

### 1. Enable Caching

Ensure Redis is properly configured for caching:
- Story responses
- API responses
- Session data

### 2. CDN Setup

For static content and API responses:

```bash
# Enable Cloud CDN for load balancer
gcloud compute backend-services update roadtrip-backend \
  --enable-cdn \
  --cache-mode=CACHE_ALL_STATIC
```

### 3. Database Optimization

- Create appropriate indexes
- Enable connection pooling
- Set up read replicas for scaling

## Backup and Disaster Recovery

### 1. Database Backups

Automated daily backups:
```bash
# Cloud SQL automatic backups
gcloud sql instances patch roadtrip-prod \
  --backup-start-time=02:00
```

### 2. Application State

- Redis persistence enabled
- Regular GCS bucket backups
- Configuration backed up

## Rollback Procedure

1. Keep previous Docker images tagged:
```bash
docker tag gcr.io/$PROJECT_ID/roadtrip-backend:latest \
  gcr.io/$PROJECT_ID/roadtrip-backend:v1.0.0
```

2. Quick rollback:
```bash
# Docker Compose
docker-compose -f docker-compose.prod.yml pull
docker-compose -f docker-compose.prod.yml up -d

# Cloud Run
gcloud run deploy roadtrip-backend \
  --image gcr.io/$PROJECT_ID/roadtrip-backend:previous-version
```

## Troubleshooting

### Common Issues

1. **Container won't start**
   - Check logs: `docker logs roadtrip-backend`
   - Verify environment variables
   - Test database connectivity

2. **High latency**
   - Check Redis connection
   - Monitor API quotas
   - Review database query performance

3. **Memory issues**
   - Increase container memory limits
   - Check for memory leaks
   - Enable memory profiling

### Useful Commands

```bash
# View logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Enter container
docker-compose -f docker-compose.prod.yml exec backend bash

# Check resource usage
docker stats

# Database connection test
docker-compose -f docker-compose.prod.yml exec backend \
  python -c "from app.database import engine; print('DB OK')"
```

## Maintenance

### Regular Tasks

- Weekly: Review logs and metrics
- Monthly: Update dependencies
- Quarterly: Security audit
- Yearly: Disaster recovery test

### Update Procedure

1. Test updates in staging
2. Schedule maintenance window
3. Backup current state
4. Deploy new version
5. Run smoke tests
6. Monitor for issues

## Production Monitoring

### Current Monitoring Setup
- **Metrics**: Prometheus at `/metrics` endpoint
- **Logs**: Google Cloud Logging
- **Uptime**: 99.9% over last 30 days
- **Response Time**: <200ms (p95)

### Mobile Monitoring (To Be Implemented)
- **Crash Reporting**: Sentry (configured but not active)
- **Analytics**: Google Analytics (planned)
- **Performance**: Firebase Performance (planned)

## Support & Troubleshooting

### Backend Issues
1. Check Cloud Run logs:
   ```bash
   gcloud logging read "resource.type=cloud_run_revision"
   ```
2. View metrics in Cloud Console
3. Check database connections
4. Review Redis cache hit rates

### Mobile Issues
1. Currently no crash reporting (implement Sentry)
2. Check device logs during development
3. Use Expo dev tools for debugging
4. Review network requests in Flipper

## Next Steps

1. **Immediate** (Week 1): Fix mobile security issues
2. **Short-term** (Weeks 2-4): Complete mobile hardening
3. **Pre-launch** (Week 5): Create app store assets
4. **Launch** (Weeks 6-7): Submit to app stores
5. **Post-launch**: Scale infrastructure based on usage