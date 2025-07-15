#!/bin/bash
# Adaptive Security Script
# Automatically adjusts security policies based on traffic patterns

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-roadtrip-460720}"
ENVIRONMENT="${ENVIRONMENT:-production}"
POLICY_NAME="roadtrip-security-policy-${ENVIRONMENT}"

# Thresholds
NORMAL_RPS=100
HIGH_RPS=500
CRITICAL_RPS=1000
ERROR_RATE_THRESHOLD=5
ATTACK_CONFIDENCE_THRESHOLD=0.7

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Log file
LOG_FILE="/var/log/adaptive_security.log"

# Function to log
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

# Function to get current request rate
get_request_rate() {
    gcloud monitoring read \
        "loadbalancing.googleapis.com/https/request_count" \
        --filter="resource.url_map_name=\"roadtrip-url-map-${ENVIRONMENT}\"" \
        --window=1m \
        --format="value(point.value.int64_value)" \
        --project=${PROJECT_ID} 2>/dev/null | \
        tail -1 || echo "0"
}

# Function to get error rate
get_error_rate() {
    local total_requests=$(get_request_rate)
    local error_requests=$(gcloud logging read "resource.type=http_load_balancer AND 
        httpRequest.status>=400 AND 
        timestamp>=\"$(date -u -d '1 minute ago' +%Y-%m-%dT%H:%M:%S)Z\"" \
        --format="value(httpRequest.status)" \
        --project=${PROJECT_ID} 2>/dev/null | wc -l)
    
    if [ "${total_requests}" -gt 0 ]; then
        echo "scale=2; ${error_requests} * 100 / ${total_requests}" | bc
    else
        echo "0"
    fi
}

# Function to get attack confidence
get_attack_confidence() {
    gcloud monitoring read \
        "networksecurity.googleapis.com/l7_ddos/detection_confidence" \
        --filter="resource.type=\"cloud_armor_policy\"" \
        --window=1m \
        --format="value(point.value.double_value)" \
        --project=${PROJECT_ID} 2>/dev/null | \
        tail -1 || echo "0"
}

# Function to adjust security level
adjust_security_level() {
    local current_rps=$1
    local error_rate=$2
    local attack_confidence=$3
    
    log "Current metrics - RPS: ${current_rps}, Error rate: ${error_rate}%, Attack confidence: ${attack_confidence}"
    
    # Determine security level
    if (( $(echo "${attack_confidence} > ${ATTACK_CONFIDENCE_THRESHOLD}" | bc -l) )); then
        log "HIGH ATTACK CONFIDENCE - Enabling maximum protection"
        enable_high_security
    elif [ "${current_rps}" -gt "${CRITICAL_RPS}" ]; then
        log "CRITICAL TRAFFIC LEVEL - Enabling enhanced protection"
        enable_medium_security
    elif [ "${current_rps}" -gt "${HIGH_RPS}" ] || (( $(echo "${error_rate} > ${ERROR_RATE_THRESHOLD}" | bc -l) )); then
        log "ELEVATED TRAFFIC/ERRORS - Enabling moderate protection"
        enable_low_security
    else
        log "NORMAL TRAFFIC - Standard protection active"
        enable_standard_security
    fi
}

# Enable high security (under attack)
enable_high_security() {
    log "Applying HIGH security configuration"
    
    # Enable strict rate limiting
    gcloud compute security-policies rules update 3000 \
        --security-policy=${POLICY_NAME} \
        --rate-limit-threshold-count=20 \
        --project=${PROJECT_ID} 2>/dev/null || \
    gcloud compute security-policies rules create 3000 \
        --security-policy=${POLICY_NAME} \
        --action=rate-based-ban \
        --rate-limit-threshold-count=20 \
        --rate-limit-threshold-interval-sec=60 \
        --ban-duration-sec=3600 \
        --conform-action=allow \
        --exceed-action=deny-429 \
        --enforce-on-key=IP \
        --description="Adaptive security - HIGH" \
        --project=${PROJECT_ID} \
        --expression="request.path.matches('/api/.*')"
    
    # Enable additional WAF rules
    for priority in 4000 4100 4200 4300 4400 4500; do
        gcloud compute security-policies rules update ${priority} \
            --security-policy=${POLICY_NAME} \
            --preview=false \
            --project=${PROJECT_ID} 2>/dev/null || true
    done
    
    log "HIGH security configuration applied"
}

# Enable medium security
enable_medium_security() {
    log "Applying MEDIUM security configuration"
    
    # Moderate rate limiting
    gcloud compute security-policies rules update 3000 \
        --security-policy=${POLICY_NAME} \
        --rate-limit-threshold-count=50 \
        --project=${PROJECT_ID} 2>/dev/null || \
    gcloud compute security-policies rules create 3000 \
        --security-policy=${POLICY_NAME} \
        --action=rate-based-ban \
        --rate-limit-threshold-count=50 \
        --rate-limit-threshold-interval-sec=60 \
        --ban-duration-sec=600 \
        --conform-action=allow \
        --exceed-action=deny-429 \
        --enforce-on-key=IP \
        --description="Adaptive security - MEDIUM" \
        --project=${PROJECT_ID} \
        --expression="request.path.matches('/api/.*')"
    
    log "MEDIUM security configuration applied"
}

# Enable low security
enable_low_security() {
    log "Applying LOW security configuration"
    
    # Light rate limiting
    gcloud compute security-policies rules update 3000 \
        --security-policy=${POLICY_NAME} \
        --rate-limit-threshold-count=100 \
        --project=${PROJECT_ID} 2>/dev/null
    
    log "LOW security configuration applied"
}

# Enable standard security
enable_standard_security() {
    log "Applying STANDARD security configuration"
    
    # Normal rate limiting
    gcloud compute security-policies rules update 3000 \
        --security-policy=${POLICY_NAME} \
        --rate-limit-threshold-count=100 \
        --ban-duration-sec=600 \
        --project=${PROJECT_ID} 2>/dev/null
    
    # Disable some aggressive WAF rules in preview mode
    for priority in 4300 4400 4500; do
        gcloud compute security-policies rules update ${priority} \
            --security-policy=${POLICY_NAME} \
            --preview=true \
            --project=${PROJECT_ID} 2>/dev/null || true
    done
    
    log "STANDARD security configuration applied"
}

# Function to analyze and whitelist legitimate traffic
analyze_false_positives() {
    log "Analyzing potential false positives"
    
    # Find IPs with many blocked requests but valid user agents
    local blocked_legitimate=$(gcloud logging read "
        jsonPayload.enforcedSecurityPolicy.outcome=DENY AND 
        httpRequest.userAgent=~'.*RoadTripApp.*' AND
        timestamp>=\"$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)Z\"" \
        --format="value(jsonPayload.remoteIp)" \
        --project=${PROJECT_ID} 2>/dev/null | \
        sort | uniq -c | sort -nr | head -10)
    
    if [ -n "${blocked_legitimate}" ]; then
        log "Found potentially legitimate blocked IPs:"
        echo "${blocked_legitimate}"
        
        # Auto-whitelist IPs with more than 50 blocked legitimate requests
        while IFS= read -r line; do
            count=$(echo "${line}" | awk '{print $1}')
            ip=$(echo "${line}" | awk '{print $2}')
            
            if [ "${count}" -gt 50 ]; then
                log "Auto-whitelisting IP: ${ip} (${count} blocked requests)"
                
                # Create whitelist rule
                priority=$(shuf -i 500-599 -n 1)
                gcloud compute security-policies rules create ${priority} \
                    --security-policy=${POLICY_NAME} \
                    --action=allow \
                    --src-ip-ranges="${ip}/32" \
                    --description="Auto-whitelist: Legitimate traffic from ${ip}" \
                    --project=${PROJECT_ID} 2>/dev/null || true
            fi
        done <<< "${blocked_legitimate}"
    fi
}

# Function to clean up old rules
cleanup_old_rules() {
    log "Cleaning up old adaptive rules"
    
    # List all rules and remove old adaptive/emergency rules
    local rules=$(gcloud compute security-policies rules list \
        --security-policy=${POLICY_NAME} \
        --format="table(priority,description)" \
        --project=${PROJECT_ID} 2>/dev/null | \
        grep -E "(Emergency block:|Auto-whitelist:|Adaptive security -)" | \
        awk '{print $1}')
    
    for rule in ${rules}; do
        # Check rule age (would need to implement based on description timestamp)
        log "Evaluating rule ${rule} for cleanup"
        
        # Remove rules older than 24 hours (simplified - would need actual timestamp check)
        # gcloud compute security-policies rules delete ${rule} \
        #     --security-policy=${POLICY_NAME} \
        #     --project=${PROJECT_ID} --quiet
    done
}

# Main monitoring loop
main() {
    log "Starting adaptive security monitoring for ${ENVIRONMENT}"
    
    while true; do
        # Get current metrics
        current_rps=$(get_request_rate)
        error_rate=$(get_error_rate)
        attack_confidence=$(get_attack_confidence)
        
        # Adjust security level based on metrics
        adjust_security_level "${current_rps}" "${error_rate}" "${attack_confidence}"
        
        # Analyze false positives every 5 iterations (5 minutes)
        if [ $((SECONDS % 300)) -eq 0 ]; then
            analyze_false_positives
        fi
        
        # Cleanup old rules every hour
        if [ $((SECONDS % 3600)) -eq 0 ]; then
            cleanup_old_rules
        fi
        
        # Sleep for 60 seconds before next check
        sleep 60
    done
}

# Handle signals for graceful shutdown
trap 'log "Adaptive security monitoring stopped"; exit 0' SIGINT SIGTERM

# Check if running as service or standalone
if [ "${1:-}" == "daemon" ]; then
    # Run as daemon
    main &
    echo $! > /var/run/adaptive_security.pid
    log "Started as daemon with PID $(cat /var/run/adaptive_security.pid)"
else
    # Run in foreground
    main
fi