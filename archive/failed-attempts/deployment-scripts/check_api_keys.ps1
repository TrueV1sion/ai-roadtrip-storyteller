# Check if API keys are set locally
Write-Host "Checking API Keys Configuration..." -ForegroundColor Green

Write-Host "`nLocal Environment Variables:" -ForegroundColor Yellow

# Check Google Maps API Key
if ($env:GOOGLE_MAPS_API_KEY) {
    Write-Host "✅ GOOGLE_MAPS_API_KEY is set (length: $($env:GOOGLE_MAPS_API_KEY.Length))" -ForegroundColor Green
} else {
    Write-Host "❌ GOOGLE_MAPS_API_KEY is NOT set" -ForegroundColor Red
    Write-Host "   Set it with: `$env:GOOGLE_MAPS_API_KEY = 'your-api-key'" -ForegroundColor Yellow
}

# Check Google Application Credentials
if ($env:GOOGLE_APPLICATION_CREDENTIALS) {
    Write-Host "✅ GOOGLE_APPLICATION_CREDENTIALS is set: $env:GOOGLE_APPLICATION_CREDENTIALS" -ForegroundColor Green
    if (Test-Path $env:GOOGLE_APPLICATION_CREDENTIALS) {
        Write-Host "   ✅ File exists" -ForegroundColor Green
    } else {
        Write-Host "   ❌ File does NOT exist" -ForegroundColor Red
    }
} else {
    Write-Host "❌ GOOGLE_APPLICATION_CREDENTIALS is NOT set" -ForegroundColor Red
    Write-Host "   This is needed for Vertex AI to work" -ForegroundColor Yellow
}

Write-Host "`nTo fix missing keys:" -ForegroundColor Cyan
Write-Host "1. Set Google Maps API Key:"
Write-Host "   `$env:GOOGLE_MAPS_API_KEY = 'your-maps-api-key'" -ForegroundColor White
Write-Host ""
Write-Host "2. Set Google Application Credentials:"
Write-Host "   `$env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\path\to\service-account.json'" -ForegroundColor White
Write-Host ""
Write-Host "3. Then run: .\fix_deployment_env.ps1" -ForegroundColor White