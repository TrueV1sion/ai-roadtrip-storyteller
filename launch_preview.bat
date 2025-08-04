@echo off
REM Launch Preview Environment for AI Road Trip Storyteller (Windows)
REM This script sets up and launches a fully functional preview environment

echo ===============================================
echo    AI ROAD TRIP PREVIEW ENVIRONMENT SETUP
echo ===============================================
echo.

REM Check prerequisites
echo [CHECK] Verifying prerequisites...

REM Check Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed
    exit /b 1
)

REM Check npm
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] npm is not installed
    exit /b 1
)

REM Check gcloud
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Google Cloud SDK is not installed
    exit /b 1
)

echo [OK] All prerequisites met
echo.

REM Backend status check
echo [BACKEND] Checking backend health...
set BACKEND_URL=https://roadtrip-mvp-792001900150.us-central1.run.app

curl -s "%BACKEND_URL%/health" > health_response.json 2>nul
if %errorlevel% neq 0 (
    echo [WARNING] Backend health check failed
) else (
    echo [OK] Backend is operational
)

REM Check if Vertex AI build completed
echo.
echo [BUILD] Checking Vertex AI fix deployment...
gcloud builds list --region=us-central1 --limit=1 --format="value(status)" --project=roadtrip-460720 > build_status.txt 2>nul
set /p BUILD_STATUS=<build_status.txt
if "%BUILD_STATUS%"=="SUCCESS" (
    echo [OK] Vertex AI fix has been deployed
) else if "%BUILD_STATUS%"=="WORKING" (
    echo [INFO] Vertex AI fix deployment is still in progress
    echo        The AI features may not work until deployment completes
) else (
    echo [WARNING] Vertex AI fix deployment status: %BUILD_STATUS%
)

REM Setup mobile environment
echo.
echo [MOBILE] Setting up preview environment...

REM Create .env file for preview
(
echo # AI Road Trip Preview Environment
echo EXPO_PUBLIC_API_URL=%BACKEND_URL%
echo EXPO_PUBLIC_ENVIRONMENT=preview
echo EXPO_PUBLIC_PLATFORM=ios
echo EXPO_PUBLIC_MVP_MODE=false
echo EXPO_PUBLIC_ENABLE_BOOKING=true
echo EXPO_PUBLIC_ENABLE_VOICE=true
echo EXPO_PUBLIC_ENABLE_AR=true
echo EXPO_PUBLIC_APP_NAME=AI Road Trip Preview
echo EXPO_PUBLIC_SENTRY_DSN=
) > mobile\.env

echo [OK] Environment file created

REM Install dependencies if needed
cd mobile
if not exist "node_modules" (
    echo.
    echo [INSTALL] Installing mobile dependencies...
    call npm install
)

REM Start Expo
echo.
echo [LAUNCH] Starting Expo development server...
echo.
echo ===============================================
echo    PREVIEW ENVIRONMENT READY!
echo ===============================================
echo.
echo Backend URL: %BACKEND_URL%
echo.
echo To test the preview:
echo.
echo 1. EXPO GO APP (Recommended for quick preview):
echo    - Install Expo Go on your phone
echo    - Scan the QR code that will appear
echo    - Test all features
echo.
echo 2. iOS SIMULATOR:
echo    Press 'i' in the terminal
echo.
echo 3. ANDROID EMULATOR:
echo    Press 'a' in the terminal
echo.
echo 4. WEB BROWSER:
echo    Press 'w' in the terminal
echo.
echo FEATURES TO TEST:
echo - Voice Commands: Say 'Hey Roadtrip' and ask for stories
echo - Navigation: Request directions to any destination
echo - AI Stories: Get location-based stories while navigating
echo - Bookings: Search for restaurants and activities
echo - Voice Personalities: Try different narrator voices
echo - Offline Mode: Download maps and stories
echo.
echo Known Issues:
echo - Vertex AI may still show errors until deployment completes
echo - Some API keys are exposed (will be fixed in production)
echo - Console warnings are expected in preview mode
echo.
echo Starting Expo in 5 seconds...
timeout /t 5 /nobreak >nul

REM Clear cache and start Expo
call npx expo start --clear

REM Cleanup temp files
if exist ..\health_response.json del ..\health_response.json
if exist ..\build_status.txt del ..\build_status.txt