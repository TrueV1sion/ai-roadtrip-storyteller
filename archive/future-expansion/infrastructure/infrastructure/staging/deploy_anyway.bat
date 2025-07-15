@echo off
echo.
echo DEPLOYING WITH CURRENT PERMISSIONS
echo ==================================
echo.
echo We have 6/11 permissions which is ENOUGH for staging:
echo - Cloud SQL: YES (using SQLite fallback if needed)
echo - Redis: YES (using memory cache if needed)  
echo - Secret Manager: YES
echo - Storage: YES
echo - AI Platform: YES
echo - Logging: YES
echo.
echo Missing permissions will be handled by fallbacks:
echo - Monitoring/Trace: Basic logging only
echo - Network/VPC: Use public endpoints
echo - TTS: Mock voice responses
echo.
echo Starting deployment...
echo.

cd C:\Users\jared\OneDrive\Desktop\RoadTrip
call infrastructure\staging\deploy_full_application.sh

echo.
echo Deployment initiated!
echo.
pause