# Fix environment variables for the deployed service
Write-Host "Fixing environment variables for roadtrip-mvp..." -ForegroundColor Green

# First, let's check current environment variables
Write-Host "`nChecking current configuration..." -ForegroundColor Yellow
gcloud run services describe roadtrip-mvp --region us-central1 --format="value(spec.template.spec.containers[0].env[].name)"

# Update with proper environment variables
Write-Host "`nUpdating environment variables..." -ForegroundColor Yellow

# Get the API key from local environment
$mapsKey = $env:GOOGLE_MAPS_API_KEY
if (-not $mapsKey) {
    Write-Host "ERROR: GOOGLE_MAPS_API_KEY not found in environment!" -ForegroundColor Red
    Write-Host "Please set it first: `$env:GOOGLE_MAPS_API_KEY = 'your-key-here'" -ForegroundColor Yellow
    exit 1
}

# Update the service with all required environment variables
gcloud run services update roadtrip-mvp `
    --region us-central1 `
    --update-env-vars @"
GOOGLE_AI_PROJECT_ID=roadtrip-460720
GOOGLE_AI_LOCATION=us-central1
GCS_BUCKET_NAME=roadtrip-mvp-audio
GOOGLE_MAPS_API_KEY=$mapsKey
GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json
"@

Write-Host "`nEnvironment variables updated!" -ForegroundColor Green

# Create the GCS bucket if it doesn't exist
Write-Host "`nEnsuring GCS bucket exists..." -ForegroundColor Yellow
$bucketExists = gcloud storage buckets describe gs://roadtrip-mvp-audio 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating GCS bucket..." -ForegroundColor Yellow
    gsutil mb -l us-central1 gs://roadtrip-mvp-audio
    Write-Host "Bucket created!" -ForegroundColor Green
} else {
    Write-Host "Bucket already exists!" -ForegroundColor Green
}

Write-Host "`nDeployment fixed! Test again with:" -ForegroundColor Green
Write-Host ".\test_full_navigation.ps1" -ForegroundColor Cyan