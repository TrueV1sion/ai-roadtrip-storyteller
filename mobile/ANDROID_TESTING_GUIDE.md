# AI Road Trip - Complete Android Testing Guide

## Quick Start for Android

### Prerequisites
- ✅ Android Studio installed
- ✅ Android device with Developer Mode enabled
- ✅ USB Debugging enabled on device
- ✅ Device connected via USB cable

## Step-by-Step Build & Install

### 1. Run the Build Script
```cmd
cd mobile
clean-and-build-android.bat
```

This script will:
- Clean any existing Android build
- Generate native Android project
- Build the APK
- Install on connected device
- Grant permissions automatically

### 2. Manual Build (if script fails)
```cmd
cd mobile

# Clean existing build
rmdir /s /q android

# Generate Android project
npx expo prebuild --platform android

# Build APK
cd android
gradlew.bat assembleDebug

# Install on device
adb install app\build\outputs\apk\debug\app-debug.apk
```

### 3. Update Network Configuration

Find your computer's IP:
```cmd
ipconfig | findstr IPv4
```

Update `mobile\.env`:
```env
# Replace with your IP
EXPO_PUBLIC_DEV_API_URL=http://192.168.1.XXX:8000
```

## Android-Specific Setup

### Enable All Permissions
When the app launches, grant:
1. **Location** - "Allow all the time"
2. **Microphone** - Allow
3. **Physical Activity** - Allow (for motion detection)

### Voice Recognition Setup
Android uses Google's speech recognition. Ensure:
- Google app is installed and updated
- "Hey Google" detection is working
- Device language is set to English (US)

### Battery Optimization
For best performance:
1. Settings > Apps > AI Road Trip
2. Battery > Unrestricted
3. Allow background activity

## Testing Voice Commands

### Basic Test Flow
1. Launch app
2. Wait for "Listening..." indicator
3. Say "Hey Roadtrip"
4. Wait for response tone
5. Give command: "Navigate to downtown"

### Voice Commands to Test
```
"Hey Roadtrip" (wake word)
"Navigate to [place]"
"Tell me about this area"
"What's interesting nearby"
"Change voice to Morgan Freeman"
"Pause stories"
"Resume stories"
```

### Troubleshooting Voice

#### Voice Not Working
```cmd
# Check if Google Speech services installed
adb shell pm list packages | findstr speech

# Clear Google app cache
adb shell pm clear com.google.android.googlequicksearchbox

# Test microphone
adb shell am start -a android.speech.action.RECOGNIZE_SPEECH
```

#### Permission Issues
```cmd
# Grant all permissions via ADB
adb shell pm grant com.roadtrip.app android.permission.RECORD_AUDIO
adb shell pm grant com.roadtrip.app android.permission.ACCESS_FINE_LOCATION
adb shell pm grant com.roadtrip.app android.permission.ACCESS_BACKGROUND_LOCATION
```

## Running Development Server

### Start Metro Bundler
```cmd
cd mobile
npx react-native start --reset-cache
```

### Connect to Development Server
1. Ensure device and computer on same WiFi
2. Open app on device
3. Shake device to open dev menu
4. Settings > Debug server host
5. Enter: `YOUR_IP:8081`

## Debugging Tools

### View Logs
```cmd
# All app logs
adb logcat | findstr roadtrip

# React Native logs only
npx react-native log-android

# Errors only
adb logcat *:E
```

### Performance Monitoring
```cmd
# Check memory usage
adb shell dumpsys meminfo com.roadtrip.app

# Check battery usage
adb shell dumpsys batterystats | findstr roadtrip
```

## Common Android Issues

### Issue 1: Build Fails
```cmd
# Clean everything
cd android
gradlew.bat clean
cd ..
npx expo prebuild --platform android --clear
```

### Issue 2: App Crashes on Launch
```cmd
# Check crash logs
adb logcat -b crash

# Common fix: Clear app data
adb shell pm clear com.roadtrip.app
```

### Issue 3: Network Connection Failed
- Disable mobile data, use WiFi only
- Check firewall isn't blocking port 8000
- Try using ngrok for tunneling:
  ```cmd
  ngrok http 8000
  # Use ngrok URL in .env
  ```

### Issue 4: Voice Recognition Fails
- Install Google app if missing
- Update Google Play Services
- Try in quiet environment first
- Check microphone with voice recorder

## Testing Checklist

### Pre-Drive Test (5 min)
- [ ] App launches without crash
- [ ] Permissions granted
- [ ] Voice wake word responds
- [ ] Location services active
- [ ] Can connect to backend

### Stationary Test (10 min)
- [ ] All voice commands work
- [ ] Mock stories play
- [ ] UI is responsive
- [ ] Settings accessible
- [ ] No memory leaks

### Drive Test (30 min)
- [ ] Mount phone securely
- [ ] Connect Bluetooth audio
- [ ] Test navigation commands
- [ ] Verify story triggers
- [ ] Monitor battery usage

## Android Auto Integration (Optional)

To test with Android Auto:

1. Install Android Auto app
2. Enable developer settings in Android Auto
3. Add to `AndroidManifest.xml`:
```xml
<uses-feature
    android:name="android.hardware.type.automotive"
    android:required="false" />
```

## Build Variants

### Debug Build (Development)
```cmd
gradlew.bat assembleDebug
```

### Release Build (Testing)
```cmd
gradlew.bat assembleRelease
```

### Bundle for Play Store
```cmd
gradlew.bat bundleRelease
```

## Useful ADB Commands

```cmd
# Install APK
adb install -r app-debug.apk

# Uninstall app
adb uninstall com.roadtrip.app

# Start app
adb shell am start -n com.roadtrip.app/.MainActivity

# Force stop app
adb shell am force-stop com.roadtrip.app

# Take screenshot
adb shell screencap /sdcard/screenshot.png
adb pull /sdcard/screenshot.png

# Record screen
adb shell screenrecord /sdcard/demo.mp4
# Press Ctrl+C to stop
adb pull /sdcard/demo.mp4
```

## Ready to Test!

1. Run `clean-and-build-android.bat`
2. Update `.env` with your IP
3. Launch app on device
4. Test "Hey Roadtrip"
5. Go for a test drive!

Remember: Safety first - mount device securely and use voice commands only while driving.