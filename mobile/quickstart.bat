@echo off
REM AI Road Trip - Quick Start Script for Test Drive (Windows)
REM This script sets up and launches the mobile app for testing

echo.
echo  AI Road Trip - Quick Start for Test Drive
echo ==========================================
echo.

REM Check if we're in the mobile directory
if not exist "package.json" (
    echo Error: Not in the mobile directory. Please run from the mobile folder.
    exit /b 1
)

REM Check prerequisites
echo Checking prerequisites...

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: Node.js is not installed. Please install Node.js 18+
    exit /b 1
)

where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: npm is not installed. Please install npm
    exit /b 1
)

where expo >nul 2>nul
if %errorlevel% neq 0 (
    echo Installing Expo CLI...
    call npm install -g expo-cli
)

REM Install dependencies if needed
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
) else (
    echo Dependencies already installed
)

REM Check if .env file exists
if not exist ".env" (
    echo No .env file found. Creating from example...
    copy .env.example .env
    echo Please update .env with your configuration
)

REM Clear caches
echo Clearing caches...
start /b npx expo start -c >nul 2>&1
timeout /t 5 >nul
taskkill /f /im node.exe >nul 2>&1

REM Platform selection
echo.
echo Select your platform:
echo 1) iOS Simulator (Mac only - won't work on Windows)
echo 2) Android Emulator
echo 3) Physical Device (Expo Go)
echo 4) Web Browser
echo 5) Development Build (iOS - requires Mac)
echo 6) Development Build (Android)
echo.

set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" (
    echo iOS Simulator is not available on Windows. Please use option 2, 3, or 4.
    pause
    exit /b 1
)

if "%choice%"=="2" (
    echo Starting Android Emulator...
    call npm run android
    goto end
)

if "%choice%"=="3" (
    echo Starting for Physical Device...
    echo.
    echo IMPORTANT: For physical device testing:
    echo 1. Install Expo Go from App Store/Play Store
    echo 2. Make sure your phone and computer are on the same network
    echo 3. Update EXPO_PUBLIC_DEV_API_URL in .env with your computer's IP
    echo.
    echo Your computer's IP addresses:
    for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do echo   -%%a
    echo.
    pause
    call npx expo start --tunnel
    goto end
)

if "%choice%"=="4" (
    echo Starting Web Browser...
    call npm run web
    goto end
)

if "%choice%"=="5" (
    echo iOS builds require a Mac. Please use a Mac for iOS development.
    pause
    exit /b 1
)

if "%choice%"=="6" (
    echo Building for Android Device...
    echo This requires EAS CLI
    where eas >nul 2>nul
    if %errorlevel% neq 0 (
        echo Installing EAS CLI...
        call npm install -g eas-cli
    )
    call eas build --platform android --profile development
    goto end
)

echo Invalid choice
exit /b 1

:end
echo.
echo Quick Start Complete!
echo.
echo Next Steps:
echo 1. Make sure backend is deployed and accessible
echo 2. Test voice commands: 'Hey Roadtrip, start navigation'
echo 3. Grant location and microphone permissions when prompted
echo 4. Try driving mode for the full experience
echo.
echo Troubleshooting:
echo - If voice doesn't work: Rebuild with development profile
echo - If backend connection fails: Check .env configuration
echo - If location fails: Check device settings for permissions
echo.
echo Have a great test drive!
pause