#!/bin/bash
# Setup script for Road Trip GCP infrastructure

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check for gcloud
    if ! command -v gcloud &> /dev/null; then
        print_error "gcloud CLI not found. Please install Google Cloud SDK."
        exit 1
    fi
    
    # Check for terraform
    if ! command -v terraform &> /dev/null; then
        print_error "Terraform not found. Please install Terraform."
        exit 1
    fi
    
    # Check for kubectl
    if ! command -v kubectl &> /dev/null; then
        print_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    
    print_status "All prerequisites met!"
}

# Setup GCP project
setup_gcp_project() {
    print_status "Setting up GCP project..."
    
    # Get project ID
    read -p "Enter your GCP Project ID: " PROJECT_ID
    
    # Set the project
    gcloud config set project $PROJECT_ID
    
    # Enable required APIs
    print_status "Enabling required GCP APIs..."
    gcloud services enable \
        compute.googleapis.com \
        container.googleapis.com \
        servicenetworking.googleapis.com \
        cloudresourcemanager.googleapis.com \
        redis.googleapis.com \
        sqladmin.googleapis.com \
        secretmanager.googleapis.com \
        monitoring.googleapis.com \
        logging.googleapis.com \
        cloudbuild.googleapis.com \
        artifactregistry.googleapis.com \
        certificatemanager.googleapis.com \
        dns.googleapis.com
    
    print_status "GCP APIs enabled successfully!"
}

# Create terraform state bucket
create_state_bucket() {
    print_status "Creating Terraform state bucket..."
    
    BUCKET_NAME="${PROJECT_ID}-terraform-state"
    
    # Check if bucket exists
    if gsutil ls -b gs://${BUCKET_NAME} &> /dev/null; then
        print_warning "Terraform state bucket already exists"
    else
        gsutil mb -p ${PROJECT_ID} -c STANDARD -l ${REGION:-us-central1} gs://${BUCKET_NAME}
        gsutil versioning set on gs://${BUCKET_NAME}
        print_status "Terraform state bucket created: gs://${BUCKET_NAME}"
    fi
}

# Initialize Terraform
init_terraform() {
    print_status "Initializing Terraform..."
    
    cd terraform
    
    # Create backend config
    cat > backend.tf <<EOF
terraform {
  backend "gcs" {
    bucket = "${PROJECT_ID}-terraform-state"
    prefix = "terraform/state"
  }
}
EOF
    
    # Copy example tfvars if not exists
    if [ ! -f terraform.tfvars ]; then
        cp terraform.tfvars.example terraform.tfvars
        print_warning "Please edit terraform.tfvars with your configuration"
        read -p "Press enter when ready to continue..."
    fi
    
    # Initialize
    terraform init
    
    print_status "Terraform initialized successfully!"
}

# Create service account for CI/CD
create_cicd_service_account() {
    print_status "Creating CI/CD service account..."
    
    SA_NAME="roadtrip-cicd-sa"
    SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Create service account
    gcloud iam service-accounts create ${SA_NAME} \
        --display-name="Road Trip CI/CD Service Account"
    
    # Grant necessary roles
    for role in \
        "roles/container.developer" \
        "roles/storage.admin" \
        "roles/cloudbuild.builds.editor" \
        "roles/artifactregistry.writer" \
        "roles/iam.serviceAccountUser"
    do
        gcloud projects add-iam-policy-binding ${PROJECT_ID} \
            --member="serviceAccount:${SA_EMAIL}" \
            --role="${role}"
    done
    
    # Create and download key
    gcloud iam service-accounts keys create cicd-key.json \
        --iam-account=${SA_EMAIL}
    
    print_status "CI/CD service account created. Key saved to cicd-key.json"
    print_warning "Keep this key secure and add it to your GitHub secrets as GCP_SA_KEY"
}

# Main execution
main() {
    print_status "Starting Road Trip infrastructure setup..."
    
    check_prerequisites
    setup_gcp_project
    create_state_bucket
    init_terraform
    create_cicd_service_account
    
    print_status "Setup complete!"
    print_status "Next steps:"
    echo "1. Edit terraform/terraform.tfvars with your configuration"
    echo "2. Run 'cd terraform && terraform plan' to review changes"
    echo "3. Run 'terraform apply' to create infrastructure"
    echo "4. Add cicd-key.json content to GitHub secrets as GCP_SA_KEY"
    echo "5. Configure your domain DNS to point to the load balancer IP"
}

# Run main function
main