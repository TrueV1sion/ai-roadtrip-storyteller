# Google Secret Manager Setup Guide

This guide walks through setting up Google Secret Manager for secure credential storage in production.

## Prerequisites

1. Google Cloud SDK (`gcloud`) installed
2. A Google Cloud project with billing enabled
3. Appropriate permissions in the project

## Step 1: Enable Required APIs

```bash
# Enable Secret Manager API
gcloud services enable secretmanager.googleapis.com

# Verify it's enabled
gcloud services list --enabled | grep secretmanager
```

## Step 2: Create Service Account (if needed)

```bash
# Create service account for the application
gcloud iam service-accounts create roadtrip-app \
    --display-name="Road Trip Application Service Account" \
    --description="Service account for AI Road Trip Storyteller application"

# Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:roadtrip-app@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Create and download service account key
gcloud iam service-accounts keys create roadtrip-sa-key.json \
    --iam-account=roadtrip-app@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

## Step 3: Set Environment Variables

```bash
# Set the project ID
export GOOGLE_CLOUD_PROJECT_ID="your-project-id"

# Set the path to service account credentials
export GOOGLE_APPLICATION_CREDENTIALS="path/to/roadtrip-sa-key.json"
```

## Step 4: Run Migration Script

### Dry Run (Recommended First)

```bash
# Test what would be migrated without making changes
python scripts/migrate_to_secret_manager.py --dry-run
```

### Actual Migration

```bash
# Run the migration
python scripts/migrate_to_secret_manager.py

# The script will:
# 1. Validate your environment
# 2. Load secrets from .env file and environment
# 3. Create/update secrets in Secret Manager
# 4. Generate a migration report
```

## Step 5: Verify Migration

```bash
# List all secrets
gcloud secrets list

# View a specific secret (without the value)
gcloud secrets describe roadtrip-secret-key

# Test access to a secret
gcloud secrets versions access latest --secret="roadtrip-secret-key"
```

## Step 6: Update Application Configuration

The application automatically uses Secret Manager when available. No code changes needed if using the updated configuration.

### For Development

Continue using `.env` file - the application will use environment variables when Secret Manager is not available.

### For Production

1. Set environment variables:
   ```bash
   export GOOGLE_CLOUD_PROJECT_ID="your-project-id"
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/sa-key.json"
   ```

2. Or use Google Cloud default credentials:
   ```bash
   gcloud auth application-default login
   ```

## Secret Naming Convention

All secrets follow the pattern: `roadtrip-{service}-{type}`

Examples:
- `roadtrip-secret-key` - Application secret key
- `roadtrip-database-url` - Database connection string
- `roadtrip-google-maps-key` - Google Maps API key
- `roadtrip-spotify-id` - Spotify Client ID

## Security Best Practices

1. **Least Privilege**: Grant only necessary permissions
2. **Rotation**: Regularly rotate secrets (quarterly recommended)
3. **Audit Logging**: Enable audit logs for secret access
4. **Versioning**: Keep previous versions for rollback capability
5. **Access Control**: Use IAM to control who can access secrets

## Troubleshooting

### Permission Denied Errors

```bash
# Check current authentication
gcloud auth list

# Check service account permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:roadtrip-app@*"
```

### Secret Not Found

```bash
# Verify secret exists
gcloud secrets list | grep roadtrip

# Check secret ID matches expected format
# Environment var DATABASE_URL -> Secret ID roadtrip-database-url
```

### Application Can't Access Secrets

1. Verify `GOOGLE_CLOUD_PROJECT_ID` is set
2. Check `GOOGLE_APPLICATION_CREDENTIALS` points to valid key file
3. Ensure Secret Manager API is enabled
4. Verify service account has `secretmanager.secretAccessor` role

## Migration Report

After running the migration, check the generated report:
- `secret_migration_report_YYYYMMDD_HHMMSS.json`

The report shows:
- Successfully migrated secrets
- Skipped secrets (already exist or not found)
- Failed migrations with reasons
- Warnings (e.g., placeholder values detected)

## Next Steps

1. Test application with Secret Manager in staging
2. Set up secret rotation schedule
3. Configure monitoring for secret access
4. Document which team members have access
5. Create runbook for secret rotation procedures