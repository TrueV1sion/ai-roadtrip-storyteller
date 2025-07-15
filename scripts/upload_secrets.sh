#!/bin/bash
# Upload all secrets to Google Secret Manager
# Must have gcloud CLI configured first

set -e

PROJECT_ID="roadtrip-460720"

echo "=========================================="
echo "UPLOADING SECRETS TO SECRET MANAGER"
echo "Project: $PROJECT_ID"
echo "=========================================="

# Load environment variables
source .env

# Enable Secret Manager API
echo -e "\n1. Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID

# Function to create or update secret
create_or_update_secret() {
    SECRET_NAME=$1
    SECRET_VALUE=$2
    
    # Check if secret exists
    if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
        echo "Updating secret: $SECRET_NAME"
        echo -n "$SECRET_VALUE" | gcloud secrets versions add $SECRET_NAME \
            --data-file=- \
            --project=$PROJECT_ID
    else
        echo "Creating secret: $SECRET_NAME"
        echo -n "$SECRET_VALUE" | gcloud secrets create $SECRET_NAME \
            --data-file=- \
            --replication-policy="automatic" \
            --project=$PROJECT_ID
    fi
}

# Upload API keys
echo -e "\n2. Uploading API keys..."
create_or_update_secret "google-maps-api-key" "$GOOGLE_MAPS_API_KEY"
create_or_update_secret "ticketmaster-api-key" "$TICKETMASTER_API_KEY"
create_or_update_secret "ticketmaster-api-secret" "$TICKETMASTER_API_SECRET"
create_or_update_secret "openweathermap-api-key" "$OPENWEATHERMAP_API_KEY"
create_or_update_secret "recreation-gov-api-key" "$RECREATION_GOV_API_KEY"

# Upload optional API keys if they exist
echo -e "\n3. Uploading optional API keys..."
[ ! -z "$SPOTIFY_CLIENT_ID" ] && create_or_update_secret "spotify-client-id" "$SPOTIFY_CLIENT_ID"
[ ! -z "$SPOTIFY_CLIENT_SECRET" ] && create_or_update_secret "spotify-client-secret" "$SPOTIFY_CLIENT_SECRET"
[ ! -z "$OPENTABLE_CLIENT_ID" ] && create_or_update_secret "opentable-client-id" "$OPENTABLE_CLIENT_ID"
[ ! -z "$OPENTABLE_CLIENT_SECRET" ] && create_or_update_secret "opentable-client-secret" "$OPENTABLE_CLIENT_SECRET"
[ ! -z "$SHELL_RECHARGE_API_KEY" ] && create_or_update_secret "shell-recharge-api-key" "$SHELL_RECHARGE_API_KEY"
[ ! -z "$CHARGEPOINT_API_KEY" ] && create_or_update_secret "chargepoint-api-key" "$CHARGEPOINT_API_KEY"
[ ! -z "$VIATOR_API_KEY" ] && create_or_update_secret "viator-api-key" "$VIATOR_API_KEY"

# Upload security keys from production env
echo -e "\n4. Uploading security keys..."
source .env.production
create_or_update_secret "app-secret-key" "$SECRET_KEY"
create_or_update_secret "jwt-secret-key" "$JWT_SECRET_KEY"

# Grant Cloud Run service account access to all secrets
echo -e "\n5. Granting Cloud Run access to secrets..."
SERVICE_ACCOUNT="roadtrip-460720-compute@developer.gserviceaccount.com"

for SECRET in google-maps-api-key ticketmaster-api-key ticketmaster-api-secret openweathermap-api-key \
              recreation-gov-api-key app-secret-key jwt-secret-key; do
    echo "Granting access to: $SECRET"
    gcloud secrets add-iam-policy-binding $SECRET \
        --member="serviceAccount:$SERVICE_ACCOUNT" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID || true
done

# Create a consolidated environment variable secret for Cloud Run
echo -e "\n6. Creating consolidated environment secret..."
cat > /tmp/cloud_run_env.yaml << EOF
ENVIRONMENT: production
APP_VERSION: 1.0.0
GCP_PROJECT_ID: $PROJECT_ID
GOOGLE_AI_PROJECT_ID: $PROJECT_ID
GOOGLE_AI_LOCATION: us-central1
GOOGLE_AI_MODEL: gemini-1.5-pro
GCS_BUCKET_NAME: roadtrip-460720-roadtrip-assets
USE_MOCK_APIS: false
SKIP_DB_CHECK: false
MOCK_REDIS: false
TEST_MODE: production
ENABLE_VOICE_SAFETY: true
ENABLE_BOOKING_COMMISSION: false
ENABLE_SEASONAL_PERSONALITIES: true
MAX_CONCURRENT_REQUESTS: 1000
CACHE_TTL_SECONDS: 3600
AI_TIMEOUT_SECONDS: 30
LOG_LEVEL: INFO
EOF

create_or_update_secret "cloud-run-env" "$(cat /tmp/cloud_run_env.yaml)"
rm /tmp/cloud_run_env.yaml

echo -e "\n=========================================="
echo "SECRETS UPLOAD COMPLETE!"
echo "=========================================="
echo "All secrets have been uploaded to Secret Manager"
echo ""
echo "To use in Cloud Run deployment:"
echo "  --set-secrets=\"GOOGLE_MAPS_API_KEY=google-maps-api-key:latest\""
echo "  --set-secrets=\"SECRET_KEY=app-secret-key:latest\""
echo "  etc..."
echo ""
echo "Or mount the consolidated env file:"
echo "  --set-secrets=\"/app/.env=cloud-run-env:latest\""
echo "=========================================="