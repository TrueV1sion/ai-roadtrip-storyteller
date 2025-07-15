#!/bin/bash
# Beta Launch Deployment Script
# Deploys AI Road Trip Storyteller to production for beta launch

set -e  # Exit on error

echo "🚀 AI ROAD TRIP STORYTELLER - BETA LAUNCH DEPLOYMENT"
echo "=============================================="
echo "Deployment started at: $(date)"
echo ""

# Configuration
PROJECT_ID="ai-road-trip-storyteller"
REGION="us-central1"
SERVICE_NAME="roadtrip-api"
BETA_VERSION="beta-1.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[$(date +'%H:%M:%S')] WARNING:${NC} $1"
}

print_error() {
    echo -e "${RED}[$(date +'%H:%M:%S')] ERROR:${NC} $1"
}

# Pre-deployment checks
print_status "Running pre-deployment checks..."

# Check if logged in to gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &>/dev/null; then
    print_error "Not logged in to Google Cloud. Please run: gcloud auth login"
    exit 1
fi

# Set project
print_status "Setting Google Cloud project..."
gcloud config set project $PROJECT_ID

# Check if required APIs are enabled
print_status "Verifying required APIs..."
REQUIRED_APIS=(
    "run.googleapis.com"
    "sqladmin.googleapis.com"
    "redis.googleapis.com"
    "secretmanager.googleapis.com"
    "monitoring.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    if ! gcloud services list --enabled --filter="name:$api" --format="value(name)" | grep -q $api; then
        print_warning "Enabling $api..."
        gcloud services enable $api
    fi
done

# Build and push Docker image
print_status "Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:$BETA_VERSION -f Dockerfile.cloudrun .

print_status "Pushing Docker image to Container Registry..."
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:$BETA_VERSION

# Update database schema
print_status "Running database migrations..."
export DATABASE_URL=$(gcloud secrets versions access latest --secret="roadtrip-database-url")
alembic upgrade head

# Deploy to Cloud Run
print_status "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME:$BETA_VERSION \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars="ENVIRONMENT=production,VERSION=$BETA_VERSION" \
    --set-secrets="DATABASE_URL=roadtrip-database-url:latest,SECRET_KEY=roadtrip-secret-key:latest,GOOGLE_MAPS_API_KEY=roadtrip-google-maps-key:latest,TICKETMASTER_API_KEY=roadtrip-ticketmaster-key:latest,OPENWEATHERMAP_API_KEY=roadtrip-openweather-key:latest" \
    --memory 2Gi \
    --cpu 2 \
    --min-instances 2 \
    --max-instances 100 \
    --concurrency 100 \
    --timeout 300

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)')
print_status "Service deployed at: $SERVICE_URL"

# Update load balancer
print_status "Updating load balancer configuration..."
gcloud compute backend-services update roadtrip-backend \
    --global \
    --enable-cdn \
    --cache-mode CACHE_ALL_STATIC

# Deploy monitoring dashboards
print_status "Deploying monitoring dashboards..."
kubectl apply -f infrastructure/k8s/monitoring/

# Run smoke tests
print_status "Running smoke tests..."
python scripts/validate_deployment.py --url $SERVICE_URL --environment production

# Create beta user pool
print_status "Creating beta user accounts..."
python scripts/create_beta_users.py --count 100

# Enable monitoring alerts
print_status "Enabling monitoring alerts..."
gcloud alpha monitoring policies create --notification-channels=$(gcloud alpha monitoring channels list --filter="displayName:'Beta Launch Alerts'" --format="value(name)") --policy-from-file=monitoring/alerting-policies.yaml

# Tag the release
print_status "Tagging release in git..."
git tag -a $BETA_VERSION -m "Beta launch release"
git push origin $BETA_VERSION

# Generate deployment report
print_status "Generating deployment report..."
cat > deployment_report_$(date +%Y%m%d_%H%M%S).txt << EOF
AI Road Trip Storyteller - Beta Deployment Report
==============================================
Date: $(date)
Version: $BETA_VERSION
Service URL: $SERVICE_URL
Project: $PROJECT_ID
Region: $REGION

Deployment Status: SUCCESS

Next Steps:
1. Monitor initial traffic at: https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME/metrics
2. Check error logs at: https://console.cloud.google.com/logs
3. Review monitoring dashboard at: https://console.cloud.google.com/monitoring
4. Send beta invitations using: python scripts/send_beta_invitations.py

Emergency Rollback:
gcloud run services update-traffic $SERVICE_NAME --to-revisions=PREVIOUS=100

Support Contacts:
- On-call Engineer: [Configure in PagerDuty]
- CTO: [Contact]
- Support Lead: [Contact]
EOF

print_status "Deployment complete! 🎉"
echo ""
echo "=============================================="
echo "BETA LAUNCH DEPLOYMENT SUCCESSFUL"
echo "=============================================="
echo "Service URL: $SERVICE_URL"
echo "Version: $BETA_VERSION"
echo ""
echo "Next step: Run 'python scripts/send_beta_invitations.py' to invite beta users"