# Production Secrets Management Guide

This guide covers secure credential management for production deployment of the AI Road Trip Storyteller.

## Overview

In production, all sensitive credentials are stored in Google Secret Manager instead of environment variables or configuration files. This provides:

- **Centralized Management**: All secrets in one secure location
- **Access Control**: Fine-grained IAM permissions
- **Audit Logging**: Track who accessed which secrets when
- **Versioning**: Maintain history and enable rollback
- **Rotation**: Easy secret rotation without code changes

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Application   │────▶│ SecretManager    │────▶│ Google Secret   │
│   (FastAPI)     │     │ Client           │     │ Manager API     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │ Local Cache      │
                        │ (5 min TTL)      │
                        └──────────────────┘
```

## Implementation Details

### Secret Manager Client

Located at: `backend/app/core/secrets.py`

Features:
- Automatic fallback to environment variables in development
- 5-minute cache to reduce API calls
- Graceful error handling
- Support for secret versioning

### Configuration Integration

Located at: `backend/app/core/config.py`

The application configuration automatically loads secrets from Secret Manager when:
1. Running in production (not CI environment)
2. Google Cloud credentials are available
3. Secret Manager API is accessible

### Secret Naming Convention

| Environment Variable | Secret Manager ID | Description |
|---------------------|-------------------|-------------|
| DATABASE_URL | roadtrip-database-url | PostgreSQL connection string |
| SECRET_KEY | roadtrip-secret-key | Application secret key |
| JWT_SECRET_KEY | roadtrip-jwt-secret | JWT signing key |
| REDIS_URL | roadtrip-redis-url | Redis connection string |
| GOOGLE_MAPS_API_KEY | roadtrip-google-maps-key | Google Maps API key |
| TICKETMASTER_API_KEY | roadtrip-ticketmaster-key | Ticketmaster API key |
| SPOTIFY_CLIENT_SECRET | roadtrip-spotify-secret | Spotify client secret |

## Production Setup

### 1. Prerequisites

```bash
# Install Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Initialize gcloud
gcloud init

# Set project
gcloud config set project YOUR_PROJECT_ID
```

### 2. Enable APIs

```bash
# Enable required APIs
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

### 3. Create Service Account

```bash
# Create service account
gcloud iam service-accounts create roadtrip-prod \
    --display-name="Road Trip Production Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:roadtrip-prod@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"
```

### 4. Migrate Secrets

```bash
# Set environment variables for migration
export GOOGLE_CLOUD_PROJECT_ID="your-project-id"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account-key.json"

# Run migration script
python scripts/migrate_to_secret_manager.py
```

### 5. Deploy Application

For Cloud Run:
```bash
# Build and deploy
gcloud run deploy roadtrip-api \
    --image gcr.io/YOUR_PROJECT_ID/roadtrip-api:latest \
    --service-account roadtrip-prod@YOUR_PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars GOOGLE_CLOUD_PROJECT_ID=YOUR_PROJECT_ID
```

For Kubernetes:
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: roadtrip-api
spec:
  template:
    spec:
      serviceAccountName: roadtrip-prod
      containers:
      - name: api
        env:
        - name: GOOGLE_CLOUD_PROJECT_ID
          value: "your-project-id"
```

## Security Best Practices

### 1. Least Privilege Access

```bash
# Create custom role with minimal permissions
gcloud iam roles create roadtripSecretAccessor \
    --project=YOUR_PROJECT_ID \
    --title="Road Trip Secret Accessor" \
    --description="Access secrets for Road Trip app" \
    --permissions=secretmanager.versions.access
```

### 2. Secret Rotation

Create a rotation schedule:
```bash
# Example: Rotate database password quarterly
gcloud scheduler jobs create http rotate-db-password \
    --schedule="0 0 1 */3 *" \
    --uri=https://YOUR_FUNCTION_URL/rotate-db-password \
    --http-method=POST
```

### 3. Audit Logging

Enable and monitor access logs:
```bash
# View secret access logs
gcloud logging read \
    'resource.type="secretmanager.googleapis.com/Secret"' \
    --limit=50 \
    --format=json
```

### 4. Monitoring

Set up alerts for unusual access patterns:
```yaml
# monitoring/secret-access-alert.yaml
displayName: Unusual Secret Access
conditions:
  - displayName: High secret access rate
    conditionThreshold:
      filter: |
        resource.type="secretmanager.googleapis.com/Secret"
        AND severity>=WARNING
      comparison: COMPARISON_GT
      thresholdValue: 100
      duration: 300s
```

## Testing

### Verify Secret Access

```bash
# Test secret access
python scripts/test_secret_manager.py

# Check specific secret
gcloud secrets versions access latest --secret="roadtrip-database-url"
```

### Load Testing

Test performance impact:
```python
# scripts/test_secret_performance.py
import time
from backend.app.core.secrets import get_secret_manager

manager = get_secret_manager()

# Test cache performance
start = time.time()
for i in range(100):
    manager.get_secret("roadtrip-secret-key")
end = time.time()

print(f"100 cached reads: {end - start:.2f}s")
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Check service account permissions
   gcloud projects get-iam-policy YOUR_PROJECT_ID \
       --flatten="bindings[].members" \
       --filter="bindings.members:serviceAccount:*"
   ```

2. **Secret Not Found**
   ```bash
   # List all secrets
   gcloud secrets list
   
   # Check secret exists
   gcloud secrets describe roadtrip-database-url
   ```

3. **Slow Performance**
   - Check cache is working (5-minute TTL)
   - Verify you're not creating new clients repeatedly
   - Use connection pooling for Secret Manager client

### Debug Mode

Enable debug logging:
```python
# backend/app/core/config.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Disaster Recovery

### Backup Secrets

```bash
# Export all secrets
for secret in $(gcloud secrets list --format="value(name)"); do
    echo "Backing up $secret"
    gcloud secrets versions access latest --secret="$secret" > "backup/$secret.txt"
done
```

### Restore Procedure

1. Create new project if needed
2. Run setup scripts
3. Restore secrets from backup
4. Update service configurations
5. Test all integrations

## Compliance

### Data Residency

Ensure secrets are stored in appropriate regions:
```bash
# Create secret with specific replication policy
gcloud secrets create roadtrip-eu-secret \
    --replication-policy="user-managed" \
    --locations="europe-west1,europe-west4"
```

### Access Reviews

Regular access reviews:
```bash
# Generate access report
gcloud asset search-all-iam-policies \
    --scope=projects/YOUR_PROJECT_ID \
    --query="resource:secretmanager.googleapis.com" \
    > secret-access-report.json
```

## Next Steps

1. Set up secret rotation automation
2. Configure monitoring dashboards
3. Create runbooks for common operations
4. Schedule security audits
5. Document emergency procedures