# Testing Your Cloud Run Deployment 🧪

## 1. Get Your Service URL

After successful deployment, get your URL:

```cmd
gcloud run services describe roadtrip-api --region us-central1 --format "value(status.url)"
```

It will look like: `https://roadtrip-api-xxxxx-uc.a.run.app`

## 2. Quick Health Checks

### Basic Health Check
```cmd
curl https://roadtrip-api-xxxxx-uc.a.run.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-07T...",
  "version": "1.0.0"
}
```

### Detailed Health Check
```cmd
curl https://roadtrip-api-xxxxx-uc.a.run.app/health/detailed
```

This shows database, Redis, and API status.

## 3. Test API Documentation

Open in your browser:
```
https://roadtrip-api-xxxxx-uc.a.run.app/docs
```

This opens the interactive Swagger UI where you can test all endpoints!

## 4. Test Core Features

### Test Voice Assistant
```cmd
curl -X POST https://roadtrip-api-xxxxx-uc.a.run.app/api/voice-assistant/interact ^
  -H "Content-Type: application/json" ^
  -d "{\"user_input\": \"Plan a trip to Disneyland\", \"context\": {\"origin\": \"San Francisco\"}}"
```

### Test Story Generation
```cmd
curl -X POST https://roadtrip-api-xxxxx-uc.a.run.app/api/stories/generate ^
  -H "Content-Type: application/json" ^
  -d "{\"location\": \"Grand Canyon\", \"style\": \"adventure\"}"
```

### Test Directions
```cmd
curl -X POST https://roadtrip-api-xxxxx-uc.a.run.app/api/directions ^
  -H "Content-Type: application/json" ^
  -d "{\"origin\": \"San Francisco, CA\", \"destination\": \"Los Angeles, CA\"}"
```

## 5. Create Test Script

Save this as `test_deployment.ps1` (PowerShell):

```powershell
# Get service URL
$SERVICE_URL = gcloud run services describe roadtrip-api --region us-central1 --format "value(status.url)"
Write-Host "Testing deployment at: $SERVICE_URL" -ForegroundColor Green

# Test health
Write-Host "`nTesting health endpoint..." -ForegroundColor Yellow
$health = Invoke-RestMethod "$SERVICE_URL/health"
Write-Host "Health Status: $($health.status)" -ForegroundColor Green

# Test detailed health
Write-Host "`nTesting detailed health..." -ForegroundColor Yellow
$detailed = Invoke-RestMethod "$SERVICE_URL/health/detailed"
Write-Host "Services:" -ForegroundColor Green
$detailed.health_checks | ConvertTo-Json

# Test voice assistant
Write-Host "`nTesting voice assistant..." -ForegroundColor Yellow
$body = @{
    user_input = "I want to go to Disneyland with my family"
    context = @{
        origin = "San Francisco, CA"
    }
} | ConvertTo-Json

$response = Invoke-RestMethod -Method Post -Uri "$SERVICE_URL/api/voice-assistant/interact" -ContentType "application/json" -Body $body
Write-Host "Voice Response: $($response.response)" -ForegroundColor Green
Write-Host "Selected Personality: $($response.voice_personality.name)" -ForegroundColor Cyan

Write-Host "`nAll tests completed!" -ForegroundColor Green
Write-Host "API Docs available at: $SERVICE_URL/docs" -ForegroundColor Cyan
```

Run it:
```powershell
.\test_deployment.ps1
```

## 6. Monitor Performance

### View Logs
```cmd
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=roadtrip-api" --limit 50
```

### Check Metrics
```cmd
gcloud monitoring metrics list --filter="metric.type:run.googleapis.com"
```

## 7. Test with Python

Create `test_api.py`:

```python
import requests
import json

# Get service URL
import subprocess
result = subprocess.run(['gcloud', 'run', 'services', 'describe', 'roadtrip-api', 
                        '--region', 'us-central1', '--format', 'value(status.url)'], 
                       capture_output=True, text=True)
SERVICE_URL = result.stdout.strip()

print(f"Testing {SERVICE_URL}")

# Test health
response = requests.get(f"{SERVICE_URL}/health")
print(f"Health: {response.json()}")

# Test voice assistant
data = {
    "user_input": "Plan a road trip to the Grand Canyon",
    "context": {"origin": "Las Vegas, NV"}
}
response = requests.post(f"{SERVICE_URL}/api/voice-assistant/interact", json=data)
result = response.json()
print(f"\nVoice Assistant Response:")
print(f"- Personality: {result.get('voice_personality', {}).get('name')}")
print(f"- Response: {result.get('response')}")
print(f"- Processing Time: {result.get('metadata', {}).get('processing_time_ms')}ms")

# Test API endpoints
print(f"\nExplore more at: {SERVICE_URL}/docs")
```

## 8. Load Testing (Optional)

Simple load test with curl:
```bash
# Test 10 concurrent requests
for i in {1..10}; do
  curl -s https://roadtrip-api-xxxxx-uc.a.run.app/health &
done
wait
```

## 9. Mobile App Testing

Update your mobile app to use the Cloud Run URL:

In `mobile/src/config/env.ts`:
```javascript
export const API_URL = 'https://roadtrip-api-xxxxx-uc.a.run.app';
```

## 10. Common Issues & Solutions

### "Unauthorized" Error
- Check if `--allow-unauthenticated` was set during deployment
- Fix: `gcloud run services update roadtrip-api --region us-central1 --allow-unauthenticated`

### "Timeout" Error
- Increase timeout: `gcloud run services update roadtrip-api --region us-central1 --timeout 300`

### "Memory Exceeded" Error
- Increase memory: `gcloud run services update roadtrip-api --region us-central1 --memory 4Gi`

## Quick Test Commands Summary

```cmd
# Get URL
set URL=https://roadtrip-api-xxxxx-uc.a.run.app

# Test health
curl %URL%/health

# Open docs
start %URL%/docs

# Test voice
curl -X POST %URL%/api/voice-assistant/interact -H "Content-Type: application/json" -d "{\"user_input\":\"Hello\"}"
```

## Success Indicators ✅

- Health endpoint returns `{"status": "healthy"}`
- API docs page loads
- Voice assistant responds with personality selection
- No errors in logs
- Response times < 1 second

Your app is successfully deployed when all these tests pass!