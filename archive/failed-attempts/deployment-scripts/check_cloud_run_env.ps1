# Check what environment variables are set on Cloud Run
Write-Host "Checking Cloud Run environment variables..." -ForegroundColor Green

# Get the service configuration
Write-Host "`nCurrent environment variables on roadtrip-mvp:" -ForegroundColor Yellow
gcloud run services describe roadtrip-mvp --region us-central1 --format="value(spec.template.spec.containers[0].env[].name)" | ForEach-Object {
    Write-Host "  - $_" -ForegroundColor White
}

Write-Host "`nChecking if Google Maps API key is set..." -ForegroundColor Yellow
$hasMapKey = gcloud run services describe roadtrip-mvp --region us-central1 --format="value(spec.template.spec.containers[0].env[?name=='GOOGLE_MAPS_API_KEY'].name)"
if ($hasMapKey) {
    Write-Host "✅ GOOGLE_MAPS_API_KEY is set" -ForegroundColor Green
} else {
    Write-Host "❌ GOOGLE_MAPS_API_KEY is NOT set" -ForegroundColor Red
    Write-Host "`nLet's fix this now..." -ForegroundColor Yellow
}

Write-Host "`nTo update just the Maps API key:" -ForegroundColor Cyan
Write-Host 'gcloud run services update roadtrip-mvp --region us-central1 --update-env-vars "GOOGLE_MAPS_API_KEY=AIzaSyAuduVqyKAf47TAZkCd9j4dnDd87oaLXYQ"' -ForegroundColor White