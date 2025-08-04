#!/bin/bash
# Setup script for Google Secret Manager secrets required by RoadTrip backend
# Run this before deploying with Cloud Build

set -e

echo "Setting up Google Secret Manager secrets for RoadTrip backend..."

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: No project ID set. Run 'gcloud config set project YOUR_PROJECT_ID'"
    exit 1
fi

echo "Using project: $PROJECT_ID"

# Enable Secret Manager API
echo "Enabling Secret Manager API..."
gcloud services enable secretmanager.googleapis.com

# Function to create or update a secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    local description=$3
    
    # Check if secret exists
    if gcloud secrets describe $secret_name --project=$PROJECT_ID &>/dev/null; then
        echo "Updating secret: $secret_name"
        echo -n "$secret_value" | gcloud secrets versions add $secret_name --data-file=- --project=$PROJECT_ID
    else
        echo "Creating secret: $secret_name"
        echo -n "$secret_value" | gcloud secrets create $secret_name \
            --data-file=- \
            --replication-policy="automatic" \
            --labels="app=roadtrip,component=backend" \
            --project=$PROJECT_ID
        
        if [ -n "$description" ]; then
            gcloud secrets update $secret_name --update-labels="description=$description" --project=$PROJECT_ID
        fi
    fi
}

# Database URL
echo ""
echo "Setting up database connection..."
read -p "Enter PostgreSQL DATABASE_URL (format: postgresql://user:pass@host:port/dbname): " DATABASE_URL
create_or_update_secret "roadtrip-database-url" "$DATABASE_URL" "PostgreSQL connection string"

# Redis URL
echo ""
echo "Setting up Redis connection..."
read -p "Enter Redis URL (format: redis://host:port/0): " REDIS_URL
create_or_update_secret "roadtrip-redis-url" "$REDIS_URL" "Redis connection string"

# JWT Secret
echo ""
echo "Setting up JWT secret..."
read -p "Enter JWT_SECRET_KEY (or press Enter to generate): " JWT_SECRET
if [ -z "$JWT_SECRET" ]; then
    JWT_SECRET=$(openssl rand -base64 32)
    echo "Generated JWT secret: $JWT_SECRET"
fi
create_or_update_secret "roadtrip-jwt-secret" "$JWT_SECRET" "JWT signing key"

# Google Maps API Key
echo ""
echo "Setting up Google Maps API..."
read -p "Enter GOOGLE_MAPS_API_KEY: " GOOGLE_MAPS_KEY
create_or_update_secret "roadtrip-google-maps-key" "$GOOGLE_MAPS_KEY" "Google Maps API key"

# Ticketmaster API Key
echo ""
echo "Setting up Ticketmaster API..."
read -p "Enter TICKETMASTER_API_KEY: " TICKETMASTER_KEY
create_or_update_secret "roadtrip-ticketmaster-key" "$TICKETMASTER_KEY" "Ticketmaster API key"

# OpenTable API Key
echo ""
echo "Setting up OpenTable API..."
read -p "Enter OPENTABLE_API_KEY (or press Enter to skip): " OPENTABLE_KEY
OPENTABLE_KEY=${OPENTABLE_KEY:-"dummy-key"}
create_or_update_secret "roadtrip-opentable-key" "$OPENTABLE_KEY" "OpenTable API key"

# Recreation.gov API Key
echo ""
echo "Setting up Recreation.gov API..."
read -p "Enter RECREATION_GOV_API_KEY: " RECREATION_KEY
create_or_update_secret "roadtrip-recreation-gov-key" "$RECREATION_KEY" "Recreation.gov API key"

# Viator API Key
echo ""
echo "Setting up Viator API..."
read -p "Enter VIATOR_API_KEY (or press Enter to skip): " VIATOR_KEY
VIATOR_KEY=${VIATOR_KEY:-"dummy-key"}
create_or_update_secret "roadtrip-viator-key" "$VIATOR_KEY" "Viator API key"

# OpenWeather API Key
echo ""
echo "Setting up OpenWeather API..."
read -p "Enter OPENWEATHER_API_KEY: " OPENWEATHER_KEY
create_or_update_secret "roadtrip-openweather-key" "$OPENWEATHER_KEY" "OpenWeather API key"

# Sentry DSN (optional)
echo ""
echo "Setting up Sentry monitoring (optional)..."
read -p "Enter SENTRY_DSN (or press Enter to skip): " SENTRY_DSN
SENTRY_DSN=${SENTRY_DSN:-""}
create_or_update_secret "roadtrip-sentry-dsn" "$SENTRY_DSN" "Sentry error tracking DSN"

# Grant Cloud Run service account access to secrets
echo ""
echo "Granting service account access to secrets..."
SERVICE_ACCOUNT="roadtrip-backend@${PROJECT_ID}.iam.gserviceaccount.com"

# Create service account if it doesn't exist
if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT --project=$PROJECT_ID &>/dev/null; then
    echo "Creating service account..."
    gcloud iam service-accounts create roadtrip-backend \
        --display-name="RoadTrip Backend Service Account" \
        --project=$PROJECT_ID
fi

# Grant secret accessor role
echo "Granting secret accessor role..."
for secret in roadtrip-database-url roadtrip-redis-url roadtrip-jwt-secret \
              roadtrip-google-maps-key roadtrip-ticketmaster-key roadtrip-opentable-key \
              roadtrip-recreation-gov-key roadtrip-viator-key roadtrip-openweather-key \
              roadtrip-sentry-dsn; do
    gcloud secrets add-iam-policy-binding $secret \
        --member="serviceAccount:${SERVICE_ACCOUNT}" \
        --role="roles/secretmanager.secretAccessor" \
        --project=$PROJECT_ID &>/dev/null || true
done

echo ""
echo "Secret setup complete!"
echo ""
echo "Next steps:"
echo "1. Set up Cloud SQL instance: gcloud sql instances create roadtrip-postgres --tier=db-g1-small --region=us-central1"
echo "2. Set up VPC connector for private access"
echo "3. Run Cloud Build: gcloud builds submit --config=backend/cloudbuild.yaml"
echo ""
echo "To verify secrets:"
echo "gcloud secrets list --filter='labels.app=roadtrip'
"