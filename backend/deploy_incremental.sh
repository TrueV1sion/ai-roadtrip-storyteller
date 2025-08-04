#!/bin/bash
# Incremental deployment script for Google Cloud Run

set -e

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-roadtrip-mvp}"
SERVICE_NAME="roadtrip-backend-incremental"
REGION="${GOOGLE_CLOUD_REGION:-us-central1}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=== AI Road Trip Backend Incremental Deployment ==="
echo "Project: ${PROJECT_ID}"
echo "Service: ${SERVICE_NAME}"
echo "Region: ${REGION}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed"
    exit 1
fi

# Check authentication
echo "Checking Google Cloud authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "Error: Not authenticated with Google Cloud"
    echo "Run: gcloud auth login"
    exit 1
fi

# Set project
echo "Setting project to ${PROJECT_ID}..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "Enabling required Google Cloud APIs..."
gcloud services enable cloudbuild.googleapis.com cloudrun.googleapis.com artifactregistry.googleapis.com

# Fix imports first
echo "Fixing import statements..."
python fix_imports.py

# Build the Docker image
echo "Building Docker image..."
docker build -f Dockerfile.incremental -t ${IMAGE_NAME} .

# Push to Google Container Registry
echo "Pushing image to Google Container Registry..."
docker push ${IMAGE_NAME}

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --timeout 60 \
    --max-instances 10 \
    --min-instances 1 \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "LOG_LEVEL=INFO" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-env-vars "CORS_ORIGINS=*"

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo ""
echo "=== Deployment Complete ==="
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Test endpoints:"
echo "  Health check: ${SERVICE_URL}/health"
echo "  Detailed health: ${SERVICE_URL}/health/detailed"
echo "  API docs: ${SERVICE_URL}/docs"
echo ""
echo "To view logs:"
echo "  gcloud run services logs read ${SERVICE_NAME} --region ${REGION}"
echo ""
echo "To update environment variables:"
echo "  gcloud run services update ${SERVICE_NAME} --region ${REGION} --update-env-vars KEY=VALUE"