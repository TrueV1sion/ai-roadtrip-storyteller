@echo off
REM Deploy Backend Production Script for Windows
REM Deploys the fixed backend to Google Cloud Run

setlocal enabledelayedexpansion

echo === RoadTrip Backend Production Deployment ===

REM Configuration
set PROJECT_ID=roadtrip-460720
set REGION=us-central1
set SERVICE_NAME=roadtrip-backend-production

REM Check if gcloud is installed
where gcloud >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: gcloud CLI is not installed
    echo Please install from: https://cloud.google.com/sdk/docs/install
    exit /b 1
)

REM Set the project
echo Setting project to %PROJECT_ID%...
gcloud config set project %PROJECT_ID%

REM Check if user is authenticated
gcloud auth list --filter=status:ACTIVE --format="value(account)" | findstr . >nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Not authenticated with gcloud. Please run 'gcloud auth login'
    exit /b 1
)

REM Enable required APIs
echo Enabling required APIs...
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com secretmanager.googleapis.com aiplatform.googleapis.com

REM Check if secrets exist (create placeholders if they don't)
echo Checking required secrets...

set SECRETS=database-url redis-url jwt-secret-key jwt-refresh-secret-key google-maps-api-key openweather-api-key ticketmaster-api-key opentable-api-key viator-api-key recreation-gov-api-key spotify-client-id spotify-client-secret twilio-account-sid twilio-auth-token twilio-from-phone sendgrid-api-key encryption-key

for %%s in (%SECRETS%) do (
    gcloud secrets describe %%s --project=%PROJECT_ID% >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo Creating placeholder for secret: %%s
        echo PLACEHOLDER_VALUE | gcloud secrets create %%s --data-file=- --project=%PROJECT_ID% --replication-policy="automatic"
    ) else (
        echo Secret exists: %%s
    )
)

REM Grant Secret Manager access to the service account
echo Granting Secret Manager access to service account...
set SERVICE_ACCOUNT=roadtrip-mvp-sa@%PROJECT_ID%.iam.gserviceaccount.com

for %%s in (%SECRETS%) do (
    gcloud secrets add-iam-policy-binding %%s --member="serviceAccount:%SERVICE_ACCOUNT%" --role="roles/secretmanager.secretAccessor" --project=%PROJECT_ID% --quiet >nul 2>&1
)

REM Navigate to project root
cd /d "%~dp0\..\.."

REM Check if backend directory exists
if not exist "backend" (
    echo Error: backend directory not found
    exit /b 1
)

REM Check if Dockerfile exists
if not exist "backend\Dockerfile" (
    echo Error: backend\Dockerfile not found
    exit /b 1
)

REM Check if cloudbuild file exists
if not exist "backend\cloudbuild-backend-production.yaml" (
    echo Error: backend\cloudbuild-backend-production.yaml not found
    exit /b 1
)

REM Submit the build
echo Submitting build to Cloud Build...
gcloud builds submit --config=backend/cloudbuild-backend-production.yaml --project=%PROJECT_ID% --region=%REGION% --substitutions=_SERVICE_NAME=%SERVICE_NAME%,_REGION=%REGION%

if %ERRORLEVEL% EQU 0 (
    echo Deployment successful!
    
    REM Get service URL
    for /f "tokens=*" %%i in ('gcloud run services describe %SERVICE_NAME% --region=%REGION% --project=%PROJECT_ID% --format="get(status.url)"') do set SERVICE_URL=%%i
    
    echo Service deployed at: !SERVICE_URL!
    echo Health check: !SERVICE_URL!/health
    echo API docs: !SERVICE_URL!/docs
    
    REM Test the health endpoint
    echo.
    echo Testing health endpoint...
    curl -s "!SERVICE_URL!/health"
    
) else (
    echo Deployment failed!
    exit /b 1
)

echo.
echo === Deployment Complete ===
echo Next steps:
echo 1. Update the secret values in Secret Manager with actual values
echo 2. Test the API endpoints
echo 3. Monitor logs: gcloud run logs tail %SERVICE_NAME% --region=%REGION%

endlocal