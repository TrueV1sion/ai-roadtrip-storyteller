#!/bin/bash
#
# Script to help set up external API keys for the Road Trip application
# Run this after deploy_dev_environment.sh
#

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Check if project ID is set
if [[ -z "${PROJECT_ID:-}" ]]; then
    error "PROJECT_ID not set. Please set: export PROJECT_ID=your-project-id"
    exit 1
fi

echo "========================================="
echo -e "${BLUE}API Key Setup for Road Trip Application${NC}"
echo "========================================="
echo ""
echo "This script will help you set up the required API keys."
echo "You'll need to obtain keys from the following services:"
echo ""

# Function to update a secret
update_secret() {
    local secret_name=$1
    local prompt=$2
    
    echo -e "${YELLOW}$prompt${NC}"
    read -s -p "Enter API key (or press Enter to skip): " api_key
    echo ""
    
    if [[ -n "$api_key" ]]; then
        echo -n "$api_key" | gcloud secrets versions add $secret_name --data-file=- 2>/dev/null
        log "Updated $secret_name"
    else
        warning "Skipped $secret_name"
    fi
}

# Google Maps API
echo "----------------------------------------"
echo -e "${BLUE}1. Google Maps API${NC}"
echo "   Required for: Location services, directions, place details"
echo "   Get it from: https://console.cloud.google.com/apis/credentials"
echo "   APIs to enable: Maps JavaScript API, Places API, Geocoding API, Directions API"
echo ""
update_secret "roadtrip-google-maps-api-key" "Google Maps API Key"

# OpenWeatherMap API
echo ""
echo "----------------------------------------"
echo -e "${BLUE}2. OpenWeatherMap API${NC}"
echo "   Required for: Weather information"
echo "   Get it from: https://openweathermap.org/api"
echo "   Plan needed: Free tier is sufficient for development"
echo ""
update_secret "openweather-api-key" "OpenWeatherMap API Key"

# Ticketmaster API
echo ""
echo "----------------------------------------"
echo -e "${BLUE}3. Ticketmaster API${NC}"
echo "   Required for: Event discovery and ticketing"
echo "   Get it from: https://developer.ticketmaster.com/"
echo "   Plan needed: Free tier available"
echo ""
update_secret "ticketmaster-api-key" "Ticketmaster API Key"

# Recreation.gov API
echo ""
echo "----------------------------------------"
echo -e "${BLUE}4. Recreation.gov API${NC}"
echo "   Required for: Campground and park information"
echo "   Get it from: https://ridb.recreation.gov/docs"
echo "   Plan needed: Free API"
echo ""
update_secret "recreation-gov-api-key" "Recreation.gov API Key"

# Optional APIs
echo ""
echo "========================================="
echo -e "${BLUE}Optional API Keys (for additional features)${NC}"
echo "========================================="
echo ""

# Spotify
echo "----------------------------------------"
echo -e "${BLUE}5. Spotify API (Optional)${NC}"
echo "   Required for: Music integration"
echo "   Get it from: https://developer.spotify.com/"
echo ""
read -p "Do you want to set up Spotify API? (y/N): " setup_spotify
if [[ "$setup_spotify" =~ ^[Yy]$ ]]; then
    update_secret "roadtrip-spotify-id" "Spotify Client ID"
    update_secret "roadtrip-spotify-secret" "Spotify Client Secret"
fi

# OpenTable
echo ""
echo "----------------------------------------"
echo -e "${BLUE}6. OpenTable API (Optional)${NC}"
echo "   Required for: Restaurant reservations"
echo "   Get it from: Contact OpenTable for partner access"
echo ""
read -p "Do you have OpenTable API access? (y/N): " setup_opentable
if [[ "$setup_opentable" =~ ^[Yy]$ ]]; then
    update_secret "roadtrip-opentable-key" "OpenTable API Key"
fi

# Verify setup
echo ""
echo "========================================="
echo -e "${GREEN}Verification${NC}"
echo "========================================="
echo ""

# Check which secrets are properly set
log "Checking configured secrets..."
echo ""

REQUIRED_SECRETS=(
    "roadtrip-google-maps-api-key"
    "openweather-api-key"
    "ticketmaster-api-key"
    "recreation-gov-api-key"
)

MISSING_SECRETS=()

for secret in "${REQUIRED_SECRETS[@]}"; do
    value=$(gcloud secrets versions access latest --secret=$secret 2>/dev/null || echo "")
    if [[ "$value" == "REPLACE_WITH_ACTUAL_KEY" ]] || [[ -z "$value" ]]; then
        MISSING_SECRETS+=($secret)
        echo -e "${RED}✗ $secret - Not configured${NC}"
    else
        echo -e "${GREEN}✓ $secret - Configured${NC}"
    fi
done

echo ""

if [[ ${#MISSING_SECRETS[@]} -eq 0 ]]; then
    log "All required API keys are configured!"
    echo ""
    echo "Next steps:"
    echo "1. Restart the Cloud Run service to pick up new secrets:"
    echo "   gcloud run services update roadtrip-api-dev --region=us-central1"
    echo ""
    echo "2. Test the API endpoints:"
    SERVICE_URL=$(gcloud run services describe roadtrip-api-dev --region=us-central1 --format='value(status.url)' 2>/dev/null || echo "")
    if [[ -n "$SERVICE_URL" ]]; then
        echo "   curl ${SERVICE_URL}/health"
        echo "   Visit: ${SERVICE_URL}/docs"
    fi
else
    warning "Some required API keys are missing:"
    for secret in "${MISSING_SECRETS[@]}"; do
        echo "  - $secret"
    done
    echo ""
    echo "To update a missing key later:"
    echo "  echo -n 'YOUR_API_KEY' | gcloud secrets versions add SECRET_NAME --data-file=-"
fi

echo ""
echo "========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "========================================="