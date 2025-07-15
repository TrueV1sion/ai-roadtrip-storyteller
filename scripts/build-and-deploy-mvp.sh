#!/bin/bash
# Build and deploy MVP with correct Vertex AI configuration

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}🏗️  Building and Deploying MVP with Vertex AI${NC}"
echo -e "${BLUE}===================================================${NC}"

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo -e "\n${YELLOW}Step 1: Build the container image${NC}"

# Create a simplified Dockerfile for MVP
cat > Dockerfile.mvp << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional Vertex AI dependencies
RUN pip install --no-cache-dir \
    google-cloud-aiplatform>=1.25.0 \
    vertexai>=1.0.0

# Copy application code
COPY backend/ .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV GOOGLE_CLOUD_PROJECT=roadtrip-460720

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF

echo -e "${GREEN}✓ Dockerfile created${NC}"

echo -e "\n${YELLOW}Step 2: Build and push the image${NC}"

# Build the image
docker build -f Dockerfile.mvp -t $IMAGE_NAME:latest .

# Push to Container Registry
docker push $IMAGE_NAME:latest

echo -e "${GREEN}✓ Image pushed to Container Registry${NC}"

echo -e "\n${YELLOW}Step 3: Deploy to Cloud Run${NC}"

# Deploy with all the correct configurations
gcloud run deploy $SERVICE_NAME \
    --image=$IMAGE_NAME:latest \
    --region=$REGION \
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

echo -e "${GREEN}✓ Service deployed${NC}"

# Cleanup
rm -f Dockerfile.mvp

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo -e "\n${BLUE}===================================================${NC}"
echo -e "${BLUE}🎉 Deployment Complete!${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "Next steps:"
echo "1. Wait 30 seconds for the service to fully start"
echo "2. Test health: curl $SERVICE_URL/health"
echo "3. Test AI: curl -X POST $SERVICE_URL/api/voice-assistant/interact -H 'Content-Type: application/json' -d '{\"user_input\": \"Tell me about Chicago\", \"location\": {\"latitude\": 41.8781, \"longitude\": -87.6298}, \"user_id\": \"test\"}'"
echo ""
echo -e "${GREEN}🚗 Your road trip app should now work with real Vertex AI!${NC}"