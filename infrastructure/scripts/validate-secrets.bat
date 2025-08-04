@echo off
REM RoadTrip Secret Validation Script for Windows
REM Usage: validate-secrets.bat [PROJECT_ID]

setlocal enabledelayedexpansion

set PROJECT_ID=%1
if "%PROJECT_ID%"=="" set PROJECT_ID=roadtrip-460720

echo RoadTrip Secret Validation
echo =========================
echo Project ID: %PROJECT_ID%
echo.

REM Check if Python script exists
if not exist "%~dp0validate_secrets.py" (
    echo Creating validation script...
    REM We'll use the shell script logic but in Python
)

REM For now, we'll do basic validation using gcloud directly
echo Checking Critical Secrets...
echo ==========================

set CRITICAL_SECRETS=roadtrip-database-url roadtrip-redis-url roadtrip-jwt-secret roadtrip-secret-key roadtrip-google-maps-key

set MISSING_COUNT=0
set PLACEHOLDER_COUNT=0

for %%s in (%CRITICAL_SECRETS%) do (
    echo Checking %%s...
    gcloud secrets versions access latest --secret=%%s --project=%PROJECT_ID% >temp_secret.txt 2>nul
    if !errorlevel! neq 0 (
        echo   [MISSING] %%s
        set /a MISSING_COUNT+=1
    ) else (
        findstr /C:"PLACEHOLDER_" temp_secret.txt >nul
        if !errorlevel! equ 0 (
            echo   [PLACEHOLDER] %%s - Needs real value
            set /a PLACEHOLDER_COUNT+=1
        ) else (
            echo   [OK] %%s
        )
    )
)

del temp_secret.txt 2>nul

echo.
echo Summary:
echo ========
if %MISSING_COUNT% gtr 0 (
    echo CRITICAL: %MISSING_COUNT% secrets are missing!
)
if %PLACEHOLDER_COUNT% gtr 0 (
    echo WARNING: %PLACEHOLDER_COUNT% secrets are using placeholder values!
)

if %MISSING_COUNT% gtr 0 (
    exit /b 1
)

if %PLACEHOLDER_COUNT% gtr 0 (
    echo.
    echo The application may not function correctly with placeholder values.
    echo Update secrets using:
    echo   echo your-value ^| gcloud secrets versions add SECRET_ID --data-file=- --project=%PROJECT_ID%
)

endlocal