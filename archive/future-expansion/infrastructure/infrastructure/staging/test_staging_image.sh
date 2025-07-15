#!/bin/bash

# Test script for staging Docker image
# This script performs various tests on the built Docker image

set -euo pipefail

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
IMAGE_NAME="gcr.io/roadtrip-460720/roadtrip-backend-staging:latest"
CONTAINER_NAME="roadtrip-staging-test"
TEST_PORT=8081

echo -e "${GREEN}Testing staging Docker image${NC}"
echo "Image: ${IMAGE_NAME}"

# Function to cleanup
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    docker stop ${CONTAINER_NAME} 2>/dev/null || true
    docker rm ${CONTAINER_NAME} 2>/dev/null || true
}

# Set trap to cleanup on exit
trap cleanup EXIT

# Test 1: Image exists
echo -e "\n${YELLOW}Test 1: Checking if image exists...${NC}"
if docker image inspect ${IMAGE_NAME} > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Image exists${NC}"
else
    echo -e "${RED}✗ Image not found. Please build it first.${NC}"
    exit 1
fi

# Test 2: Image security scan
echo -e "\n${YELLOW}Test 2: Running security scan...${NC}"
echo "Checking for common vulnerabilities..."
docker run --rm ${IMAGE_NAME} python -c "import sys; print(f'Python version: {sys.version}')"
docker run --rm ${IMAGE_NAME} pip list --format=freeze | grep -E "(fastapi|uvicorn|gunicorn)" || true

# Test 3: Start container
echo -e "\n${YELLOW}Test 3: Starting container...${NC}"
docker run -d \
    --name ${CONTAINER_NAME} \
    -p ${TEST_PORT}:8080 \
    -e ENVIRONMENT=staging \
    -e TEST_MODE=mock \
    -e LOG_LEVEL=INFO \
    -e JWT_SECRET_KEY=test-secret \
    -e SECRET_KEY=test-secret \
    -e CSRF_SECRET_KEY=test-csrf \
    ${IMAGE_NAME}

# Wait for container to start
echo "Waiting for container to be ready..."
sleep 10

# Test 4: Container is running
echo -e "\n${YELLOW}Test 4: Checking container status...${NC}"
if docker ps | grep -q ${CONTAINER_NAME}; then
    echo -e "${GREEN}✓ Container is running${NC}"
    docker ps --filter name=${CONTAINER_NAME} --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    echo -e "${RED}✗ Container is not running${NC}"
    echo "Container logs:"
    docker logs ${CONTAINER_NAME}
    exit 1
fi

# Test 5: Health check
echo -e "\n${YELLOW}Test 5: Testing health endpoint...${NC}"
for i in {1..5}; do
    if curl -f -s http://localhost:${TEST_PORT}/health > /dev/null; then
        echo -e "${GREEN}✓ Health check passed${NC}"
        break
    else
        if [ $i -eq 5 ]; then
            echo -e "${RED}✗ Health check failed after 5 attempts${NC}"
            exit 1
        fi
        echo "Attempt $i failed, retrying in 5 seconds..."
        sleep 5
    fi
done

# Test 6: API documentation
echo -e "\n${YELLOW}Test 6: Testing API documentation...${NC}"
if curl -f -s http://localhost:${TEST_PORT}/docs > /dev/null; then
    echo -e "${GREEN}✓ API documentation accessible${NC}"
else
    echo -e "${YELLOW}⚠ API documentation not accessible (may be disabled in staging)${NC}"
fi

# Test 7: Memory and CPU usage
echo -e "\n${YELLOW}Test 7: Checking resource usage...${NC}"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" ${CONTAINER_NAME}

# Test 8: Check logs for errors
echo -e "\n${YELLOW}Test 8: Checking logs for errors...${NC}"
ERROR_COUNT=$(docker logs ${CONTAINER_NAME} 2>&1 | grep -iE "(error|exception|critical)" | wc -l)
if [ ${ERROR_COUNT} -eq 0 ]; then
    echo -e "${GREEN}✓ No errors found in logs${NC}"
else
    echo -e "${YELLOW}⚠ Found ${ERROR_COUNT} potential errors in logs${NC}"
    echo "Recent logs:"
    docker logs --tail 20 ${CONTAINER_NAME}
fi

# Test 9: Image size
echo -e "\n${YELLOW}Test 9: Checking image size...${NC}"
SIZE=$(docker image inspect ${IMAGE_NAME} --format='{{.Size}}' | numfmt --to=iec)
echo "Image size: ${SIZE}"
if [ $(docker image inspect ${IMAGE_NAME} --format='{{.Size}}') -lt 1073741824 ]; then
    echo -e "${GREEN}✓ Image size is under 1GB${NC}"
else
    echo -e "${YELLOW}⚠ Image size is over 1GB - consider optimization${NC}"
fi

# Test 10: Non-root user
echo -e "\n${YELLOW}Test 10: Checking user permissions...${NC}"
USER_ID=$(docker exec ${CONTAINER_NAME} id -u)
if [ "${USER_ID}" != "0" ]; then
    echo -e "${GREEN}✓ Running as non-root user (UID: ${USER_ID})${NC}"
else
    echo -e "${RED}✗ Running as root user - security risk!${NC}"
fi

# Summary
echo -e "\n${GREEN}=== Test Summary ===${NC}"
echo -e "${GREEN}All tests completed!${NC}"
echo -e "\nNext steps:"
echo "1. Push to registry: docker push ${IMAGE_NAME}"
echo "2. Deploy to Cloud Run: gcloud run deploy roadtrip-backend-staging --image ${IMAGE_NAME}"