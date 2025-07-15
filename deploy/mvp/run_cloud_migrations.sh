#!/bin/bash
# Run database migrations on Cloud SQL
# This uses Cloud SQL Proxy for secure connection

set -e

# Configuration
PROJECT_ID="roadtrip-mvp-prod"
REGION="us-central1"
SQL_INSTANCE="roadtrip-mvp-db"
DATABASE="roadtrip"

echo "🗄️  Running Database Migrations on Cloud SQL"
echo "==========================================="
echo ""

# Check for cloud_sql_proxy
if ! command -v cloud_sql_proxy &> /dev/null; then
    echo "Installing Cloud SQL Proxy..."
    curl -o cloud_sql_proxy https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64
    chmod +x cloud_sql_proxy
    PROXY_CMD="./cloud_sql_proxy"
else
    PROXY_CMD="cloud_sql_proxy"
fi

# Start Cloud SQL Proxy in background
echo "Starting Cloud SQL Proxy..."
$PROXY_CMD -instances="${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"=tcp:5432 &
PROXY_PID=$!

# Wait for proxy to start
sleep 3

# Set database URL for local connection through proxy
export DATABASE_URL="postgresql://postgres:roadtrip_mvp_2024@localhost:5432/${DATABASE}"

# Run migrations
echo ""
echo "Running Alembic migrations..."
cd ../..  # Go to project root
alembic upgrade head

echo ""
echo "✅ Migrations completed successfully!"

# Stop proxy
kill $PROXY_PID

echo ""
echo "Cloud SQL Proxy stopped."