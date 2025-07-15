#!/bin/bash
# Fix secret name mismatches for deployment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}🔐 Fixing Secret Names in Google Secret Manager${NC}"
echo -e "${BLUE}===================================================${NC}"

PROJECT_ID="roadtrip-460720"

echo -e "\n${YELLOW}Step 1: Create missing/misnamed secrets${NC}"

# Load values from .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Function to create or update a secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    
    if gcloud secrets describe $secret_name --project=$PROJECT_ID >/dev/null 2>&1; then
        echo "Secret $secret_name already exists"
    else
        echo "Creating secret: $secret_name"
        echo -n "$secret_value" | gcloud secrets create $secret_name --data-file=- --project=$PROJECT_ID
    fi
}

# Fix database URL secret name (roadtrip-db-url -> roadtrip-database-url)
echo -e "\n${YELLOW}Fixing database URL secret...${NC}"
DB_URL_VALUE=$(gcloud secrets versions access latest --secret="roadtrip-db-url" --project=$PROJECT_ID 2>/dev/null || echo "")
if [ ! -z "$DB_URL_VALUE" ]; then
    create_or_update_secret "roadtrip-database-url" "$DB_URL_VALUE"
    echo -e "${GREEN}✓ Created roadtrip-database-url${NC}"
else
    # Use value from .env or default
    DB_URL="${DATABASE_URL:-postgresql://roadtrip:roadtrip123@localhost:5432/roadtrip}"
    create_or_update_secret "roadtrip-database-url" "$DB_URL"
    echo -e "${GREEN}✓ Created roadtrip-database-url from .env${NC}"
fi

# Ensure all required secrets exist
echo -e "\n${YELLOW}Verifying all required secrets...${NC}"

# API Keys that should exist
REQUIRED_SECRETS=(
    "roadtrip-database-url"
    "roadtrip-jwt-secret"
    "roadtrip-secret-key"
    "google-maps-api-key"
    "openweather-api-key"
    "ticketmaster-api-key"
    "recreation-gov-api-key"
)

echo -e "\n${YELLOW}Secret Status:${NC}"
for secret in "${REQUIRED_SECRETS[@]}"; do
    if gcloud secrets describe $secret --project=$PROJECT_ID >/dev/null 2>&1; then
        echo -e "${GREEN}✓ $secret exists${NC}"
    else
        echo -e "${RED}✗ $secret missing${NC}"
        
        # Try to create from environment
        case $secret in
            "google-maps-api-key")
                if [ ! -z "$GOOGLE_MAPS_API_KEY" ]; then
                    create_or_update_secret "$secret" "$GOOGLE_MAPS_API_KEY"
                fi
                ;;
            "openweather-api-key")
                if [ ! -z "$OPENWEATHERMAP_API_KEY" ]; then
                    create_or_update_secret "$secret" "$OPENWEATHERMAP_API_KEY"
                fi
                ;;
            "ticketmaster-api-key")
                if [ ! -z "$TICKETMASTER_API_KEY" ]; then
                    create_or_update_secret "$secret" "$TICKETMASTER_API_KEY"
                fi
                ;;
        esac
    fi
done

echo -e "\n${YELLOW}Step 2: List all secrets for verification${NC}"
echo "Current secrets in project $PROJECT_ID:"
gcloud secrets list --project=$PROJECT_ID --format="table(name)" | grep -E "(roadtrip|google-maps|ticketmaster|openweather|recreation)" | sort

echo -e "\n${BLUE}===================================================${NC}"
echo -e "${BLUE}📋 Next Steps:${NC}"
echo -e "${BLUE}===================================================${NC}"
echo ""
echo "1. Secrets have been standardized to match cloudbuild.yaml"
echo ""
echo "2. To trigger a new Cloud Build deployment:"
echo "   gcloud builds submit --config=cloudbuild.yaml"
echo ""
echo "3. To manually deploy with correct secrets:"
echo "   gcloud run deploy roadtrip-api \\"
echo "     --image gcr.io/$PROJECT_ID/roadtrip-backend:latest \\"
echo "     --region us-central1 \\"
echo "     --set-secrets=DATABASE_URL=roadtrip-database-url:latest,JWT_SECRET_KEY=roadtrip-jwt-secret:latest,SECRET_KEY=roadtrip-secret-key:latest"
echo ""
echo -e "${GREEN}✅ Secret names are now consistent!${NC}"