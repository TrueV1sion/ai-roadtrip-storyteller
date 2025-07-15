#!/bin/bash
# Import existing resources into Terraform state

PROJECT_ID="roadtrip-460720"

echo "Importing existing resources..."

# Import existing secrets
echo "Importing existing secrets..."
terraform import google_secret_manager_secret.db_password projects/$PROJECT_ID/secrets/roadtrip-db-password || true
terraform import google_secret_manager_secret.api_secrets[\"roadtrip-secret-key\"] projects/$PROJECT_ID/secrets/roadtrip-secret-key || true
terraform import google_secret_manager_secret.api_secrets[\"roadtrip-jwt-secret\"] projects/$PROJECT_ID/secrets/roadtrip-jwt-secret || true
terraform import google_secret_manager_secret.api_secrets[\"google-maps-api-key\"] projects/$PROJECT_ID/secrets/google-maps-api-key || true
terraform import google_secret_manager_secret.api_secrets[\"ticketmaster-api-key\"] projects/$PROJECT_ID/secrets/ticketmaster-api-key || true
terraform import google_secret_manager_secret.api_secrets[\"openweather-api-key\"] projects/$PROJECT_ID/secrets/openweather-api-key || true
terraform import google_secret_manager_secret.api_secrets[\"spotify-client-id\"] projects/$PROJECT_ID/secrets/spotify-client-id || true
terraform import google_secret_manager_secret.api_secrets[\"spotify-client-secret\"] projects/$PROJECT_ID/secrets/spotify-client-secret || true

# Import existing storage bucket
echo "Importing existing storage bucket..."
terraform import google_storage_bucket.assets $PROJECT_ID-roadtrip-assets || true

echo "Import complete. Now run 'terraform plan' to see what will be changed."