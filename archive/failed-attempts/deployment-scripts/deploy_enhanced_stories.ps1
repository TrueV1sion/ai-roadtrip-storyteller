# Deploy with enhanced location-specific stories
Write-Host "Deploying MVP with enhanced storytelling..." -ForegroundColor Green

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
Write-Host "Enhanced with rich stories for:" -ForegroundColor Cyan
Write-Host "✅ Detroit - Motor City & Motown heritage" -ForegroundColor White
Write-Host "✅ Chicago - Architecture & culture" -ForegroundColor White
Write-Host "✅ Nashville - Music City" -ForegroundColor White
Write-Host "✅ Miami - Beaches & Latin culture" -ForegroundColor White
Write-Host "✅ Las Vegas - Entertainment capital" -ForegroundColor White
Write-Host "✅ New York - The Big Apple" -ForegroundColor White
Write-Host "✅ Major National Parks" -ForegroundColor White
Write-Host "✅ And many more locations!" -ForegroundColor White

Write-Host "`nTry Detroit again - you'll get rich, specific stories now!" -ForegroundColor Yellow