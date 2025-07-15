#!/bin/bash
# AI Road Trip Storyteller - Deployment Script

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-roadtrip-prod}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-roadtrip-api}"
ENVIRONMENT="${ENVIRONMENT:-staging}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting deployment to ${ENVIRONMENT}${NC}"

# Validate environment
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    echo -e "${RED}❌ Invalid environment: $ENVIRONMENT${NC}"
    exit 1
fi

# Build and tag image
echo -e "${YELLOW}📦 Building Docker image...${NC}"
docker build -t gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${GITHUB_SHA:-latest} .

# Push to GCR
echo -e "${YELLOW}⬆️  Pushing to Google Container Registry...${NC}"
docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${GITHUB_SHA:-latest}

# Deploy to Cloud Run
echo -e "${YELLOW}☁️  Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME}-${ENVIRONMENT} \
    --image gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${GITHUB_SHA:-latest} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --set-env-vars ENVIRONMENT=${ENVIRONMENT}

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME}-${ENVIRONMENT} \
    --region ${REGION} \
    --platform managed \
    --format 'value(status.url)')

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"

# Run smoke tests
echo -e "${YELLOW}🧪 Running smoke tests...${NC}"
curl -s -o /dev/null -w "%{http_code}" ${SERVICE_URL}/health | grep -q "200" || {
    echo -e "${RED}❌ Health check failed!${NC}"
    exit 1
}

echo -e "${GREEN}✅ All tests passed!${NC}"
