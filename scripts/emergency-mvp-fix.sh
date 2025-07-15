#!/bin/bash
# Emergency fix for MVP deployment - get it running for tomorrow's road trip!

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}🚑 Emergency MVP Fix for Road Trip${NC}"
echo -e "${BLUE}===================================================${NC}"

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"

echo -e "\n${YELLOW}Step 1: Enable required Google APIs${NC}"
gcloud services enable \
    generativelanguage.googleapis.com \
    aiplatform.googleapis.com \
    texttospeech.googleapis.com \
    storage.googleapis.com \
    secretmanager.googleapis.com

echo -e "${GREEN}✓ APIs enabled${NC}"

# Skip secret creation for MVP - using environment variables for simplicity
# echo -e "\n${YELLOW}Step 2: Create minimal secrets in Secret Manager${NC}"
# In production, you should use Secret Manager, but for MVP we'll use env vars

echo -e "\n${YELLOW}Step 2: Update Cloud Run service with minimal environment${NC}"

# Check if we need to update SECRET_KEY and JWT_SECRET_KEY
# For MVP, we'll keep them as env vars for simplicity
if [ -z "$SECRET_KEY" ]; then
    SECRET_KEY=$(openssl rand -base64 32)
fi
if [ -z "$JWT_SECRET_KEY" ]; then
    JWT_SECRET_KEY=$(openssl rand -base64 32)
fi

# Update the service with essential environment variables
# Using Gemini 2.0 Flash for general AI tasks and 2.0 Pro for orchestration
echo "Updating Cloud Run service configuration..."
gcloud run services update $SERVICE_NAME \
    --region $REGION \
    --update-env-vars "ENVIRONMENT=production,DEBUG=false,LOG_LEVEL=INFO,APP_VERSION=1.0.0-mvp,CORS_ORIGINS=*,GOOGLE_CLOUD_PROJECT_ID=$PROJECT_ID,GOOGLE_AI_PROJECT_ID=$PROJECT_ID,GOOGLE_AI_LOCATION=us-central1,GOOGLE_AI_MODEL=gemini-2.0-flash-001,GOOGLE_AI_ORCHESTRATION_MODEL=gemini-2.0-pro-001,VERTEX_AI_LOCATION=us-central1,RATE_LIMIT_ENABLED=true,RATE_LIMIT_DEFAULT=100/hour,FEATURE_VOICE_COMMANDS=true,FEATURE_BOOKINGS=false,FEATURE_2FA=false,DATABASE_URL=sqlite:///./test.db,REDIS_URL=redis://localhost:6379,SECRET_KEY=$SECRET_KEY,JWT_SECRET_KEY=$JWT_SECRET_KEY"

echo -e "${GREEN}✓ Service updated${NC}"

echo -e "\n${YELLOW}Step 3: Grant service account permissions${NC}"

# Get the service account
SERVICE_ACCOUNT=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(spec.template.spec.serviceAccountName)')

if [ -z "$SERVICE_ACCOUNT" ]; then
    SERVICE_ACCOUNT="$PROJECT_ID-compute@developer.gserviceaccount.com"
fi

echo "Service account: $SERVICE_ACCOUNT"

# Grant necessary permissions
for role in \
    "aiplatform.user" \
    "secretmanager.secretAccessor" \
    "storage.objectAdmin"
do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/$role" \
        --quiet
done

echo -e "${GREEN}✓ Permissions granted${NC}"

echo -e "\n${YELLOW}Step 4: Test the service${NC}"

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo "Service URL: $SERVICE_URL"

sleep 5  # Give service time to restart

# Test health endpoint
echo -e "\n${YELLOW}Testing health endpoint...${NC}"
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" "$SERVICE_URL/health")
HTTP_STATUS=$(echo "$HEALTH_RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ Service is responding!${NC}"
    echo "$HEALTH_RESPONSE" | grep -v "HTTP_STATUS:"
else
    echo -e "${RED}❌ Service health check failed (HTTP $HTTP_STATUS)${NC}"
fi

echo -e "\n${BLUE}===================================================${NC}"
echo -e "${BLUE}🎯 Quick Start Guide for Your Road Trip:${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""
echo "1. Your API is running at: $SERVICE_URL"
echo ""
echo "2. You still need to add your API keys via the Cloud Console:"
echo "   - Go to: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/revisions"
echo "   - Click 'Edit & Deploy New Revision'"
echo "   - Add these environment variables:"
echo "     • GOOGLE_MAPS_API_KEY (required for navigation)"
echo "     • OPENWEATHERMAP_API_KEY (for weather stories)"
echo ""
echo "3. For the mobile app, update the API URL to: $SERVICE_URL"
echo ""
echo "4. Monitor logs during your trip:"
echo "   gcloud logging tail \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\""
echo ""
echo -e "${YELLOW}⚠️  MVP Mode Active:${NC}"
echo "- Using SQLite (no external database needed)"
echo "- Gemini 2.0 Flash for stories & responses"
echo "- Gemini 2.0 Pro for intelligent orchestration"
echo "- Bookings disabled for simplicity"
echo "- No authentication required"
echo ""
echo -e "${GREEN}Safe travels! 🚗✨${NC}"