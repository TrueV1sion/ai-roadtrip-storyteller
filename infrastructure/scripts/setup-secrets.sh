#!/bin/bash

# RoadTrip API Secret Manager Setup Script
# This script creates all required secrets in Google Secret Manager
# Usage: ./setup-secrets.sh [PROJECT_ID] [ENVIRONMENT]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROJECT_ID="${1:-roadtrip-460720}"
ENVIRONMENT="${2:-production}"

echo -e "${BLUE}RoadTrip Secret Manager Setup${NC}"
echo -e "${BLUE}================================${NC}"
echo "Project ID: $PROJECT_ID"
echo "Environment: $ENVIRONMENT"
echo ""

# Function to create or update a secret
create_secret() {
    local secret_id="$1"
    local secret_value="$2"
    local description="$3"
    
    echo -n "Setting up secret: $secret_id... "
    
    # Check if secret exists
    if gcloud secrets describe "$secret_id" --project="$PROJECT_ID" &>/dev/null; then
        # Update existing secret
        echo -n "$secret_value" | gcloud secrets versions add "$secret_id" \
            --data-file=- \
            --project="$PROJECT_ID" 2>/dev/null
        echo -e "${GREEN}Updated${NC}"
    else
        # Create new secret
        echo -n "$secret_value" | gcloud secrets create "$secret_id" \
            --data-file=- \
            --replication-policy="automatic" \
            --project="$PROJECT_ID" 2>/dev/null
        
        # Add description
        gcloud secrets update "$secret_id" \
            --update-labels="environment=$ENVIRONMENT,component=backend" \
            --project="$PROJECT_ID" 2>/dev/null
        
        echo -e "${GREEN}Created${NC}"
    fi
}

# Function to create a placeholder secret
create_placeholder() {
    local secret_id="$1"
    local description="$2"
    create_secret "$secret_id" "PLACEHOLDER_${secret_id^^}_VALUE" "$description"
}

echo -e "${YELLOW}Creating Core Secrets...${NC}"
echo "========================="

# Core application secrets
create_secret "roadtrip-secret-key" "$(openssl rand -hex 32)" "Django/FastAPI secret key"
create_secret "roadtrip-jwt-secret" "$(openssl rand -hex 64)" "JWT signing key"
create_secret "roadtrip-csrf-secret" "$(openssl rand -hex 32)" "CSRF protection key"
create_secret "encryption-key" "$(openssl rand -hex 32)" "Data encryption key"

# Database URL (placeholder - needs to be updated with actual DB connection)
create_placeholder "roadtrip-database-url" "PostgreSQL connection string"

# Redis URL (placeholder - needs to be updated with actual Redis connection)
create_placeholder "roadtrip-redis-url" "Redis connection string"

# GCS Bucket
create_placeholder "roadtrip-gcs-bucket" "Google Cloud Storage bucket name"

echo ""
echo -e "${YELLOW}Creating Required API Keys...${NC}"
echo "=============================="

# Google Services (Required)
create_placeholder "roadtrip-google-maps-key" "Google Maps API key - Required for navigation"

# Weather Service (Required)
create_placeholder "roadtrip-openweather-key" "OpenWeatherMap API key - Required for weather data"

# Booking Partners (Required for booking features)
create_placeholder "roadtrip-ticketmaster-key" "Ticketmaster API key - Required for event booking"
create_placeholder "roadtrip-ticketmaster-secret" "Ticketmaster API secret"
create_placeholder "roadtrip-recreation-key" "Recreation.gov API key - Required for campground booking"
create_placeholder "roadtrip-recreation-secret" "Recreation.gov API secret"
create_placeholder "roadtrip-recreation-account" "Recreation.gov account ID"

echo ""
echo -e "${YELLOW}Creating Optional API Keys...${NC}"
echo "=============================="

# Restaurant Booking APIs
create_placeholder "roadtrip-opentable-key" "OpenTable API key - Optional"
create_placeholder "roadtrip-opentable-partner" "OpenTable partner ID - Optional"
create_placeholder "roadtrip-opentable-id" "OpenTable client ID - Optional"
create_placeholder "roadtrip-opentable-secret" "OpenTable client secret - Optional"
create_placeholder "roadtrip-resy-key" "Resy API key - Optional"
create_placeholder "roadtrip-resy-id" "Resy client ID - Optional"
create_placeholder "roadtrip-resy-secret" "Resy client secret - Optional"

# Travel & Activities
create_placeholder "roadtrip-viator-key" "Viator API key - Optional for tours"
create_placeholder "roadtrip-viator-partner" "Viator partner ID - Optional"

# Music Integration
create_placeholder "roadtrip-spotify-id" "Spotify client ID - Optional for music"
create_placeholder "roadtrip-spotify-secret" "Spotify client secret - Optional"

# EV Charging
create_placeholder "roadtrip-shell-key" "Shell Recharge API key - Optional"
create_placeholder "roadtrip-chargepoint-id" "ChargePoint client ID - Optional"
create_placeholder "roadtrip-chargepoint-secret" "ChargePoint client secret - Optional"
create_placeholder "roadtrip-chargepoint-key" "ChargePoint API key - Optional"

# Flight Tracking
create_placeholder "roadtrip-flightstats-key" "FlightStats API key - Optional"
create_placeholder "roadtrip-flightstats-id" "FlightStats app ID - Optional"
create_placeholder "roadtrip-flightaware-key" "FlightAware API key - Optional"
create_placeholder "roadtrip-aviationstack-key" "AviationStack API key - Optional"
create_placeholder "roadtrip-flightlabs-key" "FlightLabs API key - Optional"
create_placeholder "roadtrip-flight-tracking-key" "Generic flight tracking API key - Optional"

# Airport Services
create_placeholder "roadtrip-priority-pass-key" "Priority Pass API key - Optional"
create_placeholder "roadtrip-airline-lounge-key" "Airline lounge API key - Optional"

# Communication Services (Optional)
create_placeholder "roadtrip-twilio-sid" "Twilio account SID - Optional for SMS"
create_placeholder "roadtrip-twilio-token" "Twilio auth token - Optional"
create_placeholder "roadtrip-twilio-phone" "Twilio phone number - Optional"
create_placeholder "roadtrip-sendgrid-key" "SendGrid API key - Optional for email"

# Two-Factor Authentication
create_placeholder "roadtrip-two-factor-secret" "2FA secret key - Optional"

echo ""
echo -e "${YELLOW}Setting Secret Permissions...${NC}"
echo "=============================="

# Grant the service account access to all secrets
SERVICE_ACCOUNT="roadtrip-mvp-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Granting secret accessor role to service account: $SERVICE_ACCOUNT"

# Get all secrets and grant access
for secret in $(gcloud secrets list --project="$PROJECT_ID" --filter="name:roadtrip-" --format="value(name)"); do
    echo -n "  Granting access to $secret... "
    gcloud secrets add-iam-policy-binding "$secret" \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor" \
        --project="$PROJECT_ID" &>/dev/null
    echo -e "${GREEN}Done${NC}"
done

echo ""
echo -e "${GREEN}Secret setup complete!${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT NEXT STEPS:${NC}"
echo "====================="
echo ""
echo "1. Update the following placeholder secrets with actual values:"
echo "   - roadtrip-database-url: Your PostgreSQL connection string"
echo "   - roadtrip-redis-url: Your Redis connection string"
echo "   - roadtrip-gcs-bucket: Your GCS bucket name"
echo ""
echo "2. Replace API key placeholders with actual API keys:"
echo "   ${RED}REQUIRED for core functionality:${NC}"
echo "   - roadtrip-google-maps-key: Get from Google Cloud Console"
echo "   - roadtrip-openweather-key: Get from openweathermap.org (free tier available)"
echo "   - roadtrip-ticketmaster-key: Get from developer.ticketmaster.com"
echo "   - roadtrip-recreation-key: Get from recreation.gov/api"
echo ""
echo "   ${YELLOW}OPTIONAL for additional features:${NC}"
echo "   - Spotify: Create app at developer.spotify.com"
echo "   - OpenTable: Contact OpenTable for partner access"
echo "   - Viator: Apply at viatorapi.viator.com"
echo "   - Others: See API_CREDENTIALS.md for details"
echo ""
echo "3. Update secrets using:"
echo "   echo -n 'your-actual-value' | gcloud secrets versions add SECRET_ID --data-file=-"
echo ""
echo "4. Verify secrets are accessible:"
echo "   ./validate-secrets.sh $PROJECT_ID"