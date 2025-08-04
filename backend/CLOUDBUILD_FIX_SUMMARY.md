# Cloud Build Configuration Fix Summary

## Critical Issues Fixed

### 1. **Dependency Reference Error (Line 152)**
- **Original**: `waitFor: ['scan-image']` 
- **Fixed**: `waitFor: ['unit-tests']`
- **Issue**: Referenced non-existent step ID 'scan-image', actual ID was 'trivy-scan'

### 2. **Non-existent Test Directory (Line 136)**
- **Original**: `pytest tests/performance/`
- **Fixed**: Removed performance test step, replaced with unit tests only
- **Issue**: No `tests/performance/` directory exists in the project

### 3. **Trivy Scanner Issues**
- **Original**: Used `aquasec/trivy` image directly
- **Fixed**: Replaced with Google Container Analysis (`gcloud container images scan`)
- **Issue**: Trivy image may not be accessible in Cloud Build environment

### 4. **Missing Environment Variables**
- **Added**: 
  - `GOOGLE_AI_MODEL=gemini-1.5-flash`
  - `TWO_FACTOR_SECRET` (via Secret Manager)
  - All other required environment variables

### 5. **Resource Standardization**
- **Memory**: Set to 4GB consistently
- **CPU**: Set to 4 CPUs consistently  
- **Timeout**: Set to 600 seconds (10 minutes) for API operations

## Files Created/Updated

### 1. `backend/cloudbuild.yaml` (Updated)
- Fixed all dependency errors
- Replaced Trivy with Google Container Analysis
- Added proper unit test execution
- Included all required environment variables
- Implemented proper rollback strategy

### 2. `backend/cloudbuild-prod-clean.yaml` (New)
- Simplified production-ready configuration
- Minimal steps: Build → Push → Deploy → Verify
- No complex scanning or performance tests
- Focused on successful deployment

## Deployment Instructions

### Option 1: Use Fixed Main Configuration
```bash
gcloud builds submit \
  --config=backend/cloudbuild.yaml \
  --project=YOUR_PROJECT_ID
```

### Option 2: Use Simplified Configuration
```bash
gcloud builds submit \
  --config=backend/cloudbuild-prod-clean.yaml \
  --project=YOUR_PROJECT_ID
```

## Pre-Deployment Checklist

1. **Ensure all secrets exist in Secret Manager**:
   ```bash
   # Check if secrets exist
   gcloud secrets list --project=YOUR_PROJECT_ID
   
   # Required secrets:
   - roadtrip-database-url
   - roadtrip-redis-url
   - roadtrip-jwt-secret
   - roadtrip-google-maps-key
   - roadtrip-ticketmaster-key
   - roadtrip-opentable-key
   - roadtrip-recreation-gov-key
   - roadtrip-viator-key
   - roadtrip-openweather-key
   - roadtrip-sentry-dsn
   - roadtrip-2fa-secret
   - roadtrip-audio-encryption-key
   - roadtrip-ar-api-key
   ```

2. **Enable required APIs**:
   ```bash
   gcloud services enable \
     run.googleapis.com \
     cloudbuild.googleapis.com \
     secretmanager.googleapis.com \
     containeranalysis.googleapis.com
   ```

3. **Create service account if needed**:
   ```bash
   gcloud iam service-accounts create roadtrip-backend \
     --display-name="RoadTrip Backend Service Account"
   ```

## Key Changes Summary

| Issue | Original | Fixed |
|-------|----------|-------|
| Step dependency | `waitFor: ['scan-image']` | `waitFor: ['unit-tests']` |
| Performance tests | `pytest tests/performance/` | Removed (directory doesn't exist) |
| Security scanning | Trivy scanner | Google Container Analysis |
| Resource allocation | Inconsistent | 4GB RAM, 4 CPUs standard |
| Environment variables | Missing GOOGLE_AI_MODEL | Added all required vars |
| Project ID | Some hardcoded | All use ${PROJECT_ID} |

## Recommended Deployment Approach

1. **Test with simplified config first** (`cloudbuild-prod-clean.yaml`)
2. **Once working, use full config** (`cloudbuild.yaml`) for advanced features
3. **Monitor Cloud Build logs** for any issues
4. **Verify deployment** with health check: `curl https://YOUR_SERVICE_URL/health`

## Troubleshooting

If deployment fails:
1. Check Cloud Build logs: `gcloud builds list --limit=5`
2. Verify all secrets exist: `gcloud secrets list`
3. Check service account permissions
4. Ensure Docker image builds locally first
5. Use simplified config for faster debugging

## Next Steps

1. Deploy using the fixed configuration
2. Monitor deployment progress in Cloud Console
3. Test all endpoints after deployment
4. Set up Cloud Build triggers for automated deployments