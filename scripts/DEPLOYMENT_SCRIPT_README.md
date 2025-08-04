# Production Deployment Script

## Overview

The `deploy_production.py` script is a comprehensive, cross-platform deployment automation tool for deploying the AI Road Trip Storyteller application to Google Cloud Platform. It replaces all previous shell scripts with a single, unified Python script that works on both Windows and Unix systems.

## Features

- ✅ **Cross-platform**: Works on Windows, macOS, and Linux
- ✅ **Pre-flight checks**: Validates all requirements before deployment
- ✅ **Automated setup**: Enables APIs, creates service accounts, configures permissions
- ✅ **Safe deployments**: Gradual traffic shifting with automatic rollback
- ✅ **Production-ready**: Handles secrets, monitoring, and error recovery
- ✅ **Dry-run mode**: Preview changes without executing
- ✅ **Rollback support**: Easy rollback to previous versions

## Prerequisites

1. **Python 3.7+** installed
2. **Google Cloud SDK (gcloud)** installed and configured
3. **Docker** installed and running
4. **Git** repository cloned locally
5. **GCP Project** with billing enabled

## Installation

No additional installation required - the script uses only Python standard library.

## Usage

### Basic Deployment

```bash
# Deploy to staging (default)
python scripts/deploy_production.py --project-id your-project-id

# Deploy to production
python scripts/deploy_production.py --project-id your-project-id --environment production

# Deploy to specific region
python scripts/deploy_production.py --project-id your-project-id --region europe-west1
```

### Advanced Options

```bash
# Dry run - see what would happen without executing
python scripts/deploy_production.py --project-id your-project-id --dry-run

# Skip confirmation prompts (useful for CI/CD)
python scripts/deploy_production.py --project-id your-project-id --environment production --force

# Enable verbose logging
python scripts/deploy_production.py --project-id your-project-id --verbose

# Rollback to previous version
python scripts/deploy_production.py --project-id your-project-id --rollback roadtrip-backend-abc123
```

## Deployment Process

The script performs the following steps:

1. **Prerequisites Check**
   - Verifies gcloud CLI installation
   - Checks authentication status
   - Validates project access
   - Ensures Docker is running

2. **Environment Setup**
   - Enables required Google Cloud APIs
   - Creates service account (if needed)
   - Grants necessary IAM roles
   - Validates Secret Manager secrets

3. **Build & Push**
   - Builds Docker image locally
   - Tags with timestamp and latest
   - Pushes to Google Container Registry

4. **Deploy Service**
   - Deploys to Cloud Run without traffic
   - Configures environment variables
   - Sets up secret bindings
   - Applies resource limits

5. **Verification**
   - Performs health checks
   - Tests critical endpoints
   - Validates service readiness

6. **Traffic Shifting**
   - Gradually shifts traffic (10% → 50% → 100%)
   - Monitors each stage
   - Automatic rollback on failure

7. **Cleanup**
   - Removes old revisions (keeps last 3)
   - Updates service tags

## Required APIs

The script automatically enables these APIs:
- Cloud Run API
- Cloud Build API
- Secret Manager API
- Cloud SQL Admin API
- Redis API
- Vertex AI API
- Cloud Trace API
- Monitoring API
- Logging API
- Maps API
- Places API
- Text-to-Speech API
- Speech-to-Text API

## Required Secrets

For production deployments, these secrets must exist in Secret Manager:
- `roadtrip-database-url`
- `roadtrip-redis-url`
- `roadtrip-jwt-secret`
- `roadtrip-secret-key`
- `roadtrip-csrf-secret`
- `roadtrip-google-maps-key`
- `roadtrip-ticketmaster-key`
- `roadtrip-openweather-key`
- `roadtrip-recreation-key`
- `roadtrip-spotify-id`
- `roadtrip-spotify-secret`
- `roadtrip-viator-key`
- `roadtrip-opentable-key`

## Service Configuration

Default configuration (can be modified in script):
- **Memory**: 2Gi
- **CPU**: 2 cores
- **Timeout**: 900 seconds (15 minutes)
- **Max Instances**: 100
- **Min Instances**: 1
- **Concurrency**: 100 requests per instance

## Rollback Procedure

To rollback to a previous version:

1. **List available revisions**:
   ```bash
   gcloud run revisions list --service=roadtrip-backend --region=us-central1
   ```

2. **Rollback to specific revision**:
   ```bash
   python scripts/deploy_production.py --project-id your-project-id --rollback roadtrip-backend-abc123
   ```

## CI/CD Integration

The script is designed for CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Deploy to Production
  run: |
    python scripts/deploy_production.py \
      --project-id ${{ secrets.GCP_PROJECT_ID }} \
      --environment production \
      --force
  env:
    GOOGLE_APPLICATION_CREDENTIALS: ${{ steps.auth.outputs.credentials_file_path }}
```

## Troubleshooting

### Common Issues

1. **"gcloud not found"**
   - Install Google Cloud SDK: https://cloud.google.com/sdk

2. **"Not authenticated"**
   - Run: `gcloud auth login`

3. **"Docker daemon not running"**
   - Start Docker Desktop (Windows/Mac)
   - Run: `sudo systemctl start docker` (Linux)

4. **"Project not found"**
   - Verify project ID is correct
   - Ensure you have access to the project

5. **"APIs not enabled"**
   - The script will attempt to enable them automatically
   - Ensure billing is enabled on the project

### Logs

Check deployment logs:
```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# View build logs
gcloud builds list --limit 5
```

## Security Notes

- Never commit secrets to version control
- Use Secret Manager for all sensitive values
- Service account has minimal required permissions
- HTTPS is enforced in production
- Authentication can be enabled per endpoint

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Cloud Run logs for errors
3. Ensure all prerequisites are met
4. Verify secrets are properly configured

## Next Steps

After successful deployment:
1. Verify the service is running: `https://[SERVICE_URL]/health`
2. Check API documentation: `https://[SERVICE_URL]/docs`
3. Monitor performance in Cloud Console
4. Set up alerts for errors/latency
5. Configure custom domain (optional)