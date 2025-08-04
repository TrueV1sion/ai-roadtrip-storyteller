@echo off
REM Incremental deployment script for Google Cloud Run (Windows)

setlocal enabledelayedexpansion

REM Configuration
if "%GOOGLE_CLOUD_PROJECT%"=="" set GOOGLE_CLOUD_PROJECT=roadtrip-mvp
set SERVICE_NAME=roadtrip-backend-incremental
if "%GOOGLE_CLOUD_REGION%"=="" set GOOGLE_CLOUD_REGION=us-central1
set IMAGE_NAME=gcr.io/%GOOGLE_CLOUD_PROJECT%/%SERVICE_NAME%

echo === AI Road Trip Backend Incremental Deployment ===
echo Project: %GOOGLE_CLOUD_PROJECT%
echo Service: %SERVICE_NAME%
echo Region: %GOOGLE_CLOUD_REGION%
echo.

REM Check if gcloud is installed
where gcloud >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: gcloud CLI is not installed
    echo Please install Google Cloud SDK from https://cloud.google.com/sdk/
    exit /b 1
)

REM Check authentication
echo Checking Google Cloud authentication...
gcloud auth list --filter=status:ACTIVE --format="value(account)" | findstr . >nul
if %errorlevel% neq 0 (
    echo Error: Not authenticated with Google Cloud
    echo Run: gcloud auth login
    exit /b 1
)

REM Set project
echo Setting project to %GOOGLE_CLOUD_PROJECT%...
gcloud config set project %GOOGLE_CLOUD_PROJECT%

REM Enable required APIs
echo Enabling required Google Cloud APIs...
call gcloud services enable cloudbuild.googleapis.com cloudrun.googleapis.com artifactregistry.googleapis.com

REM Fix imports first
echo Fixing import statements...
python fix_imports.py

REM Build the Docker image
echo Building Docker image...
docker build -f Dockerfile.incremental -t %IMAGE_NAME% .

REM Configure Docker for GCR
echo Configuring Docker for Google Container Registry...
call gcloud auth configure-docker

REM Push to Google Container Registry
echo Pushing image to Google Container Registry...
docker push %IMAGE_NAME%

REM Deploy to Cloud Run
echo Deploying to Cloud Run...
call gcloud run deploy %SERVICE_NAME% ^
    --image %IMAGE_NAME% ^
    --region %GOOGLE_CLOUD_REGION% ^
    --platform managed ^
    --allow-unauthenticated ^
    --port 8080 ^
    --memory 1Gi ^
    --cpu 1 ^
    --timeout 60 ^
    --max-instances 10 ^
    --min-instances 1 ^
    --set-env-vars "ENVIRONMENT=production" ^
    --set-env-vars "LOG_LEVEL=INFO" ^
    --set-env-vars "GOOGLE_CLOUD_PROJECT=%GOOGLE_CLOUD_PROJECT%" ^
    --set-env-vars "CORS_ORIGINS=*"

REM Get the service URL
for /f "delims=" %%i in ('gcloud run services describe %SERVICE_NAME% --region %GOOGLE_CLOUD_REGION% --format "value(status.url)"') do set SERVICE_URL=%%i

echo.
echo === Deployment Complete ===
echo Service URL: %SERVICE_URL%
echo.
echo Test endpoints:
echo   Health check: %SERVICE_URL%/health
echo   Detailed health: %SERVICE_URL%/health/detailed
echo   API docs: %SERVICE_URL%/docs
echo.
echo To view logs:
echo   gcloud run services logs read %SERVICE_NAME% --region %GOOGLE_CLOUD_REGION%
echo.
echo To update environment variables:
echo   gcloud run services update %SERVICE_NAME% --region %GOOGLE_CLOUD_REGION% --update-env-vars KEY=VALUE

pause