#!/bin/bash

# RoadTrip Secret Validation Script
# This script validates that all required secrets are accessible
# Usage: ./validate-secrets.sh [PROJECT_ID]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PROJECT_ID="${1:-roadtrip-460720}"

echo -e "${BLUE}RoadTrip Secret Validation${NC}"
echo -e "${BLUE}==========================${NC}"
echo "Project ID: $PROJECT_ID"
echo ""

# Arrays to track status
MISSING_REQUIRED=()
MISSING_OPTIONAL=()
PLACEHOLDER_REQUIRED=()
PLACEHOLDER_OPTIONAL=()
VALID_SECRETS=()

# Function to check a secret
check_secret() {
    local secret_id="$1"
    local is_required="$2"
    local description="$3"
    
    echo -n "Checking $secret_id... "
    
    # Try to access the secret
    if secret_value=$(gcloud secrets versions access latest --secret="$secret_id" --project="$PROJECT_ID" 2>/dev/null); then
        # Check if it's still a placeholder
        if [[ "$secret_value" == "PLACEHOLDER_"* ]]; then
            echo -e "${YELLOW}PLACEHOLDER${NC} - $description"
            if [[ "$is_required" == "true" ]]; then
                PLACEHOLDER_REQUIRED+=("$secret_id: $description")
            else
                PLACEHOLDER_OPTIONAL+=("$secret_id: $description")
            fi
        else
            echo -e "${GREEN}OK${NC}"
            VALID_SECRETS+=("$secret_id")
        fi
    else
        echo -e "${RED}MISSING${NC} - $description"
        if [[ "$is_required" == "true" ]]; then
            MISSING_REQUIRED+=("$secret_id: $description")
        else
            MISSING_OPTIONAL+=("$secret_id: $description")
        fi
    fi
}

echo -e "${YELLOW}Checking Core Secrets...${NC}"
echo "========================"

# Core application secrets (all required)
check_secret "roadtrip-secret-key" "true" "Application secret key"
check_secret "roadtrip-jwt-secret" "true" "JWT signing key"
check_secret "roadtrip-csrf-secret" "true" "CSRF protection key"
check_secret "encryption-key" "true" "Data encryption key"
check_secret "roadtrip-database-url" "true" "PostgreSQL connection"
check_secret "roadtrip-redis-url" "true" "Redis connection"
check_secret "roadtrip-gcs-bucket" "true" "GCS bucket name"

echo ""
echo -e "${YELLOW}Checking Required API Keys...${NC}"
echo "============================="

# Required for core functionality
check_secret "roadtrip-google-maps-key" "true" "Google Maps API (navigation)"
check_secret "roadtrip-openweather-key" "true" "Weather data"
check_secret "roadtrip-ticketmaster-key" "true" "Event booking"
check_secret "roadtrip-ticketmaster-secret" "true" "Ticketmaster secret"
check_secret "roadtrip-recreation-key" "true" "Campground booking"
check_secret "roadtrip-recreation-secret" "true" "Recreation.gov secret"
check_secret "roadtrip-recreation-account" "true" "Recreation.gov account"

echo ""
echo -e "${YELLOW}Checking Optional API Keys...${NC}"
echo "============================="

# Restaurant booking
check_secret "roadtrip-opentable-key" "false" "Restaurant booking"
check_secret "roadtrip-opentable-partner" "false" "OpenTable partner ID"
check_secret "roadtrip-opentable-id" "false" "OpenTable client ID"
check_secret "roadtrip-opentable-secret" "false" "OpenTable client secret"
check_secret "roadtrip-resy-key" "false" "Resy restaurant booking"
check_secret "roadtrip-resy-id" "false" "Resy client ID"
check_secret "roadtrip-resy-secret" "false" "Resy client secret"

# Travel & activities
check_secret "roadtrip-viator-key" "false" "Tours and activities"
check_secret "roadtrip-viator-partner" "false" "Viator partner ID"

# Music
check_secret "roadtrip-spotify-id" "false" "Music integration"
check_secret "roadtrip-spotify-secret" "false" "Spotify secret"

# EV charging
check_secret "roadtrip-shell-key" "false" "Shell EV charging"
check_secret "roadtrip-chargepoint-id" "false" "ChargePoint ID"
check_secret "roadtrip-chargepoint-secret" "false" "ChargePoint secret"
check_secret "roadtrip-chargepoint-key" "false" "ChargePoint API"

# Flight tracking
check_secret "roadtrip-flightstats-key" "false" "Flight tracking"
check_secret "roadtrip-flightstats-id" "false" "FlightStats ID"
check_secret "roadtrip-flightaware-key" "false" "FlightAware API"
check_secret "roadtrip-aviationstack-key" "false" "AviationStack API"
check_secret "roadtrip-flightlabs-key" "false" "FlightLabs API"
check_secret "roadtrip-flight-tracking-key" "false" "Generic flight API"

# Airport services
check_secret "roadtrip-priority-pass-key" "false" "Airport lounges"
check_secret "roadtrip-airline-lounge-key" "false" "Airline lounges"

# Communication
check_secret "roadtrip-twilio-sid" "false" "SMS notifications"
check_secret "roadtrip-twilio-token" "false" "Twilio auth"
check_secret "roadtrip-twilio-phone" "false" "SMS from number"
check_secret "roadtrip-sendgrid-key" "false" "Email service"

# 2FA
check_secret "roadtrip-two-factor-secret" "false" "2FA authentication"

echo ""
echo -e "${BLUE}Validation Summary${NC}"
echo "=================="
echo ""

# Summary statistics
echo "Valid secrets: ${#VALID_SECRETS[@]}"
echo "Placeholder (required): ${#PLACEHOLDER_REQUIRED[@]}"
echo "Placeholder (optional): ${#PLACEHOLDER_OPTIONAL[@]}"
echo "Missing (required): ${#MISSING_REQUIRED[@]}"
echo "Missing (optional): ${#MISSING_OPTIONAL[@]}"

# Detailed issues
if [[ ${#MISSING_REQUIRED[@]} -gt 0 ]]; then
    echo ""
    echo -e "${RED}CRITICAL: Missing Required Secrets${NC}"
    echo "=================================="
    printf '%s\n' "${MISSING_REQUIRED[@]}"
fi

if [[ ${#PLACEHOLDER_REQUIRED[@]} -gt 0 ]]; then
    echo ""
    echo -e "${RED}CRITICAL: Required Secrets Still Using Placeholders${NC}"
    echo "=================================================="
    printf '%s\n' "${PLACEHOLDER_REQUIRED[@]}"
fi

if [[ ${#MISSING_OPTIONAL[@]} -gt 0 ]]; then
    echo ""
    echo -e "${YELLOW}WARNING: Missing Optional Secrets${NC}"
    echo "================================="
    printf '%s\n' "${MISSING_OPTIONAL[@]}"
fi

if [[ ${#PLACEHOLDER_OPTIONAL[@]} -gt 0 ]]; then
    echo ""
    echo -e "${YELLOW}INFO: Optional Secrets Using Placeholders${NC}"
    echo "========================================"
    printf '%s\n' "${PLACEHOLDER_OPTIONAL[@]}"
fi

# Exit status
if [[ ${#MISSING_REQUIRED[@]} -gt 0 ]] || [[ ${#PLACEHOLDER_REQUIRED[@]} -gt 0 ]]; then
    echo ""
    echo -e "${RED}Validation FAILED: Required secrets are missing or using placeholders${NC}"
    exit 1
else
    echo ""
    echo -e "${GREEN}Validation PASSED: All required secrets are configured${NC}"
    exit 0
fi