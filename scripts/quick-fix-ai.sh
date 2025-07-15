#!/bin/bash
# Quick fix to ensure Vertex AI is configured properly

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}🔧 Quick Fix for AI Configuration${NC}"
echo -e "${BLUE}===================================================${NC}"

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"

echo -e "\n${YELLOW}Updating environment variables for Vertex AI...${NC}"

# Update just the critical AI-related variables
gcloud run services update $SERVICE_NAME \
    --region $REGION \
    --update-env-vars "\
GOOGLE_APPLICATION_CREDENTIALS=/tmp/keys/gcp-key.json,\
GOOGLE_CLOUD_PROJECT=$PROJECT_ID,\
VERTEX_AI_PROJECT=$PROJECT_ID,\
VERTEX_AI_LOCATION=us-central1,\
USE_VERTEX_AI=true,\
AI_PROVIDER=vertex,\
DISABLE_GEMINI_API=true"

echo -e "${GREEN}✓ Environment updated${NC}"

echo -e "\n${YELLOW}Waiting for service to restart...${NC}"
sleep 15

# Test the service
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo -e "\n${YELLOW}Testing service...${NC}"
curl -s "$SERVICE_URL/health" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"Status: {data.get('status', 'unknown')}\")"

echo -e "\n${BLUE}===================================================${NC}"
echo -e "${BLUE}Alternative Solution:${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""
echo "If the AI is still not working, you have two options:"
echo ""
echo "1. Get a Gemini API key (quick fix for tomorrow):"
echo "   - Go to: https://makersuite.google.com/app/apikey"
echo "   - Create an API key"
echo "   - Update the service:"
echo "     gcloud run services update $SERVICE_NAME --region $REGION --update-env-vars GEMINI_API_KEY=YOUR_KEY"
echo ""
echo "2. Fix the code to use Vertex AI (proper solution):"
echo "   - The code needs to be updated to use Vertex AI client instead of Google AI Studio"
echo ""
echo "Service URL: $SERVICE_URL"