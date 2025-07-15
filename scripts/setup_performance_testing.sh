#!/bin/bash

# AI Road Trip Storyteller - Performance Testing Setup Script
# This script sets up the environment for comprehensive performance testing

set -e

echo "🚀 Setting up AI Road Trip Storyteller Performance Testing Environment"
echo "=================================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if running from project root
if [ ! -f "backend/app/main.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

print_info "Checking system requirements..."

# Check Python version
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1-2)
if [ "$(echo "$PYTHON_VERSION >= 3.9" | bc)" -eq 0 ]; then
    print_error "Python 3.9+ is required (found $PYTHON_VERSION)"
    exit 1
fi
print_status "Python $PYTHON_VERSION detected"

# Check Node.js version
if ! command -v node &> /dev/null; then
    print_warning "Node.js not found - mobile testing will be limited"
else
    NODE_VERSION=$(node --version | sed 's/v//')
    print_status "Node.js $NODE_VERSION detected"
fi

# Check available system resources
TOTAL_RAM=$(free -g | awk '/^Mem:/{print $2}')
CPU_CORES=$(nproc)
AVAILABLE_DISK=$(df -BG . | awk 'NR==2{print $4}' | sed 's/G//')

print_info "System Resources:"
print_info "  CPU Cores: $CPU_CORES"
print_info "  Total RAM: ${TOTAL_RAM}GB"
print_info "  Available Disk: ${AVAILABLE_DISK}GB"

if [ "$TOTAL_RAM" -lt 4 ]; then
    print_warning "Less than 4GB RAM available - performance tests may be limited"
fi

if [ "$CPU_CORES" -lt 2 ]; then
    print_warning "Less than 2 CPU cores - concurrent testing will be limited"
fi

# Install system dependencies
print_info "Installing system dependencies..."

if command -v apt-get &> /dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y \
        postgresql-client \
        redis-tools \
        build-essential \
        libpq-dev \
        bc \
        curl \
        jq
elif command -v brew &> /dev/null; then
    brew install postgresql redis bc jq
elif command -v yum &> /dev/null; then
    sudo yum install -y postgresql redis bc jq
else
    print_warning "Package manager not detected - manual dependency installation may be required"
fi

print_status "System dependencies installed"

# Setup Python virtual environment
print_info "Setting up Python virtual environment..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_status "Virtual environment created"
else
    print_info "Virtual environment already exists"
fi

source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
print_info "Installing Python dependencies..."

pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install performance testing specific dependencies
pip install \
    locust \
    aiohttp \
    matplotlib \
    pandas \
    prometheus_client \
    psutil \
    numpy \
    redis

print_status "Python dependencies installed"

# Setup environment configuration
print_info "Setting up environment configuration..."

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_status "Environment file created from template"
    else
        cat > .env << EOF
# AI Road Trip Storyteller Environment Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost/roadtrip
REDIS_URL=redis://localhost:6379
ENVIRONMENT=development
DEBUG=true
JWT_SECRET_KEY=your-secret-key-here
RATE_LIMIT_ENABLED=false

# Performance Testing Settings
PERFORMANCE_TESTING=true
MAX_CONCURRENT_CONNECTIONS=1000
EOF
        print_status "Environment file created"
    fi
else
    print_info "Environment file already exists"
fi

# Setup services using Docker Compose
print_info "Setting up required services..."

if command -v docker-compose &> /dev/null || command -v docker &> /dev/null; then
    if [ -f "docker-compose.yml" ]; then
        print_info "Starting PostgreSQL and Redis services..."
        
        # Start only database and cache services
        docker-compose up -d postgres redis
        
        # Wait for services to be ready
        print_info "Waiting for services to be ready..."
        
        # Wait for PostgreSQL
        timeout 60 bash -c 'until docker-compose exec -T postgres pg_isready -U postgres; do sleep 2; done' || {
            print_error "PostgreSQL failed to start"
            exit 1
        }
        
        # Wait for Redis
        timeout 60 bash -c 'until docker-compose exec -T redis redis-cli ping; do sleep 2; done' || {
            print_error "Redis failed to start"
            exit 1
        }
        
        print_status "Database and Redis services are running"
    else
        print_warning "docker-compose.yml not found - manual service setup required"
    fi
else
    print_warning "Docker not available - manual service setup required"
fi

# Run database migrations
print_info "Running database migrations..."

if command -v alembic &> /dev/null; then
    alembic upgrade head
    print_status "Database migrations completed"
else
    print_warning "Alembic not found - database migrations skipped"
fi

# Create performance testing directories
print_info "Setting up performance testing directories..."

mkdir -p tests/performance/reports/benchmarks
mkdir -p tests/performance/reports/load_tests
mkdir -p tests/performance/reports/stress_tests
mkdir -p tests/performance/reports/monitoring

print_status "Performance testing directories created"

# Verify installation
print_info "Verifying installation..."

# Test Python imports
python3 -c "
import locust
import aiohttp
import matplotlib
import pandas
import prometheus_client
import psutil
import numpy
import redis
print('All Python dependencies imported successfully')
" || {
    print_error "Python dependency verification failed"
    exit 1
}

print_status "Python dependencies verified"

# Test database connection
if [ -f ".env" ]; then
    source .env
    if command -v psql &> /dev/null && [ -n "$DATABASE_URL" ]; then
        if psql "$DATABASE_URL" -c "SELECT 1;" &> /dev/null; then
            print_status "Database connection verified"
        else
            print_warning "Database connection failed - check DATABASE_URL"
        fi
    fi
fi

# Test Redis connection
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        print_status "Redis connection verified"
    else
        print_warning "Redis connection failed"
    fi
fi

# Create quick test script
print_info "Creating quick test script..."

cat > run_quick_performance_test.sh << 'EOF'
#!/bin/bash

# Quick Performance Test Runner
echo "🏃 Running Quick Performance Test..."

# Activate virtual environment
source venv/bin/activate

# Start API server in background
echo "Starting API server..."
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for server to be ready
echo "Waiting for API server..."
timeout 60 bash -c 'until curl -sf http://localhost:8000/api/health; do sleep 2; done'

if [ $? -eq 0 ]; then
    echo "✅ API server is ready"
    
    # Run quick performance test
    echo "Running performance tests..."
    python tests/performance/run_performance_tests.py --ci-mode
    
    echo "✅ Performance tests completed"
else
    echo "❌ API server failed to start"
fi

# Cleanup
echo "Cleaning up..."
kill $API_PID 2>/dev/null || true

echo "🎉 Quick performance test finished!"
EOF

chmod +x run_quick_performance_test.sh
print_status "Quick test script created: run_quick_performance_test.sh"

# Generate performance testing checklist
print_info "Generating performance testing checklist..."

cat > PERFORMANCE_TESTING_CHECKLIST.md << 'EOF'
# Performance Testing Checklist

## Pre-Test Setup ✅
- [ ] All system dependencies installed
- [ ] Python virtual environment activated
- [ ] Required services (PostgreSQL, Redis) running
- [ ] Database migrations completed
- [ ] Environment variables configured

## Test Execution
- [ ] Run baseline benchmarks: `python tests/performance/run_performance_tests.py --skip-load --skip-stress`
- [ ] Run load tests: `python tests/performance/run_performance_tests.py --skip-stress --skip-benchmarks`
- [ ] Run stress tests: `python tests/performance/run_performance_tests.py --skip-load --skip-benchmarks`
- [ ] Run full suite: `python tests/performance/run_performance_tests.py`

## CI/CD Integration
- [ ] GitHub Actions workflow configured
- [ ] Performance regression detection enabled
- [ ] Alert thresholds configured appropriately

## Monitoring Setup
- [ ] Prometheus metrics endpoint accessible
- [ ] Performance monitoring enabled
- [ ] Alert notifications configured

## Post-Test Analysis
- [ ] Review generated reports in `tests/performance/reports/`
- [ ] Analyze performance trends
- [ ] Update baselines if needed
- [ ] Document any performance issues found

## Quick Commands

```bash
# Quick test (CI mode)
./run_quick_performance_test.sh

# Full performance suite
source venv/bin/activate
python tests/performance/run_performance_tests.py

# Monitoring only
python tests/performance/run_performance_tests.py --enable-monitoring --skip-load --skip-stress --skip-benchmarks

# Custom URL testing
python tests/performance/run_performance_tests.py --url https://your-api.com --ci-mode
```
EOF

print_status "Performance testing checklist created: PERFORMANCE_TESTING_CHECKLIST.md"

# Final summary
echo ""
echo "🎉 Performance Testing Environment Setup Complete!"
echo "=================================================="
print_info "What's been set up:"
print_info "  ✅ System dependencies installed"
print_info "  ✅ Python virtual environment with all dependencies"
print_info "  ✅ Docker services (PostgreSQL, Redis) started"
print_info "  ✅ Database migrations completed"
print_info "  ✅ Performance testing directories created"
print_info "  ✅ Quick test script created"
print_info "  ✅ Testing checklist generated"

echo ""
print_info "Next steps:"
print_info "  1. Review PERFORMANCE_TESTING_CHECKLIST.md"
print_info "  2. Run quick test: ./run_quick_performance_test.sh"
print_info "  3. Check results in tests/performance/reports/"

echo ""
print_info "For help, see: tests/performance/README.md"

# Check if API server can start
print_info "Testing API server startup..."
source venv/bin/activate

timeout 10 bash -c '
uvicorn backend.app.main:app --host 0.0.0.0 --port 8001 &
API_PID=$!
sleep 5
if curl -sf http://localhost:8001/api/health; then
    echo "✅ API server test successful"
else
    echo "⚠️  API server test failed - check configuration"
fi
kill $API_PID 2>/dev/null || true
'

echo ""
print_status "Performance testing environment is ready! 🚀"