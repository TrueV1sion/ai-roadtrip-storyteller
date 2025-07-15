#!/bin/bash

# Setup VPC peering for staging environment

set -e

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Setting up VPC Peering for Staging ===${NC}"
echo ""

PROJECT_ID="roadtrip-460720"
REGION="us-central1"

# 1. Allocate IP range for VPC peering
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if VPC peering already exists
print_status "Checking existing VPC peering..."
if gcloud compute addresses describe roadtrip-staging-ip-range --global 2>/dev/null; then
    print_status "IP range already allocated"
else
    print_status "Allocating IP range for VPC peering..."
    gcloud compute addresses create roadtrip-staging-ip-range \
        --global \
        --purpose=VPC_PEERING \
        --prefix-length=24 \
        --network=roadtrip-vpc-staging \
        --project=$PROJECT_ID
    print_success "IP range allocated"
fi

# 2. Create service connection
print_status "Creating service networking connection..."
if gcloud services vpc-peerings list --network=roadtrip-vpc-staging --service=servicenetworking.googleapis.com 2>/dev/null | grep -q "servicenetworking"; then
    print_status "Service connection already exists"
else
    gcloud services vpc-peerings connect \
        --service=servicenetworking.googleapis.com \
        --ranges=roadtrip-staging-ip-range \
        --network=roadtrip-vpc-staging \
        --project=$PROJECT_ID
    print_success "Service connection created"
fi

# 3. Enable private Google access on subnet
print_status "Enabling private Google access on subnet..."
gcloud compute networks subnets update roadtrip-subnet-staging \
    --region=$REGION \
    --enable-private-ip-google-access \
    --project=$PROJECT_ID
print_success "Private Google access enabled"

# 4. Create Cloud NAT for outbound connectivity
print_status "Creating Cloud NAT..."
if gcloud compute routers describe roadtrip-staging-router --region=$REGION 2>/dev/null; then
    print_status "Router already exists"
else
    gcloud compute routers create roadtrip-staging-router \
        --region=$REGION \
        --network=roadtrip-vpc-staging \
        --project=$PROJECT_ID
    print_success "Router created"
fi

if gcloud compute routers nats describe roadtrip-staging-nat --router=roadtrip-staging-router --region=$REGION 2>/dev/null; then
    print_status "NAT already exists"
else
    gcloud compute routers nats create roadtrip-staging-nat \
        --router=roadtrip-staging-router \
        --region=$REGION \
        --nat-all-subnet-ip-ranges \
        --auto-allocate-nat-external-ips \
        --project=$PROJECT_ID
    print_success "Cloud NAT created"
fi

echo ""
echo -e "${GREEN}=== VPC Peering Setup Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Deploy Cloud SQL with private IP"
echo "2. Deploy Redis with private service access"
echo "3. Create VPC connector for Cloud Run"