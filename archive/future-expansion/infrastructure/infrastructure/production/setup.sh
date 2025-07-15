#!/bin/bash
#
# Production Infrastructure Setup Script
# AI Road Trip Storyteller
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 AI Road Trip Storyteller - Production Infrastructure Setup${NC}"
echo "============================================================"
echo ""

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    # Check for gcloud
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}❌ gcloud CLI not found. Please install Google Cloud SDK${NC}"
        exit 1
    fi
    
    # Check for terraform
    if ! command -v terraform &> /dev/null; then
        echo -e "${RED}❌ Terraform not found. Please install Terraform${NC}"
        exit 1
    fi
    
    # Check gcloud auth
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" &> /dev/null; then
        echo -e "${RED}❌ Not authenticated to Google Cloud. Run: gcloud auth login${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All prerequisites met${NC}"
}

# Setup project
setup_project() {
    echo ""
    echo -e "${YELLOW}Setting up Google Cloud project...${NC}"
    
    # Get or create project
    read -p "Enter your GCP project ID (or press Enter to create new): " PROJECT_ID
    
    if [ -z "$PROJECT_ID" ]; then
        PROJECT_ID="roadtrip-prod-$(date +%Y%m%d)"
        echo "Creating new project: $PROJECT_ID"
        gcloud projects create $PROJECT_ID --name="AI Road Trip Storyteller Production"
    fi
    
    # Set project
    gcloud config set project $PROJECT_ID
    
    # Link billing account
    echo ""
    echo "Available billing accounts:"
    gcloud billing accounts list
    read -p "Enter billing account ID: " BILLING_ACCOUNT
    gcloud billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT
    
    echo -e "${GREEN}✅ Project configured: $PROJECT_ID${NC}"
}

# Enable APIs
enable_apis() {
    echo ""
    echo -e "${YELLOW}Enabling required APIs...${NC}"
    
    APIS=(
        "compute.googleapis.com"
        "container.googleapis.com"
        "sqladmin.googleapis.com"
        "redis.googleapis.com"
        "storage.googleapis.com"
        "cloudrun.googleapis.com"
        "secretmanager.googleapis.com"
        "monitoring.googleapis.com"
        "logging.googleapis.com"
        "cloudtrace.googleapis.com"
        "cloudbuild.googleapis.com"
        "artifactregistry.googleapis.com"
        "certificatemanager.googleapis.com"
        "vpcaccess.googleapis.com"
        "servicenetworking.googleapis.com"
    )
    
    for api in "${APIS[@]}"; do
        echo "Enabling $api..."
        gcloud services enable $api
    done
    
    echo -e "${GREEN}✅ All APIs enabled${NC}"
}

# Create service account
create_service_account() {
    echo ""
    echo -e "${YELLOW}Creating Terraform service account...${NC}"
    
    SA_NAME="terraform-deploy"
    SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Create service account
    gcloud iam service-accounts create $SA_NAME \
        --display-name="Terraform Deployment Account" \
        --description="Service account for Terraform infrastructure deployment"
    
    # Grant roles
    ROLES=(
        "roles/editor"
        "roles/compute.admin"
        "roles/container.admin"
        "roles/cloudsql.admin"
        "roles/redis.admin"
        "roles/storage.admin"
        "roles/run.admin"
        "roles/secretmanager.admin"
        "roles/monitoring.admin"
        "roles/logging.admin"
        "roles/billing.projectManager"
    )
    
    for role in "${ROLES[@]}"; do
        echo "Granting $role..."
        gcloud projects add-iam-policy-binding $PROJECT_ID \
            --member="serviceAccount:${SA_EMAIL}" \
            --role="$role"
    done
    
    # Create and download key
    gcloud iam service-accounts keys create terraform-sa-key.json \
        --iam-account=$SA_EMAIL
    
    echo -e "${GREEN}✅ Service account created: $SA_EMAIL${NC}"
    echo -e "${YELLOW}⚠️  Service account key saved to: terraform-sa-key.json${NC}"
    echo -e "${YELLOW}⚠️  Keep this file secure and do not commit to git!${NC}"
}

# Create state bucket
create_state_bucket() {
    echo ""
    echo -e "${YELLOW}Creating Terraform state bucket...${NC}"
    
    BUCKET_NAME="${PROJECT_ID}-terraform-state"
    
    # Create bucket
    gsutil mb -p $PROJECT_ID -c STANDARD -l us-central1 gs://$BUCKET_NAME/
    
    # Enable versioning
    gsutil versioning set on gs://$BUCKET_NAME/
    
    # Set lifecycle rule to delete old versions after 30 days
    cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 30,
          "isLive": false
        }
      }
    ]
  }
}
EOF
    
    gsutil lifecycle set lifecycle.json gs://$BUCKET_NAME/
    rm lifecycle.json
    
    echo -e "${GREEN}✅ State bucket created: gs://$BUCKET_NAME/${NC}"
}

# Initialize secrets
init_secrets() {
    echo ""
    echo -e "${YELLOW}Initializing secrets in Secret Manager...${NC}"
    
    # Database password
    DB_PASSWORD=$(openssl rand -base64 32)
    echo -n "$DB_PASSWORD" | gcloud secrets create db-password --data-file=-
    
    # JWT secret
    JWT_SECRET=$(openssl rand -base64 64)
    echo -n "$JWT_SECRET" | gcloud secrets create jwt-secret --data-file=-
    
    echo -e "${GREEN}✅ Initial secrets created${NC}"
    echo -e "${YELLOW}⚠️  Database password: $DB_PASSWORD${NC}"
    echo -e "${YELLOW}⚠️  Save this password securely!${NC}"
}

# Setup Terraform
setup_terraform() {
    echo ""
    echo -e "${YELLOW}Setting up Terraform...${NC}"
    
    # Create terraform.tfvars
    cat > terraform.tfvars <<EOF
# Auto-generated Terraform variables
project_id = "$PROJECT_ID"
billing_account = "$BILLING_ACCOUNT"

# Update these values as needed
region = "us-central1"
zone = "us-central1-a"
environment = "production"

# Database configuration
db_instance_name = "roadtrip-prod-db"
db_tier = "db-n1-standard-4"
db_disk_size = 100
db_high_availability = true

# Redis configuration
redis_instance_name = "roadtrip-prod-cache"
redis_tier = "STANDARD_HA"
redis_memory_size = 5

# Storage configuration
storage_bucket_name = "${PROJECT_ID}-media"

# Cloud Run configuration
cloud_run_min_instances = 3
cloud_run_max_instances = 100

# Monitoring
notification_channels = []  # Add your notification channels here

# Budget
billing_budget_amount = 5000
EOF
    
    # Update backend configuration
    sed -i "s/roadtrip-terraform-state/${PROJECT_ID}-terraform-state/g" main.tf
    
    # Initialize Terraform
    export GOOGLE_APPLICATION_CREDENTIALS="terraform-sa-key.json"
    terraform init
    
    echo -e "${GREEN}✅ Terraform initialized${NC}"
}

# Create initial resources
create_initial_resources() {
    echo ""
    echo -e "${YELLOW}Creating initial resources...${NC}"
    
    # Create artifact registry for Docker images
    gcloud artifacts repositories create roadtrip-images \
        --repository-format=docker \
        --location=us-central1 \
        --description="Docker images for AI Road Trip Storyteller"
    
    # Configure Docker auth
    gcloud auth configure-docker us-central1-docker.pkg.dev
    
    echo -e "${GREEN}✅ Initial resources created${NC}"
}

# Generate deployment guide
generate_guide() {
    echo ""
    echo -e "${YELLOW}Generating deployment guide...${NC}"
    
    cat > DEPLOYMENT_GUIDE.md <<EOF
# Production Deployment Guide

## Project Information
- **Project ID**: $PROJECT_ID
- **Region**: us-central1
- **State Bucket**: gs://${PROJECT_ID}-terraform-state/

## Prerequisites Completed
- ✅ Google Cloud project created and configured
- ✅ APIs enabled
- ✅ Service account created
- ✅ Terraform state bucket created
- ✅ Initial secrets created
- ✅ Artifact registry created

## Next Steps

### 1. Deploy Infrastructure
\`\`\`bash
# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS="terraform-sa-key.json"

# Plan deployment
terraform plan

# Apply infrastructure
terraform apply
\`\`\`

### 2. Build and Deploy Application
\`\`\`bash
# Build Docker image
docker build -t us-central1-docker.pkg.dev/$PROJECT_ID/roadtrip-images/app:latest .

# Push to registry
docker push us-central1-docker.pkg.dev/$PROJECT_ID/roadtrip-images/app:latest

# Deploy to Cloud Run (handled by Terraform)
\`\`\`

### 3. Configure Secrets
Add your API keys to Secret Manager:
\`\`\`bash
echo -n "YOUR_API_KEY" | gcloud secrets create google-maps-api-key --data-file=-
echo -n "YOUR_API_KEY" | gcloud secrets create ticketmaster-api-key --data-file=-
echo -n "YOUR_API_KEY" | gcloud secrets create openweathermap-api-key --data-file=-
echo -n "YOUR_API_KEY" | gcloud secrets create recreation-gov-api-key --data-file=-
\`\`\`

### 4. Configure Domain (Optional)
1. Reserve static IP: \`gcloud compute addresses create roadtrip-prod-ip --global\`
2. Configure DNS to point to the IP
3. Update load balancer configuration

### 5. Setup Monitoring
1. Create notification channel in Cloud Console
2. Update terraform.tfvars with channel ID
3. Run \`terraform apply\` to configure alerts

## Important URLs
- **Cloud Console**: https://console.cloud.google.com/home/dashboard?project=$PROJECT_ID
- **Cloud Run**: https://console.cloud.google.com/run?project=$PROJECT_ID
- **Secret Manager**: https://console.cloud.google.com/security/secret-manager?project=$PROJECT_ID
- **Monitoring**: https://console.cloud.google.com/monitoring?project=$PROJECT_ID

## Security Checklist
- [ ] All secrets stored in Secret Manager
- [ ] Service accounts follow least privilege
- [ ] VPC configured with private subnets
- [ ] Cloud SQL using private IP
- [ ] SSL certificates configured
- [ ] Backup policies enabled
- [ ] Monitoring alerts configured

## Support
For issues or questions, refer to the infrastructure documentation or contact the DevOps team.
EOF
    
    echo -e "${GREEN}✅ Deployment guide created: DEPLOYMENT_GUIDE.md${NC}"
}

# Main execution
main() {
    check_prerequisites
    setup_project
    enable_apis
    create_service_account
    create_state_bucket
    init_secrets
    setup_terraform
    create_initial_resources
    generate_guide
    
    echo ""
    echo -e "${GREEN}🎉 Production infrastructure setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Review and update terraform.tfvars"
    echo "2. Add your API keys to Secret Manager"
    echo "3. Run: terraform plan"
    echo "4. Run: terraform apply"
    echo ""
    echo -e "${YELLOW}Important files created:${NC}"
    echo "- terraform-sa-key.json (keep secure!)"
    echo "- terraform.tfvars (review and update)"
    echo "- DEPLOYMENT_GUIDE.md (follow for deployment)"
}

# Run main function
main