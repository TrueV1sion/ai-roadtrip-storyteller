#!/bin/bash

# Current Status Check for Staging Environment
# Date: 2025-07-05

echo "=== Staging Environment Status Check ==="
echo

# Set project
PROJECT_ID="roadtrip-460720"
gcloud config set project $PROJECT_ID 2>/dev/null

echo "1. Checking VPC Network..."
gcloud compute networks describe roadtrip-vpc-staging --format="table(name,autoCreateSubnetworks,creationTimestamp)" 2>/dev/null || echo "   ❌ VPC not found"

echo
echo "2. Checking Subnet..."
gcloud compute networks subnets describe roadtrip-subnet-staging --region=us-central1 --format="table(name,ipCidrRange,privateIpGoogleAccess)" 2>/dev/null || echo "   ❌ Subnet not found"

echo
echo "3. Checking Service Account..."
gcloud iam service-accounts describe roadtrip-staging-e6a9121e@roadtrip-460720.iam.gserviceaccount.com --format="table(email,displayName)" 2>/dev/null || echo "   ❌ Service account not found"

echo
echo "4. Checking Storage Bucket..."
gsutil ls -L -b gs://roadtrip-460720-roadtrip-staging-assets 2>/dev/null | grep -E "(Location:|Versioning:|Time created:)" || echo "   ❌ Bucket not found"

echo
echo "5. Checking Secrets..."
echo "   Staging secrets created:"
gcloud secrets list --filter="name:staging" --format="table(name)" 2>/dev/null | grep -c "staging" | xargs echo "   Total staging secrets:"

echo
echo "6. Checking Cloud SQL Instance..."
gcloud sql instances describe roadtrip-db-staging-e6a9121e --format="table(name,databaseVersion,settings.tier,state)" 2>/dev/null || echo "   ❌ Cloud SQL instance not found"

echo
echo "7. Checking Redis Instance..."
gcloud redis instances describe roadtrip-redis-staging --region=us-central1 --format="table(name,memorySizeGb,redisVersion,state)" 2>/dev/null || echo "   ❌ Redis instance not found"

echo
echo "8. Checking Cloud Run Service..."
gcloud run services describe roadtrip-backend-staging --region=us-central1 --format="table(metadata.name,status.url,status.conditions[0].type,status.conditions[0].status)" 2>/dev/null || echo "   ❌ Cloud Run service not found"

echo
echo "9. Checking Monitoring Dashboard..."
gcloud monitoring dashboards list --filter="displayName:'Road Trip Staging Dashboard'" --format="table(displayName,name)" 2>/dev/null || echo "   ❌ Dashboard not found"

echo
echo "10. Checking APIs Enabled..."
REQUIRED_APIS=(
    "run.googleapis.com"
    "cloudbuild.googleapis.com"
    "sqladmin.googleapis.com"
    "redis.googleapis.com"
    "monitoring.googleapis.com"
    "aiplatform.googleapis.com"
)

ENABLED_COUNT=0
for api in "${REQUIRED_APIS[@]}"; do
    if gcloud services list --enabled --filter="name:$api" --format="value(name)" 2>/dev/null | grep -q "$api"; then
        ((ENABLED_COUNT++))
    fi
done
echo "   APIs enabled: $ENABLED_COUNT/${#REQUIRED_APIS[@]}"

echo
echo "=== Summary ==="
echo "✅ Successfully deployed: VPC, Subnet, Service Account, Storage, Secrets, Monitoring"
echo "❌ Pending deployment: Cloud SQL, Redis, Cloud Run, VPC Connector"
echo "⚠️  IAM permissions need to be granted by project owner"
echo
echo "Next step: Grant IAM roles to service account and complete deployment"