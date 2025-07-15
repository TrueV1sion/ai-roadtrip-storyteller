# Setup Vertex AI authentication for Cloud Run
Write-Host "Setting up Vertex AI authentication..." -ForegroundColor Green

# Create a service account for the application
$serviceAccountName = "roadtrip-mvp-sa"
$serviceAccountEmail = "$serviceAccountName@roadtrip-460720.iam.gserviceaccount.com"

Write-Host "`nCreating service account..." -ForegroundColor Yellow
gcloud iam service-accounts create $serviceAccountName `
    --display-name="Road Trip MVP Service Account" `
    --project=roadtrip-460720 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Service account created" -ForegroundColor Green
} else {
    Write-Host "Service account already exists" -ForegroundColor Yellow
}

Write-Host "`nGranting necessary permissions..." -ForegroundColor Yellow

# Grant Vertex AI User role
gcloud projects add-iam-policy-binding roadtrip-460720 `
    --member="serviceAccount:$serviceAccountEmail" `
    --role="roles/aiplatform.user" `
    --quiet

# Grant Storage Admin for audio files
gcloud projects add-iam-policy-binding roadtrip-460720 `
    --member="serviceAccount:$serviceAccountEmail" `
    --role="roles/storage.admin" `
    --quiet

# Grant Text-to-Speech access
gcloud projects add-iam-policy-binding roadtrip-460720 `
    --member="serviceAccount:$serviceAccountEmail" `
    --role="roles/cloudtts.client" `
    --quiet

Write-Host "`n✅ Permissions granted" -ForegroundColor Green

Write-Host "`nUpdating Cloud Run service to use the service account..." -ForegroundColor Yellow

# Update Cloud Run to use this service account
gcloud run services update roadtrip-mvp `
    --service-account=$serviceAccountEmail `
    --region=us-central1

Write-Host "`n✅ Cloud Run updated" -ForegroundColor Green

# Enable required APIs
Write-Host "`nEnsuring required APIs are enabled..." -ForegroundColor Yellow
gcloud services enable aiplatform.googleapis.com --project=roadtrip-460720
gcloud services enable texttospeech.googleapis.com --project=roadtrip-460720
gcloud services enable storage.googleapis.com --project=roadtrip-460720

Write-Host "`n✅ APIs enabled" -ForegroundColor Green

Write-Host "`nRedeploying with authentication..." -ForegroundColor Yellow

# Final deployment with everything configured
gcloud run deploy roadtrip-mvp `
    --source . `
    --region us-central1 `
    --platform managed `
    --allow-unauthenticated `
    --memory 2Gi `
    --cpu 2 `
    --timeout 300 `
    --service-account=$serviceAccountEmail `
    --set-env-vars @"
GOOGLE_AI_PROJECT_ID=roadtrip-460720
GOOGLE_AI_LOCATION=us-central1
GOOGLE_AI_MODEL=gemini-1.5-flash
GCS_BUCKET_NAME=roadtrip-460720-roadtrip-assets
GOOGLE_MAPS_API_KEY=AIzaSyAuduVqyKAf47TAZkCd9j4dnDd87oaLXYQ
GOOGLE_CLOUD_PROJECT=roadtrip-460720
"@

Write-Host "`nVertex AI setup complete!" -ForegroundColor Green
Write-Host "The app can now generate unique stories for ANY location:" -ForegroundColor Cyan
Write-Host "- Small towns and neighborhoods" -ForegroundColor White
Write-Host "- International destinations" -ForegroundColor White
Write-Host "- Hidden gems and local spots" -ForegroundColor White
Write-Host "- Any place you can imagine!" -ForegroundColor White

Write-Host "`nTest with any location - even obscure ones!" -ForegroundColor Yellow