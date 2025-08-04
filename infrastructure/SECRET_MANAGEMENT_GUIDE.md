# RoadTrip Secret Management Guide

## Quick Start

### 1. Initial Setup (One-time)
```bash
# Navigate to scripts directory
cd infrastructure/scripts

# Run setup script (creates all secrets with placeholders)
./setup-secrets.sh roadtrip-460720

# Or on Windows
setup-secrets.bat roadtrip-460720
```

### 2. Update Critical Secrets (Required)
```bash
# Database URL (get from Cloud SQL instance)
echo -n "postgresql://user:password@/roadtrip?host=/cloudsql/project:region:instance" | \
  gcloud secrets versions add roadtrip-database-url --data-file=-

# Redis URL (get from Redis instance)
echo -n "redis://10.x.x.x:6379/0" | \
  gcloud secrets versions add roadtrip-redis-url --data-file=-

# Google Maps API Key (get from Cloud Console)
echo -n "AIza..." | \
  gcloud secrets versions add roadtrip-google-maps-key --data-file=-
```

### 3. Validate Configuration
```bash
# Check all secrets are properly configured
./validate-secrets.sh roadtrip-460720

# Or on Windows
validate-secrets.bat roadtrip-460720
```

## Secret Reference

### Priority Levels

#### 🔴 CRITICAL (App won't start without these)
- `roadtrip-database-url` - PostgreSQL connection
- `roadtrip-redis-url` - Redis cache connection
- `roadtrip-jwt-secret` - Authentication
- `roadtrip-secret-key` - Session management
- `roadtrip-google-maps-key` - Navigation core

#### 🟡 REQUIRED (Core features disabled without these)
- `roadtrip-openweather-key` - Weather data
- `roadtrip-ticketmaster-key` - Event booking
- `roadtrip-recreation-key` - Campground booking

#### 🟢 OPTIONAL (Enhanced features only)
- `roadtrip-spotify-id/secret` - Music integration
- `roadtrip-viator-key` - Tour booking
- `roadtrip-opentable-*` - Restaurant reservations
- Others - See full list below

## Common Commands

### View a Secret
```bash
gcloud secrets versions access latest --secret=roadtrip-database-url
```

### Update a Secret
```bash
echo -n "new-value" | gcloud secrets versions add SECRET_ID --data-file=-
```

### List All Secrets
```bash
gcloud secrets list --filter="name:roadtrip-"
```

### Grant Access to Service Account
```bash
gcloud secrets add-iam-policy-binding SECRET_ID \
  --member="serviceAccount:roadtrip-mvp-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## Environment Variable Mappings

The application expects certain environment variable names that map to secrets:

| Environment Variable | Secret ID | Purpose |
|---------------------|-----------|---------|
| DATABASE_URL | roadtrip-database-url | PostgreSQL connection |
| REDIS_URL | roadtrip-redis-url | Redis connection |
| GOOGLE_MAPS_API_KEY | roadtrip-google-maps-key | Maps API |
| OPENWEATHERMAP_API_KEY | roadtrip-openweather-key | Weather API |
| TICKETMASTER_API_KEY | roadtrip-ticketmaster-key | Events API |

## Deployment Configuration

Use the provided CloudBuild configuration:
```bash
gcloud builds submit --config=infrastructure/cloudbuild-with-secrets.yaml
```

This configuration automatically maps all secrets to the correct environment variables.

## Security Best Practices

1. **Never commit secrets to git**
   - Use Secret Manager for all sensitive data
   - Keep .env files in .gitignore

2. **Rotate secrets regularly**
   - Use versioning for seamless rotation
   - Update authentication keys quarterly

3. **Limit access**
   - Only grant access to service accounts that need it
   - Use least-privilege principles

4. **Monitor access**
   - Enable audit logging for secret access
   - Review access patterns regularly

## Troubleshooting

### Secret Not Found Error
```
Error: Secret [SECRET_ID] not found
```
**Solution**: Run setup script to create the secret, then update with actual value

### Permission Denied
```
Error: Permission 'secretmanager.versions.access' denied
```
**Solution**: Grant the service account access to the secret (see commands above)

### Invalid Secret Value
```
Error: Failed to parse secret value
```
**Solution**: Ensure the secret value is properly formatted (no trailing newlines)

## Cost Optimization

- Secret Manager pricing: $0.06 per secret per month
- First 6 secrets are free
- Version storage: $0.01 per 10,000 operations

With ~50 secrets, expect ~$3/month for Secret Manager.

## Support

For issues with:
- **Secret creation**: Check IAM permissions
- **Secret access**: Verify service account roles
- **CloudBuild**: Check logs in Cloud Console
- **Application**: Check application logs for secret loading errors