@echo off
REM RoadTrip Secret Manager Setup Script for Windows
REM Usage: setup-secrets.bat [PROJECT_ID]

setlocal enabledelayedexpansion

set PROJECT_ID=%1
if "%PROJECT_ID%"=="" set PROJECT_ID=roadtrip-460720

echo RoadTrip Secret Manager Setup
echo =============================
echo Project ID: %PROJECT_ID%
echo.

REM Check if gcloud is installed
where gcloud >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: gcloud CLI is not installed or not in PATH
    echo Please install Google Cloud SDK from: https://cloud.google.com/sdk/docs/install
    exit /b 1
)

REM Check if authenticated
gcloud auth list --filter=status:ACTIVE --format="value(account)" >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Not authenticated with gcloud
    echo Please run: gcloud auth login
    exit /b 1
)

REM Check Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    exit /b 1
)

REM Run the Python setup script
echo Running secret setup script...
python "%~dp0setup_all_secrets.py" %PROJECT_ID%

if %errorlevel% neq 0 (
    echo.
    echo ERROR: Secret setup failed
    exit /b 1
)

echo.
echo Secret setup completed successfully!
echo.
echo To validate secrets, run:
echo   validate-secrets.bat %PROJECT_ID%

endlocal