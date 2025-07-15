# PowerShell script to set Cloud Run environment variables
Write-Host "Setting environment variables for roadtrip-mvp service..." -ForegroundColor Green

# Set the environment variables
gcloud run services update roadtrip-mvp `
    --region us-central1 `
    --update-env-vars @"
GOOGLE_AI_PROJECT_ID=roadtrip-460720,
GOOGLE_AI_LOCATION=us-central1,
GCS_BUCKET_NAME=roadtrip-mvp-audio,
GOOGLE_MAPS_API_KEY=$env:GOOGLE_MAPS_API_KEY
"@

Write-Host "Environment variables updated!" -ForegroundColor Green

# Create the GCS bucket for audio storage
Write-Host "`nCreating GCS bucket for audio storage..." -ForegroundColor Green
gcloud storage buckets create gs://roadtrip-mvp-audio --location=us-central1

Write-Host "`nSetup complete! You can test the API at:" -ForegroundColor Green
Write-Host "https://roadtrip-mvp-792001900150.us-central1.run.app/api/mvp/voice" -ForegroundColor Cyan