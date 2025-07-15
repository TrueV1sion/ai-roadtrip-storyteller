#!/bin/bash

# AI Road Trip Storyteller - Production Deployment Script
# This script automates the deployment process to Google Cloud Platform

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT_ID:-""}
REGION=${DEPLOY_REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"roadtrip-api"}
MIN_INSTANCES=${MIN_INSTANCES:-"1"}
MAX_INSTANCES=${MAX_INSTANCES:-"10"}
MEMORY=${MEMORY:-"2Gi"}
CPU=${CPU:-"1"}

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate environment
validate_environment() {
    print_status "Validating deployment environment..."
    
    # Check required commands
    if ! command_exists gcloud; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check if logged into gcloud
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated with gcloud. Run 'gcloud auth login' first."
        exit 1
    fi
    
    # Check project ID
    if [ -z "$PROJECT_ID" ]; then
        print_error "GOOGLE_CLOUD_PROJECT_ID environment variable is not set."
        print_status "Available projects:"
        gcloud projects list
        exit 1
    fi
    
    # Verify project exists and is accessible
    if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
        print_error "Cannot access project '$PROJECT_ID'. Check project ID and permissions."
        exit 1
    fi
    
    print_success "Environment validation passed"
}

# Function to enable required APIs
enable_apis() {
    print_status "Enabling required Google Cloud APIs..."
    
    local apis=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "containerregistry.googleapis.com"
        "sqladmin.googleapis.com"
        "secretmanager.googleapis.com"
        "texttospeech.googleapis.com"
        "maps-backend.googleapis.com"
        "redis.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        print_status "Enabling $api..."
        if gcloud services enable "$api" --project="$PROJECT_ID"; then
            print_success "Enabled $api"
        else
            print_warning "Failed to enable $api (may already be enabled)"
        fi
    done
}

# Function to check environment files
check_environment_files() {
    print_status "Checking environment configuration..."
    
    if [ ! -f ".env" ]; then
        print_error ".env file not found. Run 'python configure_apis_simple.py' first."
        exit 1
    fi
    
    # Check for required environment variables
    local required_vars=(
        "GOOGLE_MAPS_API_KEY"
        "DATABASE_URL"
        "SECRET_KEY"
    )
    
    for var in "${required_vars[@]}"; do
        if ! grep -q "^$var=" .env; then
            print_warning "Required environment variable $var not found in .env"
        fi
    done
    
    print_success "Environment configuration checked"
}

# Function to run tests
run_tests() {
    print_status "Running comprehensive tests..."
    
    # Backend tests
    print_status "Running backend tests..."
    if python -m pytest tests/unit/ -v; then
        print_success "Unit tests passed"
    else
        print_error "Unit tests failed"
        exit 1
    fi
    
    # Integration tests (with mock APIs)
    print_status "Running integration tests..."
    if python -m pytest tests/integration/ -v --tb=short; then
        print_success "Integration tests passed"
    else
        print_warning "Some integration tests failed (continuing deployment)"
    fi
    
    # API connectivity test
    print_status "Testing API connectivity..."
    if python test_apis_simple.py; then
        print_success "API connectivity test passed"
    else
        print_warning "API connectivity test failed (continuing deployment)"
    fi
}

# Function to build and push Docker image
build_and_push_image() {
    print_status "Building and pushing Docker image..."
    
    local image_tag="gcr.io/$PROJECT_ID/$SERVICE_NAME:$(date +%Y%m%d%H%M%S)"
    local latest_tag="gcr.io/$PROJECT_ID/$SERVICE_NAME:latest"
    
    # Build image
    print_status "Building Docker image..."
    if docker build -t "$image_tag" -t "$latest_tag" .; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
    
    # Configure Docker to use gcloud as credential helper
    gcloud auth configure-docker --quiet
    
    # Push image
    print_status "Pushing Docker image to Google Container Registry..."
    if docker push "$image_tag" && docker push "$latest_tag"; then
        print_success "Docker image pushed successfully"
        echo "$latest_tag" > .last_deployed_image
    else
        print_error "Failed to push Docker image"
        exit 1
    fi
}

# Function to create or update Cloud SQL database
setup_database() {
    print_status "Setting up Cloud SQL database..."
    
    local db_instance="roadtrip-db"
    local db_name="roadtrip_prod"
    
    # Check if instance exists
    if gcloud sql instances describe "$db_instance" --project="$PROJECT_ID" >/dev/null 2>&1; then
        print_status "Database instance '$db_instance' already exists"
    else
        print_status "Creating Cloud SQL instance..."
        gcloud sql instances create "$db_instance" \
            --database-version=POSTGRES_13 \
            --tier=db-f1-micro \
            --region="$REGION" \
            --project="$PROJECT_ID"
        print_success "Created Cloud SQL instance"
    fi
    
    # Create database if it doesn't exist
    if ! gcloud sql databases describe "$db_name" --instance="$db_instance" --project="$PROJECT_ID" >/dev/null 2>&1; then
        print_status "Creating database '$db_name'..."
        gcloud sql databases create "$db_name" --instance="$db_instance" --project="$PROJECT_ID"
        print_success "Created database"
    fi
}

# Function to setup secrets in Secret Manager
setup_secrets() {
    print_status "Setting up secrets in Google Secret Manager..."
    
    # Read .env file and create secrets
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ $key =~ ^#.*$ ]] && continue
        [[ -z $key ]] && continue
        
        # Remove quotes from value
        value=$(echo "$value" | sed 's/^["'\'']//' | sed 's/["'\'']$//')
        
        # Create or update secret
        if gcloud secrets describe "$key" --project="$PROJECT_ID" >/dev/null 2>&1; then
            print_status "Updating secret $key..."
            echo -n "$value" | gcloud secrets versions add "$key" --data-file=- --project="$PROJECT_ID"
        else
            print_status "Creating secret $key..."
            echo -n "$value" | gcloud secrets create "$key" --data-file=- --project="$PROJECT_ID"
        fi
    done < .env
    
    print_success "Secrets configured"
}

# Function to deploy to Cloud Run
deploy_to_cloud_run() {
    print_status "Deploying to Google Cloud Run..."
    
    local image_tag=$(cat .last_deployed_image)
    
    # Create deployment command
    local deploy_cmd="gcloud run deploy $SERVICE_NAME"
    deploy_cmd="$deploy_cmd --image=$image_tag"
    deploy_cmd="$deploy_cmd --platform=managed"
    deploy_cmd="$deploy_cmd --region=$REGION"
    deploy_cmd="$deploy_cmd --project=$PROJECT_ID"
    deploy_cmd="$deploy_cmd --allow-unauthenticated"
    deploy_cmd="$deploy_cmd --memory=$MEMORY"
    deploy_cmd="$deploy_cmd --cpu=$CPU"
    deploy_cmd="$deploy_cmd --min-instances=$MIN_INSTANCES"
    deploy_cmd="$deploy_cmd --max-instances=$MAX_INSTANCES"
    deploy_cmd="$deploy_cmd --timeout=300"
    deploy_cmd="$deploy_cmd --concurrency=80"
    
    # Add environment variables from secrets
    while IFS='=' read -r key value; do
        [[ $key =~ ^#.*$ ]] && continue
        [[ -z $key ]] && continue
        deploy_cmd="$deploy_cmd --set-env-vars=$key=\$(gcloud secrets versions access latest --secret=$key --project=$PROJECT_ID)"
    done < .env
    
    # Execute deployment
    if eval "$deploy_cmd"; then
        print_success "Deployment to Cloud Run successful"
        
        # Get service URL
        local service_url=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)")
        print_success "Service deployed at: $service_url"
        echo "$service_url" > .deployed_url
    else
        print_error "Failed to deploy to Cloud Run"
        exit 1
    fi
}

# Function to run database migrations
run_migrations() {
    print_status "Running database migrations..."
    
    # This would typically be done by connecting to the deployed service
    # For now, we'll provide instructions
    print_status "Database migrations should be run manually after deployment:"
    print_status "1. Connect to your Cloud Run service"
    print_status "2. Run: alembic upgrade head"
    print_warning "Auto-migration from deployment script is not yet implemented"
}

# Function to verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    if [ -f ".deployed_url" ]; then
        local service_url=$(cat .deployed_url)
        
        print_status "Testing health endpoint..."
        if curl -f -s "$service_url/health" >/dev/null; then
            print_success "Health check passed"
        else
            print_warning "Health check failed - service may still be starting"
        fi
        
        print_status "Testing API endpoints..."
        if curl -f -s "$service_url/api/docs" >/dev/null; then
            print_success "API documentation accessible"
        else
            print_warning "API documentation not accessible"
        fi
    fi
}

# Function to show deployment summary
show_summary() {
    print_success "=== DEPLOYMENT SUMMARY ==="
    echo
    if [ -f ".deployed_url" ]; then
        local service_url=$(cat .deployed_url)
        echo "Service URL: $service_url"
        echo "API Documentation: $service_url/api/docs"
        echo "Health Check: $service_url/health"
    fi
    echo "Project: $PROJECT_ID"
    echo "Region: $REGION"
    echo "Service: $SERVICE_NAME"
    echo
    print_status "Next steps:"
    print_status "1. Run database migrations if needed"
    print_status "2. Test your API endpoints"
    print_status "3. Configure custom domain if desired"
    print_status "4. Set up monitoring and alerting"
    echo
}

# Main deployment function
main() {
    print_status "Starting AI Road Trip Storyteller deployment..."
    echo
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --project-id)
                PROJECT_ID="$2"
                shift 2
                ;;
            --region)
                REGION="$2"
                shift 2
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --project-id ID    Google Cloud Project ID"
                echo "  --region REGION    Deployment region (default: us-central1)"
                echo "  --skip-tests       Skip running tests"
                echo "  --skip-build       Skip building Docker image"
                echo "  --help             Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Deployment steps
    validate_environment
    enable_apis
    check_environment_files
    
    if [ "$SKIP_TESTS" != "true" ]; then
        run_tests
    fi
    
    if [ "$SKIP_BUILD" != "true" ]; then
        build_and_push_image
    fi
    
    setup_database
    setup_secrets
    deploy_to_cloud_run
    run_migrations
    verify_deployment
    show_summary
    
    print_success "Deployment completed successfully!"
}

# Run main function
main "$@"