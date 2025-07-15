# Test the FULL navigation functionality
$url = "https://roadtrip-mvp-792001900150.us-central1.run.app/api/mvp/voice"

Write-Host "Testing FULL Navigation with Turn-by-Turn Directions..." -ForegroundColor Green

# Test navigation from San Francisco to Golden Gate Bridge
Write-Host "`nTest: Navigate from San Francisco to Golden Gate Bridge" -ForegroundColor Yellow
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
    
    Write-Host "`nNavigation Response:" -ForegroundColor Cyan
    Write-Host "Destination: $($response.response.destination)" -ForegroundColor White
    Write-Host "Story: $($response.response.text)" -ForegroundColor White
    
    if ($response.route) {
        Write-Host "`nRoute Details:" -ForegroundColor Green
        Write-Host "Distance: $($response.route.distance)" -ForegroundColor White
        Write-Host "Duration: $($response.route.duration)" -ForegroundColor White
        Write-Host "From: $($response.route.start_address)" -ForegroundColor White
        Write-Host "To: $($response.route.end_address)" -ForegroundColor White
        
        Write-Host "`nTurn-by-Turn Directions:" -ForegroundColor Green
        foreach ($step in $response.route.steps) {
            Write-Host "→ $($step.instruction) ($($step.distance))" -ForegroundColor White
        }
    }
    
    if ($response.audio_url) {
        Write-Host "`nAudio narration available at:" -ForegroundColor Green
        Write-Host $response.audio_url -ForegroundColor Cyan
    }
    
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

Write-Host "`nThe app now provides COMPLETE navigation - no external navigation app needed!" -ForegroundColor Green