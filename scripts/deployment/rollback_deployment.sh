#!/bin/bash
#
# Rollback Deployment Script
# Safely rollback to previous version in case of issues
#

set -euo pipefail

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
NAMESPACE="roadtrip-production"
DEPLOYMENT_NAME="roadtrip-api"
MAX_ROLLBACK_HISTORY=10

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl not found. Please install kubectl."
        exit 1
    fi
    
    # Check cluster connection
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster."
        exit 1
    fi
    
    # Check namespace exists
    if ! kubectl get namespace $NAMESPACE &> /dev/null; then
        log_error "Namespace $NAMESPACE not found."
        exit 1
    fi
    
    log_info "Prerequisites check passed."
}

get_current_revision() {
    kubectl rollout history deployment/$DEPLOYMENT_NAME -n $NAMESPACE | tail -2 | head -1 | awk '{print $1}'
}

show_rollout_history() {
    log_info "Deployment history:"
    kubectl rollout history deployment/$DEPLOYMENT_NAME -n $NAMESPACE
}

capture_current_state() {
    log_info "Capturing current state..."
    
    # Save current deployment state
    kubectl get deployment/$DEPLOYMENT_NAME -n $NAMESPACE -o yaml > "/tmp/deployment_backup_$(date +%Y%m%d_%H%M%S).yaml"
    
    # Capture metrics
    if command -v curl &> /dev/null; then
        curl -s http://prometheus:9090/api/v1/query?query=up{job="roadtrip-api"} > "/tmp/metrics_backup_$(date +%Y%m%d_%H%M%S).json" || true
    fi
    
    log_info "Current state captured."
}

perform_rollback() {
    local target_revision=$1
    
    log_warn "Rolling back to revision $target_revision..."
    
    # Perform the rollback
    if kubectl rollout undo deployment/$DEPLOYMENT_NAME -n $NAMESPACE --to-revision=$target_revision; then
        log_info "Rollback command executed successfully."
    else
        log_error "Rollback command failed."
        exit 1
    fi
    
    # Wait for rollout to complete
    log_info "Waiting for rollback to complete..."
    if kubectl rollout status deployment/$DEPLOYMENT_NAME -n $NAMESPACE --timeout=10m; then
        log_info "Rollback completed successfully."
    else
        log_error "Rollback failed to complete within timeout."
        exit 1
    fi
}

verify_rollback() {
    log_info "Verifying rollback..."
    
    # Check pod status
    local ready_pods=$(kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT_NAME -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}' | wc -w)
    local total_pods=$(kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT_NAME -o jsonpath='{.items[*].metadata.name}' | wc -w)
    
    if [ "$ready_pods" -eq "$total_pods" ] && [ "$total_pods" -gt 0 ]; then
        log_info "All pods are running ($ready_pods/$total_pods)."
    else
        log_error "Not all pods are ready ($ready_pods/$total_pods)."
        exit 1
    fi
    
    # Check service endpoints
    local endpoints=$(kubectl get endpoints -n $NAMESPACE $DEPLOYMENT_NAME -o jsonpath='{.subsets[*].addresses[*].ip}' | wc -w)
    if [ "$endpoints" -gt 0 ]; then
        log_info "Service has $endpoints active endpoints."
    else
        log_error "No active endpoints found for service."
        exit 1
    fi
    
    # Basic health check
    log_info "Performing health check..."
    local pod_name=$(kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT_NAME -o jsonpath='{.items[0].metadata.name}')
    if kubectl exec -n $NAMESPACE $pod_name -- curl -s http://localhost:8000/health > /dev/null; then
        log_info "Health check passed."
    else
        log_warn "Health check failed - service may need time to warm up."
    fi
}

update_monitoring() {
    log_info "Updating monitoring and alerts..."
    
    # Add annotation for rollback event
    kubectl annotate deployment/$DEPLOYMENT_NAME -n $NAMESPACE \
        "rollback.timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        "rollback.operator=$USER" \
        --overwrite
    
    # Send notification (placeholder - implement actual notification)
    log_info "Rollback event logged."
}

rollback_database() {
    log_warn "Database rollback consideration..."
    
    read -p "Do you need to rollback database migrations? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Running database rollback..."
        # Placeholder for database rollback
        # kubectl exec -n $NAMESPACE deploy/$DEPLOYMENT_NAME -- alembic downgrade -1
        log_warn "Database rollback must be performed manually."
    else
        log_info "Skipping database rollback."
    fi
}

main() {
    echo "======================================"
    echo "Road Trip AI - Deployment Rollback"
    echo "======================================"
    echo
    
    # Check prerequisites
    check_prerequisites
    
    # Show current status
    log_info "Current deployment status:"
    kubectl get deployment/$DEPLOYMENT_NAME -n $NAMESPACE
    echo
    
    # Show rollout history
    show_rollout_history
    echo
    
    # Get target revision
    current_revision=$(get_current_revision)
    log_info "Current revision: $current_revision"
    
    read -p "Enter target revision number (or 'latest' for previous): " target_revision
    
    if [ "$target_revision" == "latest" ]; then
        target_revision=$((current_revision - 1))
    fi
    
    # Validate revision
    if ! [[ "$target_revision" =~ ^[0-9]+$ ]] || [ "$target_revision" -lt 1 ]; then
        log_error "Invalid revision number: $target_revision"
        exit 1
    fi
    
    # Confirm rollback
    echo
    log_warn "You are about to rollback from revision $current_revision to $target_revision"
    read -p "Are you sure you want to proceed? (yes/no): " confirm
    
    if [ "$confirm" != "yes" ]; then
        log_info "Rollback cancelled."
        exit 0
    fi
    
    # Capture current state before rollback
    capture_current_state
    
    # Perform rollback
    perform_rollback $target_revision
    
    # Verify rollback
    verify_rollback
    
    # Database consideration
    rollback_database
    
    # Update monitoring
    update_monitoring
    
    echo
    log_info "Rollback completed successfully!"
    log_info "Please monitor the application closely for the next 30 minutes."
    log_info "If issues persist, contact the on-call engineer."
}

# Run main function
main "$@"