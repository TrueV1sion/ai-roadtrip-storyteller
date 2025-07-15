#!/bin/bash
# Deploy MVP directly from source using Cloud Run

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}🚀 Deploying MVP from Source${NC}"
echo -e "${BLUE}===================================================${NC}"

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"

echo -e "\n${YELLOW}Deploying directly from source code...${NC}"
echo "Cloud Run will build the container automatically"

cd backend

# Deploy from source - Cloud Run will build it
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region=$REGION \
    --project=$PROJECT_ID \
    --platform=managed \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --min-instances=1 \
    --max-instances=10 \
    --timeout=30m \
    --service-account=roadtrip-mvp-sa@$PROJECT_ID.iam.gserviceaccount.com \
    --set-env-vars "\
ENVIRONMENT=production,\
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
DEFAULT_AI_PROVIDER=google,\
VERTEX_AI_LOCATION=us-central1,\
RATE_LIMIT_ENABLED=true,\
FEATURE_VOICE_COMMANDS=true,\
FEATURE_BOOKINGS=true" \
    --set-secrets "\
GOOGLE_MAPS_API_KEY=google-maps-api-key:latest,\
TICKETMASTER_API_KEY=ticketmaster-api-key:latest,\
OPENWEATHERMAP_API_KEY=openweather-api-key:latest,\
RECREATION_GOV_API_KEY=recreation-gov-api-key:latest,\
DATABASE_URL=roadtrip-database-url:latest,\
JWT_SECRET_KEY=roadtrip-jwt-secret:latest,\
SECRET_KEY=roadtrip-secret-key:latest"

cd ..

echo -e "\n${GREEN}✅ Deployment submitted!${NC}"
echo ""
echo "Cloud Run is building and deploying your service."
echo "This may take 5-10 minutes."
echo ""
echo "Check status with:"
echo "  gcloud run services describe $SERVICE_NAME --region $REGION"