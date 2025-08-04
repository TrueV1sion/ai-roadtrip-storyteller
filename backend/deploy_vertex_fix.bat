@echo off
REM Deploy the fixed backend with Vertex AI instead of Generative Language API

echo [DEPLOY] Deploying Vertex AI fix to production
echo ==============================================

REM Variables
set PROJECT_ID=roadtrip-460720
set SERVICE_NAME=roadtrip-mvp
set REGION=us-central1
set SERVICE_ACCOUNT=roadtrip-mvp-sa@%PROJECT_ID%.iam.gserviceaccount.com

REM Check if we're in the backend directory
if not exist mvp_health.py (
    echo [ERROR] Must run from backend directory
    exit /b 1
)

REM Verify the fix is in place
echo [CHECK] Verifying Vertex AI implementation...
findstr /C:"google.generativeai" mvp_health.py >nul
if %errorlevel% equ 0 (
    echo [ERROR] mvp_health.py still contains google.generativeai!
    echo The fix was not applied correctly.
    exit /b 1
)

findstr /C:"vertexai" mvp_health.py >nul
if %errorlevel% neq 0 (
    echo [ERROR] mvp_health.py does not import vertexai!
    echo The fix was not applied correctly.
    exit /b 1
)

echo [CHECK] Vertex AI implementation verified!

REM Build with Cloud Build instead of local Docker
echo [BUILD] Submitting build to Cloud Build...
gcloud builds submit --tag gcr.io/%PROJECT_ID%/%SERVICE_NAME%:vertex-fix .

REM Deploy to Cloud Run
echo [DEPLOY] Deploying to Cloud Run...
gcloud run deploy %SERVICE_NAME% ^
    --image gcr.io/%PROJECT_ID%/%SERVICE_NAME%:vertex-fix ^
    --platform managed ^
    --region %REGION% ^
    --service-account %SERVICE_ACCOUNT% ^
    --set-env-vars "GOOGLE_AI_PROJECT_ID=%PROJECT_ID%" ^
    --set-env-vars "GOOGLE_AI_LOCATION=%REGION%" ^
    --set-env-vars "GOOGLE_AI_MODEL=gemini-1.5-flash" ^
    --set-env-vars "USE_VERTEX_AI=true" ^
    --set-env-vars "ENVIRONMENT=production" ^
    --allow-unauthenticated ^
    --memory 512Mi ^
    --cpu 1 ^
    --timeout 60 ^
    --max-instances 10

REM Get the service URL
for /f "tokens=*" %%i in ('gcloud run services describe %SERVICE_NAME% --platform managed --region %REGION% --format "value(status.url)"') do set SERVICE_URL=%%i

echo.
echo [SUCCESS] Deployment complete!
echo Service URL: %SERVICE_URL%
echo.
echo [TEST] Testing the health endpoint...
curl -s "%SERVICE_URL%/health"

echo.
echo [INFO] The Vertex AI fix has been deployed successfully!
echo The backend should no longer return 403 errors for AI requests.
pause