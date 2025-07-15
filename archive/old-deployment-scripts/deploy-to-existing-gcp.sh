#!/bin/bash
# Deployment script for EXISTING Google Cloud Project
# Project: roadtrip-460720

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Use existing project configuration
PROJECT_ID="roadtrip-460720"
REGION="us-central1"
ENVIRONMENT="production"
SERVICE_NAME="roadtrip-backend"

echo -e "${GREEN}Using existing project: $PROJECT_ID${NC}"

# Set the project
gcloud config set project $PROJECT_ID

# Step 1: Add secrets that don't exist yet
echo -e "${YELLOW}Creating secrets in Secret Manager...${NC}"

# Check and create secrets only if they don't exist
create_secret_if_not_exists() {
    SECRET_NAME=$1
    SECRET_VALUE=$2
    
    if ! gcloud secrets describe $SECRET_NAME &> /dev/null; then
        echo -e "${YELLOW}Creating secret: $SECRET_NAME${NC}"
        echo -n "$SECRET_VALUE" | gcloud secrets create $SECRET_NAME --data-file=-
    else
        echo -e "${GREEN}Secret already exists: $SECRET_NAME${NC}"
    fi
}

# Read from .env file
source .env

# Create secrets from existing .env values
create_secret_if_not_exists "roadtrip-secret-key" "$SECRET_KEY"
create_secret_if_not_exists "roadtrip-jwt-secret" "$JWT_SECRET_KEY"
create_secret_if_not_exists "roadtrip-db-password" "prodDb#2024Secure"  # Use a secure password for production
create_secret_if_not_exists "google-maps-api-key" "$GOOGLE_MAPS_API_KEY"
create_secret_if_not_exists "ticketmaster-api-key" "$TICKETMASTER_API_KEY"
create_secret_if_not_exists "openweather-api-key" "$OPENWEATHERMAP_API_KEY"
create_secret_if_not_exists "recreation-gov-api-key" "$RECREATION_GOV_API_KEY"

# Spotify credentials if available
if [[ ! -z "$SPOTIFY_CLIENT_ID" ]]; then
    create_secret_if_not_exists "spotify-client-id" "$SPOTIFY_CLIENT_ID"
    create_secret_if_not_exists "spotify-client-secret" "$SPOTIFY_CLIENT_SECRET"
else
    echo -e "${YELLOW}Spotify credentials not found in .env, skipping...${NC}"
fi

# Step 2: Enable required APIs (if not already enabled)
echo -e "${YELLOW}Enabling required APIs...${NC}"
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
    logging.googleapis.com \
    monitoring.googleapis.com \
    vpcaccess.googleapis.com \
    --quiet

echo -e "${GREEN}APIs enabled${NC}"

# Step 3: Create Terraform state bucket if needed
STATE_BUCKET="${PROJECT_ID}-terraform-state"
if ! gsutil ls gs://${STATE_BUCKET} &> /dev/null; then
    echo -e "${YELLOW}Creating Terraform state bucket...${NC}"
    gsutil mb -p ${PROJECT_ID} -l ${REGION} gs://${STATE_BUCKET}
    gsutil versioning set on gs://${STATE_BUCKET}
else
    echo -e "${GREEN}Terraform state bucket already exists${NC}"
fi

# Step 4: Deploy infrastructure with Terraform
echo -e "${YELLOW}Deploying infrastructure with Terraform...${NC}"
cd infrastructure/terraform

# Create terraform.tfvars
cat > terraform.tfvars <<EOF
project_id   = "${PROJECT_ID}"
region       = "${REGION}"
environment  = "${ENVIRONMENT}"
EOF

# Initialize and apply Terraform
terraform init -backend-config="bucket=${STATE_BUCKET}"

echo -e "${YELLOW}Planning Terraform changes...${NC}"
terraform plan -out=tfplan

echo -e "${YELLOW}Applying infrastructure changes...${NC}"
terraform apply tfplan -auto-approve

# Get outputs
DB_INSTANCE=$(terraform output -raw database_connection_name)
REDIS_HOST=$(terraform output -raw redis_host)
ASSETS_BUCKET=$(terraform output -raw assets_bucket)

# Step 5: Create database URL secret with correct format
echo -e "${YELLOW}Creating database URL secret...${NC}"
DB_PASSWORD=$(gcloud secrets versions access latest --secret="roadtrip-db-password")
DB_URL="postgresql://roadtrip:${DB_PASSWORD}@/${DB_INSTANCE}?host=/cloudsql/${DB_INSTANCE}&sslmode=disable"
echo -n "$DB_URL" | gcloud secrets versions add roadtrip-db-url --data-file=-

# Step 6: Build and deploy the application
echo -e "${YELLOW}Building and deploying application...${NC}"
cd ../..

# Use the fixed Cloud Build configuration
gcloud builds submit \
    --config=cloudbuild-fixed.yaml \
    --substitutions=_SERVICE_NAME=${SERVICE_NAME},_REGION=${REGION},_ENVIRONMENT=${ENVIRONMENT} \
    --timeout=30m

# Step 7: Get service URL and test
echo -e "${YELLOW}Verifying deployment...${NC}"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region=${REGION} \
    --format='value(status.url)')

echo -e "${GREEN}Service deployed at: ${SERVICE_URL}${NC}"

# Test the health endpoint
echo -e "${YELLOW}Testing health endpoint...${NC}"
if curl -f "${SERVICE_URL}/health/" &> /dev/null; then
    echo -e "${GREEN}Health check passed!${NC}"
else
    echo -e "${RED}Health check failed!${NC}"
    echo "Check logs with:"
    echo "gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\" --limit=50"
fi

# Step 8: Update mobile configuration
echo -e "${YELLOW}Creating mobile production config...${NC}"
cat > mobile/src/config/production.ts <<EOF
export const PRODUCTION_CONFIG = {
  API_URL: '${SERVICE_URL}',
  ENVIRONMENT: 'production',
  GOOGLE_MAPS_API_KEY: '${GOOGLE_MAPS_API_KEY}',
};
EOF

# Step 9: Create deployment summary
echo -e "${GREEN}Deployment completed!${NC}"
echo ""
echo "=== Deployment Summary ==="
echo "Project ID: ${PROJECT_ID}"
echo "Service URL: ${SERVICE_URL}"
echo "Database: ${DB_INSTANCE}"
echo "Redis Host: ${REDIS_HOST}"
echo "Assets Bucket: ${ASSETS_BUCKET}"
echo ""
echo "=== Next Steps ==="
echo "1. Test all endpoints: python backend/tests/integration/test_deployment.py --api-url=${SERVICE_URL}"
echo "2. Configure custom domain (optional)"
echo "3. Set up monitoring alerts"
echo "4. Deploy mobile apps with production URL"
echo ""
echo "=== View Logs ==="
echo "gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}\" --limit=50"
echo ""
echo "=== Update Service ==="
echo "gcloud run deploy ${SERVICE_NAME} --region=${REGION} --image=gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

# Save deployment info
cat > deployment-info.json <<EOF
{
  "project_id": "${PROJECT_ID}",
  "region": "${REGION}",
  "service_url": "${SERVICE_URL}",
  "database": "${DB_INSTANCE}",
  "redis_host": "${REDIS_HOST}",
  "assets_bucket": "${ASSETS_BUCKET}",
  "deployed_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

echo -e "${GREEN}Deployment info saved to deployment-info.json${NC}"