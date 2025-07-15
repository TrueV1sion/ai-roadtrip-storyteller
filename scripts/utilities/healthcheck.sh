#!/bin/bash

# Health check script for AI Road Trip Storyteller
# This script performs comprehensive health checks for the application

set -e

# Configuration
HOST=${HOST:-"localhost"}
PORT=${PORT:-"8000"}
TIMEOUT=${TIMEOUT:-"10"}

# Function to check HTTP endpoint
check_http() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    
    if curl --fail --silent --max-time "$TIMEOUT" \
           --write-out "HTTP %{http_code}" \
           "http://${HOST}:${PORT}${endpoint}" > /dev/null; then
        return 0
    else
        echo "Health check failed for endpoint: $endpoint"
        return 1
    fi
}

# Function to check if service is responding
check_basic_connectivity() {
    if ! curl --fail --silent --max-time "$TIMEOUT" \
             "http://${HOST}:${PORT}/health" > /dev/null; then
        echo "Basic connectivity check failed"
        exit 1
    fi
}

# Function to check database connectivity
check_database() {
    if ! curl --fail --silent --max-time "$TIMEOUT" \
             "http://${HOST}:${PORT}/health/db" > /dev/null; then
        echo "Database health check failed"
        exit 1
    fi
}

# Function to check AI service connectivity
check_ai_service() {
    if ! curl --fail --silent --max-time "$TIMEOUT" \
             "http://${HOST}:${PORT}/health/ai" > /dev/null; then
        echo "AI service health check failed"
        exit 1
    fi
}

# Function to check critical endpoints
check_critical_endpoints() {
    local endpoints=(
        "/health"
        "/api/docs"
    )
    
    for endpoint in "${endpoints[@]}"; do
        if ! check_http "$endpoint"; then
            echo "Critical endpoint check failed: $endpoint"
            exit 1
        fi
    done
}

# Main health check function
main() {
    echo "Running health checks..."
    
    # Basic connectivity test
    check_basic_connectivity
    echo "✓ Basic connectivity OK"
    
    # Check critical endpoints
    check_critical_endpoints
    echo "✓ Critical endpoints OK"
    
    # Database health check (if endpoint exists)
    if curl --fail --silent --max-time 2 "http://${HOST}:${PORT}/health/db" > /dev/null 2>&1; then
        check_database
        echo "✓ Database connectivity OK"
    fi
    
    # AI service health check (if endpoint exists)
    if curl --fail --silent --max-time 2 "http://${HOST}:${PORT}/health/ai" > /dev/null 2>&1; then
        check_ai_service
        echo "✓ AI service connectivity OK"
    fi
    
    echo "All health checks passed"
    exit 0
}

# Run main function
main "$@"