#!/bin/bash
# Secure production deployment script for AI Road Trip Storyteller
# This script ensures all security measures are in place before deployment

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${1:-roadtrip-460720}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="roadtrip-api"

echo -e "${GREEN}Starting secure production deployment for project: $PROJECT_ID${NC}"

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if a secret exists
check_secret() {
    local secret_name=$1
    gcloud secrets describe "$secret_name" --project="$PROJECT_ID" >/dev/null 2>&1
}

# Function to validate environment
validate_environment() {
    echo -e "\n${YELLOW}Validating environment...${NC}"
    
    # Check required tools
    local required_tools=("gcloud" "docker" "python3" "git")
    for tool in "${required_tools[@]}"; do
        if ! command_exists "$tool"; then
            echo -e "${RED}Error: $tool is not installed${NC}"
            exit 1
        fi
    done
    
    # Check gcloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        echo -e "${RED}Error: Not authenticated with gcloud${NC}"
        exit 1
    fi
    
    # Set project
    gcloud config set project "$PROJECT_ID"
    
    echo -e "${GREEN}✓ Environment validation passed${NC}"
}

# Function to check and create secrets
setup_secrets() {
    echo -e "\n${YELLOW}Setting up secrets in Google Secret Manager...${NC}"
    
    # Required secrets
    local required_secrets=(
        "roadtrip-database-url"
        "roadtrip-secret-key"
        "roadtrip-jwt-secret"
        "roadtrip-encryption-master-key"
        "roadtrip-google-maps-key"
        "roadtrip-ticketmaster-key"
        "roadtrip-openweather-key"
    )
    
    local missing_secrets=()
    
    for secret in "${required_secrets[@]}"; do
        if ! check_secret "$secret"; then
            missing_secrets+=("$secret")
            echo -e "${RED}✗ Missing secret: $secret${NC}"
        else
            echo -e "${GREEN}✓ Secret exists: $secret${NC}"
        fi
    done
    
    if [ ${#missing_secrets[@]} -gt 0 ]; then
        echo -e "\n${RED}Missing required secrets. Please run:${NC}"
        echo "python scripts/security/migrate_secrets_to_gsm.py --project-id $PROJECT_ID"
        echo "python scripts/security/generate_encryption_key.py --project-id $PROJECT_ID"
        exit 1
    fi
    
    # Generate new secure keys for critical secrets
    echo -e "\n${YELLOW}Generating new secure keys...${NC}"
    python3 scripts/security/migrate_secrets_to_gsm.py \
        --project-id "$PROJECT_ID" \
        --regenerate-keys \
        --dry-run
}

# Function to run security checks
run_security_checks() {
    echo -e "\n${YELLOW}Running security checks...${NC}"
    
    # Check for exposed secrets in code
    echo "Checking for exposed secrets..."
    if grep -r "AIzaSy\|sk-\|pk_\|rk_" backend/ --exclude-dir=__pycache__ 2>/dev/null; then
        echo -e "${RED}✗ Found potential exposed secrets in code${NC}"
        exit 1
    else
        echo -e "${GREEN}✓ No exposed secrets found in code${NC}"
    fi
    
    # Check .env file
    if [ -f ".env" ]; then
        if grep -E "(API_KEY|SECRET|PASSWORD)=" .env | grep -v "change-in-production\|mock_\|placeholder" > /dev/null; then
            echo -e "${RED}✗ Found real secrets in .env file${NC}"
            echo "Please remove all secrets from .env and use Google Secret Manager"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✓ Security checks passed${NC}"
}

# Function to build and scan Docker image
build_and_scan_image() {
    echo -e "\n${YELLOW}Building Docker image...${NC}"
    
    # Build image
    docker build -t "gcr.io/$PROJECT_ID/$SERVICE_NAME:security-scan" .
    
    # Scan for vulnerabilities
    echo -e "\n${YELLOW}Scanning image for vulnerabilities...${NC}"
    gcloud container images scan "gcr.io/$PROJECT_ID/$SERVICE_NAME:security-scan"
    
    # Get scan results
    local scan_results=$(gcloud container images describe "gcr.io/$PROJECT_ID/$SERVICE_NAME:security-scan" \
        --format='value(image_summary.vulnerability_counts)')
    
    if [[ "$scan_results" == *"CRITICAL"* ]]; then
        echo -e "${RED}✗ Critical vulnerabilities found in image${NC}"
        echo "Please fix vulnerabilities before deploying to production"
        exit 1
    else
        echo -e "${GREEN}✓ No critical vulnerabilities found${NC}"
    fi
}

# Function to run tests
run_tests() {
    echo -e "\n${YELLOW}Running tests...${NC}"
    
    # Run security tests
    echo "Running security tests..."
    cd backend
    python -m pytest tests/security/ -v || {
        echo -e "${RED}✗ Security tests failed${NC}"
        exit 1
    }
    
    # Run critical unit tests
    echo "Running unit tests for core services..."
    python -m pytest tests/unit/test_master_orchestration_agent.py -v || {
        echo -e "${RED}✗ Core unit tests failed${NC}"
        exit 1
    }
    
    cd ..
    echo -e "${GREEN}✓ Tests passed${NC}"
}

# Function to deploy to staging first
deploy_staging() {
    echo -e "\n${YELLOW}Deploying to staging environment...${NC}"
    
    gcloud run deploy "${SERVICE_NAME}-staging" \
        --image "gcr.io/$PROJECT_ID/$SERVICE_NAME:security-scan" \
        --region "$REGION" \
        --platform managed \
        --memory 2Gi \
        --cpu 2 \
        --min-instances 1 \
        --max-instances 10 \
        --allow-unauthenticated \
        --set-env-vars "ENVIRONMENT=staging,PRODUCTION=false,FORCE_HTTPS=true,SECURE_COOKIES=true" \
        --set-secrets "DATABASE_URL=roadtrip-database-url:latest,JWT_SECRET_KEY=roadtrip-jwt-secret:latest,SECRET_KEY=roadtrip-secret-key:latest,ENCRYPTION_MASTER_KEY=roadtrip-encryption-master-key:latest"
    
    # Get staging URL
    STAGING_URL=$(gcloud run services describe "${SERVICE_NAME}-staging" \
        --region "$REGION" \
        --format 'value(status.url)')
    
    echo -e "${GREEN}✓ Deployed to staging: $STAGING_URL${NC}"
    
    # Run smoke tests
    echo -e "\n${YELLOW}Running smoke tests on staging...${NC}"
    curl -f "$STAGING_URL/health" || {
        echo -e "${RED}✗ Staging health check failed${NC}"
        exit 1
    }
    
    echo -e "${GREEN}✓ Staging smoke tests passed${NC}"
}

# Function to deploy to production
deploy_production() {
    echo -e "\n${YELLOW}Deploying to production...${NC}"
    
    # Confirm production deployment
    echo -e "${YELLOW}⚠️  You are about to deploy to PRODUCTION${NC}"
    read -p "Are you sure you want to continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo "Production deployment cancelled"
        exit 0
    fi
    
    # Deploy using Cloud Build for proper CI/CD
    gcloud builds submit \
        --config cloudbuild.yaml \
        --substitutions "_SERVICE_NAME=$SERVICE_NAME,_REGION=$REGION"
    
    echo -e "${GREEN}✓ Production deployment initiated via Cloud Build${NC}"
}

# Function to setup monitoring
setup_monitoring() {
    echo -e "\n${YELLOW}Setting up monitoring and alerts...${NC}"
    
    # Create notification channels
    python3 scripts/monitoring/setup_alert_channels.py \
        --project-id "$PROJECT_ID"
    
    echo -e "${GREEN}✓ Monitoring setup complete${NC}"
}

# Function to encrypt existing 2FA secrets
encrypt_2fa_secrets() {
    echo -e "\n${YELLOW}Encrypting existing 2FA secrets...${NC}"
    
    python3 scripts/security/encrypt_existing_2fa_secrets.py --dry-run
    
    read -p "Proceed with 2FA secret encryption? (yes/no): " confirm
    if [ "$confirm" == "yes" ]; then
        python3 scripts/security/encrypt_existing_2fa_secrets.py
        echo -e "${GREEN}✓ 2FA secrets encrypted${NC}"
    fi
}

# Main deployment flow
main() {
    echo -e "${GREEN}=== AI Road Trip Storyteller Secure Production Deployment ===${NC}"
    
    # Validate environment
    validate_environment
    
    # Run security checks
    run_security_checks
    
    # Setup secrets
    setup_secrets
    
    # Build and scan image
    build_and_scan_image
    
    # Run tests
    run_tests
    
    # Deploy to staging
    deploy_staging
    
    # Setup monitoring
    setup_monitoring
    
    # Encrypt 2FA secrets
    encrypt_2fa_secrets
    
    # Deploy to production
    deploy_production
    
    echo -e "\n${GREEN}=== Deployment Complete ===${NC}"
    echo -e "${GREEN}✓ All security checks passed${NC}"
    echo -e "${GREEN}✓ Staging deployment verified${NC}"
    echo -e "${GREEN}✓ Production deployment initiated${NC}"
    echo -e "\nMonitor the deployment at:"
    echo "https://console.cloud.google.com/cloud-build/builds?project=$PROJECT_ID"
}

# Run main function
main "$@"