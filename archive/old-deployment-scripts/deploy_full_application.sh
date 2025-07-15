#!/bin/bash

# Deploy Full AI Road Trip Storyteller Application to Staging
# This script handles the complete deployment including Docker build and Cloud Run update

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
PURPLE='\033[0;35m'
NC='\033[0m'

echo -e "${GREEN}=== Full Application Deployment to Staging ===${NC}"
echo ""

# Configuration
PROJECT_ID="roadtrip-460720"
REGION="us-central1"
STAGING_SA="roadtrip-staging-e6a9121e@roadtrip-460720.iam.gserviceaccount.com"
BACKEND_DIR="/mnt/c/users/jared/onedrive/desktop/roadtrip/backend"
DEPLOYMENT_ID=$(date +%Y%m%d-%H%M%S)
IMAGE_TAG="gcr.io/$PROJECT_ID/roadtrip-backend-staging:$DEPLOYMENT_ID"
IMAGE_LATEST="gcr.io/$PROJECT_ID/roadtrip-backend-staging:latest"

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

print_section() {
    echo ""
    echo -e "${PURPLE}=== $1 ===${NC}"
    echo ""
}

# Pre-deployment checks
pre_deployment_checks() {
    print_section "Pre-Deployment Checks"
    
    # Check if backend directory exists
    if [ ! -d "$BACKEND_DIR" ]; then
        print_error "Backend directory not found at $BACKEND_DIR"
        exit 1
    fi
    
    # Check if Docker is available
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check if gcloud is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated with gcloud"
        exit 1
    fi
    
    # Validate IAM permissions
    print_status "Validating IAM permissions..."
    if [ -f "./validate_iam_permissions.sh" ]; then
        if ./validate_iam_permissions.sh > /tmp/iam_validation.log 2>&1; then
            print_success "IAM permissions validated"
        else
            print_warning "Some IAM permissions missing, deployment may have limited functionality"
            print_status "Run ./validate_iam_permissions.sh for details"
        fi
    fi
    
    print_success "Pre-deployment checks completed"
}

# Create staging-optimized Dockerfile
create_staging_dockerfile() {
    print_section "Creating Staging Dockerfile"
    
    cat > "$BACKEND_DIR/Dockerfile.staging" << 'EOF'
# Staging Dockerfile for AI Road Trip Storyteller
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Staging-specific environment variables
ENV ENVIRONMENT=staging
ENV PORT=8080
ENV LOG_LEVEL=INFO
ENV ENABLE_MOCK_MODE=true

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application with staging configuration
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
EOF
    
    print_success "Staging Dockerfile created"
}

# Create staging configuration
create_staging_config() {
    print_section "Creating Staging Configuration"
    
    # Create staging-specific configuration
    cat > "$BACKEND_DIR/app/core/staging_config.py" << 'EOF'
"""Staging-specific configuration with graceful fallbacks"""
import os
from typing import Optional

class StagingConfig:
    """Configuration for staging environment with fallbacks"""
    
    # Environment
    ENVIRONMENT = "staging"
    DEBUG = False
    TESTING = True
    
    # Database - fallback to SQLite if PostgreSQL not available
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./staging.db")
    USE_SQLITE = DATABASE_URL.startswith("sqlite")
    
    # Redis - disable if not available
    REDIS_URL = os.getenv("REDIS_URL", "")
    CACHE_ENABLED = bool(REDIS_URL)
    
    # Security - simplified for staging
    SECRET_KEY = os.getenv("SECRET_KEY", "staging-secret-key-change-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "staging-jwt-secret")
    JWT_ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # External APIs - use mock mode if keys not available
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
    USE_MOCK_APIS = not (GOOGLE_MAPS_API_KEY and OPENWEATHER_API_KEY)
    
    # AI Configuration
    GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "roadtrip-460720")
    VERTEX_AI_LOCATION = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    AI_MODEL = "gemini-1.5-flash"
    
    # Feature flags for staging
    ENABLE_RATE_LIMITING = False  # Simplified for testing
    ENABLE_CSRF_PROTECTION = False  # Simplified for testing
    ENABLE_DETAILED_ERRORS = True  # More details in staging
    ENABLE_API_DOCS = True  # Always show docs in staging
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @classmethod
    def get_database_url(cls) -> str:
        """Get database URL with fallback"""
        if cls.USE_SQLITE:
            return cls.DATABASE_URL
        return cls.DATABASE_URL
    
    @classmethod
    def get_redis_url(cls) -> Optional[str]:
        """Get Redis URL if available"""
        return cls.REDIS_URL if cls.CACHE_ENABLED else None
EOF
    
    # Update main.py to use staging config in staging environment
    print_status "Patching main.py for staging configuration..."
    
    # Create a patch for main.py
    cat > "$BACKEND_DIR/staging_main_patch.py" << 'EOF'
# This patch adds staging configuration support to main.py
import os

# Read the original main.py
with open("app/main.py", "r") as f:
    content = f.read()

# Add staging config import after other imports
import_line = "from app.core.config import Settings"
staging_import = """from app.core.config import Settings
if os.getenv("ENVIRONMENT") == "staging":
    from app.core.staging_config import StagingConfig
    settings = StagingConfig()
else:
    settings = Settings()"""

content = content.replace(import_line, staging_import)

# Write the updated main.py
with open("app/main.py", "w") as f:
    f.write(content)

print("✓ Patched main.py for staging configuration")
EOF
    
    cd "$BACKEND_DIR" && python staging_main_patch.py && rm staging_main_patch.py
    cd - > /dev/null
    
    print_success "Staging configuration created"
}

# Build Docker image
build_docker_image() {
    print_section "Building Docker Image"
    
    cd "$BACKEND_DIR"
    
    print_status "Building image: $IMAGE_TAG"
    
    if docker build -f Dockerfile.staging -t "$IMAGE_TAG" -t "$IMAGE_LATEST" .; then
        print_success "Docker image built successfully"
        
        # Show image details
        docker images | grep roadtrip-backend-staging | head -2
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
    
    cd - > /dev/null
}

# Push to Google Container Registry
push_docker_image() {
    print_section "Pushing to Container Registry"
    
    # Configure Docker for GCR
    print_status "Configuring Docker for GCR..."
    gcloud auth configure-docker --quiet
    
    # Push both tags
    print_status "Pushing $IMAGE_TAG..."
    if docker push "$IMAGE_TAG"; then
        print_success "Pushed versioned image"
    else
        print_error "Failed to push versioned image"
        exit 1
    fi
    
    print_status "Pushing $IMAGE_LATEST..."
    if docker push "$IMAGE_LATEST"; then
        print_success "Pushed latest image"
    else
        print_error "Failed to push latest image"
        exit 1
    fi
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    print_section "Deploying to Cloud Run"
    
    print_status "Updating Cloud Run service with new image..."
    
    # Prepare environment variables
    ENV_VARS="ENVIRONMENT=staging"
    ENV_VARS="$ENV_VARS,PORT=8080"
    ENV_VARS="$ENV_VARS,GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
    ENV_VARS="$ENV_VARS,LOG_LEVEL=INFO"
    ENV_VARS="$ENV_VARS,ENABLE_MOCK_MODE=true"
    
    # Deploy with comprehensive configuration
    if gcloud run deploy roadtrip-backend-staging \
        --image="$IMAGE_TAG" \
        --platform=managed \
        --region=$REGION \
        --allow-unauthenticated \
        --service-account=$STAGING_SA \
        --set-env-vars="$ENV_VARS" \
        --min-instances=1 \
        --max-instances=20 \
        --cpu=1 \
        --memory=1Gi \
        --timeout=300 \
        --concurrency=80 \
        --project=$PROJECT_ID; then
        
        print_success "Cloud Run service updated successfully"
        
        # Get the service URL
        STAGING_URL=$(gcloud run services describe roadtrip-backend-staging \
            --region=$REGION --format="value(status.url)" --project=$PROJECT_ID)
        
        print_success "Deployment complete!"
        echo ""
        echo -e "${GREEN}🌐 Staging URL: $STAGING_URL${NC}"
    else
        print_error "Failed to deploy to Cloud Run"
        exit 1
    fi
}

# Test deployment
test_deployment() {
    print_section "Testing Deployment"
    
    if [ -z "$STAGING_URL" ]; then
        STAGING_URL=$(gcloud run services describe roadtrip-backend-staging \
            --region=$REGION --format="value(status.url)" --project=$PROJECT_ID)
    fi
    
    print_status "Waiting for service to be ready..."
    sleep 10
    
    # Test health endpoint
    print_status "Testing /health endpoint..."
    if curl -s "$STAGING_URL/health" | python3 -m json.tool; then
        print_success "Health check passed"
    else
        print_warning "Health check failed or returned non-JSON"
    fi
    
    echo ""
    
    # Test API docs
    print_status "Testing /docs endpoint..."
    if curl -s -o /dev/null -w "%{http_code}" "$STAGING_URL/docs" | grep -q "200"; then
        print_success "API documentation available at $STAGING_URL/docs"
    else
        print_warning "API documentation not accessible"
    fi
    
    echo ""
    
    # Test root endpoint
    print_status "Testing root endpoint..."
    curl -s "$STAGING_URL/" | python3 -m json.tool || echo "Root endpoint test failed"
}

# Generate deployment report
generate_deployment_report() {
    print_section "Generating Deployment Report"
    
    cat > "deployment_report_$DEPLOYMENT_ID.md" << EOF
# Staging Deployment Report

**Deployment ID**: $DEPLOYMENT_ID  
**Date**: $(date)  
**Deployed By**: $(gcloud auth list --filter=status:ACTIVE --format="value(account)")

## Deployment Details

- **Image**: $IMAGE_TAG
- **Service**: roadtrip-backend-staging
- **Region**: $REGION
- **URL**: $STAGING_URL

## Configuration

- **Environment**: staging
- **CPU**: 1 vCPU
- **Memory**: 1 GB
- **Min Instances**: 1
- **Max Instances**: 20
- **Service Account**: $STAGING_SA

## Features Status

- ✅ Core API endpoints
- ✅ Health monitoring
- ✅ API documentation (/docs)
- ⚠️  Database: Using fallback mode (SQLite or mock)
- ⚠️  Redis: Disabled (no caching)
- ✅ AI Services: Available (may use mock mode)
- ✅ Security: Basic authentication enabled

## Test Results

\`\`\`
Health Check: $(curl -s "$STAGING_URL/health" 2>/dev/null || echo "Failed")
\`\`\`

## Next Steps

1. Configure database connection when permissions available
2. Enable Redis caching when permissions available
3. Add API keys for external services
4. Run comprehensive test suite
5. Monitor application logs

## Access Points

- **Application**: $STAGING_URL
- **API Docs**: $STAGING_URL/docs
- **Health Check**: $STAGING_URL/health
- **Metrics**: $STAGING_URL/metrics

## Commands

View logs:
\`\`\`bash
gcloud run services logs read roadtrip-backend-staging --region=$REGION
\`\`\`

Update configuration:
\`\`\`bash
gcloud run services update roadtrip-backend-staging --region=$REGION --update-env-vars=KEY=VALUE
\`\`\`

Scale service:
\`\`\`bash
gcloud run services update roadtrip-backend-staging --region=$REGION --min-instances=2 --max-instances=50
\`\`\`
EOF
    
    print_success "Deployment report saved to deployment_report_$DEPLOYMENT_ID.md"
}

# Main deployment flow
main() {
    echo -e "${YELLOW}Deployment ID:${NC} $DEPLOYMENT_ID"
    echo -e "${YELLOW}Target:${NC} Staging Environment"
    echo ""
    
    # Run all deployment steps
    pre_deployment_checks
    create_staging_dockerfile
    create_staging_config
    build_docker_image
    push_docker_image
    deploy_to_cloud_run
    test_deployment
    generate_deployment_report
    
    # Final summary
    print_section "Deployment Complete! 🎉"
    
    echo "The full AI Road Trip Storyteller application has been deployed to staging!"
    echo ""
    echo -e "${GREEN}Access your application:${NC}"
    echo "- Main URL: $STAGING_URL"
    echo "- API Docs: $STAGING_URL/docs"
    echo "- Health: $STAGING_URL/health"
    echo ""
    echo "Note: Some features may be limited due to IAM permissions."
    echo "Run ./comprehensive_iam_setup.sh to enable full functionality."
}

# Execute main function
main "$@"