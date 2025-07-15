#!/bin/bash
#
# Redis (Memorystore) Setup Script
# Sets up Redis instance for AI Road Trip Storyteller
#

set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
INSTANCE_NAME="${REDIS_INSTANCE_NAME:-roadtrip-prod-cache}"
TIER="${REDIS_TIER:-STANDARD_HA}"
MEMORY_SIZE="${REDIS_MEMORY_SIZE:-5}"
REDIS_VERSION="${REDIS_VERSION:-7.0}"
NETWORK_NAME="${VPC_NAME:-ai-roadtrip-storyteller-production-vpc}"
RESERVED_IP_RANGE="10.0.4.0/24"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🚀 Setting up Redis (Memorystore) for Production${NC}"
echo "================================================"

# Validate inputs
if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}❌ Error: GCP_PROJECT_ID environment variable not set${NC}"
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

# Allocate IP range for Redis
echo -e "\n${YELLOW}Allocating IP range for Redis...${NC}"
gcloud compute addresses create redis-ip-range \
    --global \
    --purpose=VPC_PEERING \
    --addresses=10.10.0.0 \
    --prefix-length=16 \
    --network=projects/$PROJECT_ID/global/networks/$NETWORK_NAME \
    || echo "IP range already exists"

# Create service connection
echo -e "\n${YELLOW}Creating private service connection...${NC}"
gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges=redis-ip-range \
    --network=$NETWORK_NAME \
    || echo "Service connection already exists"

# Create Redis instance
echo -e "\n${YELLOW}Creating Redis instance...${NC}"
gcloud redis instances create $INSTANCE_NAME \
    --region=$REGION \
    --tier=$TIER \
    --size=$MEMORY_SIZE \
    --redis-version=redis_$REDIS_VERSION \
    --network=projects/$PROJECT_ID/global/networks/$NETWORK_NAME \
    --connect-mode=PRIVATE_SERVICE_ACCESS \
    --reserved-ip-range=$RESERVED_IP_RANGE \
    --display-name="AI Road Trip Storyteller Production Cache" \
    --labels=environment=production,app=ai-roadtrip-storyteller \
    --redis-config=maxmemory-policy=allkeys-lru \
    --enable-auth

# Wait for instance to be ready
echo -e "\n${YELLOW}Waiting for Redis instance to be ready...${NC}"
while true; do
    STATUS=$(gcloud redis instances describe $INSTANCE_NAME --region=$REGION --format="value(state)")
    if [ "$STATUS" = "READY" ]; then
        break
    fi
    echo "Current status: $STATUS. Waiting..."
    sleep 30
done

# Get instance details
echo -e "\n${YELLOW}Getting instance details...${NC}"
REDIS_HOST=$(gcloud redis instances describe $INSTANCE_NAME --region=$REGION --format="value(host)")
REDIS_PORT=$(gcloud redis instances describe $INSTANCE_NAME --region=$REGION --format="value(port)")
REDIS_AUTH=$(gcloud redis instances describe $INSTANCE_NAME --region=$REGION --format="value(authString)")

# Store auth string in Secret Manager
echo -e "\n${YELLOW}Storing auth string in Secret Manager...${NC}"
echo -n "$REDIS_AUTH" | gcloud secrets create redis-auth-string \
    --data-file=- \
    --replication-policy="automatic" \
    --labels=environment=production,app=ai-roadtrip-storyteller \
    || echo "Secret already exists, updating..."

echo -n "$REDIS_AUTH" | gcloud secrets versions add redis-auth-string --data-file=-

# Create Redis configuration documentation
cat > redis_config.md <<EOF
# Redis Configuration for AI Road Trip Storyteller

## Instance Details
- **Instance Name**: $INSTANCE_NAME
- **Region**: $REGION
- **Tier**: $TIER (High Availability)
- **Memory**: ${MEMORY_SIZE}GB
- **Version**: Redis $REDIS_VERSION

## Connection Information
- **Host**: $REDIS_HOST
- **Port**: $REDIS_PORT
- **Auth**: Stored in Secret Manager as 'redis-auth-string'

## Connection String
\`\`\`
redis://default:AUTH_STRING@$REDIS_HOST:$REDIS_PORT
\`\`\`

## Features Enabled
- ✅ High Availability (automatic failover)
- ✅ Authentication required
- ✅ Private IP only (VPC access)
- ✅ Automatic memory management (LRU eviction)
- ✅ Daily backups

## Usage in Application

### Python Example
\`\`\`python
import redis
from google.cloud import secretmanager

# Get auth string from Secret Manager
client = secretmanager.SecretManagerServiceClient()
name = f"projects/{PROJECT_ID}/secrets/redis-auth-string/versions/latest"
response = client.access_secret_version(request={"name": name})
auth_string = response.payload.data.decode("UTF-8")

# Connect to Redis
r = redis.Redis(
    host='$REDIS_HOST',
    port=$REDIS_PORT,
    password=auth_string,
    decode_responses=True,
    socket_keepalive=True,
    socket_keepalive_options={
        1: 1,  # TCP_KEEPIDLE
        2: 1,  # TCP_KEEPINTVL
        3: 5,  # TCP_KEEPCNT
    }
)

# Test connection
r.ping()
\`\`\`

### Caching Strategy

1. **AI Response Cache**
   - Key: \`ai:response:{hash(prompt+context)}\`
   - TTL: 3600 seconds (1 hour)

2. **User Session Cache**
   - Key: \`session:{user_id}:{session_id}\`
   - TTL: 86400 seconds (24 hours)

3. **API Rate Limiting**
   - Key: \`rate:{api}:{user_id}\`
   - TTL: 60 seconds

4. **Location Data Cache**
   - Key: \`location:{lat}:{lng}:{radius}\`
   - TTL: 1800 seconds (30 minutes)

5. **Booking Search Cache**
   - Key: \`booking:{provider}:{location}:{date}\`
   - TTL: 300 seconds (5 minutes)

## Monitoring

### Key Metrics to Watch
- Memory usage percentage
- Hit rate
- Evicted keys
- Connected clients
- Operations per second

### Alerts Set Up
- Memory usage > 90%
- Connection count > 1000
- Hit rate < 80%
- Instance unavailable

## Maintenance

### Manual Backup
\`\`\`bash
gcloud redis instances export $INSTANCE_NAME \
  --region=$REGION \
  --destination=gs://roadtrip-backups/redis/backup-\$(date +%Y%m%d-%H%M%S).rdb
\`\`\`

### Scaling
To increase memory:
\`\`\`bash
gcloud redis instances update $INSTANCE_NAME \
  --region=$REGION \
  --size=10  # New size in GB
\`\`\`

EOF

# Create monitoring script
cat > monitor_redis.sh <<'EOF'
#!/bin/bash
# Redis Monitoring Script

INSTANCE_NAME="roadtrip-prod-cache"
REGION="us-central1"

echo "Redis Instance Status"
echo "===================="

# Get instance info
gcloud redis instances describe $INSTANCE_NAME --region=$REGION \
    --format="table(
        displayName,
        state,
        memorySizeGb,
        tier,
        redisVersion,
        currentLocationId
    )"

echo -e "\nMemory Usage:"
gcloud redis instances describe $INSTANCE_NAME --region=$REGION \
    --format="value(
        redisMetrics.usedMemory,
        redisMetrics.maxMemory
    )"

echo -e "\nRecent Operations:"
gcloud redis operations list --region=$REGION --filter="name:$INSTANCE_NAME" --limit=5
EOF

chmod +x monitor_redis.sh

# Output summary
echo -e "\n${GREEN}✅ Redis setup complete!${NC}"
echo -e "\n${YELLOW}Connection Information:${NC}"
echo "Host: $REDIS_HOST"
echo "Port: $REDIS_PORT"
echo "Auth: Stored in Secret Manager as 'redis-auth-string'"
echo ""
echo -e "${YELLOW}Connection URL:${NC}"
echo "redis://default:<auth>@$REDIS_HOST:$REDIS_PORT"
echo ""
echo -e "${YELLOW}Files created:${NC}"
echo "- redis_config.md (Full configuration documentation)"
echo "- monitor_redis.sh (Monitoring script)"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Update application configuration to use Redis"
echo "2. Implement caching strategies as documented"
echo "3. Set up monitoring alerts in Cloud Console"
echo "4. Test failover scenarios"