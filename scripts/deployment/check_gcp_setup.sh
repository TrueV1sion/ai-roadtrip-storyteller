#!/bin/bash
# Bash script to check GCP project setup for AI Road Trip Storyteller

echo -e "\033[0;36mAI Road Trip Storyteller - GCP Setup Checker\033[0m"
echo -e "\033[0;36m==========================================\033[0m"
echo ""

PROJECT_ID="roadtrip-460720"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Check if gcloud is installed
echo -e "${YELLOW}Checking gcloud installation...${NC}"
if command -v gcloud &> /dev/null; then
    GCLOUD_VERSION=$(gcloud version --format="value(Google Cloud SDK)" 2>/dev/null)
    echo -e "${GREEN}✓ gcloud CLI installed: $GCLOUD_VERSION${NC}"
else
    echo -e "${RED}✗ gcloud CLI not found. Please install from https://cloud.google.com/sdk${NC}"
    exit 1
fi

# Check authentication
echo -e "\n${YELLOW}Checking authentication...${NC}"
ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null)
if [ -n "$ACTIVE_ACCOUNT" ]; then
    echo -e "${GREEN}✓ Authenticated as: $ACTIVE_ACCOUNT${NC}"
else
    echo -e "${RED}✗ Not authenticated. Run: gcloud auth login${NC}"
    exit 1
fi

# Check project
echo -e "\n${YELLOW}Checking project...${NC}"
if gcloud projects describe $PROJECT_ID &>/dev/null; then
    echo -e "${GREEN}✓ Project found: $PROJECT_ID${NC}"
    
    # Check project details
    PROJECT_NAME=$(gcloud projects describe $PROJECT_ID --format="value(name)" 2>/dev/null)
    PROJECT_STATE=$(gcloud projects describe $PROJECT_ID --format="value(lifecycleState)" 2>/dev/null)
    echo -e "  Name: $PROJECT_NAME"
    echo -e "  State: $PROJECT_STATE"
else
    echo -e "${RED}✗ Project not found or not accessible: $PROJECT_ID${NC}"
    echo -e "${YELLOW}  Please check the project ID or your permissions${NC}"
    exit 1
fi

# Set project
echo -e "\n${YELLOW}Setting active project...${NC}"
gcloud config set project $PROJECT_ID &>/dev/null
echo -e "${GREEN}✓ Active project set to: $PROJECT_ID${NC}"

# Check billing
echo -e "\n${YELLOW}Checking billing...${NC}"
BILLING_ENABLED=$(gcloud beta billing projects describe $PROJECT_ID --format="value(billingEnabled)" 2>/dev/null)
if [ "$BILLING_ENABLED" == "True" ]; then
    echo -e "${GREEN}✓ Billing is enabled${NC}"
else
    echo -e "${RED}✗ Billing is not enabled. Enable at: https://console.cloud.google.com/billing${NC}"
fi

# Required APIs
REQUIRED_APIS=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "artifactregistry.googleapis.com"
    "sqladmin.googleapis.com"
    "secretmanager.googleapis.com"
    "texttospeech.googleapis.com"
    "speech.googleapis.com"
    "maps-backend.googleapis.com"
    "redis.googleapis.com"
    "monitoring.googleapis.com"
    "logging.googleapis.com"
    "cloudresourcemanager.googleapis.com"
    "iam.googleapis.com"
)

# Check enabled APIs
echo -e "\n${YELLOW}Checking enabled APIs...${NC}"
ENABLED_APIS=$(gcloud services list --enabled --format="value(config.name)" 2>/dev/null)

MISSING_APIS=()
ENABLED_COUNT=0

for api in "${REQUIRED_APIS[@]}"; do
    if echo "$ENABLED_APIS" | grep -q "^$api$"; then
        echo -e "${GREEN}✓ $api${NC}"
        ((ENABLED_COUNT++))
    else
        echo -e "${RED}✗ $api${NC}"
        MISSING_APIS+=("$api")
    fi
done

echo -e "\n${CYAN}Summary:${NC}"
echo -e "- Enabled APIs: $ENABLED_COUNT/${#REQUIRED_APIS[@]}"
echo -e "- Missing APIs: ${#MISSING_APIS[@]}"

if [ ${#MISSING_APIS[@]} -gt 0 ]; then
    echo -e "\n${YELLOW}To enable missing APIs, run:${NC}"
    echo -n "gcloud services enable"
    for api in "${MISSING_APIS[@]}"; do
        echo -n " \\"
        echo ""
        echo -n "  $api"
    done
    echo " \\"
    echo "  --project=$PROJECT_ID"
    
    echo -e "\n${YELLOW}Or run the deployment script which will enable them automatically:${NC}"
    echo "./gcp_deploy.sh --project-id $PROJECT_ID"
fi

# Check for existing resources
echo -e "\n${YELLOW}Checking for existing resources...${NC}"

# Check Cloud Run services
if gcloud run services list --format="value(metadata.name)" --region=us-central1 2>/dev/null | grep -q "roadtrip-api"; then
    echo -e "${GREEN}✓ Cloud Run service 'roadtrip-api' exists${NC}"
else
    echo -e "- Cloud Run service 'roadtrip-api' not found (will be created during deployment)"
fi

# Check Cloud SQL instances
if gcloud sql instances list --format="value(name)" 2>/dev/null | grep -q "roadtrip-db-prod"; then
    echo -e "${GREEN}✓ Cloud SQL instance 'roadtrip-db-prod' exists${NC}"
else
    echo -e "- Cloud SQL instance 'roadtrip-db-prod' not found (will be created during deployment)"
fi

echo -e "\n${GREEN}Setup check complete!${NC}"
echo ""

if [ ${#MISSING_APIS[@]} -eq 0 ] && [ "$BILLING_ENABLED" == "True" ]; then
    echo -e "${GREEN}✅ Your project is ready for deployment!${NC}"
    echo -e "${YELLOW}Run: ./gcp_deploy.sh --project-id $PROJECT_ID${NC}"
else
    echo -e "${YELLOW}⚠️  Please address the issues above before deploying${NC}"
fi