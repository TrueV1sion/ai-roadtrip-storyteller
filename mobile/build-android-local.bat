@echo off
echo ============================================
echo AI Road Trip - Android Local Build Script
echo ============================================
echo.

REM Check if we're in the mobile directory
if not exist "package.json" (
    echo Error: Not in mobile directory. Please cd to mobile folder first.
    exit /b 1
)

REM Check if Android Studio/SDK is available
where adb >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: ADB not found. Please ensure Android Studio is installed and ADB is in PATH.
    echo.
    echo Add these to your PATH:
    echo - %%LOCALAPPDATA%%\Android\Sdk\platform-tools
    echo - %%LOCALAPPDATA%%\Android\Sdk\tools
    exit /b 1
)

echo [1/6] Checking environment...
echo Node version:
node --version
echo.

REM Install dependencies if needed
if not exist "node_modules" (
    echo [2/6] Installing dependencies...
    call npm install
) else (
    echo [2/6] Dependencies already installed
)

echo.
echo [3/6] Running Expo prebuild for Android...
echo This will generate the android folder with native code...
echo.

REM Clean previous build if exists
if exist "android" (
    echo Cleaning previous Android build...
    rmdir /s /q android
)

REM Run prebuild
call npx expo prebuild --platform android --clean

if %errorlevel% neq 0 (
    echo Error: Expo prebuild failed
    exit /b 1
)

echo.
echo [4/6] Building Android APK...
echo This may take several minutes on first build...
echo.

cd android

REM Check if gradlew.bat exists
if not exist "gradlew.bat" (
    echo Error: gradlew.bat not found in android directory
    cd ..
    exit /b 1
)

REM Build debug APK
call gradlew.bat assembleDebug

if %errorlevel% neq 0 (
    echo Error: Android build failed
    cd ..
    exit /b 1
)

cd ..

echo.
echo [5/6] Build completed successfully!
echo.

REM Check if device is connected
adb devices | findstr /r "device$" >nul
if %errorlevel% neq 0 (
    echo No Android device connected via USB.
    echo.
    echo To install the app:
    echo 1. Connect your Android device via USB
    echo 2. Enable USB debugging in Developer Options
    echo 3. Run: adb install android\app\build\outputs\apk\debug\app-debug.apk
    echo.
    echo APK location: %cd%\android\app\build\outputs\apk\debug\app-debug.apk
) else (
    echo [6/6] Installing on connected device...
    adb install -r android\app\build\outputs\apk\debug\app-debug.apk
    
    if %errorlevel% eq 0 (
        echo.
        echo ✅ Success! App installed on device.
        echo.
        echo Starting the app...
        adb shell am start -n com.roadtrip.app/.MainActivity
    ) else (
        echo.
        echo Installation failed. Please install manually:
        echo adb install android\app\build\outputs\apk\debug\app-debug.apk
    )
)

echo.
echo ============================================
echo Build Summary:
echo - APK: android\app\build\outputs\apk\debug\app-debug.apk
echo - Package: com.roadtrip.app
echo - Build type: Debug
echo ============================================
echo.
echo Next steps:
echo 1. Make sure your device has granted all permissions
echo 2. Update .env with your computer's IP for API connection
echo 3. Test voice commands: "Hey Roadtrip"
echo.
pause