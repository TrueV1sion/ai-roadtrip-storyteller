#!/bin/bash

# AI Road Trip Storyteller - Rollback Script
# This script provides quick rollback capabilities for failed deployments

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT_ID:-""}
REGION=${DEPLOY_REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"roadtrip-api"}

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate environment
validate_environment() {
    print_status "Validating rollback environment..."
    
    if ! command_exists gcloud; then
        print_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated with gcloud. Run 'gcloud auth login' first."
        exit 1
    fi
    
    if [ -z "$PROJECT_ID" ]; then
        print_error "GOOGLE_CLOUD_PROJECT_ID environment variable is not set."
        exit 1
    fi
    
    print_success "Environment validation passed"
}

# Function to list available revisions
list_revisions() {
    print_status "Available revisions for service '$SERVICE_NAME':"
    echo
    
    gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="table(metadata.name:label=REVISION,spec.containerConcurrency:label=CONCURRENCY,status.conditions[0].lastTransitionTime:label=DEPLOYED,metadata.labels.serving.knative.dev/configurationGeneration:label=GENERATION)" \
        --sort-by="~metadata.creationTimestamp"
}

# Function to get current revision
get_current_revision() {
    gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.latestReadyRevisionName)"
}

# Function to rollback to specific revision
rollback_to_revision() {
    local target_revision="$1"
    
    if [ -z "$target_revision" ]; then
        print_error "No revision specified for rollback"
        exit 1
    fi
    
    print_status "Rolling back to revision: $target_revision"
    
    # Update traffic to route 100% to the target revision
    if gcloud run services update-traffic "$SERVICE_NAME" \
        --to-revisions="$target_revision=100" \
        --region="$REGION" \
        --project="$PROJECT_ID"; then
        print_success "Rollback completed successfully"
        print_status "All traffic now routed to revision: $target_revision"
    else
        print_error "Rollback failed"
        exit 1
    fi
}

# Function to rollback to previous revision
rollback_to_previous() {
    print_status "Finding previous revision..."
    
    # Get all revisions sorted by creation time (newest first)
    local revisions=($(gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(metadata.name)" \
        --sort-by="~metadata.creationTimestamp"))
    
    if [ ${#revisions[@]} -lt 2 ]; then
        print_error "No previous revision available for rollback"
        exit 1
    fi
    
    local current_revision="${revisions[0]}"
    local previous_revision="${revisions[1]}"
    
    print_status "Current revision: $current_revision"
    print_status "Previous revision: $previous_revision"
    
    rollback_to_revision "$previous_revision"
}

# Function to emergency stop (scale to 0)
emergency_stop() {
    print_warning "Emergency stop: Scaling service to 0 instances"
    
    if gcloud run services update "$SERVICE_NAME" \
        --min-instances=0 \
        --max-instances=0 \
        --region="$REGION" \
        --project="$PROJECT_ID"; then
        print_success "Service scaled to 0 instances"
        print_status "Service is now offline. Use 'restart' command to bring it back."
    else
        print_error "Failed to scale service to 0"
        exit 1
    fi
}

# Function to restart service
restart_service() {
    print_status "Restarting service..."
    
    if gcloud run services update "$SERVICE_NAME" \
        --min-instances=1 \
        --max-instances=10 \
        --region="$REGION" \
        --project="$PROJECT_ID"; then
        print_success "Service restarted successfully"
    else
        print_error "Failed to restart service"
        exit 1
    fi
}

# Function to show current status
show_status() {
    print_status "Current service status:"
    echo
    
    # Get service details
    gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="table(metadata.name:label=SERVICE,status.url:label=URL,status.latestReadyRevisionName:label=CURRENT_REVISION,spec.traffic[0].percent:label=TRAFFIC_PERCENT)"
    
    echo
    print_status "Traffic allocation:"
    gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="table(spec.traffic[].revisionName:label=REVISION,spec.traffic[].percent:label=PERCENT)"
}

# Function to create backup of current state
create_backup() {
    print_status "Creating backup of current deployment state..."
    
    local backup_dir="backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    
    # Save service configuration
    gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="export" > "$backup_dir/service_config.yaml"
    
    # Save revision list
    gcloud run revisions list \
        --service="$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="json" > "$backup_dir/revisions.json"
    
    # Save current traffic allocation
    gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(spec.traffic[].revisionName,spec.traffic[].percent)" > "$backup_dir/traffic_allocation.txt"
    
    print_success "Backup created in: $backup_dir"
    echo "$backup_dir" > .last_backup
}

# Function to show help
show_help() {
    echo "AI Road Trip Storyteller - Rollback Script"
    echo
    echo "Usage: $0 <command> [options]"
    echo
    echo "Commands:"
    echo "  status                 Show current service status"
    echo "  list                   List available revisions"
    echo "  rollback <revision>    Rollback to specific revision"
    echo "  previous              Rollback to previous revision"
    echo "  stop                  Emergency stop (scale to 0)"
    echo "  restart               Restart service"
    echo "  backup                Create backup of current state"
    echo "  help                  Show this help message"
    echo
    echo "Environment Variables:"
    echo "  GOOGLE_CLOUD_PROJECT_ID  Google Cloud Project ID"
    echo "  DEPLOY_REGION           Deployment region (default: us-central1)"
    echo "  SERVICE_NAME            Service name (default: roadtrip-api)"
    echo
    echo "Examples:"
    echo "  $0 status"
    echo "  $0 list"
    echo "  $0 rollback roadtrip-api-00001-xyz"
    echo "  $0 previous"
    echo "  $0 stop"
}

# Main function
main() {
    if [ $# -eq 0 ]; then
        show_help
        exit 1
    fi
    
    local command="$1"
    shift
    
    case "$command" in
        "status")
            validate_environment
            show_status
            ;;
        "list")
            validate_environment
            list_revisions
            ;;
        "rollback")
            validate_environment
            create_backup
            rollback_to_revision "$1"
            show_status
            ;;
        "previous")
            validate_environment
            create_backup
            rollback_to_previous
            show_status
            ;;
        "stop")
            validate_environment
            create_backup
            emergency_stop
            ;;
        "restart")
            validate_environment
            restart_service
            show_status
            ;;
        "backup")
            validate_environment
            create_backup
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            print_error "Unknown command: $command"
            echo
            show_help
            exit 1
            ;;
    esac
}

# Run main function
main "$@"