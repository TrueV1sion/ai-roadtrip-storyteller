# AI Road Trip - Test Drive Troubleshooting Guide

## Common Issues & Solutions

### 1. Voice Recognition Not Working

#### Symptoms:
- "Hey Roadtrip" wake word not detected
- Voice commands not recognized
- No microphone indicator

#### Solutions:

**For Expo Go:**
```bash
# Voice recognition requires a development build
# Expo Go doesn't support react-native-voice

# Create development build:
eas build --platform ios --profile development
# or
eas build --platform android --profile development
```

**Permission Issues:**
- iOS: Settings > Privacy > Microphone > Allow AI Road Trip
- Android: Settings > Apps > AI Road Trip > Permissions > Microphone

**Test Voice Setup:**
```javascript
// Add to your test screen
import Voice from '@react-native-voice/voice';

const testVoice = async () => {
  try {
    const available = await Voice.isAvailable();
    console.log('Voice available:', available);
  } catch (error) {
    console.error('Voice test error:', error);
  }
};
```

### 2. Location Permission Denied

#### Solutions:

**iOS:**
1. Settings > Privacy & Security > Location Services
2. Find "AI Road Trip" or "Expo Go"
3. Select "While Using App" or "Always"

**Android:**
1. Settings > Apps > AI Road Trip
2. Permissions > Location
3. Allow all the time

**Code Fix:**
```javascript
// Force permission request
import * as Location from 'expo-location';

const requestLocationPermission = async () => {
  const { status } = await Location.requestForegroundPermissionsAsync();
  if (status !== 'granted') {
    alert('Location permission is required for this app to work');
  }
};
```

### 3. Backend Connection Failed

#### Symptoms:
- "Network request failed"
- "Cannot connect to server"
- Stories not loading

#### Quick Checks:
```bash
# Test backend health
curl https://roadtrip-mvp-792001900150.us-central1.run.app/health

# Should return:
# {"status":"healthy","timestamp":"..."}
```

#### Solutions:

**Update .env:**
```env
# Make sure this URL is correct
EXPO_PUBLIC_API_URL=https://roadtrip-mvp-792001900150.us-central1.run.app

# For physical device on same network
EXPO_PUBLIC_DEV_API_URL=http://YOUR_COMPUTER_IP:8000
```

**Enable Mock Mode:**
```env
# Fallback to mock data
EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=true
EXPO_PUBLIC_MVP_MODE=true
```

### 4. Audio Not Playing

#### Solutions:

**Check Audio Session:**
```javascript
// Add to App.tsx
import { Audio } from 'expo-av';

useEffect(() => {
  Audio.setAudioModeAsync({
    allowsRecordingIOS: false,
    playsInSilentModeIOS: true,
    staysActiveInBackground: true,
    shouldDuckAndroid: true,
  });
}, []);
```

**Volume Check:**
- Ensure device volume is up
- Check if phone is in silent mode
- Test with a simple sound first

### 5. App Crashes on Launch

#### Debug Steps:

**1. Check Logs:**
```bash
# For Metro bundler errors
npx react-native log-ios
# or
npx react-native log-android

# For Expo logs
expo diagnostics
```

**2. Clear Everything:**
```bash
# Nuclear option - clear all caches
rm -rf node_modules
rm -rf .expo
rm package-lock.json
npm install
npx expo start -c
```

**3. Check Dependencies:**
```bash
# Verify all dependencies are installed
npm ls @react-native-voice/voice
npm ls expo-location
npm ls expo-av
```

### 6. Stories Not Triggering While Driving

#### Solutions:

**1. Check Location Updates:**
```javascript
// Add debug logging
const [debugInfo, setDebugInfo] = useState({});

Location.watchPositionAsync(
  {
    accuracy: Location.Accuracy.High,
    timeInterval: 5000,
    distanceInterval: 10,
  },
  (location) => {
    setDebugInfo({
      lat: location.coords.latitude,
      lng: location.coords.longitude,
      speed: location.coords.speed,
      timestamp: new Date().toISOString()
    });
  }
);
```

**2. Lower Story Trigger Threshold:**
```javascript
// In testDrive.ts
STORY_TRIGGER_RADIUS: 1000, // Increase from 500m to 1km
MIN_DISTANCE_BETWEEN_STORIES: 500, // Decrease from 1000m
```

### 7. Performance Issues

#### Solutions:

**1. Enable Performance Mode:**
```javascript
// In .env
EXPO_PUBLIC_REDUCE_ANIMATIONS=true
EXPO_PUBLIC_BATTERY_SAVER=true
```

**2. Reduce API Calls:**
```javascript
// Increase cache duration
EXPO_PUBLIC_CACHE_DURATION=14400000 // 4 hours
```

**3. Monitor Performance:**
```javascript
// Add to your screen
import { PerformanceMonitor } from '@/utils/performanceMonitor';

useEffect(() => {
  PerformanceMonitor.startMonitoring();
  return () => PerformanceMonitor.stopMonitoring();
}, []);
```

### 8. Physical Device Testing Issues

#### Cannot Connect to Development Server:

**1. Same Network Check:**
```bash
# On your computer
ifconfig | grep inet  # Mac/Linux
ipconfig | findstr IPv4  # Windows

# Ping from phone browser
http://YOUR_COMPUTER_IP:19000
```

**2. Firewall Issues:**
- Disable firewall temporarily
- Allow ports 8000, 19000, 19001

**3. Use Tunnel:**
```bash
# Bypass network issues
npx expo start --tunnel
```

### 9. Build Failures

#### EAS Build Failed:

**1. Check Credentials:**
```bash
eas credentials
```

**2. Clear Build Cache:**
```bash
eas build --clear-cache --platform ios
```

**3. Check app.config.js:**
- Ensure bundle identifier is unique
- Verify all plugins are installed

### 10. Emergency Fixes

#### App Won't Respond:
1. Force quit the app
2. Restart your device
3. Reinstall the app

#### Stuck Loading:
```javascript
// Add timeout to API calls
const timeout = new Promise((_, reject) =>
  setTimeout(() => reject(new Error('Request timeout')), 30000)
);

const apiCall = fetch(url);
const response = await Promise.race([apiCall, timeout]);
```

#### Voice Loop:
- Say "Hey Roadtrip, emergency"
- Force quit if needed
- Disable continuous listening in config

## Quick Debug Checklist

```bash
# 1. Backend accessible?
curl https://roadtrip-mvp-792001900150.us-central1.run.app/health

# 2. Permissions granted?
# Check device settings

# 3. Latest code?
git pull && npm install

# 4. Clean build?
npx expo start -c

# 5. Correct environment?
cat .env | grep API_URL

# 6. Dependencies installed?
npm ls --depth=0
```

## Contact Support

If issues persist:
1. Check logs: `expo diagnostics`
2. Save error screenshots
3. Note your device model and OS version
4. Document steps to reproduce

Remember: The app has mock data fallback, so basic functionality should work even without backend connection.