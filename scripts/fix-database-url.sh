#!/bin/bash
# Fix DATABASE_URL for staging environment

set -euo pipefail

PROJECT_ID="roadtrip-460720"
INSTANCE_NAME="roadtrip-staging-db"
DB_NAME="roadtrip"
DB_USER="roadtrip"

# Get connection name
CONNECTION_NAME="${PROJECT_ID}:us-central1:${INSTANCE_NAME}"

# Build DATABASE_URL for Cloud SQL
DATABASE_URL="postgresql://${DB_USER}:TEMP_PASSWORD@/${DB_NAME}?host=/cloudsql/${CONNECTION_NAME}"

echo "Setting DATABASE_URL for Cloud Run connection..."
echo "Connection Name: $CONNECTION_NAME"

# Update the secret
echo -n "$DATABASE_URL" | gcloud secrets versions add DATABASE_URL-staging \
    --data-file=- \
    --project=$PROJECT_ID

echo "DATABASE_URL updated. Note: You need to set the actual password."