#!/bin/bash
# AI Road Trip Storyteller - Production Deployment Script
# Purpose: Deploy application to Google Cloud Run
# Usage: ./deploy.sh [environment] [project-id]
# CI/CD: Fully compatible - zero interactive prompts

set -euo pipefail

# Configuration from environment or arguments
ENVIRONMENT="${1:-${DEPLOY_ENV:-staging}}"
PROJECT_ID="${2:-${GCP_PROJECT_ID:-}}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="roadtrip-backend-${ENVIRONMENT}"
IMAGE_NAME="roadtrip-backend:${ENVIRONMENT}"

# Logging
log() { echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"; }
error() { log "ERROR: $*" >&2; exit 1; }

# Validate required parameters
[[ -z "$PROJECT_ID" ]] && error "PROJECT_ID not set. Use: ./deploy.sh [env] [project-id]"
[[ -z "$ENVIRONMENT" ]] && error "ENVIRONMENT not set"

log "Starting deployment"
log "Environment: $ENVIRONMENT"
log "Project: $PROJECT_ID"
log "Region: $REGION"
log "Service: $SERVICE_NAME"

# Disable all interactive prompts
export CLOUDSDK_CORE_DISABLE_PROMPTS=1
export DEBIAN_FRONTEND=noninteractive
gcloud config set core/disable_prompts true 2>/dev/null || true

# Authenticate if in CI/CD
if [[ -n "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
    log "Authenticating with service account"
    gcloud auth activate-service-account --key-file="$GOOGLE_APPLICATION_CREDENTIALS"
fi

# Set project
log "Setting GCP project"
gcloud config set project "$PROJECT_ID" || error "Failed to set project"

# Build Docker image
log "Building Docker image"
docker build -t "$IMAGE_NAME" -f Dockerfile . || error "Docker build failed"

# Tag for Container Registry
GCR_IMAGE="gcr.io/${PROJECT_ID}/${IMAGE_NAME}"
log "Tagging image: $GCR_IMAGE"
docker tag "$IMAGE_NAME" "$GCR_IMAGE" || error "Docker tag failed"

# Push to Container Registry
log "Pushing image to Container Registry"
docker push "$GCR_IMAGE" || error "Docker push failed"

# Deploy to Cloud Run
log "Deploying to Cloud Run"
gcloud run deploy "$SERVICE_NAME" \
    --image "$GCR_IMAGE" \
    --platform managed \
    --region "$REGION" \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 1 \
    --port 8080 \
    --service-account "roadtrip-staging-e6a9121e@${PROJECT_ID}.iam.gserviceaccount.com" \
    --set-env-vars "ENVIRONMENT=${ENVIRONMENT},GCP_PROJECT_ID=${PROJECT_ID},GOOGLE_AI_MODEL=gemini-2.0-pro-exp,DATABASE_URL=sqlite:///app/test.db" \
    --set-secrets "JWT_SECRET_KEY=JWT_SECRET_KEY-${ENVIRONMENT}:latest,SECRET_KEY=SECRET_KEY-${ENVIRONMENT}:latest,GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY-${ENVIRONMENT}:latest" \
    --quiet \
    || error "Cloud Run deployment failed"

# Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --platform managed \
    --region "$REGION" \
    --format 'value(status.url)') || error "Failed to get service URL"

log "Deployment successful!"
log "Service URL: $SERVICE_URL"

# Run health check
log "Running health check..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health" || echo "000")

if [[ "$HEALTH_STATUS" == "200" ]]; then
    log "Health check passed"
    exit 0
else
    error "Health check failed with status: $HEALTH_STATUS"
fi