# Deploy MVP with FULL navigation capabilities
Write-Host "Deploying AI Road Trip Storyteller MVP with Navigation..." -ForegroundColor Green

# Build and deploy to Cloud Run
Write-Host "`nBuilding and deploying to Cloud Run..." -ForegroundColor Yellow
Set-Location -Path "C:\Users\Jared\OneDrive\Desktop\roadtrip\backend"

gcloud run deploy roadtrip-mvp `
    --source . `
    --region us-central1 `
    --platform managed `
    --allow-unauthenticated `
    --memory 2Gi `
    --cpu 2 `
    --timeout 60 `
    --min-instances 1 `
    --max-instances 100 `
    --set-env-vars @"
GOOGLE_AI_PROJECT_ID=roadtrip-460720,
GOOGLE_AI_LOCATION=us-central1,
GCS_BUCKET_NAME=roadtrip-mvp-audio,
GOOGLE_MAPS_API_KEY=$env:GOOGLE_MAPS_API_KEY,
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
"@

Write-Host "`nDeployment complete!" -ForegroundColor Green
Write-Host "The app now includes:" -ForegroundColor Cyan
Write-Host "✅ Voice command processing" -ForegroundColor Green
Write-Host "✅ Turn-by-turn navigation with Google Maps Directions API" -ForegroundColor Green
Write-Host "✅ Real-time route calculation" -ForegroundColor Green
Write-Host "✅ AI-generated stories about destinations" -ForegroundColor Green
Write-Host "✅ Text-to-speech audio narration" -ForegroundColor Green

Write-Host "`nTest the full navigation at:" -ForegroundColor Yellow
Write-Host "https://roadtrip-mvp-792001900150.us-central1.run.app/api/mvp/voice" -ForegroundColor Cyan