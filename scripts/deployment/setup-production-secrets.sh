#!/bin/bash

# Setup production secrets for RoadTrip Backend
# This script creates the necessary secrets that are missing

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up Production Secrets ===${NC}"

PROJECT_ID="roadtrip-460720"

# Map existing secrets to new names
echo -e "${YELLOW}Creating aliases for existing secrets...${NC}"

# Database URL - use existing roadtrip-database-url
gcloud secrets versions add database-url --data-file=- --project=${PROJECT_ID} <<< $(gcloud secrets versions access latest --secret=roadtrip-database-url --project=${PROJECT_ID}) 2>/dev/null || \
gcloud secrets create database-url --data-file=- --project=${PROJECT_ID} --replication-policy="automatic" <<< $(gcloud secrets versions access latest --secret=roadtrip-database-url --project=${PROJECT_ID})

# Redis URL - use existing REDIS_URL
gcloud secrets versions add redis-url --data-file=- --project=${PROJECT_ID} <<< $(gcloud secrets versions access latest --secret=REDIS_URL --project=${PROJECT_ID}) 2>/dev/null || \
gcloud secrets create redis-url --data-file=- --project=${PROJECT_ID} --replication-policy="automatic" <<< $(gcloud secrets versions access latest --secret=REDIS_URL --project=${PROJECT_ID})

# JWT secrets - use existing JWT_SECRET_KEY
gcloud secrets versions add jwt-secret-key --data-file=- --project=${PROJECT_ID} <<< $(gcloud secrets versions access latest --secret=JWT_SECRET_KEY --project=${PROJECT_ID}) 2>/dev/null || \
gcloud secrets create jwt-secret-key --data-file=- --project=${PROJECT_ID} --replication-policy="automatic" <<< $(gcloud secrets versions access latest --secret=JWT_SECRET_KEY --project=${PROJECT_ID})

# Create JWT refresh secret key (same as JWT secret for now)
gcloud secrets versions add jwt-refresh-secret-key --data-file=- --project=${PROJECT_ID} <<< $(gcloud secrets versions access latest --secret=JWT_SECRET_KEY --project=${PROJECT_ID}) 2>/dev/null || \
gcloud secrets create jwt-refresh-secret-key --data-file=- --project=${PROJECT_ID} --replication-policy="automatic" <<< $(gcloud secrets versions access latest --secret=JWT_SECRET_KEY --project=${PROJECT_ID})

# Create missing secrets with placeholder values
echo -e "${YELLOW}Creating placeholder secrets for missing values...${NC}"

# Viator API Key
gcloud secrets describe viator-api-key --project=${PROJECT_ID} &>/dev/null || \
echo "PLACEHOLDER_VIATOR_KEY" | gcloud secrets create viator-api-key --data-file=- --project=${PROJECT_ID} --replication-policy="automatic"

# OpenTable API Key  
gcloud secrets describe opentable-api-key --project=${PROJECT_ID} &>/dev/null || \
echo "PLACEHOLDER_OPENTABLE_KEY" | gcloud secrets create opentable-api-key --data-file=- --project=${PROJECT_ID} --replication-policy="automatic"

# Twilio credentials
gcloud secrets describe twilio-account-sid --project=${PROJECT_ID} &>/dev/null || \
echo "PLACEHOLDER_TWILIO_SID" | gcloud secrets create twilio-account-sid --data-file=- --project=${PROJECT_ID} --replication-policy="automatic"

gcloud secrets describe twilio-auth-token --project=${PROJECT_ID} &>/dev/null || \
echo "PLACEHOLDER_TWILIO_TOKEN" | gcloud secrets create twilio-auth-token --data-file=- --project=${PROJECT_ID} --replication-policy="automatic"

gcloud secrets describe twilio-from-phone --project=${PROJECT_ID} &>/dev/null || \
echo "+1234567890" | gcloud secrets create twilio-from-phone --data-file=- --project=${PROJECT_ID} --replication-policy="automatic"

# SendGrid API Key
gcloud secrets describe sendgrid-api-key --project=${PROJECT_ID} &>/dev/null || \
echo "PLACEHOLDER_SENDGRID_KEY" | gcloud secrets create sendgrid-api-key --data-file=- --project=${PROJECT_ID} --replication-policy="automatic"

# Encryption Key
gcloud secrets describe encryption-key --project=${PROJECT_ID} &>/dev/null || \
echo "$(openssl rand -base64 32)" | gcloud secrets create encryption-key --data-file=- --project=${PROJECT_ID} --replication-policy="automatic"

# Grant access to service account
echo -e "${YELLOW}Granting Secret Manager access to service account...${NC}"
SERVICE_ACCOUNT="roadtrip-mvp-sa@${PROJECT_ID}.iam.gserviceaccount.com"

SECRETS=(
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

for secret in "${SECRETS[@]}"; do
    echo "Granting access to: $secret"
    gcloud secrets add-iam-policy-binding ${secret} \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor" \
        --project=${PROJECT_ID} \
        --quiet || true
done

echo -e "${GREEN}=== Secret Setup Complete ===${NC}"
echo -e "${YELLOW}Note: Some secrets are using placeholder values and should be updated with real credentials${NC}"