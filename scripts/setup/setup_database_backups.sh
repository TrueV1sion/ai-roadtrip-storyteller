#!/bin/bash
# Setup script for automated database backups

set -e

echo "=== AI Road Trip Storyteller - Database Backup Setup ==="
echo

# Check if running on Google Cloud
if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud CLI not found. Please install Google Cloud SDK first."
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
if [ -z "$PROJECT_ID" ]; then
    echo "Error: No Google Cloud project configured."
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "Using Google Cloud Project: $PROJECT_ID"
echo

# Function to check if a service is enabled
check_service() {
    local service=$1
    if gcloud services list --enabled --filter="name:$service" --format="value(name)" | grep -q "$service"; then
        echo "✓ $service is enabled"
        return 0
    else
        echo "✗ $service is not enabled"
        return 1
    fi
}

# Function to create bucket if it doesn't exist
create_bucket_if_needed() {
    local bucket=$1
    if gsutil ls -b gs://$bucket &> /dev/null; then
        echo "✓ Bucket gs://$bucket already exists"
    else
        echo "Creating bucket gs://$bucket..."
        gsutil mb -p $PROJECT_ID -c STANDARD -l us-central1 gs://$bucket/
        echo "✓ Bucket created"
    fi
}

# Function to create service account if it doesn't exist
create_service_account_if_needed() {
    local sa_name=$1
    local sa_email="${sa_name}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    if gcloud iam service-accounts describe $sa_email &> /dev/null; then
        echo "✓ Service account $sa_name already exists"
    else
        echo "Creating service account $sa_name..."
        gcloud iam service-accounts create $sa_name \
            --display-name="Database Backup Service Account" \
            --description="Service account for automated database backups"
        echo "✓ Service account created"
    fi
}

# 1. Enable required APIs
echo "1. Checking required APIs..."
REQUIRED_APIS=(
    "storage-component.googleapis.com"
    "cloudscheduler.googleapis.com"
    "run.googleapis.com"
    "secretmanager.googleapis.com"
)

for api in "${REQUIRED_APIS[@]}"; do
    if ! check_service $api; then
        echo "   Enabling $api..."
        gcloud services enable $api
        echo "   ✓ Enabled"
    fi
done
echo

# 2. Create backup bucket
echo "2. Setting up backup storage..."
BACKUP_BUCKET="roadtrip-db-backups-${PROJECT_ID}"
create_bucket_if_needed $BACKUP_BUCKET

# Set lifecycle policy
echo "   Setting lifecycle policy (90-day retention)..."
cat > /tmp/lifecycle.json << EOF
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 90,
          "matchesPrefix": ["postgres/"]
        }
      }
    ]
  }
}
EOF

gsutil lifecycle set /tmp/lifecycle.json gs://$BACKUP_BUCKET/
rm /tmp/lifecycle.json
echo "   ✓ Lifecycle policy set"
echo

# 3. Create service account
echo "3. Setting up service account..."
SA_NAME="roadtrip-backup"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
create_service_account_if_needed $SA_NAME

# Grant permissions
echo "   Granting permissions..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/storage.objectAdmin" \
    --condition="expression=resource.name.startsWith('projects/_/buckets/${BACKUP_BUCKET}'),title=BackupBucketOnly"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="roles/cloudscheduler.jobRunner"

echo "   ✓ Permissions granted"
echo

# 4. Build and push backup container
echo "4. Building backup container..."
echo "   This step requires Docker. Building container..."

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "   ⚠️  Docker not found. Please build and push the container manually:"
    echo "      cd infrastructure/backup"
    echo "      docker build -f Dockerfile.backup -t gcr.io/$PROJECT_ID/roadtrip-backup:latest ../.."
    echo "      docker push gcr.io/$PROJECT_ID/roadtrip-backup:latest"
else
    cd infrastructure/backup
    docker build -f Dockerfile.backup -t gcr.io/$PROJECT_ID/roadtrip-backup:latest ../..
    docker push gcr.io/$PROJECT_ID/roadtrip-backup:latest
    cd ../..
    echo "   ✓ Container built and pushed"
fi
echo

# 5. Update configuration files
echo "5. Updating configuration files..."
# Update Kubernetes CronJob
sed -i "s/YOUR_PROJECT_ID/$PROJECT_ID/g" infrastructure/backup/backup-cronjob.yaml
# Update Cloud Run Job
sed -i "s/YOUR_PROJECT_ID/$PROJECT_ID/g" infrastructure/backup/cloud-run-backup-job.yaml
echo "   ✓ Configuration files updated"
echo

# 6. Deploy backup job
echo "6. Deploying backup job..."
echo "   Choose deployment method:"
echo "   1) Cloud Run + Cloud Scheduler (Recommended for serverless)"
echo "   2) Kubernetes CronJob (If using GKE)"
echo "   3) Skip deployment (Manual setup)"
read -p "   Select option (1-3): " deployment_choice

case $deployment_choice in
    1)
        echo "   Deploying to Cloud Run..."
        # Create Cloud Run job
        gcloud run jobs replace infrastructure/backup/cloud-run-backup-job.yaml \
            --region=us-central1
        
        # Create Cloud Scheduler job
        gcloud scheduler jobs create http roadtrip-db-backup \
            --location=us-central1 \
            --schedule="0 2 * * *" \
            --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/roadtrip-db-backup:run" \
            --http-method=POST \
            --oidc-service-account-email=$SA_EMAIL \
            --time-zone="UTC" \
            --description="Daily database backup at 2 AM UTC"
        
        echo "   ✓ Cloud Run job deployed"
        ;;
    2)
        echo "   Deploying to Kubernetes..."
        kubectl apply -f infrastructure/backup/backup-cronjob.yaml
        echo "   ✓ Kubernetes CronJob deployed"
        ;;
    3)
        echo "   Skipping deployment. Manual setup required."
        ;;
    *)
        echo "   Invalid option. Skipping deployment."
        ;;
esac
echo

# 7. Test backup
echo "7. Testing backup setup..."
read -p "   Would you like to run a test backup now? (y/N): " test_backup

if [[ $test_backup =~ ^[Yy]$ ]]; then
    echo "   Running test backup..."
    if [ "$deployment_choice" == "1" ]; then
        # Trigger Cloud Run job
        gcloud scheduler jobs run roadtrip-db-backup --location=us-central1
        echo "   ✓ Backup job triggered. Check logs with:"
        echo "     gcloud run jobs executions list --job=roadtrip-db-backup --region=us-central1"
    else
        echo "   Running local test..."
        python scripts/database_backup.py backup --no-upload
        echo "   ✓ Local backup test completed"
    fi
fi
echo

# 8. Summary
echo "=== Setup Complete ==="
echo
echo "Backup Configuration:"
echo "  - Bucket: gs://$BACKUP_BUCKET"
echo "  - Service Account: $SA_EMAIL"
echo "  - Schedule: Daily at 2 AM UTC"
echo "  - Retention: 90 days"
echo
echo "Next Steps:"
echo "  1. Verify DATABASE_URL is set in Secret Manager"
echo "  2. Monitor first automated backup (tomorrow 2 AM UTC)"
echo "  3. Set up alerts for backup failures"
echo "  4. Test restore procedure monthly"
echo
echo "Useful Commands:"
echo "  - Manual backup: python scripts/database_backup.py backup"
echo "  - List backups: python scripts/database_backup.py list"
echo "  - Restore: python scripts/database_backup.py restore --backup-name <name>"
echo
echo "Documentation: docs/database_backup_guide.md"