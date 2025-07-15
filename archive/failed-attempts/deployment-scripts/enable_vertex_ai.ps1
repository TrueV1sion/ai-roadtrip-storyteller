# Enable Vertex AI for real location-specific stories
Write-Host "Setting up Vertex AI for better stories..." -ForegroundColor Green

# First, let's enable the service account for Cloud Run
Write-Host "`nEnabling default service account for Vertex AI access..." -ForegroundColor Yellow

# Get the project number
$projectNumber = gcloud projects describe roadtrip-460720 --format="value(projectNumber)"
Write-Host "Project Number: $projectNumber" -ForegroundColor Cyan

# Update Cloud Run to use the default service account with proper permissions
gcloud run services update roadtrip-mvp `
    --region us-central1 `
    --service-account "$projectNumber-compute@developer.gserviceaccount.com"

Write-Host "`nGranting Vertex AI permissions..." -ForegroundColor Yellow

# Grant necessary permissions
gcloud projects add-iam-policy-binding roadtrip-460720 `
    --member="serviceAccount:$projectNumber-compute@developer.gserviceaccount.com" `
    --role="roles/aiplatform.user"

Write-Host "`nRedeploying with proper authentication..." -ForegroundColor Yellow

# Redeploy to pick up the service account
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
    --service-account "$projectNumber-compute@developer.gserviceaccount.com" `
    --set-env-vars @"
GOOGLE_AI_PROJECT_ID=roadtrip-460720
GOOGLE_AI_LOCATION=us-central1
GOOGLE_AI_MODEL=gemini-1.5-flash
GCS_BUCKET_NAME=roadtrip-460720-roadtrip-assets
GOOGLE_MAPS_API_KEY=AIzaSyAuduVqyKAf47TAZkCd9j4dnDd87oaLXYQ
"@

Write-Host "`nVertex AI setup complete!" -ForegroundColor Green
Write-Host "You should now get rich, location-specific stories about:" -ForegroundColor Cyan
Write-Host "- Detroit's automotive history" -ForegroundColor White
Write-Host "- Motown music heritage" -ForegroundColor White
Write-Host "- Local landmarks and attractions" -ForegroundColor White
Write-Host "- And much more!" -ForegroundColor White

Write-Host "`nTest it again with Detroit or any other city!" -ForegroundColor Yellow