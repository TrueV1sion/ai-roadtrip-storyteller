#!/bin/bash

# Terraform Authentication Setup Script
# Security Operations Team - Emergency Auth Configuration
# Date: 2025-07-07

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="roadtrip-460720"
SERVICE_ACCOUNT_EMAIL="792001900150-compute@developer.gserviceaccount.com"
KEY_DIR="${HOME}/.gcp"
KEY_FILE="${KEY_DIR}/terraform-auth-key.json"
CREDENTIALS_FILE="${KEY_DIR}/application_default_credentials.json"

echo -e "${BLUE}=== Terraform Authentication Setup ===${NC}"
echo -e "${YELLOW}This script provides multiple authentication methods for Terraform${NC}"
echo ""

# Function to check if gcloud is installed
check_gcloud() {
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}ERROR: gcloud CLI is not installed${NC}"
        echo "Please install Google Cloud SDK: https://cloud.google.com/sdk/docs/install"
        return 1
    fi
    return 0
}

# Function to check current authentication
check_current_auth() {
    echo -e "${BLUE}Checking current authentication status...${NC}"
    
    # Check if application default credentials exist
    if [ -f "$HOME/.config/gcloud/application_default_credentials.json" ]; then
        echo -e "${GREEN}✓ Application Default Credentials found${NC}"
        export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json"
        return 0
    fi
    
    # Check if GOOGLE_APPLICATION_CREDENTIALS is set
    if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        echo -e "${GREEN}✓ Service account key found at: $GOOGLE_APPLICATION_CREDENTIALS${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}⚠ No authentication credentials found${NC}"
    return 1
}

# Method 1: Use existing service account (non-interactive)
setup_service_account_auth() {
    echo -e "${BLUE}Setting up service account authentication...${NC}"
    
    # Create directory if it doesn't exist
    mkdir -p "$KEY_DIR"
    
    # Check if we can impersonate the service account
    if check_gcloud; then
        echo -e "${YELLOW}Attempting to generate access token for service account...${NC}"
        
        # Try to get access token
        if gcloud auth print-access-token --impersonate-service-account="$SERVICE_ACCOUNT_EMAIL" &> /dev/null; then
            echo -e "${GREEN}✓ Can impersonate service account${NC}"
            
            # Create a temporary access token configuration
            cat > "${KEY_DIR}/terraform-env.sh" << EOF
#!/bin/bash
# Terraform environment configuration
# Source this file before running Terraform

export GOOGLE_OAUTH_ACCESS_TOKEN=\$(gcloud auth print-access-token --impersonate-service-account="$SERVICE_ACCOUNT_EMAIL")
export GOOGLE_PROJECT="$PROJECT_ID"
export TF_VAR_project_id="$PROJECT_ID"

echo "Terraform environment configured for project: $PROJECT_ID"
echo "Using service account: $SERVICE_ACCOUNT_EMAIL"
EOF
            chmod +x "${KEY_DIR}/terraform-env.sh"
            echo -e "${GREEN}✓ Created environment script at: ${KEY_DIR}/terraform-env.sh${NC}"
            echo -e "${YELLOW}Run: source ${KEY_DIR}/terraform-env.sh before terraform commands${NC}"
            return 0
        else
            echo -e "${RED}✗ Cannot impersonate service account${NC}"
        fi
    fi
    
    return 1
}

# Method 2: Create minimal auth configuration
create_auth_workaround() {
    echo -e "${BLUE}Creating authentication workaround...${NC}"
    
    # Create a wrapper script for Terraform
    cat > "${KEY_DIR}/terraform-wrapper.sh" << 'EOF'
#!/bin/bash
# Terraform wrapper with authentication handling

# Check if running in CI/CD or automated environment
if [ -n "$CI" ] || [ -n "$AUTOMATION" ]; then
    echo "Running in automated environment"
    # Use environment variables for auth
    if [ -z "$GOOGLE_CREDENTIALS" ]; then
        echo "ERROR: GOOGLE_CREDENTIALS environment variable not set"
        echo "Please set GOOGLE_CREDENTIALS with base64-encoded service account key"
        exit 1
    fi
    
    # Decode and use credentials
    echo "$GOOGLE_CREDENTIALS" | base64 -d > /tmp/gcp-key.json
    export GOOGLE_APPLICATION_CREDENTIALS="/tmp/gcp-key.json"
fi

# Pass through to terraform
exec terraform "$@"
EOF
    
    chmod +x "${KEY_DIR}/terraform-wrapper.sh"
    echo -e "${GREEN}✓ Created Terraform wrapper at: ${KEY_DIR}/terraform-wrapper.sh${NC}"
}

# Method 3: Environment variable configuration
setup_env_vars() {
    echo -e "${BLUE}Setting up environment variables...${NC}"
    
    cat > "${KEY_DIR}/terraform.env" << EOF
# Terraform Authentication Environment Variables
# Source this file or add to your shell profile

# Project Configuration
export GOOGLE_PROJECT="$PROJECT_ID"
export GOOGLE_REGION="us-central1"
export GOOGLE_ZONE="us-central1-a"

# Terraform Variables
export TF_VAR_project_id="$PROJECT_ID"
export TF_VAR_environment="production"

# Authentication Options:
# Option 1: Set path to service account key
# export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"

# Option 2: Use access token (temporary, ~1 hour)
# export GOOGLE_OAUTH_ACCESS_TOKEN="\$(gcloud auth print-access-token)"

# Option 3: Use impersonation
# export GOOGLE_IMPERSONATE_SERVICE_ACCOUNT="$SERVICE_ACCOUNT_EMAIL"

# Terraform behavior
export TF_LOG="INFO"
export TF_LOG_PATH="terraform.log"

# Disable interactive prompts
export TF_INPUT=false
export TF_CLI_ARGS_plan="-input=false"
export TF_CLI_ARGS_apply="-input=false -auto-approve"
EOF
    
    echo -e "${GREEN}✓ Created environment file at: ${KEY_DIR}/terraform.env${NC}"
}

# Method 4: Create provider override
create_provider_override() {
    echo -e "${BLUE}Creating Terraform provider override...${NC}"
    
    cat > "${KEY_DIR}/provider-override.tf" << EOF
# Provider configuration override for authentication
# Copy this file to your Terraform directory as needed

provider "google" {
  project = "$PROJECT_ID"
  region  = "us-central1"
  
  # Authentication options (uncomment one):
  
  # Option 1: Use access token (for CI/CD)
  # access_token = var.google_access_token
  
  # Option 2: Use service account impersonation
  # impersonate_service_account = "$SERVICE_ACCOUNT_EMAIL"
  
  # Option 3: Disable all authentication (for planning only)
  # skip_credentials_validation = true
}

provider "google-beta" {
  project = "$PROJECT_ID"
  region  = "us-central1"
  
  # Match authentication method with google provider
}

# Variable for access token if using that method
# variable "google_access_token" {
#   description = "Google Cloud access token"
#   type        = string
#   default     = ""
#   sensitive   = true
# }
EOF
    
    echo -e "${GREEN}✓ Created provider override at: ${KEY_DIR}/provider-override.tf${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}Starting Terraform authentication setup...${NC}"
    echo ""
    
    # Check current auth status
    if check_current_auth; then
        echo -e "${GREEN}Authentication is already configured!${NC}"
        echo -e "Current credentials: $GOOGLE_APPLICATION_CREDENTIALS"
        echo ""
    fi
    
    # Try to set up service account auth
    if setup_service_account_auth; then
        echo -e "${GREEN}✓ Service account authentication configured${NC}"
    else
        echo -e "${YELLOW}⚠ Could not set up service account authentication automatically${NC}"
    fi
    
    # Create additional helpers
    create_auth_workaround
    setup_env_vars
    create_provider_override
    
    # Create quick setup script
    cat > "${KEY_DIR}/quick-auth.sh" << 'EOF'
#!/bin/bash
# Quick authentication setup for Terraform

echo "Terraform Authentication Quick Setup"
echo "==================================="
echo ""
echo "Choose authentication method:"
echo "1) Use gcloud auth (interactive)"
echo "2) Use service account key file"
echo "3) Use access token (temporary)"
echo "4) Skip auth (dry run only)"
echo ""
read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo "Running gcloud auth..."
        gcloud auth application-default login
        echo "Authentication complete!"
        ;;
    2)
        read -p "Enter path to service account key JSON: " keypath
        export GOOGLE_APPLICATION_CREDENTIALS="$keypath"
        echo "export GOOGLE_APPLICATION_CREDENTIALS=\"$keypath\"" >> ~/.bashrc
        echo "Authentication configured!"
        ;;
    3)
        echo "Generating access token..."
        export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
        echo "Access token set (valid for ~1 hour)"
        ;;
    4)
        echo "Skipping authentication - terraform plan only!"
        export TF_VAR_skip_auth=true
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "You can now run Terraform commands!"
EOF
    
    chmod +x "${KEY_DIR}/quick-auth.sh"
    
    # Summary
    echo ""
    echo -e "${GREEN}=== Setup Complete ===${NC}"
    echo ""
    echo -e "${BLUE}Available authentication methods:${NC}"
    echo ""
    echo "1) ${YELLOW}Source environment script:${NC}"
    echo "   source ${KEY_DIR}/terraform-env.sh"
    echo ""
    echo "2) ${YELLOW}Use wrapper script:${NC}"
    echo "   ${KEY_DIR}/terraform-wrapper.sh plan"
    echo ""
    echo "3) ${YELLOW}Run quick setup:${NC}"
    echo "   ${KEY_DIR}/quick-auth.sh"
    echo ""
    echo "4) ${YELLOW}Manual setup:${NC}"
    echo "   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json"
    echo "   OR"
    echo "   gcloud auth application-default login"
    echo ""
    echo -e "${BLUE}For CI/CD environments:${NC}"
    echo "   Set GOOGLE_CREDENTIALS with base64-encoded service account key"
    echo "   Example: export GOOGLE_CREDENTIALS=\$(base64 < key.json)"
    echo ""
    echo -e "${GREEN}All files created in: ${KEY_DIR}/${NC}"
}

# Run main function
main

# Export useful paths
export TERRAFORM_AUTH_DIR="${KEY_DIR}"
echo ""
echo -e "${YELLOW}TIP: Add this to your shell profile:${NC}"
echo "export TERRAFORM_AUTH_DIR=\"${KEY_DIR}\""