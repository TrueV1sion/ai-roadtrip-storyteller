#!/bin/bash

# Test Terraform Authentication
# Quick validation script to verify auth is working

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Terraform Authentication Test ===${NC}"
echo ""

# Test 1: Check gcloud auth
echo -e "${BLUE}Test 1: Checking gcloud authentication...${NC}"
if gcloud auth list --filter=status:ACTIVE --format='value(account)' &> /dev/null; then
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format='value(account)')
    echo -e "${GREEN}✓ gcloud authenticated as: $ACTIVE_ACCOUNT${NC}"
else
    echo -e "${RED}✗ No active gcloud authentication${NC}"
fi

# Test 2: Check project
echo -e "${BLUE}Test 2: Checking project configuration...${NC}"
PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -n "$PROJECT" ]; then
    echo -e "${GREEN}✓ Project configured: $PROJECT${NC}"
else
    echo -e "${RED}✗ No project configured${NC}"
fi

# Test 3: Check access token
echo -e "${BLUE}Test 3: Testing access token generation...${NC}"
if gcloud auth print-access-token &> /dev/null; then
    echo -e "${GREEN}✓ Can generate access tokens${NC}"
else
    echo -e "${RED}✗ Cannot generate access tokens${NC}"
fi

# Test 4: Check environment variables
echo -e "${BLUE}Test 4: Checking environment variables...${NC}"
if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    if [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        echo -e "${GREEN}✓ GOOGLE_APPLICATION_CREDENTIALS set and file exists${NC}"
    else
        echo -e "${YELLOW}⚠ GOOGLE_APPLICATION_CREDENTIALS set but file missing${NC}"
    fi
elif [ -n "$GOOGLE_OAUTH_ACCESS_TOKEN" ]; then
    echo -e "${GREEN}✓ Using GOOGLE_OAUTH_ACCESS_TOKEN${NC}"
else
    echo -e "${YELLOW}⚠ No authentication environment variables set${NC}"
fi

# Test 5: Check Application Default Credentials
echo -e "${BLUE}Test 5: Checking Application Default Credentials...${NC}"
if [ -f "$HOME/.config/gcloud/application_default_credentials.json" ]; then
    echo -e "${GREEN}✓ Application Default Credentials found${NC}"
else
    echo -e "${YELLOW}⚠ No Application Default Credentials${NC}"
fi

# Test 6: Terraform provider test
echo -e "${BLUE}Test 6: Testing Terraform provider...${NC}"
TEMP_DIR=$(mktemp -d)
cat > "$TEMP_DIR/test.tf" << EOF
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = "roadtrip-460720"
  region  = "us-central1"
}

data "google_project" "current" {}

output "project_id" {
  value = data.google_project.current.project_id
}
EOF

cd "$TEMP_DIR"
TERRAFORM_BIN="$(dirname "$0")/terraform"

# Try with access token
export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token 2>/dev/null || echo "")

if "$TERRAFORM_BIN" init -upgrade &> /dev/null; then
    if "$TERRAFORM_BIN" plan &> /dev/null; then
        echo -e "${GREEN}✓ Terraform can authenticate to Google Cloud${NC}"
    else
        echo -e "${RED}✗ Terraform authentication failed${NC}"
    fi
else
    echo -e "${RED}✗ Terraform init failed${NC}"
fi

# Cleanup
cd - > /dev/null
rm -rf "$TEMP_DIR"

# Summary
echo ""
echo -e "${BLUE}=== Authentication Summary ===${NC}"
echo ""

if [ -n "$GOOGLE_OAUTH_ACCESS_TOKEN" ]; then
    echo -e "${GREEN}Ready to deploy using access token method${NC}"
    echo ""
    echo "To deploy now, run:"
    echo "  export GOOGLE_OAUTH_ACCESS_TOKEN=\$(gcloud auth print-access-token)"
    echo "  cd infrastructure/production"
    echo "  ../../agent_taskforce/tools/terraform plan"
elif [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
    echo -e "${GREEN}Ready to deploy using service account key${NC}"
    echo ""
    echo "To deploy now, run:"
    echo "  cd infrastructure/production"
    echo "  ../../agent_taskforce/tools/terraform plan"
else
    echo -e "${YELLOW}Authentication needs setup${NC}"
    echo ""
    echo "Quick fix - run:"
    echo "  ./agent_taskforce/tools/setup_terraform_auth.sh"
    echo "  source ~/.gcp/terraform-env.sh"
fi

echo ""