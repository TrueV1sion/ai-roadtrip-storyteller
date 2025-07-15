#!/bin/bash
# Setup Cloud SQL PostgreSQL Instance for Production
# Must have gcloud CLI configured first

set -e

PROJECT_ID="roadtrip-460720"
REGION="us-central1"
INSTANCE_NAME="roadtrip-db"
DB_NAME="roadtrip"
DB_USER="roadtrip"

echo "=========================================="
echo "CLOUD SQL SETUP FOR PRODUCTION"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "=========================================="

# Generate secure database password
DB_PASSWORD=$(openssl rand -base64 32)
echo "Generated secure database password"

# Step 1: Create Cloud SQL instance
echo -e "\n1. Creating Cloud SQL PostgreSQL instance..."
gcloud sql instances create $INSTANCE_NAME \
    --database-version=POSTGRES_15 \
    --tier=db-g1-small \
    --region=$REGION \
    --network=default \
    --no-assign-ip \
    --backup \
    --backup-start-time=03:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=05 \
    --maintenance-release-channel=production \
    --project=$PROJECT_ID

# Step 2: Create database
echo -e "\n2. Creating database..."
gcloud sql databases create $DB_NAME \
    --instance=$INSTANCE_NAME \
    --project=$PROJECT_ID

# Step 3: Create user
echo -e "\n3. Creating database user..."
gcloud sql users create $DB_USER \
    --instance=$INSTANCE_NAME \
    --password=$DB_PASSWORD \
    --project=$PROJECT_ID

# Step 4: Store password in Secret Manager
echo -e "\n4. Storing database password in Secret Manager..."
echo -n "$DB_PASSWORD" | gcloud secrets create db-password \
    --data-file=- \
    --replication-policy="automatic" \
    --project=$PROJECT_ID

# Step 5: Grant Cloud Run access to secret
echo -e "\n5. Granting Cloud Run access to secret..."
gcloud secrets add-iam-policy-binding db-password \
    --member="serviceAccount:roadtrip-460720-compute@developer.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT_ID

# Step 6: Create connection string secret
echo -e "\n6. Creating database connection string..."
CONNECTION_STRING="postgresql://$DB_USER:$DB_PASSWORD@/$DB_NAME?host=/cloudsql/$PROJECT_ID:$REGION:$INSTANCE_NAME"
echo -n "$CONNECTION_STRING" | gcloud secrets create db-connection-string \
    --data-file=- \
    --replication-policy="automatic" \
    --project=$PROJECT_ID

# Step 7: Output connection info
echo -e "\n=========================================="
echo "CLOUD SQL SETUP COMPLETE!"
echo "=========================================="
echo "Instance: $INSTANCE_NAME"
echo "Database: $DB_NAME"
echo "User: $DB_USER"
echo "Connection Name: $PROJECT_ID:$REGION:$INSTANCE_NAME"
echo ""
echo "Password stored in Secret Manager as: db-password"
echo "Connection string stored as: db-connection-string"
echo ""
echo "To connect from Cloud Run, use:"
echo "  - Unix socket: /cloudsql/$PROJECT_ID:$REGION:$INSTANCE_NAME"
echo "  - Or retrieve connection string from Secret Manager"
echo ""
echo "Next steps:"
echo "1. Run database migrations:"
echo "   cloud_sql_proxy -instances=$PROJECT_ID:$REGION:$INSTANCE_NAME=tcp:5432"
echo "   DATABASE_URL=\"postgresql://$DB_USER:***@localhost:5432/$DB_NAME\" alembic upgrade head"
echo "=========================================="