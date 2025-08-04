#!/bin/bash

# Deploy Backend Production Script
# Deploys the fixed backend to Google Cloud Run

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== RoadTrip Backend Production Deployment ===${NC}"

# Configuration
PROJECT_ID="roadtrip-460720"
REGION="us-central1"
SERVICE_NAME="roadtrip-backend-production"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    exit 1
fi

# Set the project
echo -e "${YELLOW}Setting project to ${PROJECT_ID}...${NC}"
gcloud config set project ${PROJECT_ID}

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${RED}Error: Not authenticated with gcloud. Please run 'gcloud auth login'${NC}"
    exit 1
fi

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com \
    aiplatform.googleapis.com

# Check if secrets exist (create placeholders if they don't)
echo -e "${YELLOW}Checking required secrets...${NC}"

REQUIRED_SECRETS=(
    "database-url"
    "redis-url"
    "jwt-secret-key"
    "jwt-refresh-secret-key"
    "google-maps-api-key"
    "openweather-api-key"
    "ticketmaster-api-key"
    "opentable-api-key"
    "viator-api-key"
    "recreation-gov-api-key"
    "spotify-client-id"
    "spotify-client-secret"
    "twilio-account-sid"
    "twilio-auth-token"
    "twilio-from-phone"
    "sendgrid-api-key"
    "encryption-key"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if ! gcloud secrets describe ${secret} --project=${PROJECT_ID} &> /dev/null; then
        echo -e "${YELLOW}Creating placeholder for secret: ${secret}${NC}"
        echo "PLACEHOLDER_VALUE" | gcloud secrets create ${secret} \
            --data-file=- \
            --project=${PROJECT_ID} \
            --replication-policy="automatic"
    else
        echo -e "${GREEN}Secret exists: ${secret}${NC}"
    fi
done

# Grant Secret Manager access to the service account
echo -e "${YELLOW}Granting Secret Manager access to service account...${NC}"
SERVICE_ACCOUNT="roadtrip-mvp-sa@${PROJECT_ID}.iam.gserviceaccount.com"

for secret in "${REQUIRED_SECRETS[@]}"; do
    gcloud secrets add-iam-policy-binding ${secret} \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor" \
        --project=${PROJECT_ID} \
        --quiet || true
done

# Navigate to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}/../.."

# Check if backend directory exists
if [ ! -d "backend" ]; then
    echo -e "${RED}Error: backend directory not found${NC}"
    exit 1
fi

# Check if Dockerfile exists
if [ ! -f "backend/Dockerfile" ]; then
    echo -e "${RED}Error: backend/Dockerfile not found${NC}"
    exit 1
fi

# Check if cloudbuild file exists
if [ ! -f "backend/cloudbuild-backend-production.yaml" ]; then
    echo -e "${RED}Error: backend/cloudbuild-backend-production.yaml not found${NC}"
    exit 1
fi

# Submit the build
echo -e "${YELLOW}Submitting build to Cloud Build...${NC}"
gcloud builds submit \
    --config=backend/cloudbuild-backend-production.yaml \
    --project=${PROJECT_ID} \
    --region=${REGION} \
    --substitutions=_SERVICE_NAME=${SERVICE_NAME},_REGION=${REGION}

# Check if deployment was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Deployment successful!${NC}"
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
        --region=${REGION} \
        --project=${PROJECT_ID} \
        --format='get(status.url)')
    
    echo -e "${GREEN}Service deployed at: ${SERVICE_URL}${NC}"
    echo -e "${YELLOW}Health check: ${SERVICE_URL}/health${NC}"
    echo -e "${YELLOW}API docs: ${SERVICE_URL}/docs${NC}"
    
    # Test the health endpoint
    echo -e "\n${YELLOW}Testing health endpoint...${NC}"
    curl -s "${SERVICE_URL}/health" | jq . || echo -e "${RED}Health check failed${NC}"
    
else
    echo -e "${RED}Deployment failed!${NC}"
    exit 1
fi

echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "1. Update the secret values in Secret Manager with actual values"
echo -e "2. Test the API endpoints"
echo -e "3. Monitor logs: gcloud run logs tail ${SERVICE_NAME} --region=${REGION}"