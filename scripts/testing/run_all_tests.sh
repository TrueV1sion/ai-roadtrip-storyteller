#!/bin/bash

# AI Road Trip Storyteller - Comprehensive Test Runner
# This script runs all test suites and generates a detailed report

echo "🚀 AI Road Trip Storyteller - Test Suite Runner"
echo "=============================================="
echo ""

# Set up environment
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export NODE_ENV=test

# Create test results directory
mkdir -p test_results
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="test_results/test_report_${TIMESTAMP}.txt"

# Function to run Python tests
run_python_tests() {
    echo "🐍 Running Python Tests..."
    echo "========================"
    
    # Unit tests
    echo "Running unit tests..."
    python -m pytest tests/unit/ -v --tb=short --cov=backend/app --cov-report=html:test_results/coverage_unit
    
    # Integration tests
    echo "Running integration tests..."
    python -m pytest tests/integration/ -v --tb=short --cov=backend/app --cov-report=html:test_results/coverage_integration
    
    # Performance tests
    echo "Running performance tests..."
    python -m pytest tests/performance/ -v --tb=short -m performance
    
    # Generate combined coverage report
    python -m pytest --cov=backend/app --cov-report=html:test_results/coverage_combined --cov-report=term
}

# Function to run JavaScript/TypeScript tests
run_mobile_tests() {
    echo ""
    echo "📱 Running Mobile Tests..."
    echo "========================"
    
    cd mobile
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        echo "Installing dependencies..."
        npm install
    fi
    
    # Run Jest tests
    npm test -- --coverage --coverageDirectory=../test_results/coverage_mobile
    
    # Run specific test suites
    npm test -- --testPathPattern="game_components" --verbose
    npm test -- --testPathPattern="reservation_components" --verbose
    npm test -- --testPathPattern="spotify_components" --verbose
    
    cd ..
}

# Function to run linting
run_linting() {
    echo ""
    echo "🔍 Running Code Quality Checks..."
    echo "================================"
    
    # Python linting
    echo "Python linting..."
    python -m black backend/ --check
    python -m isort backend/ --check-only
    python -m flake8 backend/
    python -m mypy backend/ --config-file backend/mypy.ini
    
    # JavaScript/TypeScript linting
    echo "JavaScript/TypeScript linting..."
    cd mobile && npm run lint && cd ..
}

# Function to run security checks
run_security_checks() {
    echo ""
    echo "🔒 Running Security Checks..."
    echo "============================"
    
    # Python security
    python -m bandit -r backend/ -f json -o test_results/bandit_report.json
    
    # JavaScript security
    cd mobile && npm audit --json > ../test_results/npm_audit.json && cd ..
}

# Function to generate test report
generate_report() {
    echo ""
    echo "📊 Generating Test Report..."
    echo "==========================="
    
    {
        echo "AI Road Trip Storyteller - Test Report"
        echo "Generated: $(date)"
        echo "======================================"
        echo ""
        
        # Python test results
        echo "Python Test Results:"
        python -m pytest tests/ --tb=no -q
        echo ""
        
        # Coverage summary
        echo "Coverage Summary:"
        python -m pytest --cov=backend/app --cov-report=term-missing:skip-covered | grep -E "TOTAL|backend/app"
        echo ""
        
        # Mobile test results
        echo "Mobile Test Results:"
        cd mobile && npm test -- --silent --json | jq '.numTotalTests, .numPassedTests, .numFailedTests' && cd ..
        echo ""
        
        # Performance metrics
        echo "Performance Metrics:"
        echo "- API Response Times: See test_results/performance_metrics.json"
        echo "- Mobile Load Times: See test_results/mobile_performance.json"
        echo ""
        
        # Security summary
        echo "Security Summary:"
        echo "- Python vulnerabilities: $(python -m bandit -r backend/ -f json | jq '.results | length')"
        echo "- NPM vulnerabilities: $(cd mobile && npm audit --json | jq '.vulnerabilities | length' && cd ..)"
        
    } > "$REPORT_FILE"
    
    echo "Report saved to: $REPORT_FILE"
}

# Main execution
main() {
    echo "Starting comprehensive test suite..."
    echo ""
    
    # Check dependencies
    command -v python >/dev/null 2>&1 || { echo "Python is required but not installed."; exit 1; }
    command -v node >/dev/null 2>&1 || { echo "Node.js is required but not installed."; exit 1; }
    command -v npm >/dev/null 2>&1 || { echo "npm is required but not installed."; exit 1; }
    
    # Run all test suites
    run_python_tests 2>&1 | tee -a "$REPORT_FILE"
    run_mobile_tests 2>&1 | tee -a "$REPORT_FILE"
    run_linting 2>&1 | tee -a "$REPORT_FILE"
    run_security_checks 2>&1 | tee -a "$REPORT_FILE"
    
    # Generate final report
    generate_report
    
    echo ""
    echo "✅ Test suite completed!"
    echo "📄 Full report available at: $REPORT_FILE"
    echo "📊 Coverage reports available in: test_results/"
    echo ""
    
    # Open coverage report in browser (optional)
    if command -v open >/dev/null 2>&1; then
        read -p "Open coverage report in browser? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            open test_results/coverage_combined/index.html
        fi
    fi
}

# Run main function
main

# Exit with appropriate code
if grep -q "FAILED" "$REPORT_FILE"; then
    exit 1
else
    exit 0
fi