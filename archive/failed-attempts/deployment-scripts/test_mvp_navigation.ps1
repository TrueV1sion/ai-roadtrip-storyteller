# Test the MVP navigation endpoint
$url = "https://roadtrip-mvp-792001900150.us-central1.run.app/api/mvp/voice"

Write-Host "Testing MVP Navigation API..." -ForegroundColor Green

# Test 1: Navigation command
Write-Host "`nTest 1: Navigation to Golden Gate Bridge" -ForegroundColor Yellow
$body1 = @{
    user_input = "Navigate to Golden Gate Bridge"
    context = @{
        location = @{
            lat = 37.7749
            lng = -122.4194
        }
        location_name = "San Francisco"
    }
} | ConvertTo-Json

$response1 = Invoke-RestMethod -Uri $url -Method Post -Body $body1 -ContentType "application/json"
Write-Host "Response:" -ForegroundColor Cyan
$response1 | ConvertTo-Json -Depth 10

# Test 2: Story request
Write-Host "`nTest 2: Story about current location" -ForegroundColor Yellow
$body2 = @{
    user_input = "Tell me about this area"
    context = @{
        location = @{
            lat = 37.7749
            lng = -122.4194
        }
        location_name = "San Francisco"
    }
} | ConvertTo-Json

$response2 = Invoke-RestMethod -Uri $url -Method Post -Body $body2 -ContentType "application/json"
Write-Host "Response:" -ForegroundColor Cyan
$response2 | ConvertTo-Json -Depth 10

Write-Host "`nTests complete!" -ForegroundColor Green