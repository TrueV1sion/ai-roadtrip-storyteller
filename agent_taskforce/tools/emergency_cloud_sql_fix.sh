#!/bin/bash
# Emergency Cloud SQL Fix Script
# Fixes the database flag issue for immediate deployment

set -e

echo "=== EMERGENCY CLOUD SQL FIX ==="
echo "Fixing database deployment issue..."
echo

PROJECT_ID="roadtrip-460720"
REGION="us-central1"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Step 1: Creating Cloud SQL instance without problematic flags${NC}"
gcloud sql instances create roadtrip-db \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --project=$PROJECT_ID \
    --no-backup

echo -e "\n${YELLOW}Step 2: Creating database${NC}"
gcloud sql databases create roadtrip --instance=roadtrip-db --project=$PROJECT_ID

echo -e "\n${YELLOW}Step 3: Creating database user${NC}"
gcloud sql users create roadtrip_user --instance=roadtrip-db --password=temporary123 --project=$PROJECT_ID

echo -e "\n${GREEN}✓ Cloud SQL setup complete!${NC}"
echo -e "${GREEN}Instance: roadtrip-db${NC}"
echo -e "${GREEN}Database: roadtrip${NC}"
echo -e "${GREEN}User: roadtrip_user${NC}"
echo -e "${GREEN}Password: temporary123 (change this in production!)${NC}"

echo -e "\n${YELLOW}You can now continue with the deployment!${NC}"