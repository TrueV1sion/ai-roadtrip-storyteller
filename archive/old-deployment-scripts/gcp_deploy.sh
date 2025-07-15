#!/bin/bash

# AI Road Trip Storyteller - Google Cloud Platform Deployment Script
# This script deploys the application to GCP using Cloud Run

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration from environment
PROJECT_ID=${GOOGLE_CLOUD_PROJECT_ID:-"roadtrip-460720"}
REGION=${DEPLOY_REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"roadtrip-api"}
MIN_INSTANCES=${MIN_INSTANCES:-"2"}
MAX_INSTANCES=${MAX_INSTANCES:-"20"}
MEMORY=${MEMORY:-"2Gi"}
CPU=${CPU:-"2"}

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
        print_status "Visit: https://cloud.google.com/sdk/docs/install"
        exit 1
    fi
    
    if ! command_exists docker; then
        print_error "Docker is not installed. Please install it first."
        print_status "Visit: https://docs.docker.com/get-docker/"
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
        exit 1
    fi
    
    # Set project
    print_status "Setting GCP project to $PROJECT_ID..."
    gcloud config set project "$PROJECT_ID"
    
    print_success "Environment validation passed"
}

# Function to enable required APIs
enable_apis() {
    print_status "Enabling required Google Cloud APIs..."
    
    local apis=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "artifactregistry.googleapis.com"
        "sqladmin.googleapis.com"
        "secretmanager.googleapis.com"
        "texttospeech.googleapis.com"
        "speech.googleapis.com"
        "maps-backend.googleapis.com"
        "redis.googleapis.com"
        "monitoring.googleapis.com"
        "logging.googleapis.com"
        "cloudresourcemanager.googleapis.com"
        "iam.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        print_status "Enabling $api..."
        if gcloud services enable "$api" --project="$PROJECT_ID" 2>/dev/null; then
            print_success "Enabled $api"
        else
            print_warning "$api may already be enabled or requires billing"
        fi
    done
}

# Function to create Artifact Registry repository
create_artifact_registry() {
    print_status "Setting up Artifact Registry..."
    
    local repo_name="roadtrip-images"
    
    # Check if repository exists
    if gcloud artifacts repositories describe "$repo_name" --location="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
        print_status "Artifact Registry repository already exists"
    else
        print_status "Creating Artifact Registry repository..."
        gcloud artifacts repositories create "$repo_name" \
            --repository-format=docker \
            --location="$REGION" \
            --description="Docker images for Road Trip Storyteller" \
            --project="$PROJECT_ID"
        print_success "Created Artifact Registry repository"
    fi
    
    # Configure Docker authentication
    print_status "Configuring Docker authentication..."
    gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet
}

# Function to build and push Docker image
build_and_push_image() {
    print_status "Building Docker image..."
    
    local image_tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/roadtrip-images/${SERVICE_NAME}:$(date +%Y%m%d%H%M%S)"
    local latest_tag="${REGION}-docker.pkg.dev/${PROJECT_ID}/roadtrip-images/${SERVICE_NAME}:latest"
    
    # Build image
    print_status "Building Docker image..."
    if docker build -t "$image_tag" -t "$latest_tag" .; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
    
    # Push image
    print_status "Pushing Docker image to Artifact Registry..."
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
    
    local db_instance="roadtrip-db-prod"
    local db_name="roadtrip_production"
    
    # Check if instance exists
    if gcloud sql instances describe "$db_instance" --project="$PROJECT_ID" >/dev/null 2>&1; then
        print_status "Database instance '$db_instance' already exists"
    else
        print_status "Creating Cloud SQL instance (this may take several minutes)..."
        gcloud sql instances create "$db_instance" \
            --database-version=POSTGRES_13 \
            --tier=db-n1-standard-2 \
            --region="$REGION" \
            --network=default \
            --backup-start-time=03:00 \
            --backup-location="$REGION" \
            --retained-backups-count=7 \
            --maintenance-window-day=SUN \
            --maintenance-window-hour=4 \
            --maintenance-window-duration=2 \
            --high-availability \
            --project="$PROJECT_ID"
        print_success "Created Cloud SQL instance"
    fi
    
    # Create database if it doesn't exist
    if ! gcloud sql databases describe "$db_name" --instance="$db_instance" --project="$PROJECT_ID" >/dev/null 2>&1; then
        print_status "Creating database '$db_name'..."
        gcloud sql databases create "$db_name" --instance="$db_instance" --project="$PROJECT_ID"
        print_success "Created database"
    fi
    
    # Get connection name for the database
    local connection_name=$(gcloud sql instances describe "$db_instance" --project="$PROJECT_ID" --format="value(connectionName)")
    echo "$connection_name" > .cloud_sql_connection
}

# Function to setup Redis instance
setup_redis() {
    print_status "Setting up Redis instance..."
    
    local redis_instance="roadtrip-redis-prod"
    
    # Check if Redis instance exists
    if gcloud redis instances describe "$redis_instance" --region="$REGION" --project="$PROJECT_ID" >/dev/null 2>&1; then
        print_status "Redis instance already exists"
    else
        print_status "Creating Redis instance (this may take several minutes)..."
        gcloud redis instances create "$redis_instance" \
            --size=1 \
            --region="$REGION" \
            --redis-version=redis_6_x \
            --tier=standard \
            --display-name="Road Trip Redis Cache" \
            --project="$PROJECT_ID"
        print_success "Created Redis instance"
    fi
    
    # Get Redis host
    local redis_host=$(gcloud redis instances describe "$redis_instance" --region="$REGION" --project="$PROJECT_ID" --format="value(host)")
    echo "$redis_host" > .redis_host
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
        
        # Skip local development values
        if [[ "$key" == "DATABASE_URL" ]] || [[ "$key" == "REDIS_URL" ]]; then
            continue
        fi
        
        # Create or update secret
        if gcloud secrets describe "$key" --project="$PROJECT_ID" >/dev/null 2>&1; then
            print_status "Updating secret $key..."
            echo -n "$value" | gcloud secrets versions add "$key" --data-file=- --project="$PROJECT_ID"
        else
            print_status "Creating secret $key..."
            echo -n "$value" | gcloud secrets create "$key" --data-file=- --project="$PROJECT_ID"
        fi
    done < .env
    
    # Create production-specific secrets
    if [ -f ".cloud_sql_connection" ]; then
        local connection_name=$(cat .cloud_sql_connection)
        local db_url="postgresql://roadtrip:roadtrip123@/roadtrip_production?host=/cloudsql/${connection_name}"
        echo -n "$db_url" | gcloud secrets create "DATABASE_URL" --data-file=- --project="$PROJECT_ID" 2>/dev/null || \
        echo -n "$db_url" | gcloud secrets versions add "DATABASE_URL" --data-file=- --project="$PROJECT_ID"
    fi
    
    if [ -f ".redis_host" ]; then
        local redis_host=$(cat .redis_host)
        local redis_url="redis://${redis_host}:6379"
        echo -n "$redis_url" | gcloud secrets create "REDIS_URL" --data-file=- --project="$PROJECT_ID" 2>/dev/null || \
        echo -n "$redis_url" | gcloud secrets versions add "REDIS_URL" --data-file=- --project="$PROJECT_ID"
    fi
    
    print_success "Secrets configured"
}

# Function to create service account
setup_service_account() {
    print_status "Setting up service account..."
    
    local sa_name="roadtrip-api-sa"
    local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Create service account if it doesn't exist
    if ! gcloud iam service-accounts describe "$sa_email" --project="$PROJECT_ID" >/dev/null 2>&1; then
        print_status "Creating service account..."
        gcloud iam service-accounts create "$sa_name" \
            --display-name="Road Trip API Service Account" \
            --project="$PROJECT_ID"
    fi
    
    # Grant necessary permissions
    print_status "Granting permissions to service account..."
    local roles=(
        "roles/cloudsql.client"
        "roles/secretmanager.secretAccessor"
        "roles/logging.logWriter"
        "roles/monitoring.metricWriter"
        "roles/cloudtrace.agent"
        "roles/redis.editor"
    )
    
    for role in "${roles[@]}"; do
        gcloud projects add-iam-policy-binding "$PROJECT_ID" \
            --member="serviceAccount:${sa_email}" \
            --role="$role" \
            --condition=None \
            --quiet
    done
    
    print_success "Service account configured"
    echo "$sa_email" > .service_account
}

# Function to deploy to Cloud Run
deploy_to_cloud_run() {
    print_status "Deploying to Google Cloud Run..."
    
    local image_tag=$(cat .last_deployed_image)
    local sa_email=$(cat .service_account)
    local connection_name=$(cat .cloud_sql_connection)
    
    # Build deployment command
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
    deploy_cmd="$deploy_cmd --service-account=$sa_email"
    deploy_cmd="$deploy_cmd --add-cloudsql-instances=$connection_name"
    deploy_cmd="$deploy_cmd --set-env-vars=ENVIRONMENT=production,GOOGLE_CLOUD_PROJECT_ID=$PROJECT_ID"
    
    # Add secrets
    deploy_cmd="$deploy_cmd --set-secrets="
    deploy_cmd="${deploy_cmd}DATABASE_URL=DATABASE_URL:latest,"
    deploy_cmd="${deploy_cmd}REDIS_URL=REDIS_URL:latest,"
    deploy_cmd="${deploy_cmd}SECRET_KEY=SECRET_KEY:latest,"
    deploy_cmd="${deploy_cmd}GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY:latest,"
    deploy_cmd="${deploy_cmd}TICKETMASTER_API_KEY=TICKETMASTER_API_KEY:latest,"
    deploy_cmd="${deploy_cmd}OPENWEATHERMAP_API_KEY=OPENWEATHERMAP_API_KEY:latest"
    
    # Execute deployment
    print_status "Deploying service (this may take a few minutes)..."
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

# Function to run post-deployment tasks
post_deployment_tasks() {
    print_status "Running post-deployment tasks..."
    
    if [ -f ".deployed_url" ]; then
        local service_url=$(cat .deployed_url)
        
        # Create a job to run migrations
        print_status "Setting up database migration job..."
        cat > migrate_job.yaml <<EOF
apiVersion: run.googleapis.com/v1
kind: Job
metadata:
  name: roadtrip-db-migrate
spec:
  template:
    spec:
      template:
        spec:
          containers:
          - image: $(cat .last_deployed_image)
            command: ["alembic", "upgrade", "head"]
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: DATABASE_URL
                  key: latest
EOF
        
        print_warning "To run database migrations, execute:"
        print_warning "gcloud run jobs create roadtrip-db-migrate --image=$(cat .last_deployed_image) --command='alembic,upgrade,head' --region=$REGION"
        print_warning "gcloud run jobs execute roadtrip-db-migrate --region=$REGION"
    fi
}

# Function to verify deployment
verify_deployment() {
    print_status "Verifying deployment..."
    
    if [ -f ".deployed_url" ]; then
        local service_url=$(cat .deployed_url)
        
        print_status "Waiting for service to be ready..."
        sleep 10
        
        print_status "Testing health endpoint..."
        if curl -f -s "$service_url/health" >/dev/null; then
            print_success "Health check passed"
        else
            print_warning "Health check failed - service may still be starting"
        fi
        
        print_status "Testing API documentation..."
        if curl -f -s "$service_url/docs" >/dev/null; then
            print_success "API documentation accessible"
        else
            print_warning "API documentation not accessible"
        fi
    fi
}

# Function to show deployment summary
show_summary() {
    print_success ""
    print_success "=========================================="
    print_success "     DEPLOYMENT COMPLETED SUCCESSFULLY     "
    print_success "=========================================="
    echo
    if [ -f ".deployed_url" ]; then
        local service_url=$(cat .deployed_url)
        print_status "Service URL: ${GREEN}$service_url${NC}"
        print_status "API Documentation: ${GREEN}$service_url/docs${NC}"
        print_status "Health Check: ${GREEN}$service_url/health${NC}"
    fi
    echo
    print_status "Project: $PROJECT_ID"
    print_status "Region: $REGION"
    print_status "Service: $SERVICE_NAME"
    echo
    print_status "Next steps:"
    print_status "1. Run database migrations (see instructions above)"
    print_status "2. Test your API endpoints"
    print_status "3. Configure custom domain (optional)"
    print_status "4. Set up monitoring alerts in Cloud Console"
    print_status "5. Enable beta user access"
    echo
    print_success "Your AI Road Trip Storyteller is ready for beta testing!"
}

# Main deployment function
main() {
    print_status ""
    print_status "================================================"
    print_status "   AI Road Trip Storyteller - GCP Deployment    "
    print_status "================================================"
    echo
    
    # Deployment steps
    validate_environment
    enable_apis
    create_artifact_registry
    build_and_push_image
    setup_database
    setup_redis
    setup_service_account
    setup_secrets
    deploy_to_cloud_run
    post_deployment_tasks
    verify_deployment
    show_summary
    
    # Update todo list
    print_status "Updating deployment status..."
}

# Run main function
main "$@"