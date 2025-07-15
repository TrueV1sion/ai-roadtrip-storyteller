#!/bin/bash
# Update MVP to use live AI instead of mocks

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}🔄 Updating MVP to Live AI Mode${NC}"
echo -e "${BLUE}===================================================${NC}"

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"

echo -e "\n${YELLOW}Updating environment variables to enable real AI...${NC}"

# Just update the critical variables to switch from mock to live
gcloud run services update $SERVICE_NAME \
    --region $REGION \
    --update-env-vars "\
TEST_MODE=live,\
USE_MOCK_APIS=false,\
GOOGLE_AI_MODEL=gemini-1.5-flash,\
DEFAULT_AI_PROVIDER=google"

echo -e "${GREEN}✓ Service updated to live mode${NC}"

# Wait for deployment
echo -e "\n${YELLOW}Waiting for service to restart...${NC}"
sleep 15

# Test the service
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo -e "\n${YELLOW}Testing service health...${NC}"
curl -s "$SERVICE_URL/health" | python3 -m json.tool

echo -e "\n${BLUE}===================================================${NC}"
echo -e "${BLUE}✅ MVP Updated to Live Mode!${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "The service is now configured to use:"
echo "✅ Real AI (Vertex AI with Gemini)"
echo "✅ Live API integrations"
echo "✅ No mock responses"
echo ""
echo "Test it with:"
echo "curl -X POST $SERVICE_URL/api/voice-assistant/interact \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"user_input\": \"Navigate to Chicago\", \"location\": {\"latitude\": 41.8781, \"longitude\": -87.6298}, \"user_id\": \"test\"}'"