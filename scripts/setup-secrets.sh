#!/bin/bash
# Setup secrets in Google Secret Manager
# Usage: ./setup-secrets.sh [project-id]

set -euo pipefail

PROJECT_ID="${1:-${GCP_PROJECT_ID:-roadtrip-460720}}"

# Required secrets and their environment variable names
declare -A SECRETS=(
    ["database-url"]="DATABASE_URL"
    ["jwt-secret-key"]="JWT_SECRET_KEY"
    ["encryption-key"]="ENCRYPTION_KEY"
    ["google-maps-api-key"]="GOOGLE_MAPS_API_KEY"
    ["openweathermap-api-key"]="OPENWEATHERMAP_API_KEY"
    ["ticketmaster-api-key"]="TICKETMASTER_API_KEY"
    ["redis-password"]="REDIS_PASSWORD"
    ["csrf-secret-key"]="CSRF_SECRET_KEY"
    ["spotify-client-id"]="SPOTIFY_CLIENT_ID"
    ["spotify-client-secret"]="SPOTIFY_CLIENT_SECRET"
)

echo "Setting up secrets in Google Secret Manager"
echo "Project: $PROJECT_ID"

# Check if secrets exist or create them
for secret_name in "${!SECRETS[@]}"; do
    env_var="${SECRETS[$secret_name]}"
    
    # Check if secret exists
    if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" &>/dev/null; then
        echo "✓ Secret exists: $secret_name"
    else
        # Get value from environment or generate
        secret_value="${!env_var:-}"
        
        if [[ -z "$secret_value" ]]; then
            # Generate secure defaults for some secrets
            case "$secret_name" in
                "jwt-secret-key"|"encryption-key"|"csrf-secret-key")
                    secret_value=$(openssl rand -base64 32)
                    echo "Generated secure value for: $secret_name"
                    ;;
                "redis-password")
                    secret_value=$(openssl rand -base64 16)
                    echo "Generated secure value for: $secret_name"
                    ;;
                *)
                    echo "WARNING: No value for $secret_name (set $env_var environment variable)"
                    continue
                    ;;
            esac
        fi
        
        # Create secret
        echo -n "$secret_value" | gcloud secrets create "$secret_name" \
            --data-file=- \
            --project="$PROJECT_ID" \
            --replication-policy="automatic"
        
        echo "✓ Created secret: $secret_name"
    fi
done

echo ""
echo "Secrets setup complete!"
echo ""
echo "To set API keys, export them before running this script:"
echo "  export GOOGLE_MAPS_API_KEY='your-key'"
echo "  export OPENWEATHERMAP_API_KEY='your-key'"
echo "  export TICKETMASTER_API_KEY='your-key'"
echo "  export SPOTIFY_CLIENT_ID='your-id'"
echo "  export SPOTIFY_CLIENT_SECRET='your-secret'"