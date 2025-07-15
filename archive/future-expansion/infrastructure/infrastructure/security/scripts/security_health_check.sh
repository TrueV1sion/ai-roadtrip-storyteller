#!/bin/bash
# Security Health Check Script
# Performs comprehensive security status assessment

set -euo pipefail

# Configuration
PROJECT_ID="${PROJECT_ID:-roadtrip-460720}"
ENVIRONMENT="${ENVIRONMENT:-production}"
POLICY_NAME="roadtrip-security-policy-${ENVIRONMENT}"
LB_NAME="roadtrip-url-map-${ENVIRONMENT}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "============================================"
echo "Road Trip Security Health Check"
echo "Environment: ${ENVIRONMENT}"
echo "Time: $(date)"
echo "============================================"

# Function to check command success
check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ $1${NC}"
    else
        echo -e "${RED}✗ $1${NC}"
        return 1
    fi
}

# 1. Check Cloud Armor Policy Status
echo -e "\n${YELLOW}1. Cloud Armor Policy Status${NC}"
gcloud compute security-policies describe ${POLICY_NAME} \
    --format="table(name,rules[].priority,rules[].action,rules[].preview)" 2>/dev/null
check_status "Cloud Armor policy is active"

# 2. Check Active Security Rules
echo -e "\n${YELLOW}2. Active Security Rules Summary${NC}"
RULE_COUNT=$(gcloud compute security-policies describe ${POLICY_NAME} \
    --format="value(rules[].priority)" 2>/dev/null | wc -l)
echo "Total active rules: ${RULE_COUNT}"

# Check if emergency lockdown is enabled
EMERGENCY_STATUS=$(gcloud compute security-policies rules describe 100 \
    --security-policy=${POLICY_NAME} \
    --format="value(preview)" 2>/dev/null || echo "true")
if [ "${EMERGENCY_STATUS}" == "True" ]; then
    echo -e "${GREEN}✓ Emergency lockdown is DISABLED (normal operation)${NC}"
else
    echo -e "${RED}⚠ EMERGENCY LOCKDOWN IS ACTIVE - All traffic is blocked!${NC}"
fi

# 3. Recent Attack Activity
echo -e "\n${YELLOW}3. Recent Attack Activity (Last Hour)${NC}"
ATTACKS=$(gcloud logging read "resource.type=cloud_armor_policy AND 
    jsonPayload.enforcedSecurityPolicy.outcome=DENY AND 
    timestamp>=\"$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S)Z\"" \
    --format="value(jsonPayload.enforcedSecurityPolicy.name)" \
    --limit=1000 2>/dev/null | sort | uniq -c | sort -nr || echo "No data")

if [ "${ATTACKS}" == "No data" ] || [ -z "${ATTACKS}" ]; then
    echo -e "${GREEN}No attacks detected in the last hour${NC}"
else
    echo "Blocked by rule:"
    echo "${ATTACKS}"
fi

# 4. Load Balancer Health
echo -e "\n${YELLOW}4. Load Balancer Health${NC}"
LB_STATUS=$(gcloud compute url-maps describe ${LB_NAME} \
    --format="value(name)" 2>/dev/null && echo "Active" || echo "Not Found")
echo "Load Balancer Status: ${LB_STATUS}"

# Check backend health
BACKEND_HEALTH=$(gcloud compute backend-services get-health roadtrip-backend-service-${ENVIRONMENT} \
    --format="table(backends[].group,backends[].healthStatus[].healthState)" 2>/dev/null || echo "Unable to check")
echo -e "Backend Health:\n${BACKEND_HEALTH}"

# 5. Recent Error Rates
echo -e "\n${YELLOW}5. Error Rates (Last 5 minutes)${NC}"
ERROR_STATS=$(gcloud logging read "resource.type=http_load_balancer AND 
    httpRequest.status>=400 AND 
    timestamp>=\"$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S)Z\"" \
    --format="table(httpRequest.status)" \
    --limit=1000 2>/dev/null | tail -n +2 | sort | uniq -c || echo "No errors")

if [ "${ERROR_STATS}" == "No errors" ] || [ -z "${ERROR_STATS}" ]; then
    echo -e "${GREEN}No HTTP errors in the last 5 minutes${NC}"
else
    echo "${ERROR_STATS}"
fi

# 6. Rate Limiting Status
echo -e "\n${YELLOW}6. Rate Limiting Activity${NC}"
RATE_LIMITS=$(gcloud logging read "httpRequest.status=429 AND 
    timestamp>=\"$(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S)Z\"" \
    --format="value(jsonPayload.remoteIp)" \
    --limit=100 2>/dev/null | sort | uniq -c | sort -nr | head -10 || echo "None")

if [ "${RATE_LIMITS}" == "None" ] || [ -z "${RATE_LIMITS}" ]; then
    echo -e "${GREEN}No rate limit violations in the last 30 minutes${NC}"
else
    echo "IPs hitting rate limits:"
    echo "${RATE_LIMITS}"
fi

# 7. Current Traffic Volume
echo -e "\n${YELLOW}7. Current Traffic Volume${NC}"
TRAFFIC_RATE=$(gcloud monitoring read \
    "loadbalancing.googleapis.com/https/request_count" \
    --filter="resource.url_map_name=\"${LB_NAME}\"" \
    --window=5m \
    --format="table(point.value.int64_value,point.interval.end_time)" 2>/dev/null | tail -n 2 || echo "Unable to read metrics")
echo "${TRAFFIC_RATE}"

# 8. Security Alerts Status
echo -e "\n${YELLOW}8. Active Security Alerts${NC}"
ACTIVE_ALERTS=$(gcloud alpha monitoring policies list \
    --filter="displayName:Security OR displayName:DDoS" \
    --format="table(displayName,conditions[].displayName,conditions[].conditionThreshold.filter)" 2>/dev/null | head -20 || echo "Unable to check alerts")
echo "${ACTIVE_ALERTS}"

# 9. SSL Certificate Status
echo -e "\n${YELLOW}9. SSL Certificate Status${NC}"
SSL_STATUS=$(gcloud compute ssl-certificates describe roadtrip-ssl-cert-${ENVIRONMENT} \
    --format="table(name,managed.status,managed.domainStatus)" 2>/dev/null || echo "Not found")
echo "${SSL_STATUS}"

# 10. Summary and Recommendations
echo -e "\n${YELLOW}10. Summary${NC}"
echo "============================================"

# Calculate health score
HEALTH_SCORE=100
ISSUES=()

if [ "${EMERGENCY_STATUS}" != "True" ]; then
    HEALTH_SCORE=$((HEALTH_SCORE - 50))
    ISSUES+=("Emergency lockdown is active")
fi

if [ "${LB_STATUS}" != "Active" ]; then
    HEALTH_SCORE=$((HEALTH_SCORE - 30))
    ISSUES+=("Load balancer not found")
fi

if [ -n "${ERROR_STATS}" ] && [ "${ERROR_STATS}" != "No errors" ]; then
    HEALTH_SCORE=$((HEALTH_SCORE - 10))
    ISSUES+=("HTTP errors detected")
fi

if [ -n "${RATE_LIMITS}" ] && [ "${RATE_LIMITS}" != "None" ]; then
    HEALTH_SCORE=$((HEALTH_SCORE - 5))
    ISSUES+=("Rate limit violations detected")
fi

# Display health score
if [ ${HEALTH_SCORE} -ge 90 ]; then
    echo -e "${GREEN}Security Health Score: ${HEALTH_SCORE}/100 - Excellent${NC}"
elif [ ${HEALTH_SCORE} -ge 70 ]; then
    echo -e "${YELLOW}Security Health Score: ${HEALTH_SCORE}/100 - Good${NC}"
else
    echo -e "${RED}Security Health Score: ${HEALTH_SCORE}/100 - Needs Attention${NC}"
fi

# Display issues if any
if [ ${#ISSUES[@]} -gt 0 ]; then
    echo -e "\n${YELLOW}Issues detected:${NC}"
    for issue in "${ISSUES[@]}"; do
        echo "  - ${issue}"
    done
fi

# Recommendations
echo -e "\n${YELLOW}Recommendations:${NC}"
if [ "${EMERGENCY_STATUS}" != "True" ]; then
    echo -e "${RED}⚠ URGENT: Disable emergency lockdown to restore service${NC}"
fi

if [ -n "${ATTACKS}" ] && [ "${ATTACKS}" != "No data" ]; then
    echo "- Review blocked requests to ensure no false positives"
fi

if [ -n "${RATE_LIMITS}" ] && [ "${RATE_LIMITS}" != "None" ]; then
    echo "- Consider adjusting rate limits or whitelisting legitimate high-traffic IPs"
fi

echo -e "\n${GREEN}Health check completed successfully${NC}"