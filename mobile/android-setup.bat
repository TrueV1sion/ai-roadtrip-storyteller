@echo off
echo ============================================
echo AI Road Trip - Android Device Setup
echo ============================================
echo.

REM Check if ADB is available
where adb >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: ADB not found. Please install Android Studio.
    exit /b 1
)

REM Check device connection
echo Checking for connected devices...
adb devices | findstr /r "device$" >nul
if %errorlevel% neq 0 (
    echo No device connected. Please:
    echo 1. Connect your Android device via USB
    echo 2. Enable Developer Options
    echo 3. Enable USB Debugging
    echo 4. Accept the RSA fingerprint dialog on your device
    echo.
    pause
    exit /b 1
)

echo Device connected!
echo.

REM Get device info
echo Device Information:
for /f "tokens=1" %%i in ('adb devices ^| findstr /r "device$"') do set DEVICE_ID=%%i
echo Device ID: %DEVICE_ID%
adb -s %DEVICE_ID% shell getprop ro.product.model
adb -s %DEVICE_ID% shell getprop ro.build.version.release | findstr /r "^" && echo Android Version: 

echo.
echo Setting up permissions...

REM Grant all required permissions
echo Granting location permission...
adb shell pm grant com.roadtrip.app android.permission.ACCESS_FINE_LOCATION 2>nul
adb shell pm grant com.roadtrip.app android.permission.ACCESS_COARSE_LOCATION 2>nul
adb shell pm grant com.roadtrip.app android.permission.ACCESS_BACKGROUND_LOCATION 2>nul

echo Granting microphone permission...
adb shell pm grant com.roadtrip.app android.permission.RECORD_AUDIO 2>nul

echo Granting storage permissions...
adb shell pm grant com.roadtrip.app android.permission.READ_EXTERNAL_STORAGE 2>nul
adb shell pm grant com.roadtrip.app android.permission.WRITE_EXTERNAL_STORAGE 2>nul

echo.
echo Configuring developer settings...

REM Keep screen awake while charging (useful for testing)
adb shell settings put global stay_on_while_plugged_in 3

REM Show touches (helpful for debugging)
adb shell settings put system show_touches 1

echo.
echo Getting your computer's IP address...
echo.

REM Get local IP addresses
echo Your computer's IP addresses:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=1" %%b in ("%%a") do (
        echo   - %%b
        set LAST_IP=%%b
    )
)

echo.
echo Update your mobile\.env file with:
echo EXPO_PUBLIC_DEV_API_URL=http://%LAST_IP%:8000
echo.

REM Create a test script on device
echo Creating voice test commands...
adb shell "echo 'Hey Roadtrip' > /sdcard/test_commands.txt"
adb shell "echo 'Navigate to downtown' >> /sdcard/test_commands.txt"
adb shell "echo 'Tell me about this area' >> /sdcard/test_commands.txt"

echo.
echo ============================================
echo Setup Complete!
echo ============================================
echo.
echo Next Steps:
echo 1. Build the app: build-android-local.bat
echo 2. Update .env with IP: %LAST_IP%
echo 3. Launch app and test voice
echo.
echo Test Commands:
echo - "Hey Roadtrip"
echo - "Navigate to [destination]"
echo - "Tell me about this area"
echo.
echo Troubleshooting:
echo - If voice doesn't work: Check Google app is installed
echo - If location fails: Open Google Maps first
echo - If network fails: Disable mobile data, use WiFi only
echo.
pause