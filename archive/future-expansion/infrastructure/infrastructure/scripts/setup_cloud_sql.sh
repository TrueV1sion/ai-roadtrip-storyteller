#!/bin/bash
#
# Cloud SQL Setup Script
# Sets up PostgreSQL instance for AI Road Trip Storyteller
#

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
INSTANCE_NAME="${DB_INSTANCE_NAME:-roadtrip-prod-db}"
DB_VERSION="POSTGRES_15"
TIER="${DB_TIER:-db-n1-standard-4}"
DISK_SIZE="${DB_DISK_SIZE:-100}"
DISK_TYPE="${DB_DISK_TYPE:-PD_SSD}"
DATABASE_NAME="${DB_NAME:-roadtrip}"
DB_USER="${DB_USER:-roadtrip_app}"
NETWORK_NAME="${VPC_NAME:-ai-roadtrip-storyteller-production-vpc}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 Setting up Cloud SQL for Production${NC}"
echo "=========================================="

# Validate inputs
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Error: GCP_PROJECT_ID environment variable not set${NC}"
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

# Create Cloud SQL instance
echo -e "\n${YELLOW}Creating Cloud SQL instance...${NC}"
gcloud sql instances create $INSTANCE_NAME \
    --database-version=$DB_VERSION \
    --tier=$TIER \
    --region=$REGION \
    --network=projects/$PROJECT_ID/global/networks/$NETWORK_NAME \
    --no-assign-ip \
    --disk-size=$DISK_SIZE \
    --disk-type=$DISK_TYPE \
    --backup \
    --backup-start-time=03:00 \
    --retained-backups-count=30 \
    --transaction-log-retention-days=7 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=3 \
    --maintenance-window-duration=4 \
    --high-availability \
    --insights-config-query-insights-enabled \
    --insights-config-query-string-length=1024 \
    --insights-config-record-application-tags \
    --labels=environment=production,app=ai-roadtrip-storyteller

# Wait for instance to be ready
echo -e "\n${YELLOW}Waiting for instance to be ready...${NC}"
gcloud sql operations wait --project=$PROJECT_ID \
    $(gcloud sql operations list --instance=$INSTANCE_NAME --project=$PROJECT_ID --filter="status!=DONE" --format="value(name)" | head -n1)

# Create database
echo -e "\n${YELLOW}Creating database...${NC}"
gcloud sql databases create $DATABASE_NAME \
    --instance=$INSTANCE_NAME

# Generate secure password
DB_PASSWORD=$(openssl rand -base64 32)

# Create user
echo -e "\n${YELLOW}Creating database user...${NC}"
gcloud sql users create $DB_USER \
    --instance=$INSTANCE_NAME \
    --password=$DB_PASSWORD

# Store password in Secret Manager
echo -e "\n${YELLOW}Storing password in Secret Manager...${NC}"
echo -n "$DB_PASSWORD" | gcloud secrets create db-password \
    --data-file=- \
    --replication-policy="automatic" \
    --labels=environment=production,app=ai-roadtrip-storyteller \
    || echo "Secret already exists, updating..."

echo -n "$DB_PASSWORD" | gcloud secrets versions add db-password --data-file=-

# Create application-specific database objects
echo -e "\n${YELLOW}Setting up database schema...${NC}"

# Get connection info
CONNECTION_NAME=$(gcloud sql instances describe $INSTANCE_NAME --format="value(connectionName)")
PRIVATE_IP=$(gcloud sql instances describe $INSTANCE_NAME --format="value(ipAddresses[0].ipAddress)")

# Create schema setup script
cat > /tmp/schema_setup.sql <<EOF
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create performance indexes (to be run after initial migration)
-- CREATE INDEX CONCURRENTLY idx_stories_user_created ON stories(user_id, created_at DESC);
-- CREATE INDEX CONCURRENTLY idx_bookings_user_status ON bookings(user_id, status);
-- CREATE INDEX CONCURRENTLY idx_sessions_user_active ON sessions(user_id) WHERE is_active = true;

-- Create read-only user for analytics
CREATE USER roadtrip_readonly WITH PASSWORD '$(openssl rand -base64 32)';
GRANT CONNECT ON DATABASE $DATABASE_NAME TO roadtrip_readonly;
GRANT USAGE ON SCHEMA public TO roadtrip_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO roadtrip_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO roadtrip_readonly;

-- Performance settings
ALTER DATABASE $DATABASE_NAME SET shared_preload_libraries = 'pg_stat_statements';
ALTER DATABASE $DATABASE_NAME SET pg_stat_statements.track = 'all';
ALTER DATABASE $DATABASE_NAME SET log_min_duration_statement = 1000; -- Log slow queries > 1s
ALTER DATABASE $DATABASE_NAME SET log_connections = on;
ALTER DATABASE $DATABASE_NAME SET log_disconnections = on;
ALTER DATABASE $DATABASE_NAME SET log_lock_waits = on;
ALTER DATABASE $DATABASE_NAME SET log_temp_files = 0;
EOF

# Apply schema setup (requires Cloud SQL Proxy for this part)
echo -e "\n${YELLOW}Note: Database schema will be set up during first application deployment${NC}"

# Output connection information
echo -e "\n${GREEN}✅ Cloud SQL setup complete!${NC}"
echo -e "\n${YELLOW}Connection Information:${NC}"
echo "Instance Name: $INSTANCE_NAME"
echo "Connection Name: $CONNECTION_NAME"
echo "Private IP: $PRIVATE_IP"
echo "Database: $DATABASE_NAME"
echo "User: $DB_USER"
echo "Password: Stored in Secret Manager as 'db-password'"
echo ""
echo -e "${YELLOW}Connection String for Application:${NC}"
echo "postgresql://$DB_USER:<password>@$PRIVATE_IP:5432/$DATABASE_NAME"
echo ""
echo -e "${YELLOW}To connect using Cloud SQL Proxy:${NC}"
echo "cloud_sql_proxy -instances=$CONNECTION_NAME=tcp:5432"
echo ""
echo -e "${YELLOW}Important: Save this information securely!${NC}"

# Create backup script
cat > backup_cloud_sql.sh <<'EOF'
#!/bin/bash
# Cloud SQL Backup Script
INSTANCE_NAME="roadtrip-prod-db"
BACKUP_ID="manual-backup-$(date +%Y%m%d-%H%M%S)"

echo "Creating backup: $BACKUP_ID"
gcloud sql backups create \
    --instance=$INSTANCE_NAME \
    --description="Manual backup - $(date)" \
    --backup-id=$BACKUP_ID

echo "Backup created successfully"
gcloud sql backups list --instance=$INSTANCE_NAME --limit=5
EOF

chmod +x backup_cloud_sql.sh
echo -e "\n${GREEN}Backup script created: backup_cloud_sql.sh${NC}"