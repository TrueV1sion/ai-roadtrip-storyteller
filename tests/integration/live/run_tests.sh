#!/bin/bash

# Script to run integration tests with various configurations

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
TEST_MODE=${TEST_MODE:-mock}
GENERATE_REPORTS=${GENERATE_TEST_REPORTS:-true}

echo -e "${GREEN}Running Integration Tests in ${TEST_MODE} mode${NC}"
echo "========================================"

# Create reports directory
mkdir -p reports

# Function to run a test suite
run_test_suite() {
    local suite_name=$1
    local test_file=$2
    
    echo -e "\n${YELLOW}Running ${suite_name} Tests...${NC}"
    
    # Export common variables
    export GENERATE_TEST_REPORTS=$GENERATE_REPORTS
    
    # Run the test
    if pytest "$test_file" -v --tb=short; then
        echo -e "${GREEN}✓ ${suite_name} tests passed${NC}"
    else
        echo -e "${RED}✗ ${suite_name} tests failed${NC}"
        FAILED_TESTS+=("$suite_name")
    fi
}

# Array to track failed tests
FAILED_TESTS=()

# Run each test suite
if [ "$1" == "opentable" ] || [ -z "$1" ]; then
    export OPENTABLE_TEST_MODE=$TEST_MODE
    run_test_suite "OpenTable" "test_opentable_integration.py"
fi

if [ "$1" == "recreation" ] || [ -z "$1" ]; then
    export RECREATION_GOV_TEST_MODE=$TEST_MODE
    run_test_suite "Recreation.gov" "test_recreation_gov_integration.py"
fi

if [ "$1" == "shell" ] || [ -z "$1" ]; then
    export SHELL_RECHARGE_TEST_MODE=$TEST_MODE
    run_test_suite "Shell Recharge" "test_shell_recharge_integration.py"
fi

# Summary
echo -e "\n========================================"
echo -e "${GREEN}Test Summary${NC}"
echo "========================================"

if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Failed tests:${NC}"
    for test in "${FAILED_TESTS[@]}"; do
        echo -e "  - $test"
    done
    exit 1
fi

# List generated reports
if [ "$GENERATE_REPORTS" == "true" ]; then
    echo -e "\n${YELLOW}Generated Reports:${NC}"
    find reports -name "*.json" -type f -printf "  - %f\n" | sort
fi