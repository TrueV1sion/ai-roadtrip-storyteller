#!/bin/bash
# Emergency deployment with minimal config to get staging running

set -euo pipefail

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-backend-staging"
REGION="us-central1"

echo "Emergency deployment to get staging running..."

# Delete existing service
echo "Removing existing service..."
gcloud run services delete $SERVICE_NAME --region=$REGION --quiet || true

# Deploy fresh with all required env vars
echo "Deploying fresh service..."
gcloud run deploy $SERVICE_NAME \
    --image="gcr.io/${PROJECT_ID}/roadtrip-backend:staging" \
    --platform=managed \
    --region=$REGION \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --timeout=300 \
    --max-instances=10 \
    --min-instances=0 \
    --port=8080 \
    --service-account="roadtrip-staging-e6a9121e@${PROJECT_ID}.iam.gserviceaccount.com" \
    --set-env-vars="ENVIRONMENT=staging,GCP_PROJECT_ID=${PROJECT_ID},GOOGLE_AI_MODEL=gemini-2.0-pro-exp,DATABASE_URL=postgresql://user:pass@localhost/db,REDIS_URL=redis://localhost:6379,SECRET_KEY=temp-secret-key,JWT_SECRET_KEY=temp-jwt-key" \
    --quiet

echo "Deployment complete. Service should be running with temporary config."