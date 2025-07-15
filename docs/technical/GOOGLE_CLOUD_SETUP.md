# Google Cloud Setup Guide

## Prerequisites

1. **Install Google Cloud SDK**
   - Windows: Download from https://cloud.google.com/sdk/docs/install
   - Mac: `brew install google-cloud-sdk`
   - Linux: `curl https://sdk.cloud.google.com | bash`

2. **Create Google Cloud Account**
   - Go to https://console.cloud.google.com
   - Create account if needed
   - Enable billing (required for APIs)

## Step 1: Create Service Account

### Option A: Using the Script (Recommended)
```bash
# After installing gcloud SDK
./setup_service_account.sh
```

### Option B: Manual Steps

1. **Go to Google Cloud Console**
   ```
   https://console.cloud.google.com/iam-admin/serviceaccounts?project=roadtrip-460720
   ```

2. **Create Service Account**
   - Click "CREATE SERVICE ACCOUNT"
   - Name: `roadtrip-app`
   - Description: `Road Trip App Service Account`
   - Click "CREATE AND CONTINUE"

3. **Grant Roles**
   Add these roles:
   - Vertex AI User
   - Cloud SQL Client
   - Cloud Memorystore Redis Editor
   - Storage Object Admin
   - Secret Manager Secret Accessor
   - Logs Writer
   - Monitoring Metric Writer

4. **Create Key**
   - Click "ADD KEY" → "Create new key"
   - Choose JSON format
   - Save as `./credentials/vertex-ai-key.json`

## Step 2: Enable Required APIs

Go to: https://console.cloud.google.com/apis/library?project=roadtrip-460720

Enable these APIs:
- ✅ Vertex AI API
- ✅ Cloud SQL Admin API
- ✅ Cloud Memorystore for Redis API
- ✅ Cloud Storage API
- ✅ Secret Manager API
- ✅ Cloud Run API
- ✅ Cloud Build API
- ✅ Maps JavaScript API
- ✅ Places API
- ✅ Geocoding API
- ✅ Directions API
- ✅ Cloud Text-to-Speech API
- ✅ Cloud Speech-to-Text API

## Step 3: Create Cloud Resources

### Option A: Using Infrastructure Script
```bash
python3 setup_infrastructure.py
```

### Option B: Quick Deploy to Cloud Run
```bash
# Build and deploy directly
gcloud run deploy roadtrip-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 2 \
  --env-vars-file .env
```

## Step 4: Verify Setup

1. **Check Service Account**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS=./credentials/vertex-ai-key.json
   gcloud auth application-default print-access-token
   ```

2. **Test API Access**
   ```bash
   python3 test_apis_simple.py
   ```

## Quick Commands Reference

```bash
# Set project
gcloud config set project roadtrip-460720

# List service accounts
gcloud iam service-accounts list

# Create service account key
gcloud iam service-accounts keys create ./credentials/vertex-ai-key.json \
  --iam-account=roadtrip-app@roadtrip-460720.iam.gserviceaccount.com

# Deploy to Cloud Run
gcloud run deploy roadtrip-api --source . --region us-central1

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50
```

## Troubleshooting

### "Permission Denied" Errors
- Ensure billing is enabled
- Check service account has all required roles
- Verify APIs are enabled

### "API Not Enabled" Errors
- Go to API Library and enable the specific API
- Wait 1-2 minutes for propagation

### Local Testing Issues
- Set GOOGLE_APPLICATION_CREDENTIALS environment variable
- Ensure credentials file has correct permissions (chmod 600)

## Estimated Time
- Service account setup: 5 minutes
- API enabling: 5 minutes
- First deployment: 10-15 minutes

## Support
- Google Cloud Console: https://console.cloud.google.com
- Documentation: https://cloud.google.com/docs
- Billing: https://console.cloud.google.com/billing