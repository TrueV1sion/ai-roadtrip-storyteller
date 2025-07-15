# Proper Production Setup for Cloud Run

## What You Need

1. **Cloud SQL** (PostgreSQL) - For your database
2. **Memorystore** (Redis) - For caching
3. **VPC Connector** - To connect Cloud Run to these services

## Step 1: Create Cloud SQL Instance

```bash
# Create PostgreSQL instance
gcloud sql instances create roadtrip-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --network=default

# Set password for postgres user
gcloud sql users set-password postgres \
  --instance=roadtrip-db \
  --password=your-secure-password

# Create database
gcloud sql databases create roadtrip \
  --instance=roadtrip-db
```

## Step 2: Create Redis Instance (Memorystore)

```bash
# Create Redis instance
gcloud redis instances create roadtrip-cache \
  --size=1 \
  --region=us-central1 \
  --redis-version=redis_7_0
```

## Step 3: Create VPC Connector

```bash
# Enable VPC Access API
gcloud services enable vpcaccess.googleapis.com

# Create connector
gcloud compute networks vpc-access connectors create roadtrip-connector \
  --region=us-central1 \
  --range=10.8.0.0/28
```

## Step 4: Get Connection Details

```bash
# Get Cloud SQL connection name
gcloud sql instances describe roadtrip-db --format="value(connectionName)"
# Output: roadtrip-460720:us-central1:roadtrip-db

# Get Redis IP
gcloud redis instances describe roadtrip-cache --region=us-central1 --format="value(host)"
# Output: 10.x.x.x
```

## Step 5: Deploy with Proper Configuration

```bash
gcloud run deploy roadtrip-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --add-cloudsql-instances=roadtrip-460720:us-central1:roadtrip-db \
  --vpc-connector=roadtrip-connector \
  --set-env-vars="DATABASE_URL=postgresql://postgres:your-secure-password@/roadtrip?host=/cloudsql/roadtrip-460720:us-central1:roadtrip-db,REDIS_URL=redis://10.x.x.x:6379,ENVIRONMENT=production,GOOGLE_MAPS_API_KEY=AIzaSyAuduVqyKAf47TAZkCd9j4dnDd87oaLXYQ,TICKETMASTER_API_KEY=5X13jI3ZPzAdU3kp3trYFf4VWqSVySgo,OPENWEATHERMAP_API_KEY=d7aa0dc75ed0dae38f627ed48d3e3bf1"
```

## Alternative: Use Cloud Run with External Services

If you already have PostgreSQL and Redis running elsewhere (like on Compute Engine or external providers):

1. **Whitelist Cloud Run's IP** in your database
2. **Use public URLs** for connections
3. **Update environment variables** with external URLs

## Quick Start Options

### Option 1: Development Testing (Mock Mode)
Use mock mode just to verify Cloud Run deployment works:
```bash
gcloud run deploy roadtrip-api --source . --region us-central1 --allow-unauthenticated --set-env-vars="MOCK_REDIS=true,USE_MOCK_APIS=true,SKIP_DB_CHECK=true"
```

### Option 2: Use Cloud SQL Only (Skip Redis)
```bash
# Create minimal Cloud SQL
gcloud sql instances create roadtrip-db-mini --database-version=POSTGRES_15 --tier=db-f1-micro --region=us-central1

# Deploy with SQL only
gcloud run deploy roadtrip-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --add-cloudsql-instances=roadtrip-460720:us-central1:roadtrip-db-mini \
  --set-env-vars="DATABASE_URL=postgresql://postgres:password@/roadtrip?host=/cloudsql/roadtrip-460720:us-central1:roadtrip-db-mini,MOCK_REDIS=true"
```

### Option 3: Full Production (Recommended)
Follow steps 1-5 above for complete setup with Cloud SQL and Memorystore.

## Cost Estimates

- **Cloud SQL (db-f1-micro)**: ~$10/month
- **Memorystore (1GB)**: ~$35/month
- **VPC Connector**: ~$0.01/GB processed
- **Cloud Run**: Pay per request (usually <$10/month for moderate traffic)

**Total**: ~$50-60/month for a basic production setup

## Why Not Mock Mode in Production?

Mock mode means:
- ❌ No persistent data (lost on restart)
- ❌ No caching (slower performance)
- ❌ External APIs return fake data
- ❌ Not suitable for real users

It's only for testing that the code deploys correctly!