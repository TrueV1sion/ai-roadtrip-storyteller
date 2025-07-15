# Deploy the fixed MVP that handles missing credentials gracefully
Write-Host "Deploying fixed MVP with graceful error handling..." -ForegroundColor Green

# Build and deploy
Write-Host "`nBuilding and deploying to Cloud Run..." -ForegroundColor Yellow

gcloud run deploy roadtrip-mvp `
    --source . `
    --region us-central1 `
    --platform managed `
    --allow-unauthenticated `
    --memory 2Gi `
    --cpu 2 `
    --timeout 300 `
    --min-instances 0 `
    --max-instances 100 `
    --set-env-vars @"
GOOGLE_AI_PROJECT_ID=roadtrip-460720
GOOGLE_AI_LOCATION=us-central1
GOOGLE_AI_MODEL=gemini-1.5-flash
GCS_BUCKET_NAME=roadtrip-460720-roadtrip-assets
GOOGLE_MAPS_API_KEY=AIzaSyAuduVqyKAf47TAZkCd9j4dnDd87oaLXYQ
"@

Write-Host "`nDeployment complete!" -ForegroundColor Green
Write-Host "The service now handles missing credentials gracefully" -ForegroundColor Cyan
Write-Host "Navigation will work with Google Maps API" -ForegroundColor Green
Write-Host "Stories will use fallbacks if Vertex AI isn't available" -ForegroundColor Green

Write-Host "`nTest with:" -ForegroundColor Yellow
Write-Host ".\test_full_navigation.ps1" -ForegroundColor Cyan