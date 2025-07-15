# Check Cloud Run logs to see why it's failing
Write-Host "Checking deployment logs..." -ForegroundColor Yellow

# Get the logs for the failed revision
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=roadtrip-mvp AND resource.labels.revision_name=roadtrip-mvp-00005-jhm" --limit 50 --format="table(timestamp,severity,textPayload)" --project=roadtrip-460720

Write-Host "`nTo view full logs in the console:" -ForegroundColor Cyan
Write-Host "https://console.cloud.google.com/logs/viewer?project=roadtrip-460720&resource=cloud_run_revision/service_name/roadtrip-mvp/revision_name/roadtrip-mvp-00005-jhm" -ForegroundColor White