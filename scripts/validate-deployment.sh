#!/bin/bash
# Deployment Validation Script - Six Sigma Standards

set -e

echo "🎯 AI Road Trip Deployment Validator"
echo "==================================="

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Validation functions
check_health() {
    local service=$1
    local url=$2
    
    if curl -s -f "$url/health" > /dev/null; then
        echo -e "${GREEN}✓${NC} $service is healthy"
        return 0
    else
        echo -e "${RED}✗${NC} $service is not responding"
        return 1
    fi
}

check_metric() {
    local metric=$1
    local value=$2
    local threshold=$3
    local comparison=$4
    
    if [ "$comparison" = "lt" ] && [ "$value" -lt "$threshold" ]; then
        echo -e "${GREEN}✓${NC} $metric: $value (< $threshold)"
    elif [ "$comparison" = "gt" ] && [ "$value" -gt "$threshold" ]; then
        echo -e "${GREEN}✓${NC} $metric: $value (> $threshold)"
    else
        echo -e "${RED}✗${NC} $metric: $value (failed threshold: $threshold)"
        return 1
    fi
}

# Environment
ENV=${1:-production}
BASE_URL="https://api.roadtrip.app"

if [ "$ENV" = "staging" ]; then
    BASE_URL="https://staging.api.roadtrip.app"
fi

echo "Validating $ENV environment..."
echo ""

# Health Checks
echo "Service Health Checks:"
check_health "Backend API" "$BASE_URL"
check_health "Knowledge Graph" "$BASE_URL/api/v1/knowledge-graph"

# Performance Checks
echo ""
echo "Performance Metrics:"
RESPONSE_TIME=$(curl -w "%{time_total}" -o /dev/null -s "$BASE_URL/health")
RESPONSE_MS=$(echo "$RESPONSE_TIME * 1000" | bc | cut -d. -f1)
check_metric "API Response Time" "$RESPONSE_MS" "200" "lt"

# Database Check
echo ""
echo "Database Validation:"
DB_CONN=$(curl -s "$BASE_URL/api/v1/database/health" | jq -r '.connections')
check_metric "DB Connections" "$DB_CONN" "100" "lt"

# Cache Check
echo ""
echo "Cache Validation:"
CACHE_HIT=$(curl -s "$BASE_URL/api/v1/metrics" | jq -r '.cache_hit_rate')
CACHE_PCT=$(echo "$CACHE_HIT * 100" | bc | cut -d. -f1)
check_metric "Cache Hit Rate" "$CACHE_PCT" "80" "gt"

# Security Check
echo ""
echo "Security Validation:"
SECURITY_HEADERS=$(curl -s -I "$BASE_URL/health" | grep -c "X-Content-Type-Options\|X-Frame-Options\|X-XSS-Protection")
check_metric "Security Headers" "$SECURITY_HEADERS" "3" "gt"

# Final Report
echo ""
echo "==================================="
echo "Deployment Validation Complete"
echo "Environment: $ENV"
echo "Timestamp: $(date)"
echo "==================================="
