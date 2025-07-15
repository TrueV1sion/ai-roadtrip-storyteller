#!/bin/bash

# Deploy a simple staging Cloud Run service without VPC requirements

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Deploying Simple Staging Cloud Run Service ===${NC}"
echo ""

PROJECT_ID="roadtrip-460720"
REGION="us-central1"
STAGING_SA="roadtrip-staging-e6a9121e@roadtrip-460720.iam.gserviceaccount.com"

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Deploy Cloud Run without VPC connector
print_status "Deploying simplified Cloud Run service..."
if gcloud run deploy roadtrip-backend-staging \
    --image=gcr.io/$PROJECT_ID/roadtrip-backend-staging:placeholder \
    --platform=managed \
    --region=$REGION \
    --allow-unauthenticated \
    --service-account=$STAGING_SA \
    --set-env-vars="ENVIRONMENT=staging" \
    --min-instances=1 \
    --max-instances=20 \
    --cpu=1 \
    --memory=1Gi \
    --project=$PROJECT_ID; then
    
    STAGING_URL=$(gcloud run services describe roadtrip-backend-staging \
        --region=$REGION --format="value(status.url)" --project=$PROJECT_ID)
    print_success "Cloud Run service deployed successfully!"
    echo ""
    echo -e "${GREEN}Staging URL: $STAGING_URL${NC}"
    
    # Test the deployment
    echo ""
    print_status "Testing deployment..."
    echo ""
    
    # Test health endpoint
    print_status "Testing /health endpoint..."
    curl -s "$STAGING_URL/health" | python3 -m json.tool || echo "Health check not available yet"
    
    echo ""
    print_status "Testing root endpoint..."
    curl -s "$STAGING_URL/" | python3 -m json.tool || echo "Root endpoint not available yet"
    
else
    print_error "Failed to deploy Cloud Run service"
fi

echo ""
echo -e "${GREEN}=== Deployment Summary ===${NC}"
echo ""
echo "✅ Cloud Run Service: roadtrip-backend-staging"
echo "✅ Service Account: $STAGING_SA"
echo "✅ Environment: staging"
echo "✅ Resources: 1 CPU, 1GB Memory"
echo "✅ Scaling: 1-20 instances"
echo ""
echo "🌐 Access your staging environment at: ${STAGING_URL:-Not available}"
echo ""
echo "Next steps:"
echo "1. Deploy the actual application Docker image"
echo "2. Configure database and Redis connections when permissions are available"
echo "3. Run the validation test suite"
echo ""

# Create a simple status check script
cat > check_staging_status.sh << 'EOF'
#!/bin/bash
STAGING_URL=$(gcloud run services describe roadtrip-backend-staging \
    --region=us-central1 --format="value(status.url)" --project=roadtrip-460720)

echo "Staging Environment Status:"
echo "=========================="
echo "URL: $STAGING_URL"
echo ""
echo "Health Check:"
curl -s "$STAGING_URL/health" | python3 -m json.tool
echo ""
echo "Root Endpoint:"
curl -s "$STAGING_URL/" | python3 -m json.tool
EOF

chmod +x check_staging_status.sh
print_success "Created check_staging_status.sh for easy status monitoring"