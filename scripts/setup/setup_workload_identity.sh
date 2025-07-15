#!/bin/bash
# Setup Workload Identity for Secret Manager access
# This script configures GKE Workload Identity to allow pods to access Google Secret Manager

set -euo pipefail

# Configuration
PROJECT_ID="${1:-${GOOGLE_AI_PROJECT_ID}}"
CLUSTER_NAME="${2:-roadtrip-cluster}"
CLUSTER_ZONE="${3:-us-central1-a}"
NAMESPACE="production"
KSA_NAME="roadtrip-app"  # Kubernetes Service Account
GSA_NAME="roadtrip-workload-identity"  # Google Service Account

if [ -z "$PROJECT_ID" ]; then
    echo "Error: Project ID not provided"
    echo "Usage: $0 <PROJECT_ID> [CLUSTER_NAME] [CLUSTER_ZONE]"
    exit 1
fi

echo "Setting up Workload Identity for project: $PROJECT_ID"
echo "Cluster: $CLUSTER_NAME in $CLUSTER_ZONE"
echo "Namespace: $NAMESPACE"
echo "Kubernetes SA: $KSA_NAME"
echo "Google SA: $GSA_NAME"
echo ""

# Set project
gcloud config set project $PROJECT_ID

# 1. Enable required APIs
echo "1. Enabling required APIs..."
gcloud services enable \
    container.googleapis.com \
    secretmanager.googleapis.com \
    iam.googleapis.com

# 2. Get cluster credentials
echo "2. Getting cluster credentials..."
gcloud container clusters get-credentials $CLUSTER_NAME --zone $CLUSTER_ZONE

# 3. Create namespace if it doesn't exist
echo "3. Creating namespace if needed..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# 4. Create Google Service Account
echo "4. Creating Google Service Account..."
gcloud iam service-accounts create $GSA_NAME \
    --display-name="Road Trip Workload Identity SA" \
    --description="Service account for GKE workload identity to access Secret Manager" \
    || echo "Service account already exists"

# 5. Grant Secret Manager permissions to GSA
echo "5. Granting Secret Manager permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor"

# Optional: If you need to create secrets too
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretVersionManager"

# 6. Create Kubernetes Service Account
echo "6. Creating Kubernetes Service Account..."
kubectl create serviceaccount $KSA_NAME -n $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# 7. Add annotation for Workload Identity
echo "7. Annotating Kubernetes Service Account..."
kubectl annotate serviceaccount $KSA_NAME \
    -n $NAMESPACE \
    iam.gke.io/gcp-service-account="${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --overwrite

# 8. Create IAM policy binding
echo "8. Creating IAM policy binding..."
gcloud iam service-accounts add-iam-policy-binding \
    "${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role roles/iam.workloadIdentityUser \
    --member "serviceAccount:${PROJECT_ID}.svc.id.goog[${NAMESPACE}/${KSA_NAME}]"

# 9. Verify setup
echo ""
echo "9. Verifying setup..."
echo "Google Service Account:"
gcloud iam service-accounts describe "${GSA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo ""
echo "Kubernetes Service Account:"
kubectl get serviceaccount $KSA_NAME -n $NAMESPACE -o yaml

echo ""
echo "✅ Workload Identity setup complete!"
echo ""
echo "Next steps:"
echo "1. Deploy your application using the '$KSA_NAME' service account"
echo "2. Your pods will automatically have access to Secret Manager"
echo "3. Test with: kubectl run -it --rm debug --image=google/cloud-sdk:slim --restart=Never --serviceaccount=$KSA_NAME -n $NAMESPACE -- gcloud secrets list"
echo ""
echo "To use in your deployment, ensure you have:"
echo "  spec:"
echo "    serviceAccountName: $KSA_NAME"
echo ""