#!/bin/bash
# Production Deployment Script for Google Cloud Run
# This script handles complete production deployment with safety checks

set -euo pipefail

# Color output for better visibility
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-roadtrip-460720}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="roadtrip-backend"
ENVIRONMENT="production"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"
TERRAFORM_DIR="infrastructure/production"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
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
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 is not installed. Please install it first."
        exit 1
    fi
}

# Pre-deployment checks
print_status "Running pre-deployment checks..."

# Check required tools
check_command gcloud
check_command docker
check_command ../../agent_taskforce/tools/terraform

# Verify Google Cloud authentication
print_status "Verifying Google Cloud authentication..."
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_error "No active Google Cloud authentication found"
    print_status "Please run: gcloud auth login"
    exit 1
fi

# Set project
print_status "Setting Google Cloud project to ${PROJECT_ID}..."
gcloud config set project "${PROJECT_ID}"

# Verify project exists
if ! gcloud projects describe "${PROJECT_ID}" &> /dev/null; then
    print_error "Project ${PROJECT_ID} not found or you don't have access"
    exit 1
fi

# Enable required APIs
print_status "Enabling required Google Cloud APIs..."
REQUIRED_APIS=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "containerregistry.googleapis.com"
    "sqladmin.googleapis.com"
    "redis.googleapis.com"
    "secretmanager.googleapis.com"
    "compute.googleapis.com"
    "servicenetworking.googleapis.com"
    "monitoring.googleapis.com"
    "logging.googleapis.com"
    "cloudtrace.googleapis.com"
    "aiplatform.googleapis.com"
    "texttospeech.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    print_status "Enabling ${api}..."
    gcloud services enable "${api}" --quiet
done

# Run pre-deployment validation
print_status "Running pre-deployment validation..."
if [ -f "agent_taskforce/hooks/pre_deploy_check.sh" ]; then
    bash agent_taskforce/hooks/pre_deploy_check.sh
else
    print_warning "Pre-deployment check script not found, skipping..."
fi

# Build Docker image
print_status "Building production Docker image..."
docker build \
    --platform linux/amd64 \
    --tag "${IMAGE_NAME}" \
    --file Dockerfile \
    --build-arg ENVIRONMENT=production \
    .

# Push to Google Container Registry
print_status "Pushing image to Google Container Registry..."
docker push "${IMAGE_NAME}"

# Deploy infrastructure with Terraform
print_status "Deploying infrastructure with Terraform..."
cd "${TERRAFORM_DIR}"

# Initialize Terraform
../../agent_taskforce/tools/../../agent_taskforce/tools/terraform init -backend=true

# Plan deployment
print_status "Planning Terraform deployment..."
../../agent_taskforce/tools/terraform plan -out=tfplan

# Apply with confirmation
read -p "Do you want to apply these changes? (yes/no): " -n 3 -r
echo
if [[ $REPLY =~ ^[Yy]es$ ]]; then
    ../../agent_taskforce/tools/terraform apply tfplan
else
    print_error "Deployment cancelled by user"
    exit 1
fi

# Get Terraform outputs
DB_CONNECTION=$(../../agent_taskforce/tools/terraform output -raw production_database_connection)
REDIS_HOST=$(../../agent_taskforce/tools/terraform output -raw production_redis_host)
SERVICE_ACCOUNT=$(../../agent_taskforce/tools/terraform output -raw production_service_account)

cd ../..

# Deploy to Cloud Run
print_status "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE_NAME}" \
    --platform=managed \
    --region="${REGION}" \
    --service-account="${SERVICE_ACCOUNT}" \
    --allow-unauthenticated \
    --timeout=300 \
    --concurrency=100 \
    --cpu=2 \
    --memory=2Gi \
    --min-instances=2 \
    --max-instances=100 \
    --set-env-vars="ENVIRONMENT=${ENVIRONMENT}" \
    --set-env-vars="PORT=8000" \
    --set-env-vars="LOG_LEVEL=INFO" \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-env-vars="VERTEX_AI_LOCATION=${REGION}" \
    --set-env-vars="REDIS_HOST=${REDIS_HOST}" \
    --set-secrets="DATABASE_URL=roadtrip-production-db-url:latest" \
    --set-secrets="JWT_SECRET_KEY=JWT_SECRET_KEY-production:latest" \
    --set-secrets="SECRET_KEY=SECRET_KEY-production:latest" \
    --set-secrets="GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY-production:latest" \
    --set-secrets="OPENWEATHER_API_KEY=OPENWEATHER_API_KEY-production:latest" \
    --set-secrets="TICKETMASTER_API_KEY=TICKETMASTER_API_KEY-production:latest" \
    --add-cloudsql-instances="${DB_CONNECTION}" \
    --vpc-connector="roadtrip-production-connector" \
    --vpc-egress=private-ranges-only

# Get service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --platform=managed \
    --region="${REGION}" \
    --format="value(status.url)")

print_success "Deployment complete!"
print_status "Service URL: ${SERVICE_URL}"

# Run post-deployment health checks
print_status "Running health checks..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f "${SERVICE_URL}/health" &> /dev/null; then
        print_success "Health check passed!"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    print_status "Waiting for service to be ready... (${RETRY_COUNT}/${MAX_RETRIES})"
    sleep 10
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "Health check failed after ${MAX_RETRIES} attempts"
    exit 1
fi

# Run database migrations
print_status "Running database migrations..."
gcloud run jobs create "roadtrip-migrate-${ENVIRONMENT}" \
    --image="${IMAGE_NAME}" \
    --region="${REGION}" \
    --service-account="${SERVICE_ACCOUNT}" \
    --set-env-vars="ENVIRONMENT=${ENVIRONMENT}" \
    --set-secrets="DATABASE_URL=roadtrip-production-db-url:latest" \
    --vpc-connector="roadtrip-production-connector" \
    --vpc-egress=private-ranges-only \
    --command="alembic" \
    --args="upgrade,head" \
    --max-retries=1 \
    --task-timeout=600

gcloud run jobs execute "roadtrip-migrate-${ENVIRONMENT}" --region="${REGION}" --wait

# Setup monitoring and alerting
print_status "Setting up monitoring and alerting..."
gcloud monitoring dashboards create --config-from-file=monitoring/production-dashboard.json || true

# Create uptime check
gcloud monitoring uptime-checks create http "${SERVICE_NAME}-health" \
    --resource-type="uptime_url" \
    --resource-labels="host=${SERVICE_URL#https://},project_id=${PROJECT_ID}" \
    --http-check="path=/health,port=443,use_ssl=true" \
    --period=60 \
    --timeout=10 || true

# Setup backup job
print_status "Setting up automated backups..."
gcloud run jobs create "roadtrip-backup-${ENVIRONMENT}" \
    --image="gcr.io/${PROJECT_ID}/roadtrip-backup:latest" \
    --region="${REGION}" \
    --service-account="${SERVICE_ACCOUNT}" \
    --set-env-vars="ENVIRONMENT=${ENVIRONMENT}" \
    --set-secrets="DATABASE_URL=roadtrip-production-db-url:latest" \
    --vpc-connector="roadtrip-production-connector" \
    --vpc-egress=private-ranges-only \
    --command="python" \
    --args="/app/database_backup.py" \
    --max-retries=2 \
    --task-timeout=3600 || true

# Schedule backup job (daily at 2 AM)
gcloud scheduler jobs create http "roadtrip-backup-schedule-${ENVIRONMENT}" \
    --location="${REGION}" \
    --schedule="0 2 * * *" \
    --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/roadtrip-backup-${ENVIRONMENT}:run" \
    --http-method="POST" \
    --oauth-service-account-email="${SERVICE_ACCOUNT}" || true

# Final summary
print_success "Production deployment completed successfully!"
echo
echo "=== Deployment Summary ==="
echo "Service URL: ${SERVICE_URL}"
echo "Environment: ${ENVIRONMENT}"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Database: ${DB_CONNECTION}"
echo "Redis: ${REDIS_HOST}"
echo
echo "=== Next Steps ==="
echo "1. Monitor the service at: ${SERVICE_URL}/health"
echo "2. Check logs: gcloud logging read 'resource.type=\"cloud_run_revision\" resource.labels.service_name=\"${SERVICE_NAME}\"' --limit 50"
echo "3. View metrics in Google Cloud Console"
echo "4. Test the API endpoints"
echo
print_status "Deployment log saved to: agent_taskforce/reports/deployment_$(date +%Y%m%d_%H%M%S).log"