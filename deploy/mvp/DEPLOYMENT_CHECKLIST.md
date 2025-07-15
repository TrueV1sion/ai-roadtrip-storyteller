# MVP Cloud Deployment Checklist

## Pre-Deployment Requirements

### Local Environment
- [ ] Google Cloud SDK installed (`gcloud --version`)
- [ ] Authenticated to GCP (`gcloud auth login`)
- [ ] Docker installed (for local testing)
- [ ] Python 3.9+ with virtual environment
- [ ] All tests passing (`./run_mvp_tests.sh`)

### API Keys Required
- [ ] Google Maps API Key (for navigation)
- [ ] Google Cloud Project with billing enabled
- [ ] OpenWeatherMap API Key (for weather stories)
- [ ] Ticketmaster API Key (optional for Phase 2)
- [ ] Recreation.gov API Key (optional for Phase 2)

## Deployment Steps

### 1. Infrastructure Setup (30-45 minutes)
```bash
cd deploy/mvp
./setup_gcp_infrastructure.sh
```

This creates:
- [ ] GCP Project configured
- [ ] All required APIs enabled
- [ ] Service account with proper permissions
- [ ] Cloud Storage buckets (audio + assets)
- [ ] Cloud SQL PostgreSQL instance
- [ ] Memorystore Redis instance
- [ ] Secret Manager secrets (with placeholders)

### 2. Update Secrets (5 minutes)
Update these secrets in Secret Manager:
- [ ] `google-maps-api-key` - Your actual API key
- [ ] `openweathermap-api-key` - Your actual API key
- [ ] `ticketmaster-api-key` - Your actual API key (or leave placeholder)
- [ ] `recreation-gov-api-key` - Your actual API key (or leave placeholder)

```bash
# Example:
echo -n "YOUR_ACTUAL_API_KEY" | gcloud secrets versions add google-maps-api-key --data-file=-
```

### 3. Database Setup (10 minutes)
```bash
# Option A: Using Cloud SQL Proxy
./run_cloud_migrations.sh

# Option B: Direct connection
gcloud sql connect roadtrip-mvp-db --user=postgres
# Password: roadtrip_mvp_2024
# Then run: CREATE DATABASE roadtrip;
```

### 4. Deploy Application (15-20 minutes)
```bash
./deploy_to_cloud_run.sh
```

This will:
- [ ] Build Docker image
- [ ] Push to Google Container Registry
- [ ] Deploy to Cloud Run
- [ ] Configure environment variables
- [ ] Set up secrets from Secret Manager
- [ ] Create health check endpoint

### 5. Verify Deployment (5 minutes)
```bash
# Run the generated test script
./test_mvp_deployment.sh
```

Check:
- [ ] Health endpoint returns 200
- [ ] Root endpoint shows MVP message
- [ ] Voice interaction endpoint accepts requests

### 6. Set Up Monitoring (10 minutes)
```bash
# Update email first
export ALERT_EMAIL="your-email@example.com"
./setup_monitoring.sh
```

Creates:
- [ ] Uptime check (every 5 minutes)
- [ ] Response time alerts (>3 seconds)
- [ ] Error rate alerts (>1%)
- [ ] Memory usage alerts (>80%)
- [ ] Monitoring dashboard

## Post-Deployment Verification

### Functional Tests
- [ ] Voice input: "Navigate to Golden Gate Bridge"
- [ ] Response time <3 seconds
- [ ] Audio URL generated (check logs)
- [ ] No 5xx errors in logs

### Performance Tests
```bash
# Simple load test
for i in {1..10}; do
  curl -X POST "${SERVICE_URL}/api/voice-assistant/interact" \
    -H "Content-Type: application/json" \
    -d '{"user_input": "Tell me about this area"}' &
done
wait
```

### Security Checks
- [ ] HTTPS enforced
- [ ] API keys not exposed in logs
- [ ] Database connection encrypted
- [ ] Service account has minimal permissions

## Monitoring Commands

### View Logs
```bash
# Stream logs
gcloud run logs read --service=roadtrip-mvp --tail=50 -f

# Check for errors
gcloud run logs read --service=roadtrip-mvp --filter="severity>=ERROR"
```

### View Metrics
```bash
# Get service details
gcloud run services describe roadtrip-mvp --region=us-central1

# View recent revisions
gcloud run revisions list --service=roadtrip-mvp --region=us-central1
```

## Rollback Procedure

If issues occur:
```bash
# List revisions
gcloud run revisions list --service=roadtrip-mvp --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic roadtrip-mvp \
  --to-revisions=roadtrip-mvp-00001-abc=100 \
  --region=us-central1
```

## Cost Optimization

### Current Setup (MVP)
- Cloud Run: ~$50-100/month (with traffic)
- Cloud SQL: ~$50/month (db-g1-small)
- Redis: ~$50/month (1GB)
- Storage: <$10/month
- **Total: ~$160-210/month**

### Cost Saving Options
1. Scale Cloud SQL to zero when not in use
2. Use Cloud Run min-instances=0
3. Delete old audio files regularly (lifecycle policy set)
4. Use free tier quotas where possible

## Troubleshooting

### Common Issues

1. **"Failed to start container"**
   - Check logs: `gcloud run logs read --service=roadtrip-mvp`
   - Verify secrets are set correctly
   - Check DATABASE_URL format

2. **"502 Bad Gateway"**
   - Service is still starting (wait 2-3 minutes)
   - Check Cloud SQL is running
   - Verify database migrations completed

3. **"Permission denied"**
   - Service account needs more permissions
   - Check Secret Manager access
   - Verify Cloud SQL client role

4. **Slow response times**
   - Cold start (first request takes longer)
   - Increase min-instances to 1
   - Check Redis connection

## Success Criteria

- [ ] Service URL accessible
- [ ] Health check passing
- [ ] <3 second response time (after warm-up)
- [ ] No errors in first 10 requests
- [ ] Monitoring dashboard shows healthy metrics

## Next Steps

Once deployed successfully:

1. **Share with Beta Testers**
   - Service URL: `https://roadtrip-mvp-xxx.run.app`
   - Basic API documentation
   - Feedback form

2. **Mobile App Configuration**
   - Update `EXPO_PUBLIC_API_URL` with service URL
   - Deploy to TestFlight/Play Store

3. **Enable Phase 2 Features** (after MVP validation)
   - Set `MVP_MODE=false`
   - Enable booking routes
   - Add game features
   - Integrate music services

## Support

- **Logs**: Cloud Console → Cloud Run → Logs
- **Metrics**: Cloud Console → Monitoring → Dashboards
- **Errors**: Check Secret Manager and IAM permissions first
- **Performance**: Enable Cloud Trace for detailed analysis