#!/bin/bash
# Deploy AI Road Trip Storyteller to Google Cloud Run

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}AI Road Trip Storyteller - Cloud Run Deployment${NC}"
echo -e "${BLUE}===================================================${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: Google Cloud SDK is not installed${NC}"
    echo "Please install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID from .env or environment
PROJECT_ID=$(grep "GCP_PROJECT_ID=" .env 2>/dev/null | cut -d'=' -f2 || echo ${GCP_PROJECT_ID:-roadtrip-460720})
REGION=${REGION:-us-central1}
SERVICE_NAME=${SERVICE_NAME:-roadtrip-api}

echo -e "\n${YELLOW}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service: $SERVICE_NAME"

# Set project
echo -e "\n${YELLOW}Setting project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "\n${YELLOW}Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com cloudrun.googleapis.com artifactregistry.googleapis.com

# Create .gcloudignore if it doesn't exist
if [ ! -f .gcloudignore ]; then
    echo -e "\n${YELLOW}Creating .gcloudignore...${NC}"
    cat > .gcloudignore << EOF
.git
.gitignore
*.pyc
__pycache__/
.pytest_cache/
.coverage
.env
.env.*
*.log
node_modules/
mobile/node_modules/
.mypy_cache/
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store
credentials/
*.db
*.sqlite
test_*.py
tests/
docs/
README.md
*.md
EOF
    echo -e "${GREEN}✓ Created .gcloudignore${NC}"
fi

# Build and deploy
echo -e "\n${YELLOW}Building and deploying to Cloud Run...${NC}"
echo "This will:"
echo "  1. Build a container image using Cloud Build"
echo "  2. Push to Google Container Registry"
echo "  3. Deploy to Cloud Run"
echo ""

# Deploy using source
gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --platform managed \
    --allow-unauthenticated \
    --port 8000 \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 1 \
    --max-instances 100 \
    --timeout 30m \
    --set-env-vars="ENVIRONMENT=production,LOG_LEVEL=INFO,APP_VERSION=1.0.0" \
    --set-secrets="DATABASE_URL=roadtrip-db-url:latest" 2>/dev/null || true

# Check if deployment succeeded
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✅ Deployment successful!${NC}"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
    
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${GREEN}🎉 Your app is live!${NC}"
    echo -e "${BLUE}===================================================${NC}"
    echo ""
    echo "Service URL: $SERVICE_URL"
    echo ""
    echo "Test endpoints:"
    echo "  Health: $SERVICE_URL/health"
    echo "  Docs: $SERVICE_URL/docs"
    echo "  Detailed Health: $SERVICE_URL/health/detailed"
    echo ""
    
    # Test the health endpoint
    echo -e "${YELLOW}Testing health endpoint...${NC}"
    curl -s "$SERVICE_URL/health" | grep -q "healthy" && echo -e "${GREEN}✓ Health check passed${NC}" || echo -e "${RED}✗ Health check failed${NC}"
    
else
    echo -e "\n${RED}Deployment failed${NC}"
    echo "Check the error messages above"
fi

echo -e "\n${YELLOW}Next steps:${NC}"
echo "1. Set up environment variables in Cloud Run console"
echo "2. Configure Cloud SQL connection"
echo "3. Set up custom domain (optional)"
echo "4. Monitor logs: gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit 50"