#!/bin/bash
#
# Secret Rotation Script for Google Secret Manager
# Automatically rotates secrets on a scheduled basis
#

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-roadtrip-prod}"
ROTATION_DAYS="${ROTATION_DAYS:-90}"
NOTIFICATION_WEBHOOK="${NOTIFICATION_WEBHOOK:-}"
DRY_RUN="${DRY_RUN:-false}"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Logging functions
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

# Secrets to rotate with their generation functions
declare -A SECRET_GENERATORS=(
    ["jwt-secret-key"]="generate_jwt_secret"
    ["database-password"]="generate_database_password"
    ["redis-password"]="generate_redis_password"
    ["api-key-internal"]="generate_api_key"
    ["csrf-secret-key"]="generate_csrf_secret"
    ["encryption-key"]="generate_encryption_key"
)

# API keys that need provider-specific rotation
declare -A API_KEY_ROTATORS=(
    ["google-maps-api-key"]="rotate_google_api_key"
    ["openweather-api-key"]="rotate_openweather_api_key"
    ["ticketmaster-api-key"]="rotate_ticketmaster_api_key"
    ["viator-api-key"]="rotate_viator_api_key"
)

# Generate a secure random string
generate_secure_random() {
    local length="${1:-32}"
    openssl rand -base64 "$length" | tr -d "=+/" | cut -c1-"$length"
}

# Generate JWT secret
generate_jwt_secret() {
    generate_secure_random 64
}

# Generate database password
generate_database_password() {
    # Strong password: uppercase, lowercase, numbers, special chars
    local password=$(generate_secure_random 24)
    echo "${password}!Aa1"
}

# Generate Redis password
generate_redis_password() {
    generate_secure_random 32
}

# Generate API key
generate_api_key() {
    echo "rts_$(generate_secure_random 32)"
}

# Generate CSRF secret
generate_csrf_secret() {
    generate_secure_random 32
}

# Generate encryption key
generate_encryption_key() {
    openssl rand -base64 32
}

# Check if secret needs rotation
needs_rotation() {
    local secret_name=$1
    local last_rotation_timestamp
    
    # Get secret metadata
    local metadata=$(gcloud secrets describe "$secret_name" \
        --project="$PROJECT_ID" \
        --format=json 2>/dev/null || echo "{}")
    
    # Check if secret exists
    if [[ "$metadata" == "{}" ]]; then
        warning "Secret $secret_name does not exist"
        return 1
    fi
    
    # Get last rotation time from labels
    last_rotation_timestamp=$(echo "$metadata" | jq -r '.labels."last-rotation" // "0"')
    
    # Calculate days since last rotation
    local current_timestamp=$(date +%s)
    local days_since_rotation=$(( (current_timestamp - last_rotation_timestamp) / 86400 ))
    
    info "Secret $secret_name: $days_since_rotation days since last rotation"
    
    if [[ $days_since_rotation -ge $ROTATION_DAYS ]]; then
        return 0
    else
        return 1
    fi
}

# Rotate a secret
rotate_secret() {
    local secret_name=$1
    local new_value=$2
    
    log "Rotating secret: $secret_name"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "DRY RUN: Would rotate $secret_name"
        return 0
    fi
    
    # Create new version
    echo -n "$new_value" | gcloud secrets versions add "$secret_name" \
        --project="$PROJECT_ID" \
        --data-file=- || {
        error "Failed to add new version for $secret_name"
        return 1
    }
    
    # Update labels with rotation timestamp
    gcloud secrets update "$secret_name" \
        --project="$PROJECT_ID" \
        --update-labels="last-rotation=$(date +%s),rotated-by=automatic" || {
        error "Failed to update labels for $secret_name"
        return 1
    }
    
    # Disable old versions (keep last 3 for rollback)
    local versions=$(gcloud secrets versions list "$secret_name" \
        --project="$PROJECT_ID" \
        --format="value(name)" \
        --filter="state:ENABLED" \
        --sort-by="~createTime" | tail -n +4)
    
    for version in $versions; do
        info "Disabling old version: $version"
        gcloud secrets versions disable "$version" \
            --secret="$secret_name" \
            --project="$PROJECT_ID" || {
            warning "Failed to disable version $version"
        }
    done
    
    log "Successfully rotated secret: $secret_name"
}

# Update database password
update_database_password() {
    local new_password=$1
    
    log "Updating database password in Cloud SQL"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "DRY RUN: Would update database password"
        return 0
    fi
    
    # Update Cloud SQL user password
    gcloud sql users set-password postgres \
        --instance=roadtrip-db \
        --password="$new_password" \
        --project="$PROJECT_ID" || {
        error "Failed to update database password"
        return 1
    }
    
    # Wait for password update to propagate
    sleep 5
    
    # Test new password
    PGPASSWORD="$new_password" psql \
        -h "/cloudsql/${PROJECT_ID}:us-central1:roadtrip-db" \
        -U postgres \
        -d roadtrip_prod \
        -c "SELECT 1" > /dev/null 2>&1 || {
        error "Failed to verify new database password"
        return 1
    }
    
    log "Database password updated successfully"
}

# Update Redis password
update_redis_password() {
    local new_password=$1
    
    log "Updating Redis password"
    
    if [[ "$DRY_RUN" == "true" ]]; then
        info "DRY RUN: Would update Redis password"
        return 0
    fi
    
    # Update Redis instance
    # Note: This requires Redis instance to be configured for AUTH
    # For Google Memorystore Redis, this is done during instance creation
    warning "Redis password rotation requires manual configuration in Memorystore"
    
    return 0
}

# Rotate Google API key (placeholder - requires manual steps)
rotate_google_api_key() {
    warning "Google API key rotation requires manual steps:"
    echo "  1. Go to https://console.cloud.google.com/apis/credentials"
    echo "  2. Create a new API key with same restrictions"
    echo "  3. Update the secret in Secret Manager"
    echo "  4. Delete the old API key after verification"
    return 0
}

# Rotate OpenWeather API key (placeholder)
rotate_openweather_api_key() {
    warning "OpenWeather API key rotation requires manual steps:"
    echo "  1. Log in to OpenWeather account"
    echo "  2. Generate new API key"
    echo "  3. Update the secret in Secret Manager"
    echo "  4. Revoke old API key after verification"
    return 0
}

# Rotate Ticketmaster API key (placeholder)
rotate_ticketmaster_api_key() {
    warning "Ticketmaster API key rotation requires manual steps:"
    echo "  1. Contact Ticketmaster partner support"
    echo "  2. Request new API credentials"
    echo "  3. Update the secret in Secret Manager"
    return 0
}

# Rotate Viator API key (placeholder)
rotate_viator_api_key() {
    warning "Viator API key rotation requires manual steps:"
    echo "  1. Log in to Viator partner portal"
    echo "  2. Generate new API key"
    echo "  3. Update the secret in Secret Manager"
    echo "  4. Revoke old API key after verification"
    return 0
}

# Send notification
send_notification() {
    local status=$1
    local message=$2
    
    # Send to webhook if configured
    if [[ -n "$NOTIFICATION_WEBHOOK" ]]; then
        curl -X POST "$NOTIFICATION_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"Secret Rotation ${status}\",
                \"message\": \"${message}\"
            }" 2>/dev/null || true
    fi
    
    # Log to Cloud Logging
    gcloud logging write secret-rotation \
        "$message" \
        --severity=$([ "$status" == "SUCCESS" ] && echo "INFO" || echo "ERROR") \
        --project="$PROJECT_ID"
}

# Verify service health after rotation
verify_service_health() {
    log "Verifying service health after rotation"
    
    # Check backend health
    local health_check_url="https://api.roadtripstoryteller.com/health"
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$health_check_url" || echo "000")
    
    if [[ "$response" == "200" ]]; then
        log "Service health check passed"
        return 0
    else
        error "Service health check failed with status: $response"
        return 1
    fi
}

# Main rotation process
main() {
    log "Starting secret rotation process"
    log "Project: $PROJECT_ID"
    log "Rotation threshold: $ROTATION_DAYS days"
    log "Dry run: $DRY_RUN"
    
    local rotated_count=0
    local failed_count=0
    local rotation_report=""
    
    # Rotate generated secrets
    for secret_name in "${!SECRET_GENERATORS[@]}"; do
        if needs_rotation "$secret_name"; then
            info "Secret $secret_name needs rotation"
            
            # Generate new secret value
            local generator="${SECRET_GENERATORS[$secret_name]}"
            local new_value=$($generator)
            
            # Rotate the secret
            if rotate_secret "$secret_name" "$new_value"; then
                # Handle special cases
                case "$secret_name" in
                    "database-password")
                        update_database_password "$new_value" || {
                            error "Failed to update database password"
                            failed_count=$((failed_count + 1))
                            continue
                        }
                        ;;
                    "redis-password")
                        update_redis_password "$new_value" || {
                            error "Failed to update Redis password"
                            failed_count=$((failed_count + 1))
                            continue
                        }
                        ;;
                esac
                
                rotated_count=$((rotated_count + 1))
                rotation_report+="\n  ✓ $secret_name"
            else
                failed_count=$((failed_count + 1))
                rotation_report+="\n  ✗ $secret_name (failed)"
            fi
        fi
    done
    
    # Check API keys that need manual rotation
    for api_key in "${!API_KEY_ROTATORS[@]}"; do
        if needs_rotation "$api_key"; then
            info "API key $api_key needs rotation"
            local rotator="${API_KEY_ROTATORS[$api_key]}"
            $rotator
            rotation_report+="\n  ⚠ $api_key (manual rotation required)"
        fi
    done
    
    # Restart services if secrets were rotated
    if [[ $rotated_count -gt 0 ]] && [[ "$DRY_RUN" != "true" ]]; then
        log "Restarting services to pick up new secrets"
        
        # Trigger Cloud Run service update
        gcloud run services update roadtrip-api \
            --region=us-central1 \
            --project="$PROJECT_ID" \
            --no-traffic || {
            error "Failed to restart Cloud Run service"
        }
        
        # Wait for service to stabilize
        sleep 30
        
        # Verify service health
        verify_service_health || {
            error "Service health check failed after rotation"
            failed_count=$((failed_count + 1))
        }
    fi
    
    # Summary
    log "Secret rotation completed"
    log "Rotated: $rotated_count secrets"
    log "Failed: $failed_count secrets"
    
    if [[ -n "$rotation_report" ]]; then
        log "Rotation details:$rotation_report"
    fi
    
    # Send notification
    if [[ $failed_count -eq 0 ]]; then
        send_notification "SUCCESS" "Secret rotation completed successfully. Rotated $rotated_count secrets."
    else
        send_notification "PARTIAL" "Secret rotation completed with errors. Rotated $rotated_count, Failed $failed_count."
    fi
    
    # Exit with appropriate code
    [[ $failed_count -eq 0 ]] && exit 0 || exit 1
}

# Run main function
main "$@"