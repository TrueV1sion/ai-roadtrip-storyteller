#!/bin/bash
# Pre-deployment Validation Script
# Ensures all systems are ready for production deployment

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-roadtrip-460720}"
REGION="${REGION:-us-central1}"
MIN_PYTHON_VERSION="3.9"
REQUIRED_DISK_SPACE_GB=10

# Status tracking
ERRORS=0
WARNINGS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
    ((WARNINGS++))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    ((ERRORS++))
}

# Check functions
check_python_version() {
    log_info "Checking Python version..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        if (( $(echo "$PYTHON_VERSION >= $MIN_PYTHON_VERSION" | bc -l) )); then
            log_success "Python $PYTHON_VERSION found (required: >=$MIN_PYTHON_VERSION)"
        else
            log_error "Python $PYTHON_VERSION found, but >=$MIN_PYTHON_VERSION required"
        fi
    else
        log_error "Python3 not found"
    fi
}

check_docker() {
    log_info "Checking Docker..."
    if command -v docker &> /dev/null; then
        if docker ps &> /dev/null; then
            DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | sed 's/,$//')
            log_success "Docker $DOCKER_VERSION is running"
        else
            log_error "Docker is installed but not running or accessible"
        fi
    else
        log_error "Docker not found"
    fi
}

check_gcloud() {
    log_info "Checking Google Cloud SDK..."
    if command -v gcloud &> /dev/null; then
        GCLOUD_VERSION=$(gcloud version | head -n1 | cut -d' ' -f4)
        log_success "Google Cloud SDK $GCLOUD_VERSION found"
        
        # Check authentication
        if gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
            ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)")
            log_success "Authenticated as: $ACTIVE_ACCOUNT"
        else
            log_error "No active Google Cloud authentication"
        fi
        
        # Check project
        CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
        if [ "$CURRENT_PROJECT" = "$PROJECT_ID" ]; then
            log_success "Correct project configured: $PROJECT_ID"
        else
            log_warning "Project mismatch. Current: $CURRENT_PROJECT, Expected: $PROJECT_ID"
        fi
    else
        log_error "Google Cloud SDK not found"
    fi
}

check_terraform() {
    log_info "Checking Terraform..."
    if command -v terraform &> /dev/null; then
        TERRAFORM_VERSION=$(terraform version | head -n1 | cut -d' ' -f2)
        log_success "Terraform $TERRAFORM_VERSION found"
    else
        log_error "Terraform not found"
    fi
}

check_disk_space() {
    log_info "Checking disk space..."
    AVAILABLE_GB=$(df -BG . | tail -1 | awk '{print $4}' | sed 's/G//')
    if (( AVAILABLE_GB >= REQUIRED_DISK_SPACE_GB )); then
        log_success "Sufficient disk space: ${AVAILABLE_GB}GB available (required: ${REQUIRED_DISK_SPACE_GB}GB)"
    else
        log_error "Insufficient disk space: ${AVAILABLE_GB}GB available (required: ${REQUIRED_DISK_SPACE_GB}GB)"
    fi
}

check_required_files() {
    log_info "Checking required files..."
    REQUIRED_FILES=(
        "Dockerfile"
        "requirements.txt"
        "backend/app/main.py"
        "alembic.ini"
        "healthcheck.sh"
    )
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [ -f "$file" ]; then
            log_success "Found: $file"
        else
            log_error "Missing: $file"
        fi
    done
}

check_environment_variables() {
    log_info "Checking environment variables..."
    
    # Check if .env file exists
    if [ -f ".env" ]; then
        log_warning ".env file found - ensure it's not committed to version control"
    fi
    
    # Check critical environment variables
    CRITICAL_VARS=(
        "GOOGLE_CLOUD_PROJECT"
    )
    
    for var in "${CRITICAL_VARS[@]}"; do
        if [ -n "${!var:-}" ]; then
            log_success "$var is set"
        else
            log_warning "$var is not set (will use defaults or Secret Manager)"
        fi
    done
}

check_gcp_apis() {
    log_info "Checking Google Cloud APIs..."
    REQUIRED_APIS=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "sqladmin.googleapis.com"
        "redis.googleapis.com"
        "secretmanager.googleapis.com"
        "aiplatform.googleapis.com"
    )
    
    if command -v gcloud &> /dev/null && [ "$ERRORS" -eq 0 ]; then
        for api in "${REQUIRED_APIS[@]}"; do
            if gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
                log_success "API enabled: $api"
            else
                log_warning "API not enabled: $api (will be enabled during deployment)"
            fi
        done
    else
        log_warning "Skipping API check due to previous errors"
    fi
}

check_secrets() {
    log_info "Checking Google Secret Manager secrets..."
    
    if command -v gcloud &> /dev/null && [ "$ERRORS" -eq 0 ]; then
        # List of expected secrets
        EXPECTED_SECRETS=(
            "JWT_SECRET_KEY-production"
            "SECRET_KEY-production"
            "DATABASE_URL-production"
        )
        
        for secret in "${EXPECTED_SECRETS[@]}"; do
            if gcloud secrets describe "$secret" --project="$PROJECT_ID" &> /dev/null; then
                log_success "Secret exists: $secret"
            else
                log_warning "Secret not found: $secret (will need to be created)"
            fi
        done
    else
        log_warning "Skipping secrets check due to previous errors"
    fi
}

check_docker_build() {
    log_info "Testing Docker build..."
    
    if command -v docker &> /dev/null && [ "$ERRORS" -eq 0 ]; then
        # Try a test build with minimal layers
        if docker build --target builder -t test-build -f Dockerfile . &> /dev/null; then
            log_success "Docker build test passed"
            docker rmi test-build &> /dev/null || true
        else
            log_error "Docker build test failed"
        fi
    else
        log_warning "Skipping Docker build test due to previous errors"
    fi
}

check_database_migrations() {
    log_info "Checking database migrations..."
    
    if [ -d "alembic/versions" ]; then
        MIGRATION_COUNT=$(find alembic/versions -name "*.py" -not -name "__pycache__" | grep -v "__pycache__" | wc -l)
        if [ "$MIGRATION_COUNT" -gt 0 ]; then
            log_success "Found $MIGRATION_COUNT migration files"
        else
            log_warning "No migration files found"
        fi
    else
        log_error "Migrations directory not found: alembic/versions"
    fi
}

check_python_syntax() {
    log_info "Checking Python syntax..."
    
    if command -v python3 &> /dev/null; then
        ERROR_COUNT=0
        while IFS= read -r -d '' file; do
            if ! python3 -m py_compile "$file" 2>/dev/null; then
                log_error "Syntax error in: $file"
                ((ERROR_COUNT++))
            fi
        done < <(find backend -name "*.py" -type f -print0)
        
        if [ "$ERROR_COUNT" -eq 0 ]; then
            log_success "All Python files have valid syntax"
        fi
    else
        log_warning "Skipping Python syntax check - Python not available"
    fi
}

check_security() {
    log_info "Running security checks..."
    
    # Check for hardcoded secrets
    if grep -r "SECRET\|PASSWORD\|API_KEY" backend/ --include="*.py" | grep -v "os.environ\|getenv\|Secret" | grep "=" | grep -E "(\"|\').+(\"|\')"; then
        log_error "Potential hardcoded secrets found!"
    else
        log_success "No obvious hardcoded secrets found"
    fi
    
    # Check for debug mode
    if grep -r "DEBUG\s*=\s*True" backend/ --include="*.py"; then
        log_warning "DEBUG mode enabled in some files"
    else
        log_success "DEBUG mode not hardcoded to True"
    fi
}

run_unit_tests() {
    log_info "Running critical unit tests..."
    
    if command -v python3 &> /dev/null && [ -f "requirements.txt" ]; then
        # Check if pytest is available
        if python3 -m pytest --version &> /dev/null; then
            # Run only critical tests
            if python3 -m pytest tests/unit/test_auth.py tests/unit/test_security.py -v --tb=short &> /dev/null; then
                log_success "Critical unit tests passed"
            else
                log_error "Critical unit tests failed"
            fi
        else
            log_warning "pytest not available - skipping unit tests"
        fi
    else
        log_warning "Skipping unit tests - requirements not met"
    fi
}

# Generate summary report
generate_report() {
    echo
    echo "===== PRE-DEPLOYMENT VALIDATION SUMMARY ====="
    echo
    
    if [ "$ERRORS" -eq 0 ]; then
        echo -e "${GREEN}Status: READY FOR DEPLOYMENT${NC}"
    else
        echo -e "${RED}Status: NOT READY FOR DEPLOYMENT${NC}"
    fi
    
    echo
    echo "Errors: $ERRORS"
    echo "Warnings: $WARNINGS"
    echo
    
    if [ "$ERRORS" -gt 0 ]; then
        echo -e "${RED}Please fix all errors before proceeding with deployment.${NC}"
        exit 1
    elif [ "$WARNINGS" -gt 0 ]; then
        echo -e "${YELLOW}Warnings detected. Review them before proceeding.${NC}"
    else
        echo -e "${GREEN}All checks passed! Ready for deployment.${NC}"
    fi
    
    # Save report
    REPORT_FILE="agent_taskforce/reports/pre_deploy_check_$(date +%Y%m%d_%H%M%S).txt"
    mkdir -p "$(dirname "$REPORT_FILE")"
    {
        echo "Pre-deployment Validation Report"
        echo "Generated: $(date)"
        echo "Project: $PROJECT_ID"
        echo "Region: $REGION"
        echo ""
        echo "Results:"
        echo "- Errors: $ERRORS"
        echo "- Warnings: $WARNINGS"
        echo ""
        echo "Status: $([ "$ERRORS" -eq 0 ] && echo "PASSED" || echo "FAILED")"
    } > "$REPORT_FILE"
    
    echo
    echo "Report saved to: $REPORT_FILE"
}

# Main execution
main() {
    echo "===== ROADTRIP PRE-DEPLOYMENT VALIDATION ====="
    echo "Project: $PROJECT_ID"
    echo "Region: $REGION"
    echo "Timestamp: $(date)"
    echo
    
    # Run all checks
    check_python_version
    check_docker
    check_gcloud
    check_terraform
    check_disk_space
    check_required_files
    check_environment_variables
    check_gcp_apis
    check_secrets
    check_docker_build
    check_database_migrations
    check_python_syntax
    check_security
    run_unit_tests
    
    # Generate final report
    generate_report
}

# Execute main function
main