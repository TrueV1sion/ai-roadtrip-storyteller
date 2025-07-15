#!/bin/bash

# Deploy Monitoring Stack Script
# This script deploys Prometheus, Grafana, and exporters for production monitoring

set -e

echo "🚀 Deploying AI Road Trip Storyteller Monitoring Stack..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Docker is not installed${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Docker Compose is not installed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Prerequisites satisfied${NC}"
}

# Create necessary directories
create_directories() {
    echo -e "${YELLOW}Creating monitoring directories...${NC}"
    
    mkdir -p monitoring/data/prometheus
    mkdir -p monitoring/data/grafana
    mkdir -p monitoring/logs
    
    # Set permissions for Grafana
    chmod 777 monitoring/data/grafana
    
    echo -e "${GREEN}✓ Directories created${NC}"
}

# Deploy monitoring stack
deploy_monitoring() {
    echo -e "${YELLOW}Deploying monitoring services...${NC}"
    
    # Start monitoring profile
    docker-compose --profile monitoring up -d
    
    # Wait for services to be ready
    echo -e "${YELLOW}Waiting for services to start...${NC}"
    sleep 30
    
    # Check service health
    if docker-compose ps | grep -q "monitoring.*Up"; then
        echo -e "${GREEN}✓ Monitoring services deployed${NC}"
    else
        echo -e "${RED}Failed to deploy monitoring services${NC}"
        docker-compose logs prometheus grafana
        exit 1
    fi
}

# Configure Grafana
configure_grafana() {
    echo -e "${YELLOW}Configuring Grafana...${NC}"
    
    # Wait for Grafana to be ready
    until curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/health | grep -q "200"; do
        echo "Waiting for Grafana..."
        sleep 5
    done
    
    # Import dashboards via API
    GRAFANA_URL="http://localhost:3000"
    GRAFANA_USER="admin"
    GRAFANA_PASS="${GRAFANA_ADMIN_PASSWORD:-admin}"
    
    # Create API key
    API_KEY=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d '{"name":"deployment-key","role":"Admin"}' \
        http://${GRAFANA_USER}:${GRAFANA_PASS}@localhost:3000/api/auth/keys \
        | grep -o '"key":"[^"]*' | cut -d'"' -f4)
    
    if [ -n "$API_KEY" ]; then
        echo -e "${GREEN}✓ Grafana API key created${NC}"
        
        # Import dashboards
        for dashboard in infrastructure/monitoring/grafana-*.json; do
            if [ -f "$dashboard" ]; then
                echo "Importing dashboard: $dashboard"
                curl -s -X POST \
                    -H "Authorization: Bearer $API_KEY" \
                    -H "Content-Type: application/json" \
                    -d "@$dashboard" \
                    ${GRAFANA_URL}/api/dashboards/db
            fi
        done
    else
        echo -e "${YELLOW}⚠ Could not create API key, dashboards will be auto-provisioned${NC}"
    fi
}

# Verify deployment
verify_deployment() {
    echo -e "${YELLOW}Verifying deployment...${NC}"
    
    # Check Prometheus targets
    PROMETHEUS_TARGETS=$(curl -s http://localhost:9090/api/v1/targets | grep -o '"health":"up"' | wc -l)
    echo "Active Prometheus targets: $PROMETHEUS_TARGETS"
    
    # Check Grafana datasources
    GRAFANA_DATASOURCES=$(curl -s http://admin:${GRAFANA_ADMIN_PASSWORD:-admin}@localhost:3000/api/datasources | grep -o '"id"' | wc -l)
    echo "Configured Grafana datasources: $GRAFANA_DATASOURCES"
    
    if [ $PROMETHEUS_TARGETS -gt 0 ] && [ $GRAFANA_DATASOURCES -gt 0 ]; then
        echo -e "${GREEN}✓ Monitoring stack verified${NC}"
    else
        echo -e "${RED}Monitoring stack verification failed${NC}"
        exit 1
    fi
}

# Display access information
display_info() {
    echo -e "\n${GREEN}🎉 Monitoring Stack Deployed Successfully!${NC}"
    echo -e "\n${YELLOW}Access Information:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "Grafana:     ${GREEN}http://localhost:3000${NC}"
    echo -e "Username:    admin"
    echo -e "Password:    ${GRAFANA_ADMIN_PASSWORD:-admin}"
    echo -e "\nPrometheus:  ${GREEN}http://localhost:9090${NC}"
    echo -e "\n${YELLOW}Available Dashboards:${NC}"
    echo "• Production Overview"
    echo "• Security Dashboard"
    echo "• Infrastructure Metrics"
    echo "• Business Analytics"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Production deployment (Kubernetes)
deploy_to_kubernetes() {
    echo -e "${YELLOW}Deploying to Kubernetes...${NC}"
    
    # Apply monitoring namespace
    kubectl apply -f infrastructure/k8s/monitoring/namespace.yaml
    
    # Deploy Prometheus
    kubectl apply -f infrastructure/k8s/monitoring/prometheus-deployment.yaml
    kubectl apply -f infrastructure/k8s/monitoring/prometheus-config.yaml
    kubectl apply -f infrastructure/k8s/monitoring/prometheus-rules.yaml
    
    # Deploy Grafana
    kubectl apply -f infrastructure/k8s/monitoring/grafana-deployment.yaml
    kubectl apply -f infrastructure/k8s/monitoring/grafana-dashboards.yaml
    
    # Deploy exporters
    kubectl apply -f infrastructure/k8s/monitoring/node-exporter.yaml
    kubectl apply -f infrastructure/k8s/monitoring/postgres-exporter.yaml
    kubectl apply -f infrastructure/k8s/monitoring/redis-exporter.yaml
    
    # Wait for deployments
    kubectl -n monitoring wait --for=condition=available --timeout=300s deployment/prometheus
    kubectl -n monitoring wait --for=condition=available --timeout=300s deployment/grafana
    
    echo -e "${GREEN}✓ Kubernetes deployment complete${NC}"
}

# Main execution
main() {
    check_prerequisites
    
    # Check deployment target
    if [ "$1" == "kubernetes" ] || [ "$1" == "k8s" ]; then
        deploy_to_kubernetes
    else
        create_directories
        deploy_monitoring
        configure_grafana
        verify_deployment
        display_info
    fi
    
    echo -e "\n${GREEN}Monitoring deployment complete!${NC}"
}

# Run main function
main "$@"