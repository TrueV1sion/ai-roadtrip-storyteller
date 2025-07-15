# AI Road Trip Storyteller - Deployment Guide

## Overview

This guide covers deploying the AI Road Trip Storyteller application to production environments.

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

## Deployment Options

### Option 1: Docker Compose (Single Server)

1. Build and start services:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

2. Run database migrations:
```bash
docker-compose -f docker-compose.prod.yml exec backend \
  alembic upgrade head
```

3. Check service health:
```bash
curl http://your-domain/health
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

### Option 3: Google Cloud Run

1. Build and push container:
```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Build and tag
docker build -t gcr.io/$PROJECT_ID/roadtrip-backend:latest .

# Push to GCR
docker push gcr.io/$PROJECT_ID/roadtrip-backend:latest
```

2. Deploy to Cloud Run:
```bash
gcloud run deploy roadtrip-backend \
  --image gcr.io/$PROJECT_ID/roadtrip-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars-from-file=.env.yaml \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 100
```

## Database Setup

### Production Database

1. Create a Cloud SQL instance (recommended for GCP):
```bash
gcloud sql instances create roadtrip-prod \
  --database-version=POSTGRES_14 \
  --tier=db-g1-small \
  --region=us-central1
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

## Support

For production issues:
1. Check application logs
2. Review monitoring dashboards
3. Consult error tracking system
4. Escalate to on-call engineer if needed