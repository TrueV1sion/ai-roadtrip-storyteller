#!/bin/bash
# Google Secret Manager Integration Script
# Generated: 2025-07-07
# Purpose: Add rotated credentials to Secret Manager

PROJECT_ID="roadtrip-mvp-prod"

echo "Adding secrets to Google Secret Manager..."

# Function to create or update a secret
create_or_update_secret() {
    SECRET_NAME=$1
    SECRET_VALUE=$2
    
    # Check if secret exists
    if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
        echo "Updating existing secret: $SECRET_NAME"
        echo -n "$SECRET_VALUE" | gcloud secrets versions add $SECRET_NAME --data-file=- --project=$PROJECT_ID
    else
        echo "Creating new secret: $SECRET_NAME"
        echo -n "$SECRET_VALUE" | gcloud secrets create $SECRET_NAME --data-file=- --project=$PROJECT_ID --replication-policy="automatic"
    fi
}

# CRITICAL: Update these with actual values from provider consoles
create_or_update_secret "twilio-account-sid" "YOUR_NEW_TWILIO_ACCOUNT_SID"
create_or_update_secret "twilio-auth-token" "YOUR_NEW_TWILIO_AUTH_TOKEN"
create_or_update_secret "twilio-from-number" "YOUR_NEW_TWILIO_FROM_NUMBER"
create_or_update_secret "google-maps-api-key" "YOUR_NEW_GOOGLE_MAPS_API_KEY"

# Auto-generated secure secrets (replace with output from credential_rotator.py)
create_or_update_secret "app-secret-key" "GENERATE_WITH_CREDENTIAL_ROTATOR"
create_or_update_secret "jwt-secret-key" "GENERATE_WITH_CREDENTIAL_ROTATOR"
create_or_update_secret "database-encryption-key" "GENERATE_WITH_CREDENTIAL_ROTATOR"
create_or_update_secret "csrf-secret" "GENERATE_WITH_CREDENTIAL_ROTATOR"
create_or_update_secret "session-secret" "GENERATE_WITH_CREDENTIAL_ROTATOR"
create_or_update_secret "api-signing-key" "GENERATE_WITH_CREDENTIAL_ROTATOR"

# Additional secrets for production
create_or_update_secret "openweathermap-api-key" "YOUR_OPENWEATHERMAP_API_KEY"
create_or_update_secret "ticketmaster-api-key" "YOUR_TICKETMASTER_API_KEY"
create_or_update_secret "recreation-gov-api-key" "YOUR_RECREATION_GOV_API_KEY"

echo "Secret rotation complete. Remember to:"
echo "1. Update Twilio and Google Maps credentials with actual values"
echo "2. Grant Cloud Run service account access to these secrets"
echo "3. Update deployment scripts to reference new secret names"
echo "4. Delete all .env files from the repository"