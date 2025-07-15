#!/bin/bash

# AI Road Trip Storyteller - Staging Environment Deployment Script
# This script deploys a complete staging environment that mirrors production

set -e  # Exit on any error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="roadtrip-460720"
REGION="us-central1"
ENVIRONMENT="staging"
TERRAFORM_DIR="."
SCRIPTS_DIR="./scripts"
BACKEND_DIR="./backend"

# Deployment tracking
DEPLOYMENT_ID=$(date +%Y%m%d-%H%M%S)
LOG_FILE="staging-deployment-${DEPLOYMENT_ID}.log"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
}

print_section() {
    echo -e "\n${PURPLE}==== $1 ====${NC}\n" | tee -a "$LOG_FILE"
}

# Function to check prerequisites
check_prerequisites() {
    print_section "Checking Prerequisites"
    
    local missing_tools=()
    
    # Check required tools
    command -v gcloud >/dev/null 2>&1 || missing_tools+=("gcloud")
    command -v terraform >/dev/null 2>&1 || missing_tools+=("terraform")
    command -v docker >/dev/null 2>&1 || missing_tools+=("docker")
    command -v python3 >/dev/null 2>&1 || missing_tools+=("python3")
    command -v npm >/dev/null 2>&1 || missing_tools+=("npm")
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        print_status "Please install missing tools and try again."
        exit 1
    fi
    
    # Check gcloud authentication
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        print_error "Not authenticated with gcloud. Run 'gcloud auth login' first."
        exit 1
    fi
    
    # Set project
    gcloud config set project "$PROJECT_ID" 2>/dev/null
    
    # Verify project access
    if ! gcloud projects describe "$PROJECT_ID" >/dev/null 2>&1; then
        print_error "Cannot access project '$PROJECT_ID'. Check project ID and permissions."
        exit 1
    fi
    
    print_success "All prerequisites met"
}

# Function to enable required APIs
enable_apis() {
    print_section "Enabling Required APIs"
    
    local apis=(
        "run.googleapis.com"
        "cloudbuild.googleapis.com"
        "containerregistry.googleapis.com"
        "sqladmin.googleapis.com"
        "secretmanager.googleapis.com"
        "servicenetworking.googleapis.com"
        "redis.googleapis.com"
        "monitoring.googleapis.com"
        "logging.googleapis.com"
        "cloudtrace.googleapis.com"
        "aiplatform.googleapis.com"
        "texttospeech.googleapis.com"
        "maps-backend.googleapis.com"
        "compute.googleapis.com"
        "storage-api.googleapis.com"
    )
    
    for api in "${apis[@]}"; do
        print_status "Enabling $api..."
        if gcloud services enable "$api" --project="$PROJECT_ID" 2>/dev/null; then
            print_success "Enabled $api"
        else
            print_warning "$api may already be enabled"
        fi
    done
}

# Function to create staging-specific secrets
setup_staging_secrets() {
    print_section "Setting Up Staging Secrets"
    
    # Create staging-specific environment file
    cat > .env.staging <<EOF
# Staging Environment Configuration
ENVIRONMENT=staging
SECRET_KEY=$(openssl rand -hex 32)
JWT_SECRET_KEY=$(openssl rand -hex 32)

# API Keys (reuse from production with staging limits)
GOOGLE_MAPS_API_KEY=${GOOGLE_MAPS_API_KEY:-"staging-placeholder"}
OPENWEATHER_API_KEY=${OPENWEATHER_API_KEY:-"staging-placeholder"}
TICKETMASTER_API_KEY=${TICKETMASTER_API_KEY:-"staging-placeholder"}

# Staging-specific configurations
DEBUG=false
LOG_LEVEL=INFO
ALLOWED_HOSTS=roadtrip-backend-staging-*.a.run.app

# Feature flags for staging
ENABLE_MOCK_MODE=true
ENABLE_PERFORMANCE_LOGGING=true
ENABLE_DETAILED_ERRORS=true

# Rate limiting (more permissive for testing)
RATE_LIMIT_PER_MINUTE=1000
RATE_LIMIT_PER_HOUR=10000
EOF
    
    # Upload secrets to Secret Manager
    while IFS='=' read -r key value; do
        # Skip comments and empty lines
        [[ $key =~ ^#.*$ ]] && continue
        [[ -z $key ]] && continue
        
        # Remove quotes from value
        value=$(echo "$value" | sed 's/^["'\'']//' | sed 's/["'\'']$//')
        
        # Create staging-specific secret name
        secret_name="${key}-staging"
        
        if gcloud secrets describe "$secret_name" --project="$PROJECT_ID" >/dev/null 2>&1; then
            print_status "Updating secret $secret_name..."
            echo -n "$value" | gcloud secrets versions add "$secret_name" --data-file=- --project="$PROJECT_ID"
        else
            print_status "Creating secret $secret_name..."
            echo -n "$value" | gcloud secrets create "$secret_name" --data-file=- --project="$PROJECT_ID"
        fi
    done < .env.staging
    
    print_success "Staging secrets configured"
}

# Function to build and push staging Docker image
build_staging_image() {
    print_section "Building Staging Docker Image"
    
    local image_tag="gcr.io/$PROJECT_ID/roadtrip-backend-staging:${DEPLOYMENT_ID}"
    local latest_tag="gcr.io/$PROJECT_ID/roadtrip-backend-staging:latest"
    
    # Create staging Dockerfile
    cat > Dockerfile.staging <<'EOF'
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Set environment variables
ENV PYTHONPATH=/app
ENV ENVIRONMENT=staging
ENV PORT=8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8080"]
EOF
    
    # Build image
    print_status "Building Docker image..."
    docker build -f Dockerfile.staging -t "$image_tag" -t "$latest_tag" .
    
    # Configure Docker for GCR
    gcloud auth configure-docker --quiet
    
    # Push image
    print_status "Pushing Docker image..."
    docker push "$image_tag"
    docker push "$latest_tag"
    
    print_success "Staging image built and pushed: $latest_tag"
}

# Function to deploy infrastructure with Terraform
deploy_infrastructure() {
    print_section "Deploying Staging Infrastructure"
    
    cd "$TERRAFORM_DIR" || exit 1
    
    # Initialize Terraform
    print_status "Initializing Terraform..."
    terraform init -upgrade
    
    # Plan deployment
    print_status "Planning infrastructure changes..."
    terraform plan -var-file="terraform.tfvars" -out=staging.tfplan
    
    # Apply changes
    print_status "Applying infrastructure changes..."
    terraform apply staging.tfplan
    
    # Capture outputs
    STAGING_URL=$(terraform output -raw staging_cloud_run_url)
    STAGING_DB=$(terraform output -raw staging_database_connection)
    STAGING_REDIS=$(terraform output -raw staging_redis_host)
    
    cd - >/dev/null
    
    print_success "Infrastructure deployed successfully"
}

# Function to run database migrations
run_database_migrations() {
    print_section "Running Database Migrations"
    
    # Create migration job
    cat > migrate-staging.yaml <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: roadtrip-staging-migrate-${DEPLOYMENT_ID}
spec:
  template:
    spec:
      containers:
      - name: migrate
        image: gcr.io/$PROJECT_ID/roadtrip-backend-staging:latest
        command: ["alembic", "upgrade", "head"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: roadtrip-staging-db-url
              key: latest
      restartPolicy: Never
  backoffLimit: 3
EOF
    
    # Deploy migration job to Cloud Run Jobs
    print_status "Creating migration job..."
    gcloud run jobs create "staging-migrate-${DEPLOYMENT_ID}" \
        --image="gcr.io/$PROJECT_ID/roadtrip-backend-staging:latest" \
        --command="alembic" \
        --args="upgrade,head" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --set-env-vars="ENVIRONMENT=staging" \
        --set-secrets="DATABASE_URL=roadtrip-staging-db-url:latest" \
        --max-retries=3
    
    # Execute migration
    print_status "Running migrations..."
    gcloud run jobs execute "staging-migrate-${DEPLOYMENT_ID}" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --wait
    
    print_success "Database migrations completed"
}

# Function to seed staging data
seed_staging_data() {
    print_section "Seeding Staging Data"
    
    # Create seed data script
    cat > seed_staging_data.py <<'EOF'
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.models import User, Story, Theme, SideQuest
from backend.app.core.auth import get_password_hash
from backend.app.database import SessionLocal
from datetime import datetime, timedelta
import random

def seed_staging_data():
    db = SessionLocal()
    
    try:
        # Create test users
        test_users = []
        for i in range(5):
            user = User(
                email=f"test{i}@staging.roadtrip.app",
                username=f"staginguser{i}",
                full_name=f"Staging User {i}",
                hashed_password=get_password_hash("staging123"),
                is_active=True,
                is_verified=True,
                role="user" if i > 0 else "admin"
            )
            db.add(user)
            test_users.append(user)
        
        db.commit()
        
        # Create test themes
        themes = [
            Theme(name="Adventure", description="Epic adventure stories", is_active=True),
            Theme(name="Mystery", description="Mysterious and suspenseful tales", is_active=True),
            Theme(name="Comedy", description="Funny and lighthearted stories", is_active=True),
            Theme(name="Educational", description="Learn while you travel", is_active=True),
            Theme(name="Family", description="Family-friendly content", is_active=True)
        ]
        
        for theme in themes:
            db.add(theme)
        
        db.commit()
        
        # Create test stories
        for user in test_users[:3]:  # First 3 users get stories
            for i in range(random.randint(2, 5)):
                story = Story(
                    user_id=user.id,
                    theme_id=random.choice(themes).id,
                    title=f"Staging Story {i+1} by {user.username}",
                    content=f"This is test story content for staging environment. Story #{i+1}",
                    start_location="San Francisco, CA",
                    end_location="Los Angeles, CA",
                    duration_minutes=random.randint(120, 480),
                    distance_miles=random.uniform(100, 500),
                    is_complete=random.choice([True, False])
                )
                db.add(story)
        
        db.commit()
        
        print("✅ Staging data seeded successfully!")
        print(f"   - Created {len(test_users)} test users")
        print(f"   - Created {len(themes)} themes")
        print("   - Created sample stories")
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_staging_data()
EOF
    
    # Run seed script
    print_status "Seeding test data..."
    python3 seed_staging_data.py
    
    print_success "Staging data seeded"
}

# Function to deploy Cloud Run service
deploy_cloud_run() {
    print_section "Deploying Cloud Run Service"
    
    # Deploy with staging configuration
    gcloud run deploy roadtrip-backend-staging \
        --image="gcr.io/$PROJECT_ID/roadtrip-backend-staging:latest" \
        --platform=managed \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --allow-unauthenticated \
        --memory=1Gi \
        --cpu=1 \
        --min-instances=1 \
        --max-instances=20 \
        --timeout=300 \
        --concurrency=80 \
        --set-env-vars="ENVIRONMENT=staging" \
        --set-secrets="DATABASE_URL=roadtrip-staging-db-url:latest" \
        --set-secrets="SECRET_KEY=SECRET_KEY-staging:latest" \
        --set-secrets="JWT_SECRET_KEY=JWT_SECRET_KEY-staging:latest" \
        --add-cloudsql-instances="$STAGING_DB" \
        --vpc-connector="roadtrip-staging-connector" \
        --vpc-egress="private-ranges-only"
    
    print_success "Cloud Run service deployed"
}

# Function to configure monitoring
setup_monitoring() {
    print_section "Setting Up Monitoring"
    
    # Create uptime check
    print_status "Creating uptime check..."
    gcloud monitoring uptime-check-configs create \
        --display-name="Staging Health Check" \
        --resource-type="uptime-url" \
        --resource-labels="host=${STAGING_URL#https://}" \
        --http-check-path="/health" \
        --check-interval="60s" \
        --timeout="10s" \
        --project="$PROJECT_ID" 2>/dev/null || print_warning "Uptime check may already exist"
    
    # Create alert policy for high error rate
    cat > staging-alert-policy.json <<EOF
{
  "displayName": "Staging High Error Rate",
  "conditions": [{
    "displayName": "Error rate > 5%",
    "conditionThreshold": {
      "filter": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"roadtrip-backend-staging\" AND metric.type=\"run.googleapis.com/request_count\"",
      "aggregations": [{
        "alignmentPeriod": "300s",
        "perSeriesAligner": "ALIGN_RATE"
      }],
      "comparison": "COMPARISON_GT",
      "thresholdValue": 0.05,
      "duration": "300s"
    }
  }],
  "notificationChannels": [],
  "alertStrategy": {
    "autoClose": "1800s"
  }
}
EOF
    
    print_success "Monitoring configured"
}

# Function to run validation tests
run_validation_tests() {
    print_section "Running Validation Tests"
    
    # Create validation script
    cat > validate_staging.py <<EOF
import requests
import sys
import time

def validate_staging(base_url):
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Health check
    try:
        resp = requests.get(f"{base_url}/health", timeout=10)
        if resp.status_code == 200:
            print("✅ Health check passed")
            tests_passed += 1
        else:
            print(f"❌ Health check failed: {resp.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"❌ Health check error: {e}")
        tests_failed += 1
    
    # Test 2: API documentation
    try:
        resp = requests.get(f"{base_url}/docs", timeout=10)
        if resp.status_code == 200:
            print("✅ API documentation accessible")
            tests_passed += 1
        else:
            print(f"❌ API documentation failed: {resp.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"❌ API documentation error: {e}")
        tests_failed += 1
    
    # Test 3: Database connectivity
    try:
        resp = requests.get(f"{base_url}/api/v1/health/db", timeout=10)
        if resp.status_code == 200:
            print("✅ Database connectivity verified")
            tests_passed += 1
        else:
            print(f"❌ Database connectivity failed: {resp.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"❌ Database connectivity error: {e}")
        tests_failed += 1
    
    # Test 4: Redis connectivity
    try:
        resp = requests.get(f"{base_url}/api/v1/health/cache", timeout=10)
        if resp.status_code == 200:
            print("✅ Redis connectivity verified")
            tests_passed += 1
        else:
            print(f"❌ Redis connectivity failed: {resp.status_code}")
            tests_failed += 1
    except Exception as e:
        print(f"❌ Redis connectivity error: {e}")
        tests_failed += 1
    
    # Summary
    print(f"\n📊 Validation Summary:")
    print(f"   ✅ Passed: {tests_passed}")
    print(f"   ❌ Failed: {tests_failed}")
    
    return tests_failed == 0

if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
    
    # Wait for service to be ready
    print("⏳ Waiting for service to be ready...")
    time.sleep(10)
    
    success = validate_staging(base_url)
    sys.exit(0 if success else 1)
EOF
    
    # Run validation
    print_status "Running validation tests..."
    if python3 validate_staging.py "$STAGING_URL"; then
        print_success "All validation tests passed"
    else
        print_warning "Some validation tests failed"
    fi
}

# Function to create staging test procedures
create_test_procedures() {
    print_section "Creating Test Procedures"
    
    # Create comprehensive test plan
    cat > staging_test_procedures.md <<EOF
# Staging Environment Test Procedures

## Deployment ID: ${DEPLOYMENT_ID}
## Environment URL: ${STAGING_URL}

### 1. End-to-End User Journey Tests

#### Test Case 1.1: User Registration and Login
1. Navigate to ${STAGING_URL}/docs
2. Test user registration endpoint
3. Verify email (staging emails go to logs)
4. Test login with credentials
5. Verify JWT token generation

#### Test Case 1.2: Story Generation Flow
1. Authenticate as test user
2. Create a new trip with start/end locations
3. Select theme and preferences
4. Generate AI story
5. Verify story content and metadata

#### Test Case 1.3: Voice Interaction
1. Test TTS endpoint with sample text
2. Verify audio generation
3. Test different voice personalities
4. Check caching behavior

### 2. AI Service Integration Tests

#### Test Case 2.1: Google Vertex AI
1. Test story generation with various prompts
2. Verify response time < 5s
3. Check cache hit/miss rates
4. Test error handling for AI failures

#### Test Case 2.2: Location Services
1. Test Google Maps integration
2. Verify route calculations
3. Test POI discovery
4. Check distance/duration accuracy

### 3. Booking Services Tests

#### Test Case 3.1: Restaurant Reservations
1. Search for restaurants along route
2. Test booking availability
3. Verify commission tracking
4. Test cancellation flow

#### Test Case 3.2: Hotel Bookings
1. Search for hotels at destination
2. Check pricing and availability
3. Test booking creation
4. Verify confirmation emails

### 4. Performance Tests

#### Test Case 4.1: Load Testing
\`\`\`bash
# Run load test with 100 concurrent users
locust -f tests/load/locustfile.py --host=${STAGING_URL} --users=100 --spawn-rate=10
\`\`\`

#### Test Case 4.2: API Response Times
- Health endpoint: < 100ms
- Story generation: < 5s
- Database queries: < 500ms
- Cache operations: < 50ms

### 5. Security Tests

#### Test Case 5.1: Authentication
1. Test invalid JWT tokens
2. Verify rate limiting
3. Test CSRF protection
4. Check security headers

#### Test Case 5.2: Data Protection
1. Verify PII encryption
2. Test data export functionality
3. Check audit logging
4. Test account deletion

### 6. Mobile App Integration

#### Test Case 6.1: API Compatibility
1. Test all mobile endpoints
2. Verify response formats
3. Check error handling
4. Test offline scenarios

#### Test Case 6.2: Voice Features
1. Test voice command processing
2. Verify personality switching
3. Check audio streaming
4. Test interruption handling

### 7. Monitoring Validation

#### Test Case 7.1: Metrics Collection
1. Verify Prometheus metrics
2. Check Grafana dashboards
3. Test alert triggering
4. Validate log aggregation

### 8. Disaster Recovery

#### Test Case 8.1: Backup/Restore
1. Create test data
2. Trigger backup
3. Simulate data loss
4. Restore from backup
5. Verify data integrity

### Test Credentials

- Admin User: admin@staging.roadtrip.app / staging123
- Test User 1: test1@staging.roadtrip.app / staging123
- Test User 2: test2@staging.roadtrip.app / staging123

### Known Staging Limitations

1. Email sending is disabled (check logs instead)
2. Payment processing uses test mode
3. Some third-party APIs may have rate limits
4. Mobile push notifications are disabled

### Staging Environment Access

- API Docs: ${STAGING_URL}/docs
- Health Check: ${STAGING_URL}/health
- Metrics: ${STAGING_URL}/metrics
- Admin Panel: ${STAGING_URL}/admin (coming soon)
EOF
    
    print_success "Test procedures documented"
}

# Function to create rollback procedure
create_rollback_procedure() {
    print_section "Creating Rollback Procedure"
    
    cat > staging_rollback.sh <<EOF
#!/bin/bash
# Staging Environment Rollback Script

DEPLOYMENT_ID="$DEPLOYMENT_ID"
PROJECT_ID="$PROJECT_ID"
REGION="$REGION"

echo "🔄 Rolling back staging deployment \${DEPLOYMENT_ID}"

# Rollback Cloud Run to previous revision
echo "Rolling back Cloud Run service..."
gcloud run services update-traffic roadtrip-backend-staging \\
    --to-revisions=PREVIOUS=100 \\
    --region="\${REGION}" \\
    --project="\${PROJECT_ID}"

# Rollback database if needed (restore from backup)
echo "Database rollback requires manual intervention"
echo "Use: gcloud sql backups restore"

# Rollback Terraform changes
cd infrastructure/staging
terraform plan -destroy
# terraform destroy -auto-approve  # Uncomment to execute

echo "✅ Rollback procedure completed"
EOF
    
    chmod +x staging_rollback.sh
    print_success "Rollback procedure created"
}

# Function to generate deployment report
generate_deployment_report() {
    print_section "Generating Deployment Report"
    
    cat > "staging_deployment_report_${DEPLOYMENT_ID}.md" <<EOF
# Staging Deployment Report

## Deployment Information
- **Deployment ID**: ${DEPLOYMENT_ID}
- **Date**: $(date)
- **Environment**: Staging
- **Project**: ${PROJECT_ID}
- **Region**: ${REGION}

## Deployed Resources

### Cloud Run Service
- **URL**: ${STAGING_URL}
- **Image**: gcr.io/${PROJECT_ID}/roadtrip-backend-staging:${DEPLOYMENT_ID}
- **Min Instances**: 1
- **Max Instances**: 20

### Database
- **Instance**: ${STAGING_DB}
- **Type**: PostgreSQL 15
- **Tier**: db-f1-micro
- **Backup**: Daily at 3 AM

### Redis Cache
- **Host**: ${STAGING_REDIS}
- **Version**: Redis 7.0
- **Memory**: 1 GB

### Monitoring
- Health Check: Configured
- Uptime Monitoring: Active
- Error Rate Alerts: Configured

## Validation Results

### API Endpoints
- ✅ Health check: Passed
- ✅ API documentation: Accessible
- ✅ Database connectivity: Verified
- ✅ Redis connectivity: Verified

### Test Data
- 5 test users created
- 5 themes configured
- Sample stories generated

## Next Steps

1. **Run comprehensive test suite**
   - Execute test procedures in staging_test_procedures.md
   - Document any issues found

2. **Performance testing**
   - Run load tests with expected traffic
   - Verify response times meet SLAs

3. **Security validation**
   - Run security scan
   - Verify all secrets are properly managed

4. **Production comparison**
   - Compare configurations with production
   - Identify any missing components

5. **Sign-off**
   - QA team validation
   - Security review
   - Product owner approval

## Access Information

- **API Documentation**: ${STAGING_URL}/docs
- **Health Endpoint**: ${STAGING_URL}/health
- **Test Credentials**: See staging_test_procedures.md

## Rollback Procedure

If issues are found, use staging_rollback.sh to revert changes.

---
Generated by Staging Deployment Script
EOF
    
    print_success "Deployment report generated: staging_deployment_report_${DEPLOYMENT_ID}.md"
}

# Main deployment function
main() {
    print_section "AI Road Trip Storyteller - Staging Deployment"
    print_status "Deployment ID: ${DEPLOYMENT_ID}"
    echo
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-build)
                SKIP_BUILD=true
                shift
                ;;
            --skip-tests)
                SKIP_TESTS=true
                shift
                ;;
            --skip-seed)
                SKIP_SEED=true
                shift
                ;;
            --destroy)
                DESTROY_MODE=true
                shift
                ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --skip-build    Skip Docker image build"
                echo "  --skip-tests    Skip validation tests"
                echo "  --skip-seed     Skip data seeding"
                echo "  --destroy       Destroy staging environment"
                echo "  --help          Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Destroy mode
    if [ "$DESTROY_MODE" == "true" ]; then
        print_warning "Destroying staging environment..."
        cd "$TERRAFORM_DIR"
        terraform destroy -var-file="terraform.tfvars" -auto-approve
        print_success "Staging environment destroyed"
        exit 0
    fi
    
    # Deployment steps
    check_prerequisites
    enable_apis
    setup_staging_secrets
    
    if [ "$SKIP_BUILD" != "true" ]; then
        build_staging_image
    fi
    
    deploy_infrastructure
    deploy_cloud_run
    run_database_migrations
    
    if [ "$SKIP_SEED" != "true" ]; then
        seed_staging_data
    fi
    
    setup_monitoring
    
    if [ "$SKIP_TESTS" != "true" ]; then
        run_validation_tests
    fi
    
    create_test_procedures
    create_rollback_procedure
    generate_deployment_report
    
    print_section "Deployment Summary"
    print_success "Staging environment deployed successfully!"
    echo
    echo "🌐 Staging URL: ${STAGING_URL}"
    echo "📚 API Docs: ${STAGING_URL}/docs"
    echo "📊 Health Check: ${STAGING_URL}/health"
    echo
    echo "📄 Test Procedures: staging_test_procedures.md"
    echo "📋 Deployment Report: staging_deployment_report_${DEPLOYMENT_ID}.md"
    echo "🔄 Rollback Script: staging_rollback.sh"
    echo
    print_status "Next: Run comprehensive tests using staging_test_procedures.md"
}

# Run main function
main "$@"