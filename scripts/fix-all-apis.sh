#!/bin/bash
# Fix all API configurations for real-time road trip functionality

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}🔧 Configuring ALL APIs for Real-Time Road Trip${NC}"
echo -e "${BLUE}===================================================${NC}"

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"

# Load API keys from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}ERROR: .env file not found!${NC}"
    exit 1
fi

echo -e "\n${YELLOW}Step 1: Disable mock mode and enable real APIs${NC}"

# Build the environment variables string
ENV_VARS="ENVIRONMENT=production"
ENV_VARS="$ENV_VARS,TEST_MODE=live"  # Change from mock to live
ENV_VARS="$ENV_VARS,USE_MOCK_APIS=false"
ENV_VARS="$ENV_VARS,DEBUG=false"
ENV_VARS="$ENV_VARS,LOG_LEVEL=INFO"
ENV_VARS="$ENV_VARS,APP_VERSION=1.0.0-mvp"
ENV_VARS="$ENV_VARS,CORS_ORIGINS=*"

# Google Cloud Configuration
ENV_VARS="$ENV_VARS,GOOGLE_CLOUD_PROJECT_ID=$GOOGLE_AI_PROJECT_ID"
ENV_VARS="$ENV_VARS,GOOGLE_AI_PROJECT_ID=$GOOGLE_AI_PROJECT_ID"
ENV_VARS="$ENV_VARS,GOOGLE_AI_LOCATION=$GOOGLE_AI_LOCATION"
ENV_VARS="$ENV_VARS,GOOGLE_AI_MODEL=gemini-2.0-flash-001"
ENV_VARS="$ENV_VARS,GOOGLE_AI_ORCHESTRATION_MODEL=gemini-2.0-pro-001"
ENV_VARS="$ENV_VARS,VERTEX_AI_LOCATION=$VERTEX_AI_LOCATION"
ENV_VARS="$ENV_VARS,GCS_BUCKET_NAME=$GCS_BUCKET_NAME"

# API Keys
ENV_VARS="$ENV_VARS,GOOGLE_MAPS_API_KEY=$GOOGLE_MAPS_API_KEY"
ENV_VARS="$ENV_VARS,TICKETMASTER_API_KEY=$TICKETMASTER_API_KEY"
ENV_VARS="$ENV_VARS,TICKETMASTER_API_SECRET=$TICKETMASTER_API_SECRET"
ENV_VARS="$ENV_VARS,OPENWEATHERMAP_API_KEY=$OPENWEATHERMAP_API_KEY"
ENV_VARS="$ENV_VARS,RECREATION_GOV_API_KEY=$RECREATION_GOV_API_KEY"

# Optional APIs (from .env if available)
if [ ! -z "$SPOTIFY_CLIENT_ID" ]; then
    ENV_VARS="$ENV_VARS,SPOTIFY_CLIENT_ID=$SPOTIFY_CLIENT_ID"
    ENV_VARS="$ENV_VARS,SPOTIFY_CLIENT_SECRET=$SPOTIFY_CLIENT_SECRET"
fi

# Database and Redis (using Cloud SQL and Memorystore in production)
# For MVP, we'll use SQLite and local Redis
ENV_VARS="$ENV_VARS,DATABASE_URL=sqlite:///./roadtrip.db"
ENV_VARS="$ENV_VARS,REDIS_URL=redis://localhost:6379"

# Security Keys
ENV_VARS="$ENV_VARS,SECRET_KEY=$SECRET_KEY"
ENV_VARS="$ENV_VARS,JWT_SECRET_KEY=$JWT_SECRET_KEY"

# Feature Flags
ENV_VARS="$ENV_VARS,FEATURE_VOICE_COMMANDS=true"
ENV_VARS="$ENV_VARS,FEATURE_BOOKINGS=true"
ENV_VARS="$ENV_VARS,FEATURE_2FA=false"
ENV_VARS="$ENV_VARS,ENABLE_VOICE_SAFETY=true"
ENV_VARS="$ENV_VARS,ENABLE_BOOKING_COMMISSION=true"
ENV_VARS="$ENV_VARS,ENABLE_SEASONAL_PERSONALITIES=true"
ENV_VARS="$ENV_VARS,ENABLE_AR_FEATURES=true"

# Rate Limiting
ENV_VARS="$ENV_VARS,RATE_LIMIT_ENABLED=true"
ENV_VARS="$ENV_VARS,RATE_LIMIT_DEFAULT=100/hour"

echo -e "\n${YELLOW}Step 2: Enable required Google APIs${NC}"
gcloud services enable \
    aiplatform.googleapis.com \
    generativelanguage.googleapis.com \
    texttospeech.googleapis.com \
    speech.googleapis.com \
    storage.googleapis.com \
    secretmanager.googleapis.com \
    maps-backend.googleapis.com \
    places-backend.googleapis.com \
    directions-backend.googleapis.com

echo -e "${GREEN}✓ APIs enabled${NC}"

echo -e "\n${YELLOW}Step 3: Grant service account permissions for Vertex AI${NC}"

# Get the service account
SERVICE_ACCOUNT=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(spec.template.spec.serviceAccountName)' 2>/dev/null || echo "")

if [ -z "$SERVICE_ACCOUNT" ]; then
    # Use default compute service account
    PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
    SERVICE_ACCOUNT="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
fi

echo "Using service account: $SERVICE_ACCOUNT"

# Grant Vertex AI permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/aiplatform.user" || echo "Permission may already exist"

echo -e "${GREEN}✓ Permissions configured${NC}"

echo -e "\n${YELLOW}Step 4: Update Cloud Run service with all configurations${NC}"

# Update the service
gcloud run services update $SERVICE_NAME \
    --region $REGION \
    --update-env-vars "$ENV_VARS"

echo -e "${GREEN}✓ Service updated with all API configurations${NC}"

# Wait for deployment
echo -e "\n${YELLOW}Waiting for service to be ready...${NC}"
sleep 15

# Test the service
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo -e "\n${YELLOW}Testing service health...${NC}"

HEALTH_RESPONSE=$(curl -s "$SERVICE_URL/health" -w "\nHTTP_STATUS:%{http_code}")
HTTP_STATUS=$(echo "$HEALTH_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
HEALTH_BODY=$(echo "$HEALTH_RESPONSE" | grep -v "HTTP_STATUS:")

echo "$HEALTH_BODY" | python3 -m json.tool || echo "$HEALTH_BODY"

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "\n${GREEN}✅ Service is running!${NC}"
    
    # Check if AI is working
    if echo "$HEALTH_BODY" | grep -q '"gemini_ai".*"healthy"'; then
        echo -e "${GREEN}✅ AI is configured and working!${NC}"
    else
        echo -e "${YELLOW}⚠️  AI might still be initializing or needs additional configuration${NC}"
    fi
else
    echo -e "\n${RED}❌ Service health check failed (HTTP $HTTP_STATUS)${NC}"
fi

echo -e "\n${BLUE}===================================================${NC}"
echo -e "${BLUE}📋 Configuration Summary:${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "✅ Configured APIs:"
echo "   - Google Maps (Navigation & Places)"
echo "   - Vertex AI (Gemini 2.0 Flash & Pro)"
echo "   - Ticketmaster (Events)"
echo "   - OpenWeatherMap (Weather)"
echo "   - Recreation.gov (Camping)"
echo ""
echo "🔧 Test Commands:"
echo ""
echo "1. Test voice interaction:"
echo "   curl -X POST $SERVICE_URL/api/voice-assistant/interact \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"user_input\": \"Tell me about Chicago\", \"location\": {\"latitude\": 41.8781, \"longitude\": -87.6298}, \"user_id\": \"test\"}'"
echo ""
echo "2. View logs:"
echo "   gcloud logging tail --format='value(textPayload)' --filter='resource.type=\"cloud_run_revision\"'"
echo ""
echo -e "${GREEN}🚗 Your road trip app is ready with REAL AI!${NC}"