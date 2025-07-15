# Production Deployment Guide - AI Road Trip Storyteller

## Overview

This guide provides comprehensive instructions for deploying the AI Road Trip Storyteller to production on Google Cloud Platform. It covers infrastructure setup, deployment procedures, monitoring, and operational tasks.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Database Configuration](#database-configuration)
4. [Application Deployment](#application-deployment)
5. [Monitoring & Alerting](#monitoring--alerting)
6. [Security Configuration](#security-configuration)
7. [Backup & Recovery](#backup--recovery)
8. [Operational Procedures](#operational-procedures)
9. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools
```bash
# Install required tools
brew install google-cloud-sdk
brew install kubectl
brew install helm
brew install terraform

# Authenticate with GCP
gcloud auth login
gcloud config set project roadtrip-production
```

### Access Requirements
- GCP Project Owner or Editor role
- Access to production secrets in Secret Manager
- Domain control for SSL certificates
- PagerDuty account for alerting

## Infrastructure Setup

### 1. Create GCP Project
```bash
# Create new project
gcloud projects create roadtrip-production \
  --name="AI Road Trip Production" \
  --organization=YOUR_ORG_ID

# Enable required APIs
gcloud services enable \
  compute.googleapis.com \
  container.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  cloudkms.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  monitoring.googleapis.com
```

### 2. Terraform Infrastructure
```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
project_id = "roadtrip-production"
region = "us-central1"
environment = "production"
domain = "api.roadtripstoryteller.com"
EOF

# Plan and apply
terraform plan
terraform apply
```

### 3. GKE Cluster Setup
```bash
# Create GKE cluster
gcloud container clusters create roadtrip-production \
  --region us-central1 \
  --num-nodes 3 \
  --min-nodes 3 \
  --max-nodes 10 \
  --machine-type n2-standard-4 \
  --disk-size 100 \
  --enable-autoscaling \
  --enable-autorepair \
  --enable-ip-alias \
  --network roadtrip-vpc \
  --subnetwork roadtrip-subnet

# Get credentials
gcloud container clusters get-credentials roadtrip-production \
  --region us-central1
```

## Database Configuration

### 1. Cloud SQL Setup
```bash
# Create PostgreSQL instance
gcloud sql instances create roadtrip-db-prod \
  --database-version=POSTGRES_15 \
  --tier=db-n1-standard-4 \
  --region=us-central1 \
  --network=roadtrip-vpc \
  --backup \
  --backup-start-time=03:00 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=04

# Create database and user
gcloud sql databases create roadtrip --instance=roadtrip-db-prod
gcloud sql users create roadtrip_app \
  --instance=roadtrip-db-prod \
  --password=$(openssl rand -base64 32)
```

### 2. Redis Setup
```bash
# Create Redis instance
gcloud redis instances create roadtrip-cache-prod \
  --size=5 \
  --region=us-central1 \
  --redis-version=redis_6_x \
  --network=roadtrip-vpc
```

### 3. Database Migrations
```bash
# Connect to Cloud SQL proxy
cloud_sql_proxy -instances=roadtrip-production:us-central1:roadtrip-db-prod=tcp:5432 &

# Run migrations
export DATABASE_URL="postgresql://roadtrip_app:PASSWORD@localhost:5432/roadtrip"
alembic upgrade head
```

## Application Deployment

### 1. Build and Push Docker Images
```bash
# Build backend image
docker build -t gcr.io/roadtrip-production/backend:v1.0.0 .
docker push gcr.io/roadtrip-production/backend:v1.0.0

# Build frontend image (if applicable)
docker build -t gcr.io/roadtrip-production/frontend:v1.0.0 ./frontend
docker push gcr.io/roadtrip-production/frontend:v1.0.0
```

### 2. Configure Secrets
```bash
# Create secrets in Secret Manager
gcloud secrets create database-url --data-file=- <<< "postgresql://..."
gcloud secrets create redis-url --data-file=- <<< "redis://..."
gcloud secrets create jwt-secret --data-file=- <<< "$(openssl rand -base64 32)"
gcloud secrets create google-maps-api-key --data-file=- <<< "YOUR_KEY"

# Create Kubernetes secret
kubectl create secret generic app-secrets \
  --from-literal=DATABASE_URL=$(gcloud secrets versions access latest --secret=database-url) \
  --from-literal=REDIS_URL=$(gcloud secrets versions access latest --secret=redis-url) \
  --from-literal=JWT_SECRET=$(gcloud secrets versions access latest --secret=jwt-secret)
```

### 3. Deploy to Kubernetes
```bash
# Apply configurations
kubectl apply -f infrastructure/k8s/namespace.yaml
kubectl apply -f infrastructure/k8s/configmap.yaml
kubectl apply -f infrastructure/k8s/secrets.yaml
kubectl apply -f infrastructure/k8s/deployment-api.yaml
kubectl apply -f infrastructure/k8s/service.yaml
kubectl apply -f infrastructure/k8s/ingress.yaml
kubectl apply -f infrastructure/k8s/hpa.yaml

# Verify deployment
kubectl get pods -n roadtrip
kubectl get services -n roadtrip
kubectl get ingress -n roadtrip
```

### 4. SSL Certificate Setup
```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create certificate
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: roadtrip-tls
  namespace: roadtrip
spec:
  secretName: roadtrip-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
  - api.roadtripstoryteller.com
EOF
```

## Monitoring & Alerting

### 1. Deploy Prometheus
```bash
# Add Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values infrastructure/k8s/monitoring/prometheus-values.yaml
```

### 2. Configure Grafana
```bash
# Get Grafana password
kubectl get secret --namespace monitoring prometheus-grafana -o jsonpath="{.data.admin-password}" | base64 --decode

# Port forward to access
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Import dashboards
# Access http://localhost:3000
# Import dashboard IDs: 12114, 12117, 12120
```

### 3. Set Up Alerts
```yaml
# Apply alert rules
kubectl apply -f infrastructure/k8s/monitoring/alert-rules.yaml

# Configure PagerDuty integration
kubectl create secret generic pagerduty-key \
  --namespace monitoring \
  --from-literal=integration-key=YOUR_PAGERDUTY_KEY
```

### 4. Application Metrics
```python
# Verify metrics endpoint
curl https://api.roadtripstoryteller.com/metrics

# Key metrics to monitor:
# - http_requests_total
# - http_request_duration_seconds
# - active_connections
# - db_query_duration_seconds
# - cache_hit_rate
```

## Security Configuration

### 1. Network Security
```bash
# Create firewall rules
gcloud compute firewall-rules create allow-roadtrip-api \
  --allow tcp:443 \
  --source-ranges 0.0.0.0/0 \
  --target-tags roadtrip-api

# Configure Cloud Armor
gcloud compute security-policies create roadtrip-security-policy
gcloud compute security-policies rules create 1000 \
  --security-policy roadtrip-security-policy \
  --expression "origin.region_code == 'US'" \
  --action allow
```

### 2. API Security
```bash
# Enable API rate limiting
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: api-config
  namespace: roadtrip
data:
  RATE_LIMIT_ENABLED: "true"
  RATE_LIMIT_REQUESTS: "1000"
  RATE_LIMIT_WINDOW: "3600"
EOF
```

### 3. Secrets Rotation
```bash
# Rotate database password
NEW_PASSWORD=$(openssl rand -base64 32)
gcloud sql users set-password roadtrip_app \
  --instance=roadtrip-db-prod \
  --password=$NEW_PASSWORD

# Update Kubernetes secret
kubectl delete secret app-secrets -n roadtrip
kubectl create secret generic app-secrets \
  --from-literal=DATABASE_URL="postgresql://roadtrip_app:$NEW_PASSWORD@..."
```

## Backup & Recovery

### 1. Database Backups
```bash
# Manual backup
gcloud sql backups create \
  --instance=roadtrip-db-prod \
  --description="Manual backup before deployment"

# Verify automated backups
gcloud sql backups list --instance=roadtrip-db-prod
```

### 2. Application State Backup
```bash
# Backup Kubernetes configs
kubectl get all -n roadtrip -o yaml > k8s-backup-$(date +%Y%m%d).yaml

# Backup persistent volumes
kubectl get pv -o yaml > pv-backup-$(date +%Y%m%d).yaml
```

### 3. Disaster Recovery Test
```bash
# Restore database from backup
gcloud sql backups restore BACKUP_ID \
  --restore-instance=roadtrip-db-prod-restore

# Test application with restored database
kubectl set env deployment/api-deployment \
  DATABASE_URL="postgresql://...restored-db..." \
  -n roadtrip
```

## Operational Procedures

### 1. Deployment Process
```bash
# Blue-Green Deployment
./scripts/deploy.sh --environment production --version v1.0.1

# Rollback if needed
./scripts/rollback.sh --environment production --version v1.0.0
```

### 2. Scaling Operations
```bash
# Manual scaling
kubectl scale deployment api-deployment --replicas=5 -n roadtrip

# Update autoscaling
kubectl patch hpa api-hpa -n roadtrip --patch '{"spec":{"maxReplicas":20}}'
```

### 3. Maintenance Mode
```bash
# Enable maintenance mode
kubectl set env deployment/api-deployment \
  MAINTENANCE_MODE=true \
  -n roadtrip

# Disable maintenance mode
kubectl set env deployment/api-deployment \
  MAINTENANCE_MODE=false \
  -n roadtrip
```

### 4. Log Management
```bash
# View application logs
kubectl logs -f deployment/api-deployment -n roadtrip

# Export logs to Cloud Logging
gcloud logging read "resource.type=k8s_container \
  AND resource.labels.namespace_name=roadtrip" \
  --limit 1000 \
  --format json > logs-export.json
```

## Troubleshooting

### Common Issues

#### 1. Pod Crashes
```bash
# Check pod status
kubectl describe pod POD_NAME -n roadtrip

# Check logs
kubectl logs POD_NAME -n roadtrip --previous

# Common fixes:
# - Check resource limits
# - Verify environment variables
# - Check database connectivity
```

#### 2. Database Connection Issues
```bash
# Test connection from pod
kubectl exec -it deployment/api-deployment -n roadtrip -- \
  psql $DATABASE_URL -c "SELECT 1"

# Check Cloud SQL proxy
kubectl logs deployment/cloudsql-proxy -n roadtrip
```

#### 3. High Response Times
```bash
# Check metrics
curl https://api.roadtripstoryteller.com/api/performance/query-stats

# Analyze slow queries
kubectl exec -it deployment/api-deployment -n roadtrip -- \
  python -c "from app.core.query_analyzer import query_analyzer; print(query_analyzer.get_optimization_report())"
```

#### 4. Memory Issues
```bash
# Check memory usage
kubectl top pods -n roadtrip

# Increase memory limits
kubectl set resources deployment/api-deployment \
  --limits=memory=2Gi \
  --requests=memory=1Gi \
  -n roadtrip
```

### Emergency Procedures

#### Complete Outage
1. Check GCP status page
2. Verify DNS resolution
3. Check ingress controller
4. Review recent deployments
5. Engage on-call engineer

#### Data Corruption
1. Stop write traffic
2. Identify affected data
3. Restore from backup
4. Validate data integrity
5. Resume traffic gradually

#### Security Breach
1. Rotate all secrets immediately
2. Review access logs
3. Disable compromised accounts
4. Notify security team
5. Conduct post-mortem

## Health Checks

### API Health
```bash
# Basic health check
curl https://api.roadtripstoryteller.com/api/health

# Detailed health check
curl https://api.roadtripstoryteller.com/health/detailed
```

### Database Health
```bash
# Check connections
kubectl exec -it deployment/api-deployment -n roadtrip -- \
  python -c "from app.core.connection_pool import pool_manager; print(pool_manager.get_health_status())"
```

### Cache Health
```bash
# Redis health
kubectl exec -it deployment/redis -n roadtrip -- redis-cli ping
```

## Performance Tuning

### Database Optimization
```sql
-- Analyze query performance
EXPLAIN ANALYZE SELECT * FROM stories WHERE user_id = 123;

-- Update statistics
ANALYZE stories;
ANALYZE journeys;
ANALYZE bookings;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0;
```

### Application Optimization
```bash
# Enable performance mode
kubectl set env deployment/api-deployment \
  PERFORMANCE_MODE=true \
  CACHE_STRATEGY=aggressive \
  -n roadtrip
```

## Maintenance Schedule

### Daily
- Review error logs
- Check backup completion
- Monitor resource usage
- Review security alerts

### Weekly
- Update dependencies
- Review performance metrics
- Test disaster recovery
- Update documentation

### Monthly
- Security patching
- Certificate renewal check
- Capacity planning review
- Cost optimization

## Support Contacts

- **On-Call Engineer**: Use PagerDuty
- **Cloud Support**: GCP Support Portal
- **Security Team**: security@roadtripstoryteller.com
- **Database Admin**: dba@roadtripstoryteller.com

## Appendix

### Useful Commands
```bash
# Get all resources
kubectl get all -n roadtrip

# Describe deployment
kubectl describe deployment api-deployment -n roadtrip

# Get events
kubectl get events -n roadtrip --sort-by='.lastTimestamp'

# Port forward for debugging
kubectl port-forward deployment/api-deployment 8000:8000 -n roadtrip

# Execute commands in pod
kubectl exec -it deployment/api-deployment -n roadtrip -- /bin/bash
```

### Configuration Files
All configuration files are stored in:
- `infrastructure/k8s/` - Kubernetes manifests
- `infrastructure/terraform/` - Terraform configs
- `.github/workflows/` - CI/CD pipelines
- `scripts/` - Deployment scripts

Remember: Always test in staging before production deployment!