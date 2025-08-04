@echo off
echo ============================================
echo AI Road Trip - Clean Android Build
echo ============================================
echo.

REM Check if we're in the mobile directory
if not exist "package.json" (
    echo Error: Not in mobile directory. Please run from mobile folder.
    exit /b 1
)

echo [1/7] Cleaning existing Android build...

REM Force remove android directory
if exist "android" (
    echo Removing android directory...
    REM Try to remove normally first
    rmdir /s /q android 2>nul
    
    REM If that fails, force it
    if exist "android" (
        echo Using force delete...
        REM Take ownership and remove
        takeown /f android /r /d y >nul 2>&1
        icacls android /grant administrators:F /t >nul 2>&1
        rmdir /s /q android 2>nul
        
        REM If still exists, rename and delete later
        if exist "android" (
            echo Renaming old android folder...
            move android android_old_%random% >nul 2>&1
        )
    )
)

echo [2/7] Installing dependencies...
call npm install

echo.
echo [3/7] Running Expo prebuild...
echo Generating Android project files...
echo.

REM Set environment to avoid interactive prompts
set CI=true

REM Run prebuild without clean flag since we manually cleaned
call npx expo prebuild --platform android

if %errorlevel% neq 0 (
    echo.
    echo Prebuild failed. Trying alternative approach...
    REM Try with npm flag
    call npx expo prebuild --platform android --npm
    
    if %errorlevel% neq 0 (
        echo Error: Could not generate Android project
        exit /b 1
    )
)

echo.
echo [4/7] Verifying Android project...

if not exist "android\gradlew.bat" (
    echo Error: Android project not generated properly
    exit /b 1
)

echo Android project generated successfully!

echo.
echo [5/7] Building APK...
echo This will take several minutes on first build...
echo.

cd android

REM Make gradlew executable
attrib +x gradlew.bat >nul 2>&1

REM Clean and build
echo Cleaning gradle cache...
call gradlew.bat clean

echo Building debug APK...
call gradlew.bat assembleDebug

if %errorlevel% neq 0 (
    echo.
    echo Build failed. Trying with stacktrace...
    call gradlew.bat assembleDebug --stacktrace
    cd ..
    exit /b 1
)

cd ..

echo.
echo [6/7] APK built successfully!
echo.

set APK_PATH=android\app\build\outputs\apk\debug\app-debug.apk

if not exist "%APK_PATH%" (
    echo Error: APK not found at expected location
    exit /b 1
)

REM Get APK size
for %%A in ("%APK_PATH%") do set APK_SIZE=%%~zA
set /a APK_SIZE_MB=%APK_SIZE% / 1048576

echo APK Details:
echo - Location: %cd%\%APK_PATH%
echo - Size: %APK_SIZE_MB% MB
echo.

REM Check for connected device
adb devices 2>nul | findstr /r "device$" >nul
if %errorlevel% neq 0 (
    echo No device connected. 
    echo.
    echo To install manually:
    echo 1. Connect Android device with USB debugging enabled
    echo 2. Run: adb install "%cd%\%APK_PATH%"
    echo.
    echo Or transfer the APK file to your device and install it.
) else (
    echo [7/7] Installing on device...
    
    REM Uninstall old version first
    echo Removing old version...
    adb uninstall com.roadtrip.app >nul 2>&1
    
    REM Install new APK
    adb install -r "%APK_PATH%"
    
    if %errorlevel% eq 0 (
        echo.
        echo ✅ Installation successful!
        echo.
        
        REM Grant permissions
        echo Granting permissions...
        adb shell pm grant com.roadtrip.app android.permission.RECORD_AUDIO 2>nul
        adb shell pm grant com.roadtrip.app android.permission.ACCESS_FINE_LOCATION 2>nul
        adb shell pm grant com.roadtrip.app android.permission.ACCESS_COARSE_LOCATION 2>nul
        
        REM Start the app
        echo Starting AI Road Trip...
        adb shell am start -n com.roadtrip.app/.MainActivity
        
        echo.
        echo App launched on device!
    ) else (
        echo.
        echo Installation failed. Install manually:
        echo adb install "%cd%\%APK_PATH%"
    )
)

echo.
echo ============================================
echo Build Complete!
echo ============================================
echo.
echo Important: Update .env with your computer's IP:

REM Show IP addresses
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=1" %%b in ("%%a") do (
        echo   EXPO_PUBLIC_DEV_API_URL=http://%%b:8000
        set LAST_IP=%%b
    )
)

echo.
echo Test voice commands:
echo - "Hey Roadtrip"
echo - "Navigate to downtown"
echo - "Tell me about this area"
echo.

REM Clean up old android folders
for /d %%i in (android_old_*) do (
    rmdir /s /q "%%i" 2>nul
)

pause