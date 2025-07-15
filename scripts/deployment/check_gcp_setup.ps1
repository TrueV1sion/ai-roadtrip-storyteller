# PowerShell script to check GCP project setup for AI Road Trip Storyteller
Write-Host "AI Road Trip Storyteller - GCP Setup Checker" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

$projectId = "roadtrip-460720"

# Check if gcloud is installed
Write-Host "Checking gcloud installation..." -ForegroundColor Yellow
$gcloudVersion = gcloud version --format="value(Google Cloud SDK)" 2>$null
if ($?) {
    Write-Host "✓ gcloud CLI installed: $gcloudVersion" -ForegroundColor Green
} else {
    Write-Host "✗ gcloud CLI not found. Please install from https://cloud.google.com/sdk" -ForegroundColor Red
    exit 1
}

# Check authentication
Write-Host "`nChecking authentication..." -ForegroundColor Yellow
$activeAccount = gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null
if ($activeAccount) {
    Write-Host "✓ Authenticated as: $activeAccount" -ForegroundColor Green
} else {
    Write-Host "✗ Not authenticated. Run: gcloud auth login" -ForegroundColor Red
    exit 1
}

# Check project
Write-Host "`nChecking project..." -ForegroundColor Yellow
$project = gcloud projects describe $projectId --format="value(projectId)" 2>$null
if ($?) {
    Write-Host "✓ Project found: $projectId" -ForegroundColor Green
    
    # Check project details
    $projectName = gcloud projects describe $projectId --format="value(name)" 2>$null
    $projectState = gcloud projects describe $projectId --format="value(lifecycleState)" 2>$null
    Write-Host "  Name: $projectName" -ForegroundColor Gray
    Write-Host "  State: $projectState" -ForegroundColor Gray
} else {
    Write-Host "✗ Project not found or not accessible: $projectId" -ForegroundColor Red
    Write-Host "  Please check the project ID or your permissions" -ForegroundColor Yellow
    exit 1
}

# Set project
Write-Host "`nSetting active project..." -ForegroundColor Yellow
gcloud config set project $projectId 2>$null
Write-Host "✓ Active project set to: $projectId" -ForegroundColor Green

# Check billing
Write-Host "`nChecking billing..." -ForegroundColor Yellow
$billingEnabled = gcloud beta billing projects describe $projectId --format="value(billingEnabled)" 2>$null
if ($billingEnabled -eq "True") {
    Write-Host "✓ Billing is enabled" -ForegroundColor Green
} else {
    Write-Host "✗ Billing is not enabled. Enable at: https://console.cloud.google.com/billing" -ForegroundColor Red
}

# Required APIs
$requiredApis = @(
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "texttospeech.googleapis.com",
    "speech.googleapis.com",
    "maps-backend.googleapis.com",
    "redis.googleapis.com",
    "monitoring.googleapis.com",
    "logging.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com"
)

# Check enabled APIs
Write-Host "`nChecking enabled APIs..." -ForegroundColor Yellow
$enabledApis = gcloud services list --enabled --format="value(config.name)" 2>$null

$missingApis = @()
$enabledCount = 0

foreach ($api in $requiredApis) {
    if ($enabledApis -contains $api) {
        Write-Host "✓ $api" -ForegroundColor Green
        $enabledCount++
    } else {
        Write-Host "✗ $api" -ForegroundColor Red
        $missingApis += $api
    }
}

Write-Host "`nSummary:" -ForegroundColor Cyan
Write-Host "- Enabled APIs: $enabledCount/$($requiredApis.Count)" -ForegroundColor White
Write-Host "- Missing APIs: $($missingApis.Count)" -ForegroundColor White

if ($missingApis.Count -gt 0) {
    Write-Host "`nTo enable missing APIs, run:" -ForegroundColor Yellow
    Write-Host "gcloud services enable \" -ForegroundColor White
    foreach ($api in $missingApis) {
        Write-Host "  $api \" -ForegroundColor White
    }
    Write-Host "  --project=$projectId" -ForegroundColor White
    
    Write-Host "`nOr enable them individually:" -ForegroundColor Yellow
    foreach ($api in $missingApis) {
        Write-Host "gcloud services enable $api --project=$projectId" -ForegroundColor Gray
    }
}

# Check for existing resources
Write-Host "`nChecking for existing resources..." -ForegroundColor Yellow

# Check Cloud Run services
$cloudRunServices = gcloud run services list --format="value(metadata.name)" --region=us-central1 2>$null
if ($cloudRunServices -contains "roadtrip-api") {
    Write-Host "✓ Cloud Run service 'roadtrip-api' exists" -ForegroundColor Green
} else {
    Write-Host "- Cloud Run service 'roadtrip-api' not found (will be created during deployment)" -ForegroundColor Gray
}

# Check Cloud SQL instances
$sqlInstances = gcloud sql instances list --format="value(name)" 2>$null
if ($sqlInstances -contains "roadtrip-db-prod") {
    Write-Host "✓ Cloud SQL instance 'roadtrip-db-prod' exists" -ForegroundColor Green
} else {
    Write-Host "- Cloud SQL instance 'roadtrip-db-prod' not found (will be created during deployment)" -ForegroundColor Gray
}

Write-Host "`nSetup check complete!" -ForegroundColor Green
Write-Host ""

if ($missingApis.Count -eq 0 -and $billingEnabled -eq "True") {
    Write-Host "✅ Your project is ready for deployment!" -ForegroundColor Green
    Write-Host "Run the deployment script from WSL: ./gcp_deploy.sh" -ForegroundColor Yellow
} else {
    Write-Host "⚠️  Please address the issues above before deploying" -ForegroundColor Yellow
}