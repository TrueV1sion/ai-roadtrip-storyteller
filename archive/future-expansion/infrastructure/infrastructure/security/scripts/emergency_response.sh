#!/bin/bash
# Emergency Response Script for Security Incidents
# Provides rapid response capabilities for active attacks

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-roadtrip-460720}"
ENVIRONMENT="${ENVIRONMENT:-production}"
POLICY_NAME="roadtrip-security-policy-${ENVIRONMENT}"
LOG_DIR="/tmp/security-incident-$(date +%Y%m%d-%H%M%S)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Create log directory
mkdir -p "${LOG_DIR}"

# Function to log actions
log_action() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_DIR}/actions.log"
}

# Display menu
show_menu() {
    echo -e "\n${YELLOW}===== Road Trip Security Emergency Response =====${NC}"
    echo -e "${RED}⚠️  EMERGENCY RESPONSE MENU ⚠️${NC}"
    echo
    echo "1. Enable Emergency Lockdown (Block ALL traffic)"
    echo "2. Disable Emergency Lockdown (Restore normal operation)"
    echo "3. Block Specific IP/Range"
    echo "4. Analyze Active Attack"
    echo "5. Enable Enhanced Protection Mode"
    echo "6. Export Security Logs for Forensics"
    echo "7. Check Current Security Status"
    echo "8. Apply Rate Limit to All Endpoints"
    echo "9. Enable reCAPTCHA Challenge"
    echo "10. Exit"
    echo
    echo -n "Select action (1-10): "
}

# 1. Enable Emergency Lockdown
enable_lockdown() {
    echo -e "\n${RED}⚠️  WARNING: This will block ALL traffic to the application!${NC}"
    echo -n "Are you sure? (yes/no): "
    read -r confirm
    
    if [ "${confirm}" == "yes" ]; then
        log_action "ENABLING EMERGENCY LOCKDOWN"
        gcloud compute security-policies rules update 100 \
            --security-policy=${POLICY_NAME} \
            --preview=false \
            --project=${PROJECT_ID}
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Emergency lockdown ENABLED${NC}"
            log_action "Emergency lockdown enabled successfully"
            
            # Send alert
            echo "CRITICAL: Emergency lockdown enabled on ${ENVIRONMENT} environment" | \
                mail -s "SECURITY ALERT: Lockdown Enabled" security@roadtripai.com 2>/dev/null || true
        else
            echo -e "${RED}✗ Failed to enable lockdown${NC}"
            log_action "Failed to enable emergency lockdown"
        fi
    else
        echo "Lockdown cancelled"
    fi
}

# 2. Disable Emergency Lockdown
disable_lockdown() {
    echo -e "\n${YELLOW}Disabling emergency lockdown...${NC}"
    log_action "DISABLING EMERGENCY LOCKDOWN"
    
    gcloud compute security-policies rules update 100 \
        --security-policy=${POLICY_NAME} \
        --preview=true \
        --project=${PROJECT_ID}
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Emergency lockdown DISABLED - Normal operation restored${NC}"
        log_action "Emergency lockdown disabled successfully"
    else
        echo -e "${RED}✗ Failed to disable lockdown${NC}"
        log_action "Failed to disable emergency lockdown"
    fi
}

# 3. Block Specific IP
block_ip() {
    echo -n "Enter IP address or CIDR range to block (e.g., 1.2.3.4 or 1.2.3.0/24): "
    read -r ip_range
    
    echo -n "Enter reason for blocking: "
    read -r reason
    
    # Generate unique rule priority
    PRIORITY=$(shuf -i 200-900 -n 1)
    
    log_action "BLOCKING IP: ${ip_range} - Reason: ${reason}"
    
    gcloud compute security-policies rules create ${PRIORITY} \
        --security-policy=${POLICY_NAME} \
        --action=deny-403 \
        --src-ip-ranges="${ip_range}" \
        --description="Emergency block: ${reason}" \
        --project=${PROJECT_ID}
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Successfully blocked ${ip_range}${NC}"
        echo "Rule priority: ${PRIORITY}"
        log_action "Successfully blocked ${ip_range} with rule ${PRIORITY}"
    else
        echo -e "${RED}✗ Failed to block IP${NC}"
        log_action "Failed to block ${ip_range}"
    fi
}

# 4. Analyze Active Attack
analyze_attack() {
    echo -e "\n${YELLOW}Analyzing attack patterns...${NC}"
    log_action "ANALYZING ACTIVE ATTACK"
    
    # Get attacking IPs
    echo -e "\n${BLUE}Top 20 Attacking IPs (last 30 minutes):${NC}"
    gcloud logging read "resource.type=http_load_balancer AND 
        jsonPayload.enforcedSecurityPolicy.outcome=DENY AND 
        timestamp>=\"$(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S)Z\"" \
        --format="value(jsonPayload.remoteIp)" \
        --limit=10000 \
        --project=${PROJECT_ID} 2>/dev/null | \
        sort | uniq -c | sort -nr | head -20 | tee "${LOG_DIR}/attacking_ips.txt"
    
    # Get attack patterns
    echo -e "\n${BLUE}Attack Patterns (blocked by rule):${NC}"
    gcloud logging read "resource.type=cloud_armor_policy AND 
        jsonPayload.enforcedSecurityPolicy.outcome=DENY AND 
        timestamp>=\"$(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S)Z\"" \
        --format="value(jsonPayload.enforcedSecurityPolicy.name)" \
        --limit=10000 \
        --project=${PROJECT_ID} 2>/dev/null | \
        sort | uniq -c | sort -nr | tee "${LOG_DIR}/attack_patterns.txt"
    
    # Get targeted endpoints
    echo -e "\n${BLUE}Targeted Endpoints:${NC}"
    gcloud logging read "resource.type=http_load_balancer AND 
        timestamp>=\"$(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S)Z\"" \
        --format="value(httpRequest.requestUrl)" \
        --limit=10000 \
        --project=${PROJECT_ID} 2>/dev/null | \
        sort | uniq -c | sort -nr | head -20 | tee "${LOG_DIR}/targeted_endpoints.txt"
    
    # Geographic distribution
    echo -e "\n${BLUE}Attack Geographic Distribution:${NC}"
    gcloud logging read "resource.type=http_load_balancer AND 
        jsonPayload.enforcedSecurityPolicy.outcome=DENY AND 
        timestamp>=\"$(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S)Z\"" \
        --format="value(jsonPayload.remoteLocation)" \
        --limit=10000 \
        --project=${PROJECT_ID} 2>/dev/null | \
        sort | uniq -c | sort -nr | head -20 | tee "${LOG_DIR}/geographic_distribution.txt"
    
    echo -e "\n${GREEN}Analysis saved to: ${LOG_DIR}${NC}"
}

# 5. Enable Enhanced Protection
enhanced_protection() {
    echo -e "\n${YELLOW}Enabling enhanced protection mode...${NC}"
    log_action "ENABLING ENHANCED PROTECTION"
    
    # Create stricter rate limiting rule
    gcloud compute security-policies rules create 151 \
        --security-policy=${POLICY_NAME} \
        --action=rate-based-ban \
        --rate-limit-threshold-count=10 \
        --rate-limit-threshold-interval-sec=60 \
        --ban-duration-sec=3600 \
        --conform-action=allow \
        --exceed-action=deny-429 \
        --enforce-on-key=IP \
        --description="Enhanced protection - strict rate limit" \
        --project=${PROJECT_ID} \
        --expression="true"
    
    echo -e "${GREEN}✓ Enhanced protection enabled${NC}"
    echo "- Rate limit: 10 requests per minute"
    echo "- Ban duration: 1 hour"
    log_action "Enhanced protection enabled with strict rate limiting"
}

# 6. Export Security Logs
export_logs() {
    echo -e "\n${YELLOW}Exporting security logs for forensics...${NC}"
    log_action "EXPORTING SECURITY LOGS"
    
    # Export Cloud Armor logs
    echo "Exporting Cloud Armor logs..."
    gcloud logging read "resource.type=cloud_armor_policy" \
        --freshness=24h \
        --format=json \
        --project=${PROJECT_ID} > "${LOG_DIR}/cloud_armor_logs.json"
    
    # Export Load Balancer logs
    echo "Exporting Load Balancer logs..."
    gcloud logging read "resource.type=http_load_balancer" \
        --freshness=24h \
        --format=json \
        --project=${PROJECT_ID} > "${LOG_DIR}/load_balancer_logs.json"
    
    # Export blocked requests
    echo "Exporting blocked requests..."
    gcloud logging read "jsonPayload.enforcedSecurityPolicy.outcome=DENY" \
        --freshness=24h \
        --format=json \
        --project=${PROJECT_ID} > "${LOG_DIR}/blocked_requests.json"
    
    # Create summary report
    cat > "${LOG_DIR}/incident_summary.txt" <<EOF
Security Incident Report
========================
Date: $(date)
Environment: ${ENVIRONMENT}
Project: ${PROJECT_ID}

Log Files:
- cloud_armor_logs.json: All Cloud Armor policy logs
- load_balancer_logs.json: All load balancer traffic logs
- blocked_requests.json: All blocked requests
- attacking_ips.txt: List of attacking IP addresses
- attack_patterns.txt: Attack pattern analysis
- targeted_endpoints.txt: Most targeted endpoints
- geographic_distribution.txt: Geographic source of attacks

Actions Taken:
$(cat "${LOG_DIR}/actions.log")
EOF
    
    # Compress logs
    tar -czf "${LOG_DIR}.tar.gz" -C "$(dirname ${LOG_DIR})" "$(basename ${LOG_DIR})"
    
    echo -e "${GREEN}✓ Logs exported successfully${NC}"
    echo "Archive created: ${LOG_DIR}.tar.gz"
    log_action "Security logs exported to ${LOG_DIR}.tar.gz"
}

# 7. Check Security Status
check_status() {
    echo -e "\n${YELLOW}Current Security Status:${NC}"
    
    # Check if emergency lockdown is active
    LOCKDOWN_STATUS=$(gcloud compute security-policies rules describe 100 \
        --security-policy=${POLICY_NAME} \
        --format="value(preview)" \
        --project=${PROJECT_ID} 2>/dev/null || echo "true")
    
    if [ "${LOCKDOWN_STATUS}" == "True" ]; then
        echo -e "${GREEN}Emergency Lockdown: INACTIVE (Normal operation)${NC}"
    else
        echo -e "${RED}Emergency Lockdown: ACTIVE (All traffic blocked!)${NC}"
    fi
    
    # Count active rules
    RULE_COUNT=$(gcloud compute security-policies describe ${POLICY_NAME} \
        --format="value(rules[].priority)" \
        --project=${PROJECT_ID} 2>/dev/null | wc -l)
    echo "Active security rules: ${RULE_COUNT}"
    
    # Recent blocks
    RECENT_BLOCKS=$(gcloud logging read "jsonPayload.enforcedSecurityPolicy.outcome=DENY AND 
        timestamp>=\"$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S)Z\"" \
        --format="value(jsonPayload.enforcedSecurityPolicy.name)" \
        --project=${PROJECT_ID} 2>/dev/null | wc -l)
    echo "Requests blocked (last 5 min): ${RECENT_BLOCKS}"
    
    # Current request rate
    echo -e "\n${BLUE}Checking current traffic rate...${NC}"
    gcloud monitoring read \
        "loadbalancing.googleapis.com/https/request_count" \
        --filter="resource.url_map_name=\"roadtrip-url-map-${ENVIRONMENT}\"" \
        --window=1m \
        --format="table(point.value.int64_value,point.interval.end_time)" \
        --project=${PROJECT_ID} 2>/dev/null | tail -5
}

# 8. Apply Rate Limit
apply_rate_limit() {
    echo -e "\n${YELLOW}Applying emergency rate limit to all endpoints...${NC}"
    echo -n "Enter rate limit (requests per minute) [50]: "
    read -r rate_limit
    rate_limit=${rate_limit:-50}
    
    log_action "APPLYING RATE LIMIT: ${rate_limit} requests/minute"
    
    gcloud compute security-policies rules create 152 \
        --security-policy=${POLICY_NAME} \
        --action=rate-based-ban \
        --rate-limit-threshold-count=${rate_limit} \
        --rate-limit-threshold-interval-sec=60 \
        --ban-duration-sec=600 \
        --conform-action=allow \
        --exceed-action=deny-429 \
        --enforce-on-key=IP \
        --description="Emergency rate limit - ${rate_limit}/min" \
        --project=${PROJECT_ID} \
        --expression="true"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Rate limit applied: ${rate_limit} requests/minute${NC}"
        log_action "Rate limit successfully applied"
    else
        echo -e "${RED}✗ Failed to apply rate limit${NC}"
        log_action "Failed to apply rate limit"
    fi
}

# 9. Enable reCAPTCHA
enable_recaptcha() {
    echo -e "\n${YELLOW}Enabling reCAPTCHA challenge for suspicious traffic...${NC}"
    log_action "ENABLING RECAPTCHA CHALLENGE"
    
    # This would typically involve updating the security policy with reCAPTCHA rules
    echo -e "${YELLOW}Note: reCAPTCHA configuration requires additional setup in the application${NC}"
    echo "To fully enable:"
    echo "1. Ensure reCAPTCHA keys are configured"
    echo "2. Update frontend to handle challenges"
    echo "3. Apply the reCAPTCHA security rule"
    
    echo -n "Create reCAPTCHA rule anyway? (yes/no): "
    read -r confirm
    
    if [ "${confirm}" == "yes" ]; then
        gcloud compute security-policies rules create 153 \
            --security-policy=${POLICY_NAME} \
            --action=redirect \
            --redirect-type=google-recaptcha \
            --description="reCAPTCHA challenge for suspicious traffic" \
            --project=${PROJECT_ID} \
            --expression="origin.region_code in ['XX']"  # Placeholder
        
        echo -e "${YELLOW}Rule created but requires application configuration${NC}"
        log_action "reCAPTCHA rule created (requires app configuration)"
    fi
}

# Main loop
while true; do
    show_menu
    read -r choice
    
    case $choice in
        1) enable_lockdown ;;
        2) disable_lockdown ;;
        3) block_ip ;;
        4) analyze_attack ;;
        5) enhanced_protection ;;
        6) export_logs ;;
        7) check_status ;;
        8) apply_rate_limit ;;
        9) enable_recaptcha ;;
        10) 
            echo -e "\n${GREEN}Exiting emergency response mode${NC}"
            echo "Session logs saved to: ${LOG_DIR}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option. Please select 1-10.${NC}"
            ;;
    esac
    
    echo -e "\n${YELLOW}Press Enter to continue...${NC}"
    read -r
done