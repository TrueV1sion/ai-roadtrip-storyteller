#!/bin/bash
# Deploy Vertex AI fix to production
# This script will redeploy the backend with the current code that uses Vertex AI

set -e

echo "[DEPLOY] Starting Vertex AI fix deployment..."
echo "====================================="

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"

# Ensure we're in the backend directory
cd "$(dirname "$0")"

echo "[CHECK] Verifying current directory..."
pwd

# Check if Dockerfile exists
if [ ! -f "Dockerfile" ]; then
    echo "[ERROR] Dockerfile not found in backend directory"
    exit 1
fi

echo "[BUILD] Building Docker image..."
# Build the image with Cloud Build
gcloud builds submit . \
  --project=$PROJECT_ID \
  --region=$REGION \
  --tag gcr.io/$PROJECT_ID/$SERVICE_NAME:vertex-ai-fix \
  --timeout=30m

echo "[DEPLOY] Deploying to Cloud Run..."
# Deploy to Cloud Run with proper environment variables
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:vertex-ai-fix \
  --region=$REGION \
  --project=$PROJECT_ID \
  --platform managed \
  --memory=2Gi \
  --cpu=1 \
  --timeout=300s \
  --concurrency=100 \
  --max-instances=10 \
  --min-instances=1 \
  --service-account=roadtrip-mvp-sa@$PROJECT_ID.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --set-env-vars="ENVIRONMENT=production" \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
  --set-env-vars="GOOGLE_AI_PROJECT_ID=$PROJECT_ID" \
  --set-env-vars="GOOGLE_AI_LOCATION=$REGION" \
  --set-env-vars="VERTEX_AI_LOCATION=$REGION" \
  --set-env-vars="USE_VERTEX_AI=true" \
  --set-env-vars="GOOGLE_AI_MODEL=gemini-1.5-flash" \
  --set-env-vars="LOG_LEVEL=INFO" \
  --set-env-vars="CORS_ORIGINS=*" \
  --update-secrets="DATABASE_URL=DATABASE_URL:latest" \
  --update-secrets="REDIS_URL=REDIS_URL:latest" \
  --update-secrets="JWT_SECRET_KEY=JWT_SECRET_KEY:latest"

echo "[TEST] Waiting for deployment to complete..."
sleep 30

echo "[TEST] Testing health endpoint..."
HEALTH_URL="https://roadtrip-mvp-792001900150.us-central1.run.app/health"
response=$(curl -s $HEALTH_URL)

echo "[RESULT] Health check response:"
echo "$response" | python -m json.tool || echo "$response"

# Check if the response contains the error
if echo "$response" | grep -q "generativelanguage.googleapis.com"; then
    echo "[WARNING] Still seeing generativelanguage API error"
    echo "The deployment may need additional configuration"
else
    echo "[SUCCESS] Health check looks good!"
fi

echo ""
echo "[COMPLETE] Deployment finished!"
echo "Monitor logs with: gcloud run logs read $SERVICE_NAME --region=$REGION --limit=50"