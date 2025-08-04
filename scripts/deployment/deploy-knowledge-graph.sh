#!/bin/bash
# Deploy Knowledge Graph Service to Google Cloud Run
# This script handles the complete deployment of the Knowledge Graph service

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-roadtrip-mvp}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="roadtrip-knowledge-graph"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Deploying Knowledge Graph Service${NC}"
echo -e "${BLUE}Project: ${PROJECT_ID}${NC}"
echo -e "${BLUE}Region: ${REGION}${NC}"

# Check if running in the right directory
if [ ! -f "knowledge_graph/blazing_server.py" ]; then
    echo -e "${RED}❌ Error: Must run from project root directory${NC}"
    exit 1
fi

# Ensure gcloud is configured
echo -e "${YELLOW}📋 Checking gcloud configuration...${NC}"
gcloud config set project ${PROJECT_ID}

# Submit build to Cloud Build
echo -e "${YELLOW}🏗️  Submitting to Cloud Build...${NC}"
gcloud builds submit \
    --config=knowledge_graph/cloudbuild.yaml \
    --substitutions="_REGION=${REGION}" \
    .

# Get the service URL
echo -e "${YELLOW}🔍 Getting service URL...${NC}"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region ${REGION} \
    --platform managed \
    --format 'value(status.url)')

if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}❌ Failed to get service URL${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Knowledge Graph deployed successfully!${NC}"
echo -e "${GREEN}🌐 Service URL: ${SERVICE_URL}${NC}"
echo -e "${GREEN}📊 Dashboard: ${SERVICE_URL}${NC}"
echo -e "${GREEN}🔧 API Docs: ${SERVICE_URL}/docs${NC}"

# Test the deployment
echo -e "${YELLOW}🧪 Testing deployment...${NC}"
if curl -f -s "${SERVICE_URL}/api/health" > /dev/null; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
else
    echo -e "${RED}❌ Health check failed!${NC}"
    exit 1
fi

# Display integration instructions
echo -e "${BLUE}📝 Integration Instructions:${NC}"
echo -e "Add this to your backend environment variables:"
echo -e "KNOWLEDGE_GRAPH_URL=${SERVICE_URL}"
echo ""
echo -e "To use the Knowledge Graph in development:"
echo -e "1. Export the URL: export KNOWLEDGE_GRAPH_URL=${SERVICE_URL}"
echo -e "2. Or add to .env file: KNOWLEDGE_GRAPH_URL=${SERVICE_URL}"

echo -e "${GREEN}🎉 Deployment complete!${NC}"