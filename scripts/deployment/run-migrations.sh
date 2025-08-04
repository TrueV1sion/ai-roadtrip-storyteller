#!/bin/bash
# Run database migrations for new features
# This script handles both development and production migrations

set -euo pipefail

# Configuration
ENVIRONMENT="${ENVIRONMENT:-development}"
DATABASE_URL="${DATABASE_URL:-}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🗄️  Running Database Migrations${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"

# Function to run migrations
run_migrations() {
    local env=$1
    
    if [ "$env" == "production" ]; then
        echo -e "${YELLOW}⚠️  Running production migrations...${NC}"
        echo -e "${YELLOW}This will modify the production database!${NC}"
        read -p "Are you sure you want to continue? (yes/no): " confirm
        
        if [ "$confirm" != "yes" ]; then
            echo -e "${RED}❌ Migrations cancelled${NC}"
            exit 1
        fi
    fi
    
    # Check if alembic is available
    if ! command -v alembic &> /dev/null; then
        echo -e "${YELLOW}📦 Installing alembic...${NC}"
        pip install alembic
    fi
    
    # Run migrations
    echo -e "${YELLOW}🏃 Running migrations...${NC}"
    cd backend
    
    # Show current revision
    echo -e "${BLUE}Current revision:${NC}"
    alembic current
    
    # Show pending migrations
    echo -e "${BLUE}Pending migrations:${NC}"
    alembic history --verbose
    
    # Run the migrations
    alembic upgrade head
    
    # Show new revision
    echo -e "${GREEN}✅ New revision:${NC}"
    alembic current
}

# Main execution
case "$ENVIRONMENT" in
    development)
        echo -e "${GREEN}Running development migrations...${NC}"
        
        # Ensure database is running
        if ! docker ps | grep -q roadtrip-postgres; then
            echo -e "${YELLOW}Starting database container...${NC}"
            docker-compose -f infrastructure/docker/docker-compose.yml up -d postgres
            sleep 5
        fi
        
        run_migrations development
        ;;
        
    staging|production)
        echo -e "${YELLOW}Running ${ENVIRONMENT} migrations...${NC}"
        
        # Check for database URL
        if [ -z "$DATABASE_URL" ]; then
            echo -e "${RED}❌ DATABASE_URL not set for ${ENVIRONMENT}${NC}"
            echo "Please set DATABASE_URL environment variable"
            exit 1
        fi
        
        # Create backup first
        echo -e "${YELLOW}📦 Creating database backup...${NC}"
        BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"
        
        if [ "$ENVIRONMENT" == "production" ]; then
            # For production, use Cloud SQL export
            gcloud sql export sql roadtrip-postgres gs://roadtrip-backups/${BACKUP_FILE} \
                --database=roadtrip_production
            echo -e "${GREEN}✅ Backup saved to gs://roadtrip-backups/${BACKUP_FILE}${NC}"
        fi
        
        run_migrations $ENVIRONMENT
        ;;
        
    *)
        echo -e "${RED}❌ Unknown environment: $ENVIRONMENT${NC}"
        echo "Valid environments: development, staging, production"
        exit 1
        ;;
esac

echo -e "${GREEN}🎉 Migrations completed successfully!${NC}"

# Post-migration tasks
echo -e "${YELLOW}📋 Running post-migration tasks...${NC}"

# Verify new tables exist
echo -e "${BLUE}Verifying new tables...${NC}"
TABLES="journey_tracking trip_memories story_queue progress_tracking passenger_engagement"

for table in $TABLES; do
    if psql $DATABASE_URL -c "SELECT 1 FROM $table LIMIT 1;" &> /dev/null; then
        echo -e "${GREEN}✅ Table $table exists${NC}"
    else
        echo -e "${RED}❌ Table $table missing!${NC}"
        exit 1
    fi
done

echo -e "${GREEN}🚀 Database is ready for deployment!${NC}"