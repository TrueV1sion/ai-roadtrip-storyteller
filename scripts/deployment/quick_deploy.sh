#!/bin/bash
# Quick deployment script for AI Road Trip Storyteller
# Handles the most common deployment scenarios

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="roadtrip"
DEFAULT_REGION="us-central1"
DEFAULT_ZONE="us-central1-a"

# Functions
print_header() {
    echo -e "\n${BLUE}===================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"
    
    # Check for required tools
    command -v docker >/dev/null 2>&1 || { print_error "Docker is required but not installed."; exit 1; }
    command -v gcloud >/dev/null 2>&1 || { print_error "Google Cloud SDK is required but not installed."; exit 1; }
    
    # Check for .env file
    if [ ! -f .env ]; then
        print_error ".env file not found. Please run setup_infrastructure.py first."
        exit 1
    fi
    
    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        print_error "Docker daemon is not running."
        exit 1
    fi
    
    print_success "All prerequisites met"
}

# Build Docker image
build_image() {
    print_header "Building Docker Image"
    
    # Get project ID
    PROJECT_ID=$(gcloud config get-value project)
    if [ -z "$PROJECT_ID" ]; then
        print_error "No GCP project set. Run: gcloud config set project PROJECT_ID"
        exit 1
    fi
    
    IMAGE_TAG="gcr.io/${PROJECT_ID}/${PROJECT_NAME}:latest"
    
    print_info "Building image: ${IMAGE_TAG}"
    
    # Build with production Dockerfile
    if docker build -t "${IMAGE_TAG}" -f Dockerfile . ; then
        print_success "Docker image built successfully"
    else
        print_error "Docker build failed"
        exit 1
    fi
    
    echo "${IMAGE_TAG}"
}

# Push to Container Registry
push_image() {
    local IMAGE_TAG=$1
    print_header "Pushing Docker Image"
    
    # Configure Docker for GCR
    print_info "Configuring Docker for Google Container Registry..."
    gcloud auth configure-docker --quiet
    
    # Push image
    print_info "Pushing image to GCR..."
    if docker push "${IMAGE_TAG}"; then
        print_success "Image pushed successfully"
    else
        print_error "Failed to push image"
        exit 1
    fi
}

# Deploy to Cloud Run
deploy_cloud_run() {
    local IMAGE_TAG=$1
    print_header "Deploying to Cloud Run"
    
    SERVICE_NAME="${PROJECT_NAME}-api"
    
    # Check if service exists
    if gcloud run services describe ${SERVICE_NAME} --region=${DEFAULT_REGION} >/dev/null 2>&1; then
        print_info "Updating existing Cloud Run service..."
    else
        print_info "Creating new Cloud Run service..."
    fi
    
    # Deploy with environment variables from .env
    print_info "Deploying service ${SERVICE_NAME}..."
    
    gcloud run deploy ${SERVICE_NAME} \
        --image="${IMAGE_TAG}" \
        --region=${DEFAULT_REGION} \
        --platform=managed \
        --allow-unauthenticated \
        --port=8000 \
        --memory=2Gi \
        --cpu=2 \
        --min-instances=1 \
        --max-instances=100 \
        --set-env-vars="$(grep -v '^#' .env | grep -v '^$' | paste -sd ',' -)" \
        --add-cloudsql-instances="$(grep CLOUD_SQL_CONNECTION_NAME .env | cut -d'=' -f2)" \
        --service-account="$(grep -E '^[^#]*@.*\.iam\.gserviceaccount\.com' service-account-key.json | cut -d'"' -f4)" \
        --set-secrets="DATABASE_URL=roadtrip-db-url:latest" \
        --timeout=30m
    
    if [ $? -eq 0 ]; then
        print_success "Cloud Run deployment successful"
        
        # Get service URL
        SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region=${DEFAULT_REGION} --format='value(status.url)')
        print_success "Service deployed at: ${SERVICE_URL}"
        
        # Test health endpoint
        print_info "Testing health endpoint..."
        if curl -s "${SERVICE_URL}/health" | grep -q "healthy"; then
            print_success "Health check passed!"
        else
            print_warning "Health check failed - service may still be starting"
        fi
    else
        print_error "Cloud Run deployment failed"
        exit 1
    fi
}

# Deploy to Kubernetes (alternative)
deploy_kubernetes() {
    local IMAGE_TAG=$1
    print_header "Deploying to Kubernetes"
    
    # Check if kubectl is configured
    if ! kubectl cluster-info >/dev/null 2>&1; then
        print_error "kubectl not configured. Please set up Kubernetes cluster first."
        exit 1
    fi
    
    # Create namespace
    kubectl create namespace ${PROJECT_NAME} --dry-run=client -o yaml | kubectl apply -f -
    
    # Create deployment manifest
    cat > /tmp/deployment.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ${PROJECT_NAME}-api
  namespace: ${PROJECT_NAME}
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ${PROJECT_NAME}-api
  template:
    metadata:
      labels:
        app: ${PROJECT_NAME}-api
    spec:
      containers:
      - name: api
        image: ${IMAGE_TAG}
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: app-secrets
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
---
apiVersion: v1
kind: Service
metadata:
  name: ${PROJECT_NAME}-api
  namespace: ${PROJECT_NAME}
spec:
  selector:
    app: ${PROJECT_NAME}-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
EOF
    
    # Apply deployment
    kubectl apply -f /tmp/deployment.yaml
    
    print_success "Kubernetes deployment created"
    print_info "Waiting for pods to be ready..."
    
    kubectl wait --for=condition=ready pod -l app=${PROJECT_NAME}-api -n ${PROJECT_NAME} --timeout=300s
    
    # Get service endpoint
    EXTERNAL_IP=$(kubectl get service ${PROJECT_NAME}-api -n ${PROJECT_NAME} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -n "$EXTERNAL_IP" ]; then
        print_success "Service available at: http://${EXTERNAL_IP}"
    else
        print_warning "External IP not yet assigned. Check with: kubectl get svc -n ${PROJECT_NAME}"
    fi
}

# Run database migrations
run_migrations() {
    print_header "Running Database Migrations"
    
    print_info "Running Alembic migrations..."
    if alembic upgrade head; then
        print_success "Migrations completed successfully"
    else
        print_error "Migration failed"
        exit 1
    fi
}

# Main deployment flow
main() {
    print_header "AI Road Trip Storyteller - Quick Deploy"
    
    # Check prerequisites
    check_prerequisites
    
    # Select deployment target
    echo "Select deployment target:"
    echo "1) Cloud Run (recommended for quick start)"
    echo "2) Kubernetes (for production scale)"
    echo "3) Local Docker only"
    read -p "Enter choice (1-3): " choice
    
    case $choice in
        1)
            # Build and deploy to Cloud Run
            IMAGE_TAG=$(build_image)
            push_image "${IMAGE_TAG}"
            
            # Run migrations
            read -p "Run database migrations? (y/N): " run_mig
            if [[ $run_mig =~ ^[Yy]$ ]]; then
                run_migrations
            fi
            
            deploy_cloud_run "${IMAGE_TAG}"
            
            print_header "Deployment Complete!"
            print_info "Next steps:"
            echo "  1. Test the health endpoint"
            echo "  2. Configure your domain DNS"
            echo "  3. Set up monitoring alerts"
            echo "  4. Deploy mobile apps"
            ;;
            
        2)
            # Build and deploy to Kubernetes
            IMAGE_TAG=$(build_image)
            push_image "${IMAGE_TAG}"
            
            # Create secrets
            print_info "Creating Kubernetes secrets..."
            kubectl create secret generic app-secrets --from-env-file=.env -n ${PROJECT_NAME} --dry-run=client -o yaml | kubectl apply -f -
            
            deploy_kubernetes "${IMAGE_TAG}"
            ;;
            
        3)
            # Local Docker only
            IMAGE_TAG=$(build_image)
            
            print_header "Running Locally"
            print_info "Starting services with Docker Compose..."
            
            docker-compose up -d
            
            print_success "Services started locally"
            print_info "API available at: http://localhost:8000"
            print_info "Stop with: docker-compose down"
            ;;
            
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
    
    print_success "Deployment completed successfully! 🎉"
}

# Run main function
main "$@"