#!/bin/bash
#
# AI Road Trip Storyteller - Deploy to Existing Project
# This script deploys to an existing Google Cloud project with billing and APIs already configured
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
REGION=${REGION:-"us-central1"}
ZONE=${ZONE:-"us-central1-a"}

# Functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
    exit 1
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        error "gcloud CLI not found. Please install Google Cloud SDK."
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        error "Not authenticated with gcloud. Run 'gcloud auth login'"
    fi
    
    # Check if project is set
    PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
    if [[ -z "$PROJECT_ID" ]]; then
        error "No project set. Run: gcloud config set project YOUR_PROJECT_ID"
    fi
    
    log "Using existing project: $PROJECT_ID"
}

# Check what resources already exist
check_existing_resources() {
    log "Checking existing resources..."
    
    # Check for existing Cloud SQL
    if gcloud sql instances list --filter="name:roadtrip-db*" --format="value(name)" | grep -q .; then
        warning "Found existing Cloud SQL instances. Will use existing database."
        DB_EXISTS=true
        DB_INSTANCE=$(gcloud sql instances list --filter="name:roadtrip-db*" --format="value(name)" | head -n1)
    else
        DB_EXISTS=false
    fi
    
    # Check for existing Redis
    if gcloud redis instances list --region=$REGION --filter="name:roadtrip-redis*" --format="value(name)" 2>/dev/null | grep -q .; then
        warning "Found existing Redis instance. Will use existing Redis."
        REDIS_EXISTS=true
        REDIS_INSTANCE=$(gcloud redis instances list --region=$REGION --filter="name:roadtrip-redis*" --format="value(name)" | head -n1)
    else
        REDIS_EXISTS=false
    fi
    
    # Check for VPC
    if gcloud compute networks list --filter="name:roadtrip-vpc" --format="value(name)" | grep -q .; then
        info "Found existing VPC network."
        VPC_EXISTS=true
    else
        VPC_EXISTS=false
    fi
}

# Enable any missing APIs
enable_apis() {
    log "Checking and enabling required APIs..."
    
    REQUIRED_APIS=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "secretmanager.googleapis.com"
        "sqladmin.googleapis.com"
        "redis.googleapis.com"
        "storage-component.googleapis.com"
        "servicenetworking.googleapis.com"
        "compute.googleapis.com"
    )
    
    for api in "${REQUIRED_APIS[@]}"; do
        if ! gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q "$api"; then
            log "Enabling $api..."
            gcloud services enable $api
        else
            info "$api already enabled"
        fi
    done
}

# Check or create service account
setup_service_account() {
    log "Checking service account..."
    
    SA_NAME="roadtrip-api-sa"
    SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Check if service account exists
    if ! gcloud iam service-accounts describe $SA_EMAIL &>/dev/null; then
        log "Creating service account..."
        gcloud iam service-accounts create $SA_NAME \
            --display-name="Road Trip API Service Account"
    else
        info "Service account already exists"
    fi
    
    # Ensure necessary roles
    ROLES=(
        "roles/cloudsql.client"
        "roles/secretmanager.secretAccessor"
        "roles/storage.objectAdmin"
        "roles/run.invoker"
    )
    
    for role in "${ROLES[@]}"; do
        log "Ensuring $role..."
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:${SA_EMAIL}" \
            --role="$role" \
            --quiet 2>/dev/null || true
    done
    
    export SA_EMAIL
}

# Setup networking if needed
setup_networking() {
    if [[ "$VPC_EXISTS" == "false" ]]; then
        log "Creating VPC network..."
        
        # Create VPC
        gcloud compute networks create roadtrip-vpc \
            --subnet-mode=custom \
            --bgp-routing-mode=regional
        
        # Create subnet
        gcloud compute networks subnets create roadtrip-subnet \
            --network=roadtrip-vpc \
            --region=$REGION \
            --range=10.0.0.0/24
    fi
    
    # Check for VPC connector
    if ! gcloud compute networks vpc-access connectors describe roadtrip-connector --region=$REGION &>/dev/null; then
        log "Creating VPC connector..."
        gcloud compute networks vpc-access connectors create roadtrip-connector \
            --region=$REGION \
            --subnet=roadtrip-subnet \
            --subnet-project=$PROJECT_ID \
            --min-instances=2 \
            --max-instances=10 \
            --machine-type=e2-micro
    else
        info "VPC connector already exists"
    fi
}

# Setup or verify database
setup_database() {
    if [[ "$DB_EXISTS" == "false" ]]; then
        log "Creating Cloud SQL instance..."
        
        # Generate password
        DB_PASSWORD=$(openssl rand -base64 32)
        
        # Create instance
        gcloud sql instances create roadtrip-db \
            --database-version=POSTGRES_15 \
            --tier=db-f1-micro \
            --region=$REGION \
            --network=projects/$PROJECT_ID/global/networks/default \
            --no-assign-ip \
            --backup-start-time=03:00
        
        # Create database
        gcloud sql databases create roadtrip --instance=roadtrip-db
        
        # Create user
        gcloud sql users create roadtrip \
            --instance=roadtrip-db \
            --password=$DB_PASSWORD
        
        DB_INSTANCE="roadtrip-db"
        
        # Store password in secret manager
        echo -n "postgresql://roadtrip:${DB_PASSWORD}@/roadtrip?host=/cloudsql/${PROJECT_ID}:${REGION}:${DB_INSTANCE}" | \
            gcloud secrets create roadtrip-database-url --data-file=- 2>/dev/null || \
            echo -n "postgresql://roadtrip:${DB_PASSWORD}@/roadtrip?host=/cloudsql/${PROJECT_ID}:${REGION}:${DB_INSTANCE}" | \
            gcloud secrets versions add roadtrip-database-url --data-file=-
    else
        log "Using existing database: $DB_INSTANCE"
    fi
    
    export DB_CONNECTION_NAME="${PROJECT_ID}:${REGION}:${DB_INSTANCE}"
}

# Setup or verify Redis
setup_redis() {
    if [[ "$REDIS_EXISTS" == "false" ]]; then
        log "Creating Redis instance..."
        
        gcloud redis instances create roadtrip-redis \
            --size=1 \
            --region=$REGION \
            --redis-version=redis_7_0 \
            --async
        
        REDIS_INSTANCE="roadtrip-redis"
    else
        log "Using existing Redis: $REDIS_INSTANCE"
    fi
}

# Setup storage buckets
setup_storage() {
    log "Checking storage buckets..."
    
    # Check and create buckets if needed
    for bucket in "${PROJECT_ID}-roadtrip-assets" "${PROJECT_ID}-roadtrip-tts-cache"; do
        if ! gsutil ls gs://$bucket &>/dev/null; then
            log "Creating bucket: $bucket"
            gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$bucket/
        else
            info "Bucket already exists: $bucket"
        fi
        
        # Set permissions
        gsutil iam ch serviceAccount:${SA_EMAIL}:objectAdmin gs://$bucket/ 2>/dev/null || true
    done
}

# Verify secrets exist
verify_secrets() {
    log "Verifying secrets..."
    
    REQUIRED_SECRETS=(
        "roadtrip-database-url"
        "roadtrip-jwt-secret"
        "roadtrip-secret-key"
    )
    
    for secret in "${REQUIRED_SECRETS[@]}"; do
        if ! gcloud secrets describe $secret &>/dev/null; then
            warning "Creating missing secret: $secret"
            
            case $secret in
                "roadtrip-jwt-secret")
                    echo -n "$(openssl rand -base64 64)" | gcloud secrets create $secret --data-file=-
                    ;;
                "roadtrip-secret-key")
                    echo -n "$(openssl rand -base64 32)" | gcloud secrets create $secret --data-file=-
                    ;;
            esac
        else
            info "Secret exists: $secret"
        fi
        
        # Grant access
        gcloud secrets add-iam-policy-binding $secret \
            --member="serviceAccount:${SA_EMAIL}" \
            --role="roles/secretmanager.secretAccessor" \
            --quiet 2>/dev/null || true
    done
    
    # Check for Redis URL
    if [[ "$REDIS_EXISTS" == "true" ]]; then
        REDIS_HOST=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="get(host)" 2>/dev/null || echo "")
        if [[ -n "$REDIS_HOST" ]]; then
            echo -n "redis://${REDIS_HOST}:6379/0" | \
                gcloud secrets create roadtrip-redis-url --data-file=- 2>/dev/null || \
                echo -n "redis://${REDIS_HOST}:6379/0" | \
                gcloud secrets versions add roadtrip-redis-url --data-file=-
        fi
    fi
}

# Build and deploy application
deploy_application() {
    log "Building and deploying application..."
    
    # Get the backend directory path
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    BACKEND_DIR="$(dirname "$SCRIPT_DIR")/backend"
    
    # Check if Cloud Run service exists
    SERVICE_EXISTS=false
    if gcloud run services describe roadtrip-api --region=$REGION &>/dev/null; then
        SERVICE_EXISTS=true
        warning "Cloud Run service 'roadtrip-api' already exists. Will update it."
    fi
    
    # Build container
    log "Building container image..."
    gcloud builds submit \
        --tag gcr.io/${PROJECT_ID}/roadtrip-api:latest \
        --timeout=20m \
        "$BACKEND_DIR"
    
    # Deploy or update Cloud Run
    if [[ "$SERVICE_EXISTS" == "true" ]]; then
        log "Updating existing Cloud Run service..."
        gcloud run deploy roadtrip-api \
            --image gcr.io/${PROJECT_ID}/roadtrip-api:latest \
            --region $REGION \
            --platform managed \
            --service-account=${SA_EMAIL} \
            --set-env-vars="GOOGLE_CLOUD_PROJECT_ID=${PROJECT_ID}" \
            --set-env-vars="ENVIRONMENT=development" \
            --set-env-vars="VERTEX_AI_LOCATION=${REGION}" \
            --set-env-vars="STORAGE_BUCKET=${PROJECT_ID}-roadtrip-assets" \
            --set-env-vars="TTS_CACHE_BUCKET=${PROJECT_ID}-roadtrip-tts-cache"
    else
        log "Creating new Cloud Run service..."
        gcloud run deploy roadtrip-api \
            --image gcr.io/${PROJECT_ID}/roadtrip-api:latest \
            --region $REGION \
            --platform managed \
            --allow-unauthenticated \
            --memory 2Gi \
            --cpu 2 \
            --min-instances 0 \
            --max-instances 10 \
            --service-account=${SA_EMAIL} \
            --vpc-connector=projects/${PROJECT_ID}/locations/${REGION}/connectors/roadtrip-connector \
            --vpc-egress=private-ranges-only \
            --set-env-vars="GOOGLE_CLOUD_PROJECT_ID=${PROJECT_ID}" \
            --set-env-vars="ENVIRONMENT=development" \
            --set-env-vars="VERTEX_AI_LOCATION=${REGION}" \
            --set-env-vars="STORAGE_BUCKET=${PROJECT_ID}-roadtrip-assets" \
            --set-env-vars="TTS_CACHE_BUCKET=${PROJECT_ID}-roadtrip-tts-cache"
    fi
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe roadtrip-api \
        --region=$REGION \
        --format='value(status.url)')
    
    export SERVICE_URL
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    # Get database URL from secret
    DB_URL=$(gcloud secrets versions access latest --secret=roadtrip-database-url 2>/dev/null || echo "")
    
    if [[ -z "$DB_URL" ]]; then
        warning "Could not retrieve database URL. Skipping migrations."
        return
    fi
    
    # Create a migration job
    cat > /tmp/cloudbuild-migrate.yaml << EOF
steps:
- name: 'gcr.io/${PROJECT_ID}/roadtrip-api:latest'
  entrypoint: 'alembic'
  args: ['upgrade', 'head']
  env:
  - 'DATABASE_URL=${DB_URL}'
  - 'GOOGLE_CLOUD_PROJECT_ID=${PROJECT_ID}'
EOF
    
    gcloud builds submit \
        --config=/tmp/cloudbuild-migrate.yaml \
        --no-source
    
    rm /tmp/cloudbuild-migrate.yaml
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Check health endpoint
    if curl -f ${SERVICE_URL}/health > /dev/null 2>&1; then
        log "Health check passed!"
    else
        warning "Health check failed. Service may still be starting up."
    fi
    
    # Display summary
    echo ""
    echo "========================================="
    echo -e "${GREEN}Deployment Complete!${NC}"
    echo "========================================="
    echo ""
    echo "Project ID: $PROJECT_ID"
    echo "Service URL: $SERVICE_URL"
    echo "API Documentation: ${SERVICE_URL}/docs"
    echo ""
    echo -e "${YELLOW}Next Steps:${NC}"
    echo "1. Check your API keys are configured:"
    echo "   ./scripts/setup_api_keys.sh"
    echo ""
    echo "2. Test the API:"
    echo "   curl ${SERVICE_URL}/health"
    echo ""
    echo "3. View logs:"
    echo "   gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=roadtrip-api\" --limit=50"
    echo ""
}

# Main execution
main() {
    log "Starting deployment to existing project..."
    
    check_prerequisites
    check_existing_resources
    enable_apis
    setup_service_account
    setup_networking
    setup_database
    setup_redis
    setup_storage
    verify_secrets
    deploy_application
    run_migrations
    verify_deployment
    
    log "Deployment completed!"
}

# Handle interruption
trap 'error "Deployment interrupted."' INT TERM

# Run main function
main "$@"