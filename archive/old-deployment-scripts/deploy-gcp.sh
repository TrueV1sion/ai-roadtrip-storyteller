#!/bin/bash
# Google Cloud Deployment Script for AI Road Trip Storyteller

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-""}
REGION=${GCP_REGION:-"us-central1"}
ENVIRONMENT=${ENVIRONMENT:-"production"}
SERVICE_NAME="roadtrip-backend"

# Validate requirements
echo -e "${YELLOW}Validating deployment requirements...${NC}"

if [[ -z "$PROJECT_ID" ]]; then
    echo -e "${RED}ERROR: GCP_PROJECT_ID environment variable is not set${NC}"
    echo "Please run: export GCP_PROJECT_ID=your-project-id"
    exit 1
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}ERROR: gcloud CLI is not installed${NC}"
    echo "Please install: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if terraform is installed
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}ERROR: Terraform is not installed${NC}"
    echo "Please install: https://learn.hashicorp.com/tutorials/terraform/install-cli"
    exit 1
fi

# Set the project
echo -e "${GREEN}Setting GCP project to: $PROJECT_ID${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}Enabling required Google Cloud APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    sql-component.googleapis.com \
    sqladmin.googleapis.com \
    compute.googleapis.com \
    servicenetworking.googleapis.com \
    containerregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    redis.googleapis.com \
    storage-api.googleapis.com \
    storage-component.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    texttospeech.googleapis.com \
    aiplatform.googleapis.com \
    maps-backend.googleapis.com

echo -e "${GREEN}APIs enabled successfully${NC}"

# Create Terraform state bucket if it doesn't exist
STATE_BUCKET="${PROJECT_ID}-terraform-state"
if ! gsutil ls -b gs://${STATE_BUCKET} &> /dev/null; then
    echo -e "${YELLOW}Creating Terraform state bucket...${NC}"
    gsutil mb -p ${PROJECT_ID} -l ${REGION} gs://${STATE_BUCKET}
    gsutil versioning set on gs://${STATE_BUCKET}
fi

# Initialize Terraform
echo -e "${YELLOW}Initializing Terraform...${NC}"
cd infrastructure/terraform
terraform init -backend-config="bucket=${STATE_BUCKET}"

# Create terraform.tfvars
echo -e "${YELLOW}Creating Terraform variables file...${NC}"
cat > terraform.tfvars <<EOF
project_id   = "${PROJECT_ID}"
region       = "${REGION}"
environment  = "${ENVIRONMENT}"
EOF

# Plan Terraform changes
echo -e "${YELLOW}Planning infrastructure changes...${NC}"
terraform plan -out=tfplan

# Ask for confirmation
echo -e "${YELLOW}Do you want to apply these changes? (yes/no)${NC}"
read -r response
if [[ "$response" != "yes" ]]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 0
fi

# Apply Terraform changes
echo -e "${YELLOW}Creating infrastructure...${NC}"
terraform apply tfplan

# Get Terraform outputs
CLOUD_RUN_URL=$(terraform output -raw cloud_run_url 2>/dev/null || echo "")
DB_CONNECTION=$(terraform output -raw database_connection_name)
REDIS_HOST=$(terraform output -raw redis_host)
ASSETS_BUCKET=$(terraform output -raw assets_bucket)
SERVICE_ACCOUNT=$(terraform output -raw service_account_email)

# Create secrets
echo -e "${YELLOW}Creating application secrets...${NC}"

# Generate secure keys if not exists
if ! gcloud secrets describe roadtrip-secret-key &> /dev/null; then
    SECRET_KEY=$(openssl rand -base64 32)
    echo -n "$SECRET_KEY" | gcloud secrets create roadtrip-secret-key --data-file=-
fi

if ! gcloud secrets describe roadtrip-jwt-secret &> /dev/null; then
    JWT_SECRET=$(openssl rand -base64 32)
    echo -n "$JWT_SECRET" | gcloud secrets create roadtrip-jwt-secret --data-file=-
fi

# Add API keys (you need to update these with your actual keys)
echo -e "${YELLOW}Please add your API keys to Secret Manager:${NC}"
echo "  - google-maps-api-key"
echo "  - ticketmaster-api-key"
echo "  - openweather-api-key"
echo "  - spotify-client-id"
echo "  - spotify-client-secret"
echo ""
echo "Example command:"
echo "echo -n 'your-api-key' | gcloud secrets create google-maps-api-key --data-file=-"
echo ""

# Build and deploy the application
echo -e "${YELLOW}Building and deploying the application...${NC}"
cd ../../

# Create Cloud Build trigger if it doesn't exist
TRIGGER_NAME="${SERVICE_NAME}-deploy"
if ! gcloud builds triggers describe ${TRIGGER_NAME} &> /dev/null; then
    echo -e "${YELLOW}Creating Cloud Build trigger...${NC}"
    gcloud builds triggers create github \
        --repo-name=roadtrip \
        --repo-owner=your-github-username \
        --branch-pattern="^main$" \
        --build-config=cloudbuild.yaml \
        --name=${TRIGGER_NAME}
fi

# Submit build manually for first deployment
echo -e "${YELLOW}Submitting build to Cloud Build...${NC}"
gcloud builds submit \
    --config=cloudbuild.yaml \
    --substitutions=_SERVICE_NAME=${SERVICE_NAME},_REGION=${REGION},_ENVIRONMENT=${ENVIRONMENT}

# Wait for deployment to complete
echo -e "${YELLOW}Waiting for deployment to complete...${NC}"
gcloud run services wait ${SERVICE_NAME} --region=${REGION}

# Get the service URL
if [[ -z "$CLOUD_RUN_URL" ]]; then
    CLOUD_RUN_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${REGION} --format='value(status.url)')
fi

# Run deployment tests
echo -e "${YELLOW}Running deployment tests...${NC}"
cd backend
python -m pytest tests/integration/test_deployment.py -v --api-url=${CLOUD_RUN_URL}

# Update mobile app configuration
echo -e "${YELLOW}Updating mobile app configuration...${NC}"
cd ../mobile
cat > src/config/production.ts <<EOF
export const PRODUCTION_CONFIG = {
  API_URL: '${CLOUD_RUN_URL}',
  ENVIRONMENT: 'production',
};
EOF

# Create deployment summary
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo ""
echo "=== Deployment Summary ==="
echo "Cloud Run URL: ${CLOUD_RUN_URL}"
echo "Database: ${DB_CONNECTION}"
echo "Redis Host: ${REDIS_HOST}"
echo "Assets Bucket: ${ASSETS_BUCKET}"
echo "Service Account: ${SERVICE_ACCOUNT}"
echo ""
echo "=== Next Steps ==="
echo "1. Add your API keys to Secret Manager"
echo "2. Update DNS records to point to Cloud Run service"
echo "3. Configure custom domain (optional)"
echo "4. Set up monitoring alerts"
echo "5. Deploy mobile apps to App Store and Google Play"
echo ""
echo "=== Useful Commands ==="
echo "View logs: gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\" --limit 50"
echo "Stream logs: gcloud alpha run services logs read ${SERVICE_NAME} --region=${REGION} --tail"
echo "Update service: gcloud run deploy ${SERVICE_NAME} --region=${REGION} --image=gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"
echo ""

# Save deployment info
cat > deployment-info.json <<EOF
{
  "project_id": "${PROJECT_ID}",
  "region": "${REGION}",
  "environment": "${ENVIRONMENT}",
  "service_name": "${SERVICE_NAME}",
  "cloud_run_url": "${CLOUD_RUN_URL}",
  "database_connection": "${DB_CONNECTION}",
  "redis_host": "${REDIS_HOST}",
  "assets_bucket": "${ASSETS_BUCKET}",
  "service_account": "${SERVICE_ACCOUNT}",
  "deployed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

echo -e "${GREEN}Deployment info saved to deployment-info.json${NC}"