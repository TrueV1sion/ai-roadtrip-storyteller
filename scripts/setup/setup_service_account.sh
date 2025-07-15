#!/bin/bash
# Script to create Google Cloud service account for AI Road Trip Storyteller

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===================================================${NC}"
echo -e "${BLUE}Google Cloud Service Account Setup${NC}"
echo -e "${BLUE}===================================================${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: Google Cloud SDK is not installed${NC}"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID from .env or use default
PROJECT_ID=$(grep "GCP_PROJECT_ID=" .env | cut -d'=' -f2 || echo "roadtrip-460720")
echo -e "${BLUE}Using project: ${PROJECT_ID}${NC}"

# Set project
gcloud config set project ${PROJECT_ID}

# Service account name
SA_NAME="roadtrip-app"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo -e "\n${YELLOW}Creating service account...${NC}"

# Check if service account exists
if gcloud iam service-accounts describe ${SA_EMAIL} --project=${PROJECT_ID} &>/dev/null; then
    echo -e "${YELLOW}Service account already exists${NC}"
else
    # Create service account
    gcloud iam service-accounts create ${SA_NAME} \
        --display-name="Road Trip App Service Account" \
        --project=${PROJECT_ID}
    echo -e "${GREEN}✓ Service account created${NC}"
fi

echo -e "\n${YELLOW}Granting necessary roles...${NC}"

# List of required roles
ROLES=(
    "roles/aiplatform.user"
    "roles/cloudsql.client"
    "roles/redis.editor"
    "roles/storage.objectAdmin"
    "roles/secretmanager.secretAccessor"
    "roles/logging.logWriter"
    "roles/monitoring.metricWriter"
    "roles/cloudbuild.builds.builder"
    "roles/run.admin"
    "roles/iam.serviceAccountUser"
)

# Grant roles
for role in "${ROLES[@]}"; do
    echo -n "  Granting ${role}..."
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="${role}" \
        --quiet 2>/dev/null || true
    echo -e " ${GREEN}✓${NC}"
done

echo -e "\n${YELLOW}Creating service account key...${NC}"

# Create key file
KEY_FILE="./credentials/vertex-ai-key.json"
mkdir -p ./credentials

# Check if key already exists
if [ -f "${KEY_FILE}" ]; then
    echo -e "${YELLOW}Key file already exists at ${KEY_FILE}${NC}"
    read -p "Overwrite existing key? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing key"
    else
        gcloud iam service-accounts keys create ${KEY_FILE} \
            --iam-account=${SA_EMAIL} \
            --project=${PROJECT_ID}
        echo -e "${GREEN}✓ New key created at ${KEY_FILE}${NC}"
    fi
else
    gcloud iam service-accounts keys create ${KEY_FILE} \
        --iam-account=${SA_EMAIL} \
        --project=${PROJECT_ID}
    echo -e "${GREEN}✓ Key created at ${KEY_FILE}${NC}"
fi

# Set proper permissions
chmod 600 ${KEY_FILE}

echo -e "\n${BLUE}===================================================${NC}"
echo -e "${GREEN}✓ Service account setup complete!${NC}"
echo -e "${BLUE}===================================================${NC}"

echo -e "\nNext steps:"
echo "1. The service account key has been saved to: ${KEY_FILE}"
echo "2. This path is already configured in your .env file"
echo "3. Run: python3 setup_infrastructure.py"

# Test the service account
echo -e "\n${YELLOW}Testing service account...${NC}"
export GOOGLE_APPLICATION_CREDENTIALS=${KEY_FILE}
if gcloud auth application-default print-access-token &>/dev/null; then
    echo -e "${GREEN}✓ Service account is working correctly${NC}"
else
    echo -e "${RED}✗ Service account test failed${NC}"
    echo "Please check the credentials and permissions"
fi