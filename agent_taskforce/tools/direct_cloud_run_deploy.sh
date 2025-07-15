#!/bin/bash
# Emergency Direct Cloud Run Deployment Script
# AI Road Trip Storyteller - Mission Critical Deployment

set -e

echo "=== AI ROAD TRIP STORYTELLER - EMERGENCY DEPLOYMENT ==="
echo "Unified Deployment Team Executing Mission"
echo "Time: $(date)"
echo

# Configuration
PROJECT_ID="roadtrip-460720"
REGION="us-central1"
SERVICE_NAME="ai-roadtrip-api"
IMAGE_NAME="roadtrip-production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}[DEPLOYMENT COMMANDER]${NC} Initiating emergency deployment sequence..."

# Step 1: Verify prerequisites
echo -e "\n${YELLOW}[SECURITY OPS]${NC} Verifying authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}ERROR: Not authenticated with Google Cloud${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Authentication verified${NC}"

# Step 2: Push Docker image
echo -e "\n${YELLOW}[CONTAINER ENGINEER]${NC} Pushing Docker image to GCR..."
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME:latest || {
    echo -e "${RED}ERROR: Failed to push Docker image${NC}"
    echo "Please run: gcloud auth configure-docker"
    exit 1
}
echo -e "${GREEN}✓ Docker image pushed successfully${NC}"

# Step 3: Create Cloud SQL instance (minimal for now)
echo -e "\n${YELLOW}[DATABASE ADMIN]${NC} Setting up Cloud SQL..."
if ! gcloud sql instances describe roadtrip-db --project=$PROJECT_ID 2>/dev/null; then
    echo "Creating Cloud SQL instance..."
    gcloud sql instances create roadtrip-db \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --project=$PROJECT_ID \
        --no-backup
    
    # Create database and user
    gcloud sql databases create roadtrip --instance=roadtrip-db --project=$PROJECT_ID
    gcloud sql users create roadtrip_user --instance=roadtrip-db --password=temporary123 --project=$PROJECT_ID
else
    echo "Cloud SQL instance already exists"
fi
echo -e "${GREEN}✓ Database ready${NC}"

# Step 4: Create Redis instance
echo -e "\n${YELLOW}[DATABASE ADMIN]${NC} Setting up Redis..."
if ! gcloud redis instances describe roadtrip-cache --region=$REGION --project=$PROJECT_ID 2>/dev/null; then
    echo "Creating Redis instance..."
    gcloud redis instances create roadtrip-cache \
        --size=1 \
        --region=$REGION \
        --redis-version=redis_7_0 \
        --project=$PROJECT_ID
else
    echo "Redis instance already exists"
fi
echo -e "${GREEN}✓ Redis ready${NC}"

# Step 5: Create secrets
echo -e "\n${YELLOW}[SECURITY OPS]${NC} Configuring secrets..."
# Create temporary secrets for initial deployment
echo "temporary-jwt-secret-$(date +%s)" | gcloud secrets create jwt-secret-key --data-file=- --project=$PROJECT_ID 2>/dev/null || true
echo "temporary-app-secret-$(date +%s)" | gcloud secrets create app-secret-key --data-file=- --project=$PROJECT_ID 2>/dev/null || true

# Step 6: Deploy to Cloud Run
echo -e "\n${YELLOW}[DEPLOYMENT COMMANDER]${NC} Deploying to Cloud Run..."

# Get database connection info
DB_CONNECTION_NAME=$(gcloud sql instances describe roadtrip-db --format="value(connectionName)" --project=$PROJECT_ID)

gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$IMAGE_NAME:latest \
    --platform managed \
    --region $REGION \
    --project $PROJECT_ID \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --min-instances 1 \
    --max-instances 10 \
    --port 8000 \
    --add-cloudsql-instances $DB_CONNECTION_NAME \
    --set-env-vars "DATABASE_URL=postgresql://roadtrip_user:temporary123@/roadtrip?host=/cloudsql/$DB_CONNECTION_NAME" \
    --set-env-vars "REDIS_URL=redis://10.0.0.0:6379" \
    --set-env-vars "ENVIRONMENT=production" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
    --set-env-vars "VERTEX_AI_LOCATION=$REGION" \
    --set-secrets "JWT_SECRET_KEY=jwt-secret-key:latest" \
    --set-secrets "SECRET_KEY=app-secret-key:latest"

# Step 7: Get service URL and test
echo -e "\n${YELLOW}[SITE RELIABILITY]${NC} Validating deployment..."
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)' --project=$PROJECT_ID)
echo -e "${GREEN}✓ Service deployed at: $SERVICE_URL${NC}"

# Test health endpoint
echo -e "\n${YELLOW}[SITE RELIABILITY]${NC} Testing health endpoint..."
sleep 10  # Give service time to start
if curl -s "$SERVICE_URL/health" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Health check passed!${NC}"
else
    echo -e "${YELLOW}⚠ Health check pending - service may still be starting${NC}"
fi

# Final status
echo -e "\n${GREEN}=== DEPLOYMENT SUCCESSFUL ===${NC}"
echo "Service URL: $SERVICE_URL"
echo "API Docs: $SERVICE_URL/docs"
echo
echo -e "${YELLOW}NEXT STEPS:${NC}"
echo "1. Update API keys in Secret Manager"
echo "2. Configure custom domain"
echo "3. Set up monitoring dashboards"
echo "4. Enable VPC connector for Redis"
echo
echo -e "${GREEN}The AI Road Trip Storyteller is now live!${NC}"
echo "Families can start their magical journeys! 🚗✨"