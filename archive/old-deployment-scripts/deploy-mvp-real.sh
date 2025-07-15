#!/bin/bash
# Deploy MVP with REAL AI functionality - no mocks!

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}🚀 Deploying Road Trip MVP with Real AI${NC}"
echo -e "${BLUE}===================================================${NC}"

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"

# Load values from .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

echo -e "\n${YELLOW}Step 1: Grant Vertex AI permissions to service account${NC}"

# Get or create service account
SERVICE_ACCOUNT="roadtrip-mvp-sa@$PROJECT_ID.iam.gserviceaccount.com"

# Check if service account exists
if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "Creating service account..."
    gcloud iam service-accounts create roadtrip-mvp-sa \
        --display-name="Road Trip MVP Service Account" \
        --project=$PROJECT_ID
fi

# Grant necessary permissions
echo "Granting permissions..."
for role in \
    "aiplatform.user" \
    "storage.objectAdmin" \
    "secretmanager.secretAccessor" \
    "logging.logWriter"
do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/$role" \
        --quiet || echo "Role $role may already be assigned"
done

echo -e "${GREEN}✓ Service account configured${NC}"

echo -e "\n${YELLOW}Step 2: Deploy with real configurations${NC}"

# Deploy the service with all real configurations
# First, get the current image
CURRENT_IMAGE=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(spec.template.spec.containers[0].image)" 2>/dev/null || echo "")

if [ -z "$CURRENT_IMAGE" ]; then
    echo -e "${RED}Error: No existing service found. Need to build and push image first.${NC}"
    exit 1
fi

echo "Using image: $CURRENT_IMAGE"

gcloud run deploy $SERVICE_NAME \
    --image=$CURRENT_IMAGE \
    --region $REGION \
    --service-account=$SERVICE_ACCOUNT \
    --update-env-vars "ENVIRONMENT=production,\
TEST_MODE=live,\
USE_MOCK_APIS=false,\
DEBUG=false,\
LOG_LEVEL=INFO,\
APP_VERSION=1.0.0-mvp,\
CORS_ORIGINS=*,\
GOOGLE_CLOUD_PROJECT_ID=$PROJECT_ID,\
GOOGLE_AI_PROJECT_ID=$PROJECT_ID,\
GOOGLE_AI_LOCATION=us-central1,\
GOOGLE_AI_MODEL=gemini-1.5-flash,\
VERTEX_AI_LOCATION=us-central1,\
GCS_BUCKET_NAME=$GCS_BUCKET_NAME,\
RATE_LIMIT_ENABLED=true,\
RATE_LIMIT_DEFAULT=1000/hour,\
FEATURE_VOICE_COMMANDS=true,\
FEATURE_BOOKINGS=true,\
FEATURE_2FA=false,\
ENABLE_VOICE_SAFETY=true,\
ENABLE_BOOKING_COMMISSION=true,\
ENABLE_SEASONAL_PERSONALITIES=true,\
ENABLE_AR_FEATURES=true" \
    --update-secrets "\
GOOGLE_MAPS_API_KEY=google-maps-api-key:latest,\
TICKETMASTER_API_KEY=ticketmaster-api-key:latest,\
OPENWEATHERMAP_API_KEY=openweather-api-key:latest,\
RECREATION_GOV_API_KEY=recreation-gov-api-key:latest,\
DATABASE_URL=roadtrip-database-url:latest,\
JWT_SECRET_KEY=roadtrip-jwt-secret:latest,\
SECRET_KEY=roadtrip-secret-key:latest"

echo -e "${GREEN}✓ Service deployed with real configurations${NC}"

# Wait for deployment
echo -e "\n${YELLOW}Waiting for service to be ready...${NC}"
sleep 20

# Test the service
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo -e "\n${YELLOW}Testing service...${NC}"

# Test health endpoint
echo "1. Testing health endpoint..."
HEALTH=$(curl -s "$SERVICE_URL/health")
echo "$HEALTH" | python3 -m json.tool

# Test AI functionality
echo -e "\n2. Testing AI story generation..."
AI_TEST=$(curl -s -X POST "$SERVICE_URL/api/voice-assistant/interact" \
  -H "Content-Type: application/json" \
  -d '{
    "user_input": "Tell me an interesting story about Chicago",
    "location": {"latitude": 41.8781, "longitude": -87.6298},
    "user_id": "test-user"
  }')
echo "$AI_TEST" | python3 -m json.tool || echo "$AI_TEST"

echo -e "\n${BLUE}===================================================${NC}"
echo -e "${BLUE}🎉 Deployment Complete!${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "✅ Real AI Features Enabled:"
echo "   - Vertex AI (Gemini 1.5) for story generation"
echo "   - Google Maps for navigation"
echo "   - Weather integration"
echo "   - Event discovery"
echo "   - Camping reservations"
echo ""
echo "📱 Mobile App Configuration:"
echo "   API_URL=$SERVICE_URL"
echo ""
echo "📊 Monitor logs:"
echo "   gcloud logging tail \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\""
echo ""
echo -e "${GREEN}🚗 Your road trip app is ready with REAL AI!${NC}"