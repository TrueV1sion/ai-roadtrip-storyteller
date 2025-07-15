#!/bin/bash
# Deploy MVP to Google Cloud Run - Simplified for Quick Launch

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}🚀 AI Road Trip Storyteller - MVP Deployment${NC}"
echo -e "${BLUE}===================================================${NC}"

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"roadtrip-mvp"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="roadtrip-mvp"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo -e "\n${YELLOW}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service: $SERVICE_NAME"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ Google Cloud SDK not installed${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not installed${NC}"
    echo "Install from: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites satisfied${NC}"

# Set project
echo -e "\n${YELLOW}Setting up Google Cloud project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "\n${YELLOW}Enabling required APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    aiplatform.googleapis.com \
    texttospeech.googleapis.com \
    storage.googleapis.com

echo -e "${GREEN}✓ APIs enabled${NC}"

# Create minimal Dockerfile for MVP
echo -e "\n${YELLOW}Creating MVP Dockerfile...${NC}"
cat > Dockerfile.mvp << 'EOF'
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

echo -e "${GREEN}✓ Dockerfile created${NC}"

# Build and push Docker image
echo -e "\n${YELLOW}Building Docker image...${NC}"
docker build -f Dockerfile.mvp -t $IMAGE_NAME:latest ./backend

echo -e "\n${YELLOW}Pushing image to Container Registry...${NC}"
docker push $IMAGE_NAME:latest

echo -e "${GREEN}✓ Image pushed to registry${NC}"

# Deploy to Cloud Run
echo -e "\n${YELLOW}Deploying to Cloud Run...${NC}"

gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME:latest \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8000 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 1 \
    --max-instances 10 \
    --timeout 30m \
    --set-env-vars "
ENVIRONMENT=production,
LOG_LEVEL=INFO,
APP_VERSION=1.0.0-mvp,
CORS_ORIGINS=*
"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

echo -e "\n${GREEN}===================================================${NC}"
echo -e "${GREEN}🎉 MVP Deployed Successfully!${NC}"
echo -e "${GREEN}===================================================${NC}"
echo ""
echo -e "${BLUE}Service URL:${NC} $SERVICE_URL"
echo ""
echo -e "${YELLOW}Test Endpoints:${NC}"
echo "  Health: $SERVICE_URL/health"
echo "  MVP Health: $SERVICE_URL/api/mvp/health"
echo "  API Docs: $SERVICE_URL/docs"
echo ""

# Quick health check
echo -e "${YELLOW}Running health check...${NC}"
sleep 5  # Give service time to start

if curl -s "$SERVICE_URL/health" | grep -q "ok"; then
    echo -e "${GREEN}✓ Service is healthy!${NC}"
else
    echo -e "${RED}⚠️  Health check failed - service may still be starting${NC}"
fi

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Update mobile app with service URL: $SERVICE_URL"
echo "2. Configure environment variables in Cloud Console"
echo "3. Test voice commands on real devices"
echo "4. Monitor logs: gcloud logging tail"
echo ""
echo -e "${BLUE}View logs:${NC}"
echo "gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit 50"
echo ""
echo -e "${BLUE}Update environment variables:${NC}"
echo "gcloud run services update $SERVICE_NAME --update-env-vars KEY=VALUE"

# Cleanup
rm -f Dockerfile.mvp

echo -e "\n${GREEN}✅ MVP deployment complete!${NC}"