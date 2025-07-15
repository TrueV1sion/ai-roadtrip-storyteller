# Deploy with the API keys that are already in the .env file
Write-Host "Deploying with existing API keys from .env file..." -ForegroundColor Green

# Update the Cloud Run service with the keys from .env
Write-Host "`nUpdating Cloud Run environment variables..." -ForegroundColor Yellow

gcloud run services update roadtrip-mvp `
    --region us-central1 `
    --update-env-vars @"
GOOGLE_AI_PROJECT_ID=roadtrip-460720
GOOGLE_AI_LOCATION=us-central1
GOOGLE_AI_MODEL=gemini-1.5-flash
GCS_BUCKET_NAME=roadtrip-460720-roadtrip-assets
GOOGLE_MAPS_API_KEY=AIzaSyAuduVqyKAf47TAZkCd9j4dnDd87oaLXYQ
GCP_PROJECT_ID=roadtrip-460720
TICKETMASTER_API_KEY=5X13jI3ZPzAdU3kp3trYFf4VWqSVySgo
OPENWEATHERMAP_API_KEY=d7aa0dc75ed0dae38f627ed48d3e3bf1
"@

Write-Host "`nEnvironment variables updated with your existing keys!" -ForegroundColor Green

# Check if bucket exists (using the one from .env)
Write-Host "`nChecking GCS bucket..." -ForegroundColor Yellow
$bucketName = "roadtrip-460720-roadtrip-assets"
$bucketExists = gcloud storage buckets describe gs://$bucketName 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Creating GCS bucket: $bucketName" -ForegroundColor Yellow
    gsutil mb -l us-central1 gs://$bucketName
    Write-Host "Bucket created!" -ForegroundColor Green
} else {
    Write-Host "Bucket already exists: $bucketName" -ForegroundColor Green
}

Write-Host "`nDeployment updated with all your API keys!" -ForegroundColor Green
Write-Host "The service should now have:" -ForegroundColor Cyan
Write-Host "✅ Google Maps API for navigation" -ForegroundColor Green
Write-Host "✅ Vertex AI for story generation" -ForegroundColor Green
Write-Host "✅ Google Cloud Storage for audio files" -ForegroundColor Green
Write-Host "✅ Weather and event APIs configured" -ForegroundColor Green

Write-Host "`nTest it now with:" -ForegroundColor Yellow
Write-Host ".\test_full_navigation.ps1" -ForegroundColor Cyan