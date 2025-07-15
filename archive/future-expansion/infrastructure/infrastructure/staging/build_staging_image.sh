#!/bin/bash

# Build script for staging Docker image
# This script builds and tags the Docker image for Google Container Registry

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="roadtrip-460720"
IMAGE_NAME="roadtrip-backend-staging"
REGION="us-central1"
REGISTRY="gcr.io"
FULL_IMAGE_NAME="${REGISTRY}/${PROJECT_ID}/${IMAGE_NAME}"

# Get timestamp for tagging
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "no-git")

echo -e "${GREEN}Building staging Docker image for AI Road Trip Storyteller${NC}"
echo "Project ID: ${PROJECT_ID}"
echo "Image: ${FULL_IMAGE_NAME}"
echo "Timestamp: ${TIMESTAMP}"
echo "Git SHA: ${GIT_SHA}"

# Change to project root directory
cd /mnt/c/users/jared/onedrive/desktop/roadtrip

# Ensure required files exist
if [ ! -f "requirements.prod.txt" ]; then
    echo -e "${RED}Error: requirements.prod.txt not found${NC}"
    exit 1
fi

if [ ! -d "backend" ]; then
    echo -e "${RED}Error: backend directory not found${NC}"
    exit 1
fi

if [ ! -f "healthcheck.sh" ]; then
    echo -e "${RED}Error: healthcheck.sh not found${NC}"
    exit 1
fi

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build \
    -f infrastructure/staging/Dockerfile.staging \
    -t ${FULL_IMAGE_NAME}:latest \
    -t ${FULL_IMAGE_NAME}:${TIMESTAMP} \
    -t ${FULL_IMAGE_NAME}:${GIT_SHA} \
    --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
    --build-arg GIT_COMMIT=${GIT_SHA} \
    --platform linux/amd64 \
    .

# Check if build was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Docker image built successfully!${NC}"
    
    # Display image info
    echo -e "\n${YELLOW}Image details:${NC}"
    docker images ${FULL_IMAGE_NAME} --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
    
    # Display build recommendations
    echo -e "\n${GREEN}Next steps:${NC}"
    echo "1. Test the image locally:"
    echo "   docker run -p 8080:8080 --env-file .env.staging ${FULL_IMAGE_NAME}:latest"
    echo ""
    echo "2. Push to Google Container Registry:"
    echo "   docker push ${FULL_IMAGE_NAME}:latest"
    echo "   docker push ${FULL_IMAGE_NAME}:${TIMESTAMP}"
    echo "   docker push ${FULL_IMAGE_NAME}:${GIT_SHA}"
    echo ""
    echo "3. Deploy to Cloud Run:"
    echo "   gcloud run deploy ${IMAGE_NAME} --image ${FULL_IMAGE_NAME}:${TIMESTAMP} --region ${REGION}"
    
    # Create a build manifest
    cat > infrastructure/staging/build-manifest-${TIMESTAMP}.json <<EOF
{
    "build_timestamp": "${TIMESTAMP}",
    "git_sha": "${GIT_SHA}",
    "image_name": "${FULL_IMAGE_NAME}",
    "tags": ["latest", "${TIMESTAMP}", "${GIT_SHA}"],
    "builder": "$(whoami)@$(hostname)",
    "build_date": "$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
}
EOF
    
    echo -e "\n${GREEN}Build manifest saved to: infrastructure/staging/build-manifest-${TIMESTAMP}.json${NC}"
else
    echo -e "${RED}Docker build failed!${NC}"
    exit 1
fi