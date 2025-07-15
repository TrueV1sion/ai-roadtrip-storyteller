# Google Cloud Setup Guide

This guide walks you through setting up Google Cloud services for the AI Road Trip Storyteller application.

## Prerequisites

1. Google Cloud Account
2. Google Cloud CLI (`gcloud`) installed
3. Billing enabled on your GCP project

## Required APIs

Enable the following APIs in your Google Cloud Project:

```bash
# Set your project ID
export PROJECT_ID=your-project-id
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable aiplatform.googleapis.com              # Vertex AI
gcloud services enable maps-backend.googleapis.com            # Maps
gcloud services enable places-backend.googleapis.com          # Places
gcloud services enable directions-backend.googleapis.com      # Directions
gcloud services enable texttospeech.googleapis.com          # Text-to-Speech
gcloud services enable speech.googleapis.com                # Speech-to-Text
gcloud services enable translate.googleapis.com             # Translation
gcloud services enable language.googleapis.com              # Natural Language
gcloud services enable storage-api.googleapis.com           # Cloud Storage
gcloud services enable secretmanager.googleapis.com         # Secret Manager
gcloud services enable cloudresourcemanager.googleapis.com  # Resource Manager
```

## Service Account Setup

1. Create a service account for the application:

```bash
gcloud iam service-accounts create roadtrip-app \
    --display-name="Road Trip App Service Account"
```

2. Grant necessary roles:

```bash
# Get the service account email
SA_EMAIL=roadtrip-app@${PROJECT_ID}.iam.gserviceaccount.com

# Grant roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudtexttospeech.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudspeech.client"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/cloudtranslate.user"
```

3. Create and download service account key (for local development):

```bash
gcloud iam service-accounts keys create roadtrip-sa-key.json \
    --iam-account=${SA_EMAIL}

# Set the environment variable
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/roadtrip-sa-key.json"
```

## Google Maps API Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" > "Credentials"
3. Click "Create Credentials" > "API Key"
4. Name it "Road Trip Maps API Key"
5. Restrict the API key:
   - Application restrictions: HTTP referrers (for web) or IP addresses (for backend)
   - API restrictions: Select these APIs:
     - Maps JavaScript API
     - Places API
     - Directions API
     - Geocoding API
     - Distance Matrix API
6. Copy the API key and add it to your `.env` file as `GOOGLE_MAPS_API_KEY`

## Cloud Storage Bucket Setup

Create a bucket for storing generated audio files:

```bash
# Create the bucket
gsutil mb -p $PROJECT_ID -l us-central1 gs://roadtrip-audio-${PROJECT_ID}

# Set uniform bucket-level access
gsutil uniformbucketlevelaccess set on gs://roadtrip-audio-${PROJECT_ID}

# Grant service account access
gsutil iam ch serviceAccount:${SA_EMAIL}:objectAdmin gs://roadtrip-audio-${PROJECT_ID}
```

## Secret Manager Setup

Store sensitive values in Secret Manager:

```bash
# Database URL
echo -n "postgresql://user:password@host:5432/dbname" | \
    gcloud secrets create roadtrip-db-url --data-file=-

# JWT Secret Key
openssl rand -base64 32 | \
    gcloud secrets create roadtrip-jwt-secret --data-file=-

# Add other secrets as needed
echo -n "your-maps-api-key" | \
    gcloud secrets create roadtrip-maps-api-key --data-file=-
```

## Vertex AI Setup

1. Initialize Vertex AI in your project:

```bash
gcloud ai platform locations list
# Choose a location (e.g., us-central1)
```

2. The application uses Gemini models. No additional setup is required as long as the Vertex AI API is enabled.

## Environment Variables

Update your `.env` file with the following:

```env
# Google Cloud Configuration
GOOGLE_AI_PROJECT_ID=your-project-id
GOOGLE_AI_LOCATION=us-central1
GOOGLE_AI_MODEL=gemini-1.5-flash
GOOGLE_MAPS_API_KEY=your-maps-api-key
GCS_BUCKET_NAME=roadtrip-audio-your-project-id

# For local development with service account
GOOGLE_APPLICATION_CREDENTIALS=/path/to/roadtrip-sa-key.json
```

## Cost Optimization Tips

1. **Set up budget alerts** in the Google Cloud Console
2. **Use resource quotas** to prevent unexpected usage
3. **Enable only in specific regions** to reduce latency and costs
4. **Monitor usage** through Cloud Console dashboards
5. **Use caching** (already implemented) to reduce API calls

## Production Considerations

1. **Use Workload Identity** instead of service account keys in GKE
2. **Enable VPC Service Controls** for additional security
3. **Set up Cloud Monitoring** alerts for API errors and quotas
4. **Use Cloud CDN** for static content delivery
5. **Implement API key rotation** policies

## Troubleshooting

### Common Issues

1. **"Permission denied" errors**
   - Check that all required APIs are enabled
   - Verify service account has correct roles
   - Ensure GOOGLE_APPLICATION_CREDENTIALS is set correctly

2. **"Quota exceeded" errors**
   - Check quotas in Cloud Console
   - Request quota increases if needed
   - Implement better caching and rate limiting

3. **"API not enabled" errors**
   - Run the API enablement commands above
   - Wait a few minutes for changes to propagate

### Useful Commands

```bash
# Check enabled APIs
gcloud services list --enabled

# Check service account roles
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:serviceAccount:${SA_EMAIL}"

# Test authentication
gcloud auth application-default print-access-token
```