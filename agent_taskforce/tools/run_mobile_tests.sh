#!/bin/bash
#
# Mobile Test Runner for Road Trip App
# Executes comprehensive test suite with coverage reporting
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MOBILE_DIR="/mnt/c/users/jared/onedrive/desktop/roadtrip/mobile"
REPORT_DIR="/mnt/c/users/jared/onedrive/desktop/roadtrip/agent_taskforce/reports"
COVERAGE_THRESHOLD=80

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check prerequisites
check_prerequisites() {
    print_color $BLUE "Checking prerequisites..."
    
    if [ ! -d "$MOBILE_DIR" ]; then
        print_color $RED "Error: Mobile directory not found at $MOBILE_DIR"
        exit 1
    fi
    
    cd "$MOBILE_DIR"
    
    if [ ! -f "package.json" ]; then
        print_color $RED "Error: package.json not found"
        exit 1
    fi
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        print_color $YELLOW "Installing dependencies..."
        npm install
    fi
    
    print_color $GREEN "Prerequisites check passed!"
}

# Function to update Jest configuration for coverage
update_jest_config() {
    print_color $BLUE "Updating Jest configuration for coverage..."
    
    # Add coverage script to package.json if not exists
    if ! grep -q "test:coverage" package.json; then
        print_color $YELLOW "Adding test:coverage script to package.json..."
        
        # Use Node.js to update package.json
        node -e "
        const fs = require('fs');
        const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
        pkg.scripts = pkg.scripts || {};
        pkg.scripts['test:coverage'] = 'jest --coverage --coverageReporters=text-lcov --coverageReporters=html --coverageReporters=json-summary';
        pkg.scripts['test:watch'] = 'jest --watch';
        pkg.scripts['test:ci'] = 'jest --ci --coverage --maxWorkers=2';
        fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2));
        "
    fi
}

# Function to generate missing tests
generate_missing_tests() {
    print_color $BLUE "Generating missing tests..."
    
    cd /mnt/c/users/jared/onedrive/desktop/roadtrip
    
    # Generate test utilities first
    python3 agent_taskforce/tools/mobile_test_generator.py --utils
    
    # Generate all missing tests
    python3 agent_taskforce/tools/mobile_test_generator.py --all
    
    cd "$MOBILE_DIR"
}

# Function to run tests with coverage
run_tests() {
    local test_type=$1
    print_color $BLUE "Running $test_type tests..."
    
    case $test_type in
        "unit")
            npm run test:coverage -- --testPathPattern="(components|hooks|utils|contexts).*test\.(ts|tsx)$"
            ;;
        "integration")
            npm run test:coverage -- --testPathPattern="(screens|services).*test\.(ts|tsx)$"
            ;;
        "all")
            npm run test:coverage
            ;;
        *)
            print_color $RED "Unknown test type: $test_type"
            exit 1
            ;;
    esac
}

# Function to generate coverage report
generate_coverage_report() {
    print_color $BLUE "Generating coverage report..."
    
    if [ ! -f "coverage/coverage-summary.json" ]; then
        print_color $RED "Coverage summary not found. Running tests first..."
        run_tests "all"
    fi
    
    # Parse coverage data and create report
    node -e "
    const fs = require('fs');
    const coverage = JSON.parse(fs.readFileSync('coverage/coverage-summary.json', 'utf8'));
    const total = coverage.total;
    
    const report = {
        timestamp: new Date().toISOString(),
        summary: {
            lines: total.lines.pct,
            statements: total.statements.pct,
            functions: total.functions.pct,
            branches: total.branches.pct
        },
        files: {}
    };
    
    // Get file-level coverage
    Object.entries(coverage).forEach(([file, data]) => {
        if (file !== 'total') {
            report.files[file] = {
                lines: data.lines.pct,
                statements: data.statements.pct,
                functions: data.functions.pct,
                branches: data.branches.pct
            };
        }
    });
    
    fs.writeFileSync('coverage-report.json', JSON.stringify(report, null, 2));
    
    // Check if coverage meets threshold
    const meetsThreshold = Object.values(report.summary).every(pct => pct >= $COVERAGE_THRESHOLD);
    
    console.log('Coverage Summary:');
    console.log('Lines:', report.summary.lines + '%');
    console.log('Statements:', report.summary.statements + '%');
    console.log('Functions:', report.summary.functions + '%');
    console.log('Branches:', report.summary.branches + '%');
    console.log('');
    console.log('Threshold:', meetsThreshold ? 'PASSED' : 'FAILED');
    
    process.exit(meetsThreshold ? 0 : 1);
    "
}

# Function to run critical path tests
run_critical_path_tests() {
    print_color $BLUE "Running critical path tests..."
    
    # Define critical test suites
    CRITICAL_TESTS=(
        "src/screens/__tests__/OnboardingScreen.test.tsx"
        "src/screens/auth/__tests__/LoginScreen.test.tsx"
        "src/screens/__tests__/DrivingModeScreen.test.tsx"
        "src/screens/__tests__/VoiceBookingScreen.test.tsx"
        "src/services/__tests__/authService.test.ts"
        "src/services/__tests__/storyService.test.ts"
        "src/services/__tests__/voiceService.test.ts"
        "src/services/__tests__/locationService.test.ts"
        "src/contexts/__tests__/AuthContext.test.tsx"
        "src/components/__tests__/VoiceAssistant.test.tsx"
        "src/components/__tests__/BookingFlow.test.tsx"
        "src/components/__tests__/MapView.test.tsx"
    )
    
    # Run each critical test
    for test in "${CRITICAL_TESTS[@]}"; do
        if [ -f "$test" ]; then
            print_color $GREEN "Running: $test"
            npm test -- "$test" --coverage
        else
            print_color $YELLOW "Missing critical test: $test"
        fi
    done
}

# Function to setup continuous testing
setup_continuous_testing() {
    print_color $BLUE "Setting up continuous testing..."
    
    # Create pre-commit hook
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Run tests before commit

echo "Running mobile tests..."
cd mobile
npm test -- --onlyChanged --passWithNoTests

if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi
EOF
    
    chmod +x .git/hooks/pre-commit
    
    # Create GitHub Actions workflow
    mkdir -p ../.github/workflows
    cat > ../.github/workflows/mobile-tests.yml << 'EOF'
name: Mobile Tests

on:
  push:
    branches: [ main, develop ]
    paths:
      - 'mobile/**'
  pull_request:
    branches: [ main ]
    paths:
      - 'mobile/**'

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Setup Node.js
      uses: actions/setup-node@v3
      with:
        node-version: '18'
        cache: 'npm'
        cache-dependency-path: mobile/package-lock.json
    
    - name: Install dependencies
      run: |
        cd mobile
        npm ci
    
    - name: Run tests
      run: |
        cd mobile
        npm run test:ci
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        directory: ./mobile/coverage
        fail_ci_if_error: true
EOF
    
    print_color $GREEN "Continuous testing setup complete!"
}

# Main execution flow
main() {
    print_color $GREEN "=== Mobile Test Runner for Road Trip App ==="
    
    # Parse command line arguments
    COMMAND=${1:-"all"}
    
    case $COMMAND in
        "check")
            check_prerequisites
            ;;
        "generate")
            check_prerequisites
            generate_missing_tests
            ;;
        "unit")
            check_prerequisites
            update_jest_config
            run_tests "unit"
            ;;
        "integration")
            check_prerequisites
            update_jest_config
            run_tests "integration"
            ;;
        "critical")
            check_prerequisites
            update_jest_config
            run_critical_path_tests
            ;;
        "coverage")
            check_prerequisites
            update_jest_config
            run_tests "all"
            generate_coverage_report
            ;;
        "continuous")
            check_prerequisites
            setup_continuous_testing
            ;;
        "all")
            check_prerequisites
            update_jest_config
            generate_missing_tests
            run_tests "all"
            generate_coverage_report
            ;;
        *)
            print_color $RED "Unknown command: $COMMAND"
            echo "Usage: $0 [check|generate|unit|integration|critical|coverage|continuous|all]"
            exit 1
            ;;
    esac
    
    print_color $GREEN "Test execution complete!"
}

# Run main function
main "$@"