# Google Cloud Cost Analysis & Cleanup Plan

## Current Active Services (Project: roadtrip-460720)

### Running Services (Costing Money)
1. **roadtrip-mvp** (us-central1) - Health check only
   - URL: https://roadtrip-mvp-k2nimm2ira-uc.a.run.app
   - Status: Running with 33 revisions
   - Created: June 2025
   
2. **roadtrip-backend-staging** (us-central1) - Health check only  
   - URL: https://roadtrip-backend-staging-k2nimm2ira-uc.a.run.app
   - Status: Running with 22 revisions
   - Created: July 6, 2025

3. **roadtrip-api** (us-central1) - Health check only
   - URL: https://roadtrip-api-k2nimm2ira-uc.a.run.app
   - Status: Running with 5 revisions
   - Created: June 7, 2025

4. **roadtrip-backend-mvp** (us-central1) - Health check only
   - URL: https://roadtrip-backend-mvp-k2nimm2ira-uc.a.run.app
   - Status: Running (newest deployment)
   - Created: July 28, 2025

5. **roadtrip-api-simple** (us-central1) - Partial API (routes broken)
   - URL: https://roadtrip-api-simple-k2nimm2ira-uc.a.run.app
   - Status: Running (newest deployment) 
   - Created: July 28, 2025

6. **maptravel** (europe-west1) - Unknown functionality
   - URL: https://maptravel-k2nimm2ira-ew.a.run.app
   - Status: Running
   - Created: July 3, 2025

### Failed Services (Not Costing Runtime)
- **roadtrip-backend** (us-central1) - Failed to start
- **roadtrip-backend-full** (us-central1) - Failed to start
- **roadtrip-mvp** (europe-west1) - Failed to start

## Cost Breakdown

### Cloud Run Costs (Estimated Monthly)
Each running service incurs:
- **Request charges**: $0.40 per 1 million requests
- **Compute charges**: ~$50-100/month per service with min-instances=1
- **Memory charges**: Additional based on allocated memory (2Gi per service)

**Current Monthly Estimate**: $300-600 for all running services

### Storage Costs
- **Container Registry**: 7 container images (~$5-10/month)
- **Cloud SQL**: If running, ~$50-100/month
- **Redis/Memorystore**: If running, ~$50-100/month

## Immediate Cost Reduction Actions

### 1. Delete Redundant Services (Save ~$250-400/month)
```bash
# Delete non-functional duplicates
gcloud run services delete roadtrip-mvp --region=europe-west1 --quiet
gcloud run services delete roadtrip-backend --region=us-central1 --quiet
gcloud run services delete roadtrip-backend-full --region=us-central1 --quiet

# Delete old health-check-only services
gcloud run services delete roadtrip-api --region=us-central1 --quiet
gcloud run services delete roadtrip-backend-staging --region=us-central1 --quiet
gcloud run services delete maptravel --region=europe-west1 --quiet
```

### 2. Consolidate to Single Service
Keep only ONE service while we fix the full backend:
- **Keep**: roadtrip-api-simple (newest, partially working)
- **Delete**: roadtrip-backend-mvp, roadtrip-mvp

### 3. Reduce Min Instances
```bash
# Set min-instances to 0 for development
gcloud run services update roadtrip-api-simple \
  --region=us-central1 \
  --min-instances=0
```

## Long-Term Solution

### Phase 1: Fix Import Errors (1-2 days)
1. Fix all `backend.app.*` imports to `app.*`
2. Fix missing encryption module
3. Fix Vertex AI imports

### Phase 2: Deploy Single Production Backend (1 day)
1. Test locally with all routes working
2. Deploy as `roadtrip-backend-production`
3. Delete all other services

### Phase 3: Optimize Costs (Ongoing)
1. Use min-instances=0 for development
2. Set up proper staging/production environments
3. Implement auto-scaling policies
4. Regular cleanup of old container images

## Recommended Immediate Action

Execute cleanup now to stop bleeding money:

```bash
# 1. Delete all failed services
gcloud run services delete roadtrip-backend --region=us-central1 --quiet
gcloud run services delete roadtrip-backend-full --region=us-central1 --quiet
gcloud run services delete roadtrip-mvp --region=europe-west1 --quiet

# 2. Delete old working services
gcloud run services delete roadtrip-api --region=us-central1 --quiet
gcloud run services delete roadtrip-backend-staging --region=us-central1 --quiet
gcloud run services delete roadtrip-mvp --region=us-central1 --quiet
gcloud run services delete roadtrip-backend-mvp --region=us-central1 --quiet
gcloud run services delete maptravel --region=europe-west1 --quiet

# 3. Keep only roadtrip-api-simple and reduce costs
gcloud run services update roadtrip-api-simple \
  --region=us-central1 \
  --min-instances=0

# 4. Clean up old container images
gcloud container images delete gcr.io/roadtrip-460720/roadtrip-backend --quiet
gcloud container images delete gcr.io/roadtrip-460720/roadtrip-backend-staging --quiet
gcloud container images delete gcr.io/roadtrip-460720/roadtrip-mvp --quiet
```

**This will reduce your costs from ~$300-600/month to ~$50/month during development.**

## Next Steps After Cleanup

1. Fix the backend code import errors
2. Test thoroughly locally
3. Deploy ONE production backend
4. Update mobile app to use production URL
5. Set up proper CI/CD to avoid future service proliferation