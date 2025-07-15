#!/bin/bash
# Fix Gemini authentication issue for MVP

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}🔧 Fixing Gemini Authentication${NC}"
echo -e "${BLUE}===================================================${NC}"

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"

echo -e "\n${YELLOW}The service is trying to use Google AI Studio API instead of Vertex AI.${NC}"
echo -e "${YELLOW}For MVP, we'll disable the AI health check and use mock responses.${NC}"

# Update environment to use mock mode for now
echo -e "\n${YELLOW}Updating service to use mock AI responses...${NC}"

gcloud run services update $SERVICE_NAME \
    --region $REGION \
    --update-env-vars "TEST_MODE=mock,GEMINI_API_KEY=mock-key-for-mvp"

echo -e "${GREEN}✓ Service updated to use mock mode${NC}"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo -e "\n${YELLOW}Waiting for service to restart...${NC}"
sleep 10

# Test the service
echo -e "\n${YELLOW}Testing service...${NC}"
curl -s "$SERVICE_URL/health" | python3 -m json.tool || echo "Service may still be restarting"

echo -e "\n${BLUE}===================================================${NC}"
echo -e "${BLUE}✅ Done! Your service should now work with mock AI responses.${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""
echo "For your road trip tomorrow:"
echo "1. The service will use pre-written fallback stories"
echo "2. Navigation will still work with Google Maps"
echo "3. Voice features will work if you add TTS API access"
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "To get real AI responses later, you'll need to either:"
echo "- Get a Gemini API key from https://makersuite.google.com/app/apikey"
echo "- Or fix the code to use Vertex AI instead of Google AI Studio"