#!/bin/bash
# Master deployment script for AI Road Trip Storyteller
# Orchestrates the complete deployment of all services

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-roadtrip-mvp}"
REGION="${REGION:-us-central1}"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Timing
SCRIPT_START=$(date +%s)

echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}       AI Road Trip Storyteller - Master Deployment${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Project: ${PROJECT_ID}${NC}"
echo -e "${BLUE}Region: ${REGION}${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"

# Function to check prerequisites
check_prerequisites() {
    echo -e "\n${YELLOW}📋 Checking prerequisites...${NC}"
    
    # Check gcloud
    if ! command -v gcloud &> /dev/null; then
        echo -e "${RED}❌ gcloud CLI not found${NC}"
        exit 1
    fi
    
    # Check docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker not found${NC}"
        exit 1
    fi
    
    # Check project
    gcloud config set project ${PROJECT_ID}
    
    echo -e "${GREEN}✅ Prerequisites satisfied${NC}"
}

# Function to run database migrations
run_migrations() {
    echo -e "\n${PURPLE}🗄️  Running database migrations...${NC}"
    ./scripts/deployment/run-migrations.sh
    echo -e "${GREEN}✅ Migrations completed${NC}"
}

# Function to deploy Knowledge Graph
deploy_knowledge_graph() {
    echo -e "\n${PURPLE}🧠 Deploying Knowledge Graph...${NC}"
    ./scripts/deployment/deploy-knowledge-graph.sh
    echo -e "${GREEN}✅ Knowledge Graph deployed${NC}"
}

# Function to deploy backend
deploy_backend() {
    echo -e "\n${PURPLE}🚀 Deploying Backend API...${NC}"
    
    # Get Knowledge Graph URL
    KG_URL=$(gcloud run services describe roadtrip-knowledge-graph \
        --region ${REGION} \
        --format 'value(status.url)')
    
    export KNOWLEDGE_GRAPH_URL=$KG_URL
    
    # Submit to Cloud Build
    gcloud builds submit \
        --config=backend/cloudbuild.yaml \
        --substitutions="_REGION=${REGION},_KG_SERVICE_URL=${KG_URL}" \
        .
    
    echo -e "${GREEN}✅ Backend deployed${NC}"
}

# Function to deploy monitoring
deploy_monitoring() {
    echo -e "\n${PURPLE}📊 Deploying monitoring stack...${NC}"
    
    # Create monitoring namespace
    docker network create monitoring 2>/dev/null || true
    
    # Deploy Prometheus and Grafana
    docker-compose -f infrastructure/docker/docker-compose.monitoring.yml up -d
    
    echo -e "${GREEN}✅ Monitoring deployed${NC}"
    echo -e "${BLUE}   Prometheus: http://localhost:9090${NC}"
    echo -e "${BLUE}   Grafana: http://localhost:3000${NC}"
}

# Function to build mobile apps
build_mobile_apps() {
    echo -e "\n${PURPLE}📱 Building mobile apps...${NC}"
    
    read -p "Build mobile apps for production? (yes/no): " build_mobile
    if [ "$build_mobile" == "yes" ]; then
        cd mobile
        ../scripts/deployment/build-mobile-production.sh all production
        cd ..
        echo -e "${GREEN}✅ Mobile builds submitted${NC}"
    else
        echo -e "${YELLOW}⏭️  Skipping mobile builds${NC}"
    fi
}

# Function to verify deployment
verify_deployment() {
    echo -e "\n${YELLOW}🔍 Verifying deployment...${NC}"
    
    # Get service URLs
    BACKEND_URL=$(gcloud run services describe roadtrip-backend \
        --region ${REGION} \
        --format 'value(status.url)')
    
    KG_URL=$(gcloud run services describe roadtrip-knowledge-graph \
        --region ${REGION} \
        --format 'value(status.url)')
    
    # Test endpoints
    echo "Testing Backend health..."
    if curl -f -s "${BACKEND_URL}/health" > /dev/null; then
        echo -e "${GREEN}✅ Backend health check passed${NC}"
    else
        echo -e "${RED}❌ Backend health check failed${NC}"
        exit 1
    fi
    
    echo "Testing Knowledge Graph..."
    if curl -f -s "${KG_URL}/api/health" > /dev/null; then
        echo -e "${GREEN}✅ Knowledge Graph health check passed${NC}"
    else
        echo -e "${RED}❌ Knowledge Graph health check failed${NC}"
        exit 1
    fi
    
    # Test new endpoints
    echo "Testing Journey Tracking..."
    curl -f -s "${BACKEND_URL}/api/journey-tracking/status" > /dev/null && \
        echo -e "${GREEN}✅ Journey Tracking active${NC}"
    
    echo "Testing Story Timing..."
    curl -f -s "${BACKEND_URL}/api/story-timing/status" > /dev/null && \
        echo -e "${GREEN}✅ Story Timing active${NC}"
}

# Function to display summary
display_summary() {
    SCRIPT_END=$(date +%s)
    DURATION=$((SCRIPT_END - SCRIPT_START))
    
    echo -e "\n${CYAN}════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                    Deployment Summary${NC}"
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
    
    # Get service URLs
    BACKEND_URL=$(gcloud run services describe roadtrip-backend \
        --region ${REGION} \
        --format 'value(status.url)')
    
    KG_URL=$(gcloud run services describe roadtrip-knowledge-graph \
        --region ${REGION} \
        --format 'value(status.url)')
    
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
    echo -e "${BLUE}Duration: ${DURATION} seconds${NC}"
    echo ""
    echo -e "${PURPLE}Service URLs:${NC}"
    echo -e "  Backend API: ${BACKEND_URL}"
    echo -e "  API Docs: ${BACKEND_URL}/docs"
    echo -e "  Knowledge Graph: ${KG_URL}"
    echo -e "  KG Dashboard: ${KG_URL}"
    echo ""
    echo -e "${PURPLE}Next Steps:${NC}"
    echo -e "  1. Monitor deployment: ${BACKEND_URL}/metrics"
    echo -e "  2. Check logs: gcloud logging read"
    echo -e "  3. View dashboards: http://localhost:3000"
    echo -e "  4. Run smoke tests: ./scripts/test/smoke-tests.sh"
    echo ""
    echo -e "${CYAN}════════════════════════════════════════════════════════════════${NC}"
}

# Main execution
main() {
    echo -e "${YELLOW}⚠️  This will deploy to ${ENVIRONMENT} environment${NC}"
    read -p "Continue? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        echo -e "${RED}❌ Deployment cancelled${NC}"
        exit 0
    fi
    
    check_prerequisites
    run_migrations
    deploy_knowledge_graph
    deploy_backend
    deploy_monitoring
    build_mobile_apps
    verify_deployment
    display_summary
}

# Run main function
main