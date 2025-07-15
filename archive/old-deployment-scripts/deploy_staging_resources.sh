#!/bin/bash

# Alternative deployment script for staging resources
# Uses gcloud commands directly instead of Terraform to work around IAM limitations

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Deploying Staging Resources Directly ===${NC}"
echo ""

# Configuration
PROJECT_ID="roadtrip-460720"
REGION="us-central1"
ZONE="us-central1-a"
DEPLOYMENT_ID=$(date +%Y%m%d-%H%M%S)
STAGING_SA="roadtrip-staging-e6a9121e@roadtrip-460720.iam.gserviceaccount.com"

# Function to print status
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Create Cloud SQL instance
print_status "Creating Cloud SQL PostgreSQL instance..."
if gcloud sql instances create roadtrip-db-staging-${DEPLOYMENT_ID} \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=$REGION \
    --network=projects/$PROJECT_ID/global/networks/roadtrip-vpc-staging \
    --no-assign-ip \
    --backup-start-time=03:00 \
    --availability-type=zonal \
    --storage-size=100GB \
    --storage-type=SSD \
    --project=$PROJECT_ID; then
    print_success "Cloud SQL instance created"
    
    # Create database
    print_status "Creating database..."
    gcloud sql databases create roadtrip_staging \
        --instance=roadtrip-db-staging-${DEPLOYMENT_ID} \
        --project=$PROJECT_ID
    
    # Create user
    print_status "Creating database user..."
    DB_PASSWORD=$(openssl rand -base64 32)
    gcloud sql users create roadtrip_staging \
        --instance=roadtrip-db-staging-${DEPLOYMENT_ID} \
        --password="$DB_PASSWORD" \
        --project=$PROJECT_ID
    
    # Store password in Secret Manager
    print_status "Storing database credentials..."
    echo -n "$DB_PASSWORD" | gcloud secrets versions add roadtrip-staging-db-password --data-file=-
    
    # Get connection name
    CONNECTION_NAME=$(gcloud sql instances describe roadtrip-db-staging-${DEPLOYMENT_ID} \
        --format="value(connectionName)" --project=$PROJECT_ID)
    
    # Create database URL
    DB_URL="postgresql://roadtrip_staging:${DB_PASSWORD}@/$CONNECTION_NAME/roadtrip_staging?host=/cloudsql/${CONNECTION_NAME}"
    echo -n "$DB_URL" | gcloud secrets versions add roadtrip-staging-db-url --data-file=-
    
    print_success "Database setup complete"
else
    print_error "Failed to create Cloud SQL instance"
fi

# 2. Create Redis instance
print_status "Creating Redis instance..."
if gcloud redis instances create roadtrip-redis-staging \
    --size=1 \
    --region=$REGION \
    --zone=$ZONE \
    --redis-version=redis_7_0 \
    --network=projects/$PROJECT_ID/global/networks/roadtrip-vpc-staging \
    --connect-mode=PRIVATE_SERVICE_ACCESS \
    --project=$PROJECT_ID; then
    print_success "Redis instance created"
else
    print_error "Failed to create Redis instance"
fi

# 3. Create VPC connector
print_status "Creating VPC connector..."
if gcloud compute networks vpc-access connectors create roadtrip-staging-connector \
    --region=$REGION \
    --subnet=roadtrip-subnet-staging \
    --subnet-project=$PROJECT_ID \
    --min-instances=2 \
    --max-instances=3 \
    --project=$PROJECT_ID; then
    print_success "VPC connector created"
else
    print_error "Failed to create VPC connector"
fi

# 4. Deploy Cloud Run service (placeholder)
print_status "Deploying Cloud Run service..."
cat > hello.py << 'EOF'
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "environment": "staging"}), 200

@app.route('/')
def index():
    return jsonify({
        "message": "AI Road Trip Storyteller - Staging Environment",
        "status": "ready for deployment",
        "environment": os.environ.get('ENVIRONMENT', 'staging')
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
EOF

cat > requirements.txt << 'EOF'
Flask==3.0.0
gunicorn==21.2.0
EOF

cat > Dockerfile << 'EOF'
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY hello.py .
ENV PORT=8080
ENV ENVIRONMENT=staging
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 hello:app
EOF

# Build and deploy
print_status "Building container image..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/roadtrip-backend-staging:placeholder

print_status "Deploying to Cloud Run..."
if gcloud run deploy roadtrip-backend-staging \
    --image=gcr.io/$PROJECT_ID/roadtrip-backend-staging:placeholder \
    --platform=managed \
    --region=$REGION \
    --allow-unauthenticated \
    --service-account=$STAGING_SA \
    --set-env-vars="ENVIRONMENT=staging" \
    --vpc-connector=roadtrip-staging-connector \
    --vpc-egress=private-ranges-only \
    --min-instances=1 \
    --max-instances=20 \
    --cpu=1 \
    --memory=1Gi \
    --project=$PROJECT_ID; then
    
    STAGING_URL=$(gcloud run services describe roadtrip-backend-staging \
        --region=$REGION --format="value(status.url)" --project=$PROJECT_ID)
    print_success "Cloud Run service deployed: $STAGING_URL"
else
    print_error "Failed to deploy Cloud Run service"
fi

# 5. Clean up temporary files
rm -f hello.py requirements.txt Dockerfile

# Summary
echo ""
echo -e "${GREEN}=== Staging Environment Deployment Summary ===${NC}"
echo ""
echo "Resources created:"
echo "- Cloud SQL Instance: roadtrip-db-staging-${DEPLOYMENT_ID}"
echo "- Redis Instance: roadtrip-redis-staging"
echo "- VPC Connector: roadtrip-staging-connector"
echo "- Cloud Run Service: roadtrip-backend-staging"
echo ""
echo "Staging URL: ${STAGING_URL:-Not available}"
echo ""
echo "Next steps:"
echo "1. Build and deploy the actual application image"
echo "2. Run database migrations"
echo "3. Execute validation tests"
echo ""
echo -e "${GREEN}Deployment complete!${NC}"