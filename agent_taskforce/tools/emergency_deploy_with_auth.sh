#!/bin/bash

# Emergency Terraform Deployment with Authentication
# Combines auth setup and deployment in one script
# Security Operations Team - Unblocking Deployment

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/production"
TERRAFORM_BIN="$SCRIPT_DIR/terraform"

echo -e "${BLUE}=== Emergency Terraform Deployment with Auth ===${NC}"
echo -e "${YELLOW}This script will authenticate and deploy in one step${NC}"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    
    # Check if terraform binary exists
    if [ ! -f "$TERRAFORM_BIN" ]; then
        echo -e "${RED}ERROR: Terraform binary not found at $TERRAFORM_BIN${NC}"
        exit 1
    fi
    
    # Check if infrastructure directory exists
    if [ ! -d "$TERRAFORM_DIR" ]; then
        echo -e "${RED}ERROR: Infrastructure directory not found at $TERRAFORM_DIR${NC}"
        exit 1
    fi
    
    # Check if gcloud is available
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}ERROR: gcloud CLI not found${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ All prerequisites met${NC}"
}

# Function to setup authentication
setup_auth() {
    echo -e "${BLUE}Setting up authentication...${NC}"
    
    # Method 1: Try to use access token (fastest)
    if gcloud auth print-access-token &> /dev/null; then
        export GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token)
        export GOOGLE_PROJECT="roadtrip-460720"
        export TF_VAR_project_id="roadtrip-460720"
        echo -e "${GREEN}✓ Authentication configured using access token${NC}"
        return 0
    fi
    
    # Method 2: Check for existing credentials
    if [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ] && [ -f "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
        echo -e "${GREEN}✓ Using existing service account credentials${NC}"
        return 0
    fi
    
    # Method 3: Check for application default credentials
    if [ -f "$HOME/.config/gcloud/application_default_credentials.json" ]; then
        export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/gcloud/application_default_credentials.json"
        echo -e "${GREEN}✓ Using application default credentials${NC}"
        return 0
    fi
    
    echo -e "${RED}ERROR: No authentication method available${NC}"
    echo -e "${YELLOW}Please run one of the following:${NC}"
    echo "  1. gcloud auth login"
    echo "  2. gcloud auth application-default login"
    echo "  3. Export GOOGLE_APPLICATION_CREDENTIALS with path to service account key"
    exit 1
}

# Function to run terraform
run_terraform() {
    cd "$TERRAFORM_DIR"
    
    # Initialize
    echo -e "${BLUE}Initializing Terraform...${NC}"
    if ! "$TERRAFORM_BIN" init; then
        echo -e "${RED}ERROR: Terraform init failed${NC}"
        exit 1
    fi
    
    # Validate
    echo -e "${BLUE}Validating configuration...${NC}"
    if ! "$TERRAFORM_BIN" validate; then
        echo -e "${RED}ERROR: Terraform validation failed${NC}"
        exit 1
    fi
    
    # Plan
    echo -e "${BLUE}Creating deployment plan...${NC}"
    if ! "$TERRAFORM_BIN" plan -out=emergency.tfplan; then
        echo -e "${RED}ERROR: Terraform plan failed${NC}"
        exit 1
    fi
    
    # Show plan summary
    echo ""
    echo -e "${YELLOW}=== Deployment Plan Summary ===${NC}"
    "$TERRAFORM_BIN" show -no-color emergency.tfplan | grep -E "^  [+-~]|^Plan:" || true
    echo ""
    
    # Confirm deployment
    echo -e "${YELLOW}Ready to deploy these changes to PRODUCTION${NC}"
    read -p "Continue with deployment? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo -e "${RED}Deployment cancelled${NC}"
        exit 0
    fi
    
    # Apply
    echo -e "${BLUE}Applying infrastructure changes...${NC}"
    if ! "$TERRAFORM_BIN" apply emergency.tfplan; then
        echo -e "${RED}ERROR: Terraform apply failed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Infrastructure deployed successfully!${NC}"
}

# Function to show post-deployment steps
show_post_deployment() {
    echo ""
    echo -e "${BLUE}=== Post-Deployment Steps ===${NC}"
    echo ""
    echo "1. Create secrets in Secret Manager:"
    echo "   $SCRIPT_DIR/add_to_secret_manager.sh"
    echo ""
    echo "2. Deploy application:"
    echo "   $SCRIPT_DIR/deploy_production.sh"
    echo ""
    echo "3. Run post-deployment validation:"
    echo "   $SCRIPT_DIR/validate_deployment.sh"
    echo ""
    echo "4. Monitor deployment:"
    echo "   - Cloud Console: https://console.cloud.google.com/home/dashboard?project=roadtrip-460720"
    echo "   - Logs: gcloud logging read 'resource.type=\"cloud_run_revision\"' --limit 50"
    echo ""
}

# Main execution
main() {
    echo -e "${YELLOW}Starting emergency deployment process...${NC}"
    echo "Project: roadtrip-460720"
    echo "Environment: production"
    echo "Timestamp: $(date)"
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Setup authentication
    setup_auth
    
    # Show current auth info
    echo ""
    echo -e "${BLUE}Authentication Status:${NC}"
    echo "Active account: $(gcloud auth list --filter=status:ACTIVE --format='value(account)')"
    echo "Project: $(gcloud config get-value project)"
    echo ""
    
    # Run terraform
    run_terraform
    
    # Show post-deployment steps
    show_post_deployment
    
    # Save deployment record
    DEPLOYMENT_RECORD="$SCRIPT_DIR/../reports/emergency_deployment_$(date +%Y%m%d_%H%M%S).log"
    echo "Deployment completed at $(date)" > "$DEPLOYMENT_RECORD"
    echo "Deployed by: $(whoami)" >> "$DEPLOYMENT_RECORD"
    echo "Authentication method: ${GOOGLE_APPLICATION_CREDENTIALS:-access_token}" >> "$DEPLOYMENT_RECORD"
    
    echo -e "${GREEN}Deployment record saved to: $DEPLOYMENT_RECORD${NC}"
}

# Handle interrupts
trap 'echo -e "\n${RED}Deployment interrupted${NC}"; exit 1' INT TERM

# Run main function
main "$@"