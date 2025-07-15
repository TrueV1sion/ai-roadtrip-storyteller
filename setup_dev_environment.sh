#!/bin/bash
# Development Environment Setup Script for AI Road Trip Storyteller
# This script sets up the complete development environment

echo "🚗 AI Road Trip Storyteller - Development Setup"
echo "=============================================="

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running from project root
if [ ! -f "requirements.txt" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Step 1: Python Virtual Environment
echo ""
echo "Step 1: Setting up Python environment..."
echo "----------------------------------------"

if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    python3 -m venv venv || {
        print_error "Failed to create virtual environment"
        print_warning "Install python3-venv: sudo apt install python3-venv (Linux) or use brew (Mac)"
        exit 1
    }
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate || {
    print_error "Failed to activate virtual environment"
    exit 1
}

# Step 2: Install Python Dependencies
echo ""
echo "Step 2: Installing Python dependencies..."
echo "----------------------------------------"

print_status "Upgrading pip..."
pip install --upgrade pip

print_status "Installing production requirements..."
pip install -r requirements.txt || {
    print_error "Failed to install production requirements"
    exit 1
}

print_status "Installing development requirements..."
pip install -r requirements-dev.txt || {
    print_error "Failed to install development requirements"
    exit 1
}

# Step 3: Setup Test Configuration
echo ""
echo "Step 3: Setting up test configuration..."
echo "----------------------------------------"

# Create .env.test if it doesn't exist
if [ ! -f ".env.test" ]; then
    print_status "Creating .env.test file..."
    cat > .env.test << 'EOF'
# Test Environment Configuration
TEST_MODE=true
DATABASE_URL=postgresql://roadtrip:roadtrip_dev@localhost:5432/roadtrip_test
REDIS_URL=redis://localhost:6379/1
SECRET_KEY=test-secret-key-change-in-production
JWT_SECRET_KEY=test-jwt-secret-key

# API Keys (can be fake for testing)
GOOGLE_MAPS_API_KEY=test-google-maps-key
GOOGLE_AI_PROJECT_ID=test-project
GOOGLE_AI_LOCATION=us-central1
GOOGLE_AI_MODEL=gemini-1.5-flash
GCS_BUCKET_NAME=test-bucket
TICKETMASTER_API_KEY=test-ticketmaster-key
OPENWEATHERMAP_API_KEY=test-weather-key
RECREATION_GOV_API_KEY=test-recreation-key

# Feature Flags
MVP_MODE=true
EOF
    print_status ".env.test created"
else
    print_status ".env.test already exists"
fi

# Step 4: Start Docker Services
echo ""
echo "Step 4: Starting Docker services..."
echo "-----------------------------------"

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    print_warning "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! docker info &> /dev/null; then
    print_error "Docker is not running. Please start Docker."
    exit 1
fi

print_status "Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis || {
    print_error "Failed to start Docker services"
    print_warning "Make sure Docker is running and ports 5432/6379 are free"
    exit 1
}

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 5

# Step 5: Database Setup
echo ""
echo "Step 5: Setting up databases..."
echo "-------------------------------"

# Check if database exists
docker exec roadtrip_postgres psql -U roadtrip -lqt | cut -d \| -f 1 | grep -qw roadtrip_test
if [ $? -ne 0 ]; then
    print_status "Creating test database..."
    docker exec roadtrip_postgres createdb -U roadtrip roadtrip_test || {
        print_error "Failed to create test database"
        exit 1
    }
else
    print_status "Test database already exists"
fi

# Run migrations
print_status "Running database migrations..."
alembic upgrade head || {
    print_error "Failed to run migrations"
    print_warning "Check your database connection in .env file"
    exit 1
}

# Step 6: Verify Test Setup
echo ""
echo "Step 6: Verifying test setup..."
echo "-------------------------------"

# Check if tests can be discovered
print_status "Discovering tests..."
pytest --co -q || {
    print_error "Test discovery failed"
    exit 1
}

# Count discovered tests
test_count=$(pytest --co -q | grep -c "<Function\|<Method")
print_status "Found $test_count tests"

# Step 7: Run MVP Tests
echo ""
echo "Step 7: Running MVP tests..."
echo "----------------------------"

print_status "Running core MVP tests..."
pytest tests/unit/test_master_orchestration_agent.py -v -k "test_process_user_input_story_request" || {
    print_warning "Some tests failed - this is expected if APIs are not configured"
}

# Final Summary
echo ""
echo "========================================"
echo "✨ Development Environment Setup Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Run all tests: pytest"
echo "3. Run MVP tests only: pytest -m mvp"
echo "4. Run specific test file: pytest tests/unit/test_master_orchestration_agent.py"
echo "5. Start backend server: uvicorn backend.app.main_mvp:app --reload"
echo ""
echo "Docker services running:"
echo "- PostgreSQL: localhost:5432"
echo "- Redis: localhost:6379"
echo ""
print_warning "Remember to configure your .env file with real API keys for full functionality"
echo ""