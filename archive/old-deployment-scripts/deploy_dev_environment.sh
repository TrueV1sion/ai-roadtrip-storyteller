#!/bin/bash
#
# AI Road Trip Storyteller - Development Environment Deployment Script
# This script automates the deployment of a development environment on Google Cloud
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
REGION=${REGION:-"us-central1"}
ZONE=${ZONE:-"us-central1-a"}
PROJECT_PREFIX=${PROJECT_PREFIX:-"roadtrip-dev"}

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
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        warning "Docker not found. Container builds will use Cloud Build."
    fi
}

create_project() {
    log "Creating Google Cloud project..."
    
    # Generate unique project ID
    PROJECT_ID="${PROJECT_PREFIX}-$(date +%s)"
    
    # Check if billing account is set
    BILLING_ACCOUNT=$(gcloud beta billing accounts list --filter="open=true" --format="value(name)" --limit=1)
    if [[ -z "$BILLING_ACCOUNT" ]]; then
        error "No active billing account found. Please set up billing first."
    fi
    
    # Create project
    gcloud projects create $PROJECT_ID --name="Road Trip Dev" || error "Failed to create project"
    
    # Link billing
    gcloud beta billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT
    
    # Set as default
    gcloud config set project $PROJECT_ID
    
    export PROJECT_ID
    log "Created project: $PROJECT_ID"
}

enable_apis() {
    log "Enabling required APIs..."
    
    APIS=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "secretmanager.googleapis.com"
        "sqladmin.googleapis.com"
        "redis.googleapis.com"
        "storage-component.googleapis.com"
        "aiplatform.googleapis.com"
        "language.googleapis.com"
        "texttospeech.googleapis.com"
        "speech.googleapis.com"
        "translate.googleapis.com"
        "maps-backend.googleapis.com"
        "containerregistry.googleapis.com"
        "servicenetworking.googleapis.com"
        "compute.googleapis.com"
        "cloudscheduler.googleapis.com"
    )
    
    for api in "${APIS[@]}"; do
        log "Enabling $api..."
        gcloud services enable $api
    done
}

setup_iam() {
    log "Setting up IAM and service account..."
    
    # Create service account
    SA_NAME="roadtrip-api-sa"
    SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    gcloud iam service-accounts create $SA_NAME \
        --display-name="Road Trip API Service Account"
    
    # Grant roles
    ROLES=(
        "roles/cloudsql.client"
        "roles/secretmanager.secretAccessor"
        "roles/storage.objectAdmin"
        "roles/logging.logWriter"
        "roles/monitoring.metricWriter"
        "roles/cloudtrace.agent"
        "roles/redis.editor"
        "roles/cloudtexttospeech.client"
        "roles/aiplatform.user"
    )
    
    for role in "${ROLES[@]}"; do
        log "Granting $role..."
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:${SA_EMAIL}" \
            --role="$role" \
            --quiet
    done
    
    export SA_EMAIL
}

setup_networking() {
    log "Setting up VPC networking..."
    
    # Create VPC
    gcloud compute networks create roadtrip-vpc \
        --subnet-mode=custom \
        --bgp-routing-mode=regional
    
    # Create subnet
    gcloud compute networks subnets create roadtrip-subnet \
        --network=roadtrip-vpc \
        --region=$REGION \
        --range=10.0.0.0/24
    
    # Reserve IP range for VPC peering
    gcloud compute addresses create google-managed-services-roadtrip-vpc \
        --global \
        --purpose=VPC_PEERING \
        --prefix-length=16 \
        --network=roadtrip-vpc
    
    # Create VPC peering
    gcloud services vpc-peerings connect \
        --service=servicenetworking.googleapis.com \
        --ranges=google-managed-services-roadtrip-vpc \
        --network=roadtrip-vpc
    
    # Create VPC connector
    gcloud compute networks vpc-access connectors create roadtrip-connector \
        --region=$REGION \
        --subnet=roadtrip-subnet \
        --subnet-project=$PROJECT_ID \
        --min-instances=2 \
        --max-instances=10 \
        --machine-type=e2-micro
}

create_database() {
    log "Creating Cloud SQL database..."
    
    # Generate password
    DB_PASSWORD=$(openssl rand -base64 32)
    
    # Create instance
    gcloud sql instances create roadtrip-db-dev \
        --database-version=POSTGRES_15 \
        --tier=db-f1-micro \
        --region=$REGION \
        --network=projects/$PROJECT_ID/global/networks/roadtrip-vpc \
        --no-assign-ip \
        --backup-start-time=03:00
    
    # Create database
    gcloud sql databases create roadtrip --instance=roadtrip-db-dev
    
    # Create user
    gcloud sql users create roadtrip \
        --instance=roadtrip-db-dev \
        --password=$DB_PASSWORD
    
    export DB_PASSWORD
    export DB_CONNECTION_NAME="${PROJECT_ID}:${REGION}:roadtrip-db-dev"
}

create_redis() {
    log "Creating Redis instance..."
    
    gcloud redis instances create roadtrip-redis-dev \
        --size=1 \
        --region=$REGION \
        --network=roadtrip-vpc \
        --redis-version=redis_7_0 \
        --async
    
    # Note: Redis creation is async, we'll get the host later
}

create_storage() {
    log "Creating storage buckets..."
    
    # Create buckets
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://${PROJECT_ID}-roadtrip-assets/
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://${PROJECT_ID}-roadtrip-tts-cache/
    
    # Set permissions
    gsutil iam ch serviceAccount:${SA_EMAIL}:objectAdmin gs://${PROJECT_ID}-roadtrip-assets/
    gsutil iam ch serviceAccount:${SA_EMAIL}:objectAdmin gs://${PROJECT_ID}-roadtrip-tts-cache/
}

create_secrets() {
    log "Creating secrets in Secret Manager..."
    
    # Wait for Redis to be ready and get host
    log "Waiting for Redis instance to be ready..."
    gcloud redis instances describe roadtrip-redis-dev \
        --region=$REGION \
        --format="get(state)" | grep -q "READY" || sleep 30
    
    REDIS_HOST=$(gcloud redis instances describe roadtrip-redis-dev \
        --region=$REGION \
        --format="get(host)")
    
    # Create secrets
    echo -n "postgresql://roadtrip:${DB_PASSWORD}@/roadtrip?host=/cloudsql/${DB_CONNECTION_NAME}" | \
        gcloud secrets create roadtrip-database-url --data-file=-
    
    echo -n "redis://${REDIS_HOST}:6379/0" | \
        gcloud secrets create roadtrip-redis-url --data-file=-
    
    echo -n "$(openssl rand -base64 64)" | \
        gcloud secrets create roadtrip-jwt-secret --data-file=-
    
    echo -n "$(openssl rand -base64 32)" | \
        gcloud secrets create roadtrip-secret-key --data-file=-
    
    echo -n "$(openssl rand -base64 32)" | \
        gcloud secrets create roadtrip-encryption-master-key --data-file=-
    
    # Create placeholder secrets for API keys
    echo -n "REPLACE_WITH_ACTUAL_KEY" | \
        gcloud secrets create roadtrip-google-maps-api-key --data-file=-
    
    echo -n "REPLACE_WITH_ACTUAL_KEY" | \
        gcloud secrets create openweather-api-key --data-file=-
    
    echo -n "REPLACE_WITH_ACTUAL_KEY" | \
        gcloud secrets create ticketmaster-api-key --data-file=-
    
    echo -n "REPLACE_WITH_ACTUAL_KEY" | \
        gcloud secrets create recreation-gov-api-key --data-file=-
    
    # Grant access to all secrets
    for secret in $(gcloud secrets list --format="value(name)"); do
        gcloud secrets add-iam-policy-binding $secret \
            --member="serviceAccount:${SA_EMAIL}" \
            --role="roles/secretmanager.secretAccessor" \
            --quiet
    done
}

build_and_deploy() {
    log "Building and deploying application..."
    
    # Get the backend directory path
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    BACKEND_DIR="$(dirname "$SCRIPT_DIR")/backend"
    
    # Build container
    log "Building container image..."
    gcloud builds submit \
        --tag gcr.io/${PROJECT_ID}/roadtrip-api:latest \
        --timeout=20m \
        "$BACKEND_DIR"
    
    # Deploy to Cloud Run
    log "Deploying to Cloud Run..."
    gcloud run deploy roadtrip-api-dev \
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
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe roadtrip-api-dev \
        --region=$REGION \
        --format='value(status.url)')
    
    export SERVICE_URL
}

run_migrations() {
    log "Running database migrations..."
    
    # Create a migration job using Cloud Build
    cat > /tmp/cloudbuild-migrate.yaml << EOF
steps:
- name: 'gcr.io/${PROJECT_ID}/roadtrip-api:latest'
  entrypoint: 'alembic'
  args: ['upgrade', 'head']
  env:
  - 'DATABASE_URL=postgresql://roadtrip:${DB_PASSWORD}@/roadtrip?host=/cloudsql/${DB_CONNECTION_NAME}'
  - 'GOOGLE_CLOUD_PROJECT_ID=${PROJECT_ID}'
options:
  env:
  - 'DATABASE_URL=postgresql://roadtrip:${DB_PASSWORD}@/roadtrip?host=/cloudsql/${DB_CONNECTION_NAME}'
EOF
    
    gcloud builds submit \
        --config=/tmp/cloudbuild-migrate.yaml \
        --no-source
    
    rm /tmp/cloudbuild-migrate.yaml
}

verify_deployment() {
    log "Verifying deployment..."
    
    # Check health endpoint
    if curl -f ${SERVICE_URL}/health > /dev/null 2>&1; then
        log "Health check passed!"
    else
        error "Health check failed!"
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
    echo -e "${YELLOW}IMPORTANT: Update these placeholder secrets with actual API keys:${NC}"
    echo "- roadtrip-google-maps-api-key"
    echo "- openweather-api-key"
    echo "- ticketmaster-api-key"
    echo "- recreation-gov-api-key"
    echo ""
    echo "To update a secret:"
    echo "  echo -n 'YOUR_ACTUAL_API_KEY' | gcloud secrets versions add SECRET_NAME --data-file=-"
    echo ""
    echo "To delete this environment:"
    echo "  gcloud projects delete $PROJECT_ID"
    echo ""
}

main() {
    log "Starting AI Road Trip Storyteller development environment deployment..."
    
    # Check prerequisites
    check_prerequisites
    
    # Execute deployment steps
    create_project
    enable_apis
    setup_iam
    setup_networking
    create_database
    create_redis
    create_storage
    create_secrets
    build_and_deploy
    run_migrations
    verify_deployment
    
    log "Deployment completed successfully!"
}

# Handle interruption
trap 'error "Deployment interrupted. Project may be partially created: $PROJECT_ID"' INT TERM

# Run main function
main "$@"