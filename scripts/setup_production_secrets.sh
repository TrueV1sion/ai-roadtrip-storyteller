#!/bin/bash
#
# Setup Production Secrets in Google Secret Manager
# This script creates and populates secrets needed for production deployment
#
# Usage: ./setup_production_secrets.sh <PROJECT_ID>
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if project ID is provided
if [ $# -eq 0 ]; then
    echo -e "${RED}Error: Project ID required${NC}"
    echo "Usage: $0 <PROJECT_ID>"
    exit 1
fi

PROJECT_ID=$1
echo -e "${GREEN}Setting up secrets for project: ${PROJECT_ID}${NC}"

# Set the project
gcloud config set project ${PROJECT_ID}

# Enable Secret Manager API if not already enabled
echo -e "${YELLOW}Enabling Secret Manager API...${NC}"
gcloud services enable secretmanager.googleapis.com

# Function to create or update a secret
create_or_update_secret() {
    local SECRET_NAME=$1
    local SECRET_VALUE=$2
    local DESCRIPTION=$3
    
    # Check if secret exists
    if gcloud secrets describe ${SECRET_NAME} --project=${PROJECT_ID} >/dev/null 2>&1; then
        echo -e "${YELLOW}Secret ${SECRET_NAME} already exists. Updating...${NC}"
        echo -n "${SECRET_VALUE}" | gcloud secrets versions add ${SECRET_NAME} --data-file=-
    else
        echo -e "${GREEN}Creating secret ${SECRET_NAME}...${NC}"
        echo -n "${SECRET_VALUE}" | gcloud secrets create ${SECRET_NAME} \
            --data-file=- \
            --replication-policy="automatic" \
            --labels="app=roadtrip,env=production" \
            ${DESCRIPTION:+--description="${DESCRIPTION}"}
    fi
}

# Generate secure random keys
generate_secure_key() {
    openssl rand -base64 32
}

echo -e "${YELLOW}Generating secure keys...${NC}"

# Core Security Keys
SECRET_KEY=$(generate_secure_key)
JWT_SECRET_KEY=$(generate_secure_key)

# Database credentials (you'll need to set these)
read -p "Enter database username: " DB_USER
read -sp "Enter database password: " DB_PASSWORD
echo
read -p "Enter database name [roadtrip_prod]: " DB_NAME
DB_NAME=${DB_NAME:-roadtrip_prod}

# Redis password
REDIS_PASSWORD=$(generate_secure_key)

# Create secrets
echo -e "${GREEN}Creating core security secrets...${NC}"
create_or_update_secret "app-secret-key" "${SECRET_KEY}" "Django/Flask secret key"
create_or_update_secret "jwt-secret-key" "${JWT_SECRET_KEY}" "JWT signing key"

echo -e "${GREEN}Creating database secrets...${NC}"
create_or_update_secret "db-user" "${DB_USER}" "Database username"
create_or_update_secret "db-password" "${DB_PASSWORD}" "Database password"
create_or_update_secret "db-name" "${DB_NAME}" "Database name"

echo -e "${GREEN}Creating Redis secret...${NC}"
create_or_update_secret "redis-password" "${REDIS_PASSWORD}" "Redis password"

# API Keys (you'll need to provide these)
echo -e "${YELLOW}Setting up API keys...${NC}"
echo "Please have your API keys ready. Press Enter to skip any you don't have yet."

# Google APIs
read -p "Google Maps API Key: " GOOGLE_MAPS_API_KEY
if [ ! -z "${GOOGLE_MAPS_API_KEY}" ]; then
    create_or_update_secret "google-maps-api-key" "${GOOGLE_MAPS_API_KEY}" "Google Maps API key"
fi

# Third-party APIs
read -p "OpenWeatherMap API Key: " OPENWEATHERMAP_API_KEY
if [ ! -z "${OPENWEATHERMAP_API_KEY}" ]; then
    create_or_update_secret "openweathermap-api-key" "${OPENWEATHERMAP_API_KEY}" "OpenWeatherMap API key"
fi

read -p "Ticketmaster API Key: " TICKETMASTER_API_KEY
if [ ! -z "${TICKETMASTER_API_KEY}" ]; then
    create_or_update_secret "ticketmaster-api-key" "${TICKETMASTER_API_KEY}" "Ticketmaster API key"
fi

read -sp "Ticketmaster API Secret: " TICKETMASTER_API_SECRET
echo
if [ ! -z "${TICKETMASTER_API_SECRET}" ]; then
    create_or_update_secret "ticketmaster-api-secret" "${TICKETMASTER_API_SECRET}" "Ticketmaster API secret"
fi

read -p "Recreation.gov API Key: " RECREATION_GOV_API_KEY
if [ ! -z "${RECREATION_GOV_API_KEY}" ]; then
    create_or_update_secret "recreation-gov-api-key" "${RECREATION_GOV_API_KEY}" "Recreation.gov API key"
fi

# Partner APIs (optional)
echo -e "${YELLOW}Partner integration keys (optional):${NC}"

read -p "OpenTable Client ID: " OPENTABLE_CLIENT_ID
if [ ! -z "${OPENTABLE_CLIENT_ID}" ]; then
    create_or_update_secret "opentable-client-id" "${OPENTABLE_CLIENT_ID}" "OpenTable client ID"
fi

read -sp "OpenTable Client Secret: " OPENTABLE_CLIENT_SECRET
echo
if [ ! -z "${OPENTABLE_CLIENT_SECRET}" ]; then
    create_or_update_secret "opentable-client-secret" "${OPENTABLE_CLIENT_SECRET}" "OpenTable client secret"
fi

# Monitoring
echo -e "${YELLOW}Monitoring configuration:${NC}"

read -p "Sentry DSN: " SENTRY_DSN
if [ ! -z "${SENTRY_DSN}" ]; then
    create_or_update_secret "sentry-dsn" "${SENTRY_DSN}" "Sentry error tracking DSN"
fi

read -p "SendGrid API Key: " SENDGRID_API_KEY
if [ ! -z "${SENDGRID_API_KEY}" ]; then
    create_or_update_secret "sendgrid-api-key" "${SENDGRID_API_KEY}" "SendGrid email API key"
fi

# Create a service account for Cloud Run to access secrets
echo -e "${GREEN}Creating service account for Cloud Run...${NC}"
SERVICE_ACCOUNT_NAME="roadtrip-cloudrun-sa"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Create service account if it doesn't exist
if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT_EMAIL} --project=${PROJECT_ID} >/dev/null 2>&1; then
    gcloud iam service-accounts create ${SERVICE_ACCOUNT_NAME} \
        --display-name="Road Trip Cloud Run Service Account" \
        --description="Service account for Road Trip app running on Cloud Run"
fi

# Grant necessary permissions
echo -e "${GREEN}Granting permissions to service account...${NC}"

# Secret Manager access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

# Cloud SQL access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/cloudsql.client"

# Storage access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/storage.objectAdmin"

# Vertex AI access
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="roles/aiplatform.user"

# Create environment variable mapping file
echo -e "${GREEN}Creating environment variable mapping...${NC}"
cat > secret_mappings.yaml << EOF
# Secret Manager mappings for Cloud Run
# This file maps environment variables to Secret Manager secrets

env_variables:
  - name: SECRET_KEY
    value_from:
      secret_key_ref:
        name: app-secret-key
        version: latest
  
  - name: JWT_SECRET_KEY
    value_from:
      secret_key_ref:
        name: jwt-secret-key
        version: latest
  
  - name: DB_USER
    value_from:
      secret_key_ref:
        name: db-user
        version: latest
  
  - name: DB_PASSWORD
    value_from:
      secret_key_ref:
        name: db-password
        version: latest
  
  - name: DB_NAME
    value_from:
      secret_key_ref:
        name: db-name
        version: latest
  
  - name: REDIS_PASSWORD
    value_from:
      secret_key_ref:
        name: redis-password
        version: latest
  
  - name: GOOGLE_MAPS_API_KEY
    value_from:
      secret_key_ref:
        name: google-maps-api-key
        version: latest
  
  - name: OPENWEATHERMAP_API_KEY
    value_from:
      secret_key_ref:
        name: openweathermap-api-key
        version: latest
  
  - name: SENTRY_DSN
    value_from:
      secret_key_ref:
        name: sentry-dsn
        version: latest
EOF

echo -e "${GREEN}Secret setup complete!${NC}"
echo
echo "Next steps:"
echo "1. Review the created secrets: gcloud secrets list"
echo "2. Update any missing API keys later using:"
echo "   echo -n 'YOUR_API_KEY' | gcloud secrets versions add SECRET_NAME --data-file=-"
echo "3. Use the service account when deploying to Cloud Run:"
echo "   gcloud run deploy --service-account=${SERVICE_ACCOUNT_EMAIL}"
echo
echo -e "${YELLOW}Important: Keep the secret_mappings.yaml file for deployment configuration${NC}"