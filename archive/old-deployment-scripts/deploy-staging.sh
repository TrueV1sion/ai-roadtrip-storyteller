#!/bin/bash
set -e

# Deploy staging environment to Cloud Run

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-backend-staging"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "🚀 Starting deployment to Cloud Run staging..."

# Build and push the Docker image
echo "📦 Building Docker image..."
docker build -t ${IMAGE_NAME}:latest -f Dockerfile .

echo "⬆️ Pushing image to GCR..."
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run using the YAML configuration
echo "🌐 Deploying to Cloud Run..."
gcloud run services replace infrastructure/staging/cloud-run-staging.yaml \
    --region=${REGION} \
    --project=${PROJECT_ID}

# Wait for deployment to complete
echo "⏳ Waiting for deployment to complete..."
gcloud run services wait ${SERVICE_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID}

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region=${REGION} \
    --project=${PROJECT_ID} \
    --format='value(status.url)')

echo "✅ Deployment complete!"
echo "🔗 Service URL: ${SERVICE_URL}"

# Test the health endpoint
echo "🏥 Testing health endpoint..."
if curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health" | grep -q "200"; then
    echo "✅ Health check passed!"
else
    echo "❌ Health check failed. Checking logs..."
    gcloud run services logs read ${SERVICE_NAME} --region=${REGION} --limit=50
    exit 1
fi