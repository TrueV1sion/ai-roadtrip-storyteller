# Test navigation with detailed output
$url = "https://roadtrip-mvp-792001900150.us-central1.run.app/api/mvp/voice"

Write-Host "Testing Navigation with Detailed Response..." -ForegroundColor Green

$body = @{
    user_input = "Navigate to Golden Gate Bridge"
    context = @{
        location = @{
            lat = 37.7749
            lng = -122.4194
        }
        location_name = "Downtown San Francisco"
    }
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri $url -Method Post -Body $body -ContentType "application/json"
    
    Write-Host "`nFull Response:" -ForegroundColor Cyan
    $response | ConvertTo-Json -Depth 10
    
    Write-Host "`nParsed Details:" -ForegroundColor Yellow
    Write-Host "Response Type: $($response.response.type)" -ForegroundColor White
    Write-Host "Destination: $($response.response.destination)" -ForegroundColor White
    Write-Host "Has Route: $($response.response.has_route)" -ForegroundColor White
    Write-Host "Story: $($response.response.text)" -ForegroundColor White
    
    if ($response.route) {
        Write-Host "`nNavigation Route Found!" -ForegroundColor Green
        Write-Host "Distance: $($response.route.distance)" -ForegroundColor White
        Write-Host "Duration: $($response.route.duration)" -ForegroundColor White
    } else {
        Write-Host "`nNo route data in response" -ForegroundColor Yellow
        Write-Host "This means Google Maps directions aren't being calculated" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

Write-Host "`nChecking service health..." -ForegroundColor Cyan
$health = Invoke-RestMethod -Uri "https://roadtrip-mvp-792001900150.us-central1.run.app/api/mvp/health"
Write-Host "Maps Configured: $($health.maps_configured)" -ForegroundColor White
Write-Host "AI Configured: $($health.ai_configured)" -ForegroundColor White
Write-Host "TTS Available: $($health.tts_available)" -ForegroundColor White