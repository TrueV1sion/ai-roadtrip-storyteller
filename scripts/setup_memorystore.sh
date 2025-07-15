#!/bin/bash
# Setup Memorystore Redis Instance for Production
# Must have gcloud CLI configured first

set -e

PROJECT_ID="roadtrip-460720"
REGION="us-central1"
INSTANCE_NAME="roadtrip-cache"
REDIS_VERSION="redis_6_x"
TIER="basic"
MEMORY_SIZE_GB=1

echo "=========================================="
echo "MEMORYSTORE REDIS SETUP FOR PRODUCTION"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=========================================="

# Step 1: Enable required APIs
echo -e "\n1. Enabling required APIs..."
gcloud services enable redis.googleapis.com --project=$PROJECT_ID
gcloud services enable servicenetworking.googleapis.com --project=$PROJECT_ID

# Step 2: Reserve IP range for VPC peering
echo -e "\n2. Reserving IP range for VPC peering..."
gcloud compute addresses create google-managed-services-default \
    --global \
    --purpose=VPC_PEERING \
    --prefix-length=16 \
    --network=default \
    --project=$PROJECT_ID || echo "IP range already exists"

# Step 3: Create VPC peering connection
echo -e "\n3. Creating VPC peering connection..."
gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges=google-managed-services-default \
    --network=default \
    --project=$PROJECT_ID || echo "VPC peering already exists"

# Step 4: Create Memorystore Redis instance
echo -e "\n4. Creating Memorystore Redis instance..."
gcloud redis instances create $INSTANCE_NAME \
    --size=$MEMORY_SIZE_GB \
    --region=$REGION \
    --redis-version=$REDIS_VERSION \
    --tier=$TIER \
    --display-name="RoadTrip Cache" \
    --project=$PROJECT_ID

# Step 5: Get Redis instance details
echo -e "\n5. Getting Redis instance details..."
REDIS_HOST=$(gcloud redis instances describe $INSTANCE_NAME \
    --region=$REGION \
    --format="value(host)" \
    --project=$PROJECT_ID)

REDIS_PORT=$(gcloud redis instances describe $INSTANCE_NAME \
    --region=$REGION \
    --format="value(port)" \
    --project=$PROJECT_ID)

# Step 6: Store Redis URL in Secret Manager
echo -e "\n6. Storing Redis URL in Secret Manager..."
REDIS_URL="redis://$REDIS_HOST:$REDIS_PORT"
echo -n "$REDIS_URL" | gcloud secrets create redis-url \
    --data-file=- \
    --replication-policy="automatic" \
    --project=$PROJECT_ID

# Step 7: Grant Cloud Run access to secret
echo -e "\n7. Granting Cloud Run access to secret..."
gcloud secrets add-iam-policy-binding redis-url \
    --member="serviceAccount:roadtrip-460720-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

# Step 8: Create VPC connector for Cloud Run
echo -e "\n8. Creating VPC connector for Cloud Run..."
gcloud compute networks vpc-access connectors create roadtrip-connector \
    --region=$REGION \
    --subnet=default \
    --subnet-project=$PROJECT_ID \
    --min-instances=2 \
    --max-instances=10 \
    --machine-type=e2-micro \
    --project=$PROJECT_ID || echo "VPC connector already exists"

# Step 9: Output connection info
echo -e "\n=========================================="
echo "MEMORYSTORE SETUP COMPLETE!"
echo "=========================================="
echo "Instance: $INSTANCE_NAME"
echo "Host: $REDIS_HOST"
echo "Port: $REDIS_PORT"
echo "Redis URL: $REDIS_URL"
echo ""
echo "Redis URL stored in Secret Manager as: redis-url"
echo "VPC Connector: roadtrip-connector"
echo ""
echo "To use in Cloud Run:"
echo "1. Add VPC connector: --vpc-connector=roadtrip-connector"
echo "2. Retrieve Redis URL from Secret Manager"
echo ""
echo "Testing connection (from Compute Engine instance in same VPC):"
echo "  redis-cli -h $REDIS_HOST -p $REDIS_PORT ping"
echo "=========================================="