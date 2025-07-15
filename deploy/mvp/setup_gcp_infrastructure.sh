#!/bin/bash
# Google Cloud Platform Infrastructure Setup for MVP
# This script sets up the minimal cloud infrastructure needed for MVP

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
PROJECT_ID="roadtrip-mvp-prod"
REGION="us-central1"
ZONE="us-central1-a"

print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

echo "🚗 AI Road Trip Storyteller - GCP Infrastructure Setup"
echo "===================================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI not found. Please install Google Cloud SDK"
    echo "Visit: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Step 1: Create or set project
echo "Step 1: Setting up GCP Project..."
echo "---------------------------------"

# Check if project exists
if gcloud projects describe $PROJECT_ID &>/dev/null; then
    print_status "Project $PROJECT_ID exists"
else
    print_status "Creating project $PROJECT_ID..."
    gcloud projects create $PROJECT_ID --name="AI Road Trip MVP"
fi

# Set project
gcloud config set project $PROJECT_ID
print_status "Project set to $PROJECT_ID"

# Step 2: Enable required APIs
echo ""
echo "Step 2: Enabling Required APIs..."
echo "---------------------------------"

APIS=(
    "cloudrun.googleapis.com"
    "cloudbuild.googleapis.com"
    "texttospeech.googleapis.com"
    "storage.googleapis.com"
    "sqladmin.googleapis.com"
    "redis.googleapis.com"
    "secretmanager.googleapis.com"
    "maps-backend.googleapis.com"
    "places-backend.googleapis.com"
    "aiplatform.googleapis.com"
)

for api in "${APIS[@]}"; do
    echo "Enabling $api..."
    gcloud services enable $api --quiet
done
print_status "All APIs enabled"

# Step 3: Create Service Account
echo ""
echo "Step 3: Creating Service Account..."
echo "-----------------------------------"

SERVICE_ACCOUNT="roadtrip-app"
SA_EMAIL="${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com"

if gcloud iam service-accounts describe $SA_EMAIL &>/dev/null; then
    print_status "Service account exists"
else
    print_status "Creating service account..."
    gcloud iam service-accounts create $SERVICE_ACCOUNT \
        --display-name="Road Trip Application Service Account" \
        --description="Service account for Road Trip MVP application"
fi

# Grant necessary roles
echo "Granting IAM roles..."
ROLES=(
    "roles/cloudsql.client"
    "roles/storage.admin"
    "roles/redis.editor"
    "roles/secretmanager.secretAccessor"
    "roles/aiplatform.user"
    "roles/cloudtexttospeech.client"
)

for role in "${ROLES[@]}"; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="$role" \
        --quiet
done
print_status "IAM roles granted"

# Step 4: Create Cloud Storage Buckets
echo ""
echo "Step 4: Creating Cloud Storage Buckets..."
echo "-----------------------------------------"

# Audio storage bucket
AUDIO_BUCKET="${PROJECT_ID}-audio"
if gsutil ls -b gs://$AUDIO_BUCKET &>/dev/null; then
    print_status "Audio bucket exists"
else
    print_status "Creating audio bucket..."
    gsutil mb -p $PROJECT_ID -c standard -l $REGION gs://$AUDIO_BUCKET
    
    # Set lifecycle rule for temporary audio
    cat > /tmp/lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [{
      "action": {"type": "Delete"},
      "condition": {
        "age": 7,
        "matchesPrefix": ["temp_tts/", "standard_tts/"]
      }
    }]
  }
}
EOF
    gsutil lifecycle set /tmp/lifecycle.json gs://$AUDIO_BUCKET
    rm /tmp/lifecycle.json
fi

# Assets bucket for static files
ASSETS_BUCKET="${PROJECT_ID}-assets"
if gsutil ls -b gs://$ASSETS_BUCKET &>/dev/null; then
    print_status "Assets bucket exists"
else
    print_status "Creating assets bucket..."
    gsutil mb -p $PROJECT_ID -c standard -l $REGION gs://$ASSETS_BUCKET
fi

# Step 5: Create Cloud SQL Instance
echo ""
echo "Step 5: Setting up Cloud SQL (PostgreSQL)..."
echo "--------------------------------------------"

SQL_INSTANCE="roadtrip-mvp-db"
if gcloud sql instances describe $SQL_INSTANCE &>/dev/null; then
    print_status "Cloud SQL instance exists"
else
    print_status "Creating Cloud SQL instance (this takes 5-10 minutes)..."
    gcloud sql instances create $SQL_INSTANCE \
        --database-version=POSTGRES_15 \
        --tier=db-g1-small \
        --region=$REGION \
        --network="default" \
        --no-backup \
        --database-flags=max_connections=100
fi

# Create database
print_status "Creating database..."
gcloud sql databases create roadtrip --instance=$SQL_INSTANCE --quiet || true

# Set root password
print_status "Setting database password..."
gcloud sql users set-password postgres \
    --instance=$SQL_INSTANCE \
    --password="roadtrip_mvp_2024" \
    --quiet

# Step 6: Create Memorystore Redis Instance
echo ""
echo "Step 6: Setting up Memorystore (Redis)..."
echo "------------------------------------------"

REDIS_INSTANCE="roadtrip-mvp-cache"
if gcloud redis instances describe $REDIS_INSTANCE --region=$REGION &>/dev/null; then
    print_status "Redis instance exists"
else
    print_status "Creating Redis instance (this takes 5-10 minutes)..."
    gcloud redis instances create $REDIS_INSTANCE \
        --size=1 \
        --region=$REGION \
        --redis-version=redis_6_x \
        --network="default"
fi

# Step 7: Create Secret Manager Secrets
echo ""
echo "Step 7: Setting up Secret Manager..."
echo "-------------------------------------"

# Function to create or update secret
create_secret() {
    local secret_name=$1
    local secret_value=$2
    
    if gcloud secrets describe $secret_name &>/dev/null; then
        echo "Updating secret: $secret_name"
        echo -n "$secret_value" | gcloud secrets versions add $secret_name --data-file=-
    else
        echo "Creating secret: $secret_name"
        echo -n "$secret_value" | gcloud secrets create $secret_name --data-file=-
    fi
}

print_warning "Creating placeholder secrets - UPDATE THESE WITH REAL VALUES!"

# Database URL (will be updated after getting connection details)
create_secret "database-url" "postgresql://postgres:roadtrip_mvp_2024@/roadtrip?host=/cloudsql/${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"

# API Keys (UPDATE THESE!)
create_secret "google-maps-api-key" "YOUR_GOOGLE_MAPS_API_KEY"
create_secret "openai-api-key" "YOUR_OPENAI_API_KEY"
create_secret "ticketmaster-api-key" "YOUR_TICKETMASTER_API_KEY"
create_secret "openweathermap-api-key" "YOUR_OPENWEATHERMAP_API_KEY"

# Application secrets
create_secret "secret-key" "$(openssl rand -hex 32)"
create_secret "jwt-secret-key" "$(openssl rand -hex 32)"

print_status "Secrets created (remember to update with real values)"

# Step 8: Get connection information
echo ""
echo "Step 8: Connection Information..."
echo "---------------------------------"

# Get Cloud SQL connection info
SQL_CONNECTION_NAME=$(gcloud sql instances describe $SQL_INSTANCE --format="value(connectionName)")
print_status "Cloud SQL connection: $SQL_CONNECTION_NAME"

# Get Redis connection info
REDIS_HOST=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="value(host)")
REDIS_PORT=$(gcloud redis instances describe $REDIS_INSTANCE --region=$REGION --format="value(port)")
print_status "Redis endpoint: $REDIS_HOST:$REDIS_PORT"

# Step 9: Create deployment configuration
echo ""
echo "Step 9: Creating Deployment Configuration..."
echo "--------------------------------------------"

cat > /tmp/app.yaml << EOF
# Cloud Run deployment configuration
env: flex
runtime: python
runtime_config:
  python_version: 3.9

env_variables:
  MVP_MODE: "true"
  GCP_PROJECT_ID: "${PROJECT_ID}"
  GCS_BUCKET_NAME: "${AUDIO_BUCKET}"
  GOOGLE_AI_LOCATION: "us-central1"
  GOOGLE_AI_MODEL: "gemini-1.5-flash"

# Cloud SQL
beta_settings:
  cloud_sql_instances: "${SQL_CONNECTION_NAME}"

# Resources for MVP
resources:
  cpu: 2
  memory_gb: 2
  disk_size_gb: 10

# Health check
liveness_check:
  path: "/health"
  check_interval_sec: 30
  timeout_sec: 4
  failure_threshold: 2
  success_threshold: 2

readiness_check:
  path: "/health"
  check_interval_sec: 5
  timeout_sec: 4
  failure_threshold: 2
  success_threshold: 2
EOF

cp /tmp/app.yaml deploy/mvp/app.yaml
print_status "Deployment configuration created"

# Final Summary
echo ""
echo "======================================"
echo "✨ Infrastructure Setup Complete!"
echo "======================================"
echo ""
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""
echo "Resources Created:"
echo "- Cloud SQL: $SQL_INSTANCE"
echo "- Redis: $REDIS_INSTANCE"
echo "- Storage: gs://$AUDIO_BUCKET, gs://$ASSETS_BUCKET"
echo "- Service Account: $SA_EMAIL"
echo ""
print_warning "IMPORTANT NEXT STEPS:"
echo "1. Update secrets in Secret Manager with real API keys:"
echo "   - google-maps-api-key"
echo "   - openai-api-key (or set up Vertex AI)"
echo "   - ticketmaster-api-key"
echo "   - openweathermap-api-key"
echo ""
echo "2. Update database-url secret after migrations"
echo ""
echo "3. Deploy application:"
echo "   ./deploy_to_cloud_run.sh"
echo ""