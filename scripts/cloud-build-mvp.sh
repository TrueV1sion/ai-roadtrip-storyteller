#!/bin/bash
# Build and deploy MVP using Cloud Build

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}🏗️  Building MVP with Cloud Build${NC}"
echo -e "${BLUE}===================================================${NC}"

PROJECT_ID="roadtrip-460720"
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo -e "\n${YELLOW}Step 1: Create a Cloud Build configuration${NC}"

# Create a simplified cloudbuild configuration for MVP
cat > cloudbuild-mvp.yaml << 'EOF'
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/roadtrip-mvp:latest'
      - '-f'
      - 'backend/Dockerfile'
      - '.'

  # Push the container image to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - 'gcr.io/$PROJECT_ID/roadtrip-mvp:latest'

  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gcloud'
    args:
      - 'run'
      - 'deploy'
      - 'roadtrip-mvp'
      - '--image=gcr.io/$PROJECT_ID/roadtrip-mvp:latest'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--memory=2Gi'
      - '--cpu=2'
      - '--min-instances=1'
      - '--max-instances=10'
      - '--timeout=30m'
      - '--service-account=roadtrip-mvp-sa@$PROJECT_ID.iam.gserviceaccount.com'
      - '--set-env-vars=ENVIRONMENT=production,TEST_MODE=live,USE_MOCK_APIS=false,DEBUG=false,LOG_LEVEL=INFO,APP_VERSION=1.0.0-mvp,CORS_ORIGINS=*,GOOGLE_CLOUD_PROJECT_ID=$PROJECT_ID,GOOGLE_AI_PROJECT_ID=$PROJECT_ID,GOOGLE_AI_LOCATION=us-central1,GOOGLE_AI_MODEL=gemini-1.5-flash,DEFAULT_AI_PROVIDER=google,VERTEX_AI_LOCATION=us-central1,RATE_LIMIT_ENABLED=true,FEATURE_VOICE_COMMANDS=true,FEATURE_BOOKINGS=true'
      - '--set-secrets=GOOGLE_MAPS_API_KEY=google-maps-api-key:latest,TICKETMASTER_API_KEY=ticketmaster-api-key:latest,OPENWEATHERMAP_API_KEY=openweather-api-key:latest,RECREATION_GOV_API_KEY=recreation-gov-api-key:latest,DATABASE_URL=roadtrip-database-url:latest,JWT_SECRET_KEY=roadtrip-jwt-secret:latest,SECRET_KEY=roadtrip-secret-key:latest'

images:
  - 'gcr.io/$PROJECT_ID/roadtrip-mvp:latest'

options:
  logging: CLOUD_LOGGING_ONLY
EOF

echo -e "${GREEN}✓ Cloud Build configuration created${NC}"

echo -e "\n${YELLOW}Step 2: Check if Dockerfile exists${NC}"
if [ ! -f backend/Dockerfile ]; then
    echo "Creating Dockerfile..."
    cat > backend/Dockerfile << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Vertex AI dependencies
RUN pip install --no-cache-dir \
    google-cloud-aiplatform>=1.25.0 \
    vertexai>=1.0.0 \
    langchain>=0.1.0 \
    langchain-google-vertexai>=0.0.1

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF
    echo -e "${GREEN}✓ Dockerfile created${NC}"
else
    echo -e "${GREEN}✓ Dockerfile exists${NC}"
fi

echo -e "\n${YELLOW}Step 3: Submit build to Cloud Build${NC}"
echo "This will build your container in the cloud and deploy it..."

# Submit the build
gcloud builds submit \
    --config=cloudbuild-mvp.yaml \
    --project=$PROJECT_ID \
    --substitutions=_SERVICE_NAME=$SERVICE_NAME,_REGION=$REGION

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo -e "\n${BLUE}===================================================${NC}"
echo -e "${BLUE}🎉 Build and Deployment Complete!${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo "Test your service:"
echo "1. Health check: curl $SERVICE_URL/health"
echo "2. AI test: curl -X POST $SERVICE_URL/api/voice-assistant/interact -H 'Content-Type: application/json' -d '{\"user_input\": \"Tell me about Chicago\", \"location\": {\"latitude\": 41.8781, \"longitude\": -87.6298}, \"user_id\": \"test\"}'"
echo ""
echo -e "${GREEN}🚗 Your road trip app is being deployed with real AI!${NC}"

# Cleanup
rm -f cloudbuild-mvp.yaml