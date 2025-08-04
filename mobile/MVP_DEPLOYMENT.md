# Mobile MVP Deployment Guide

## Overview
This guide covers deploying the simplified MVP version of the AI Road Trip Storyteller mobile app.

## Pre-Deployment Checklist

### Requirements
- [ ] Node.js 16+ installed
- [ ] Expo CLI installed (`npm install -g expo-cli`)
- [ ] iOS: Xcode installed (Mac only)
- [ ] Android: Android Studio installed
- [ ] Apple Developer Account (for iOS)
- [ ] Google Play Developer Account (for Android)
- [ ] Backend deployed and accessible

### Configuration
1. **Update API URL** in `src/config/api.ts`:
   ```typescript
   // Replace with your actual Cloud Run URL
   return 'https://roadtrip-mvp-xxxxx.run.app';
   ```

2. **Set Environment Variables**:
   ```bash
   # Create .env file
   EXPO_PUBLIC_MVP_MODE=true
   EXPO_PUBLIC_API_URL=https://roadtrip-mvp-xxxxx.run.app
   EXPO_PUBLIC_PLATFORM=ios  # or android
   ```

## Running MVP Version Locally

### Install Dependencies
```bash
cd mobile
npm install
```

### Start Development Server
```bash
# Run MVP version
npm run start:mvp

# Or platform specific
npm run ios:mvp      # iOS Simulator
npm run android:mvp  # Android Emulator
```

### Test on Physical Device
1. Install Expo Go app on your phone
2. Scan QR code from terminal
3. Test core features:
   - Voice recognition
   - Navigation requests
   - Story playback
   - Map display

## Building for Production

### iOS (TestFlight)

1. **Configure app.json**:
   ```json
   {
     "expo": {
       "name": "AI Road Trip MVP",
       "slug": "roadtrip-mvp",
       "version": "1.0.0",
       "ios": {
         "bundleIdentifier": "com.yourcompany.roadtrip.mvp",
         "buildNumber": "1"
       }
     }
   }
   ```

2. **Build**:
   ```bash
   npm run build:ios:mvp
   ```

3. **Upload to App Store Connect**:
   - Download .ipa file
   - Use Transporter app to upload
   - Submit for TestFlight review

### Android (Internal Testing)

1. **Configure app.json**:
   ```json
   {
     "expo": {
       "android": {
         "package": "com.yourcompany.roadtrip.mvp",
         "versionCode": 1
       }
     }
   }
   ```

2. **Build**:
   ```bash
   npm run build:android:mvp
   ```

3. **Upload to Play Console**:
   - Download .aab file
   - Upload to Internal Testing track
   - Add testers

## MVP Features to Test

### Core Functionality
1. **Voice Commands**:
   - "Navigate to [destination]"
   - "Tell me about this area"
   - "What's interesting nearby?"

2. **Map Features**:
   - Current location tracking
   - Route visualization
   - Destination markers

3. **Story Playback**:
   - Audio streaming
   - Text display
   - Pause/resume

4. **Safety Features**:
   - Auto-pause detection
   - Speed-based content filtering

### Performance Targets
- Voice recognition: <1 second
- Backend response: <3 seconds
- Audio start: <1 second
- Map updates: 60 FPS

## Troubleshooting

### Common Issues

1. **Voice Recognition Not Working**
   - Check microphone permissions
   - Verify @react-native-voice/voice is linked
   - Test on real device (not simulator)

2. **API Connection Failed**
   - Verify API URL is correct
   - Check network connectivity
   - Ensure CORS is configured on backend

3. **Location Not Updating**
   - Check location permissions
   - Verify GPS is enabled
   - Test outdoors for better signal

4. **Audio Not Playing**
   - Check audio permissions
   - Verify audio URL is HTTPS
   - Test speaker/headphone output

### Debug Commands
```bash
# View logs
expo logs

# Clear cache
expo start -c

# Check native dependencies
expo doctor
```

## Monitoring

### Crash Reporting
```javascript
// Add to App.tsx
import * as Sentry from 'sentry-expo';

Sentry.init({
  dsn: 'YOUR_SENTRY_DSN',
  enableInExpoDevelopment: false,
  debug: __DEV__,
});
```

### Analytics
```javascript
// Track key events
import * as Analytics from 'expo-firebase-analytics';

Analytics.logEvent('voice_command', {
  command_type: 'navigation',
  success: true,
});
```

## Beta Testing Guide

### TestFlight (iOS)
1. Add testers in App Store Connect
2. Send invitation emails
3. Testers install TestFlight app
4. Accept invitation and install

### Internal Testing (Android)
1. Add testers in Play Console
2. Share testing link
3. Testers join program
4. Download from Play Store

### Feedback Collection
- In-app feedback button
- Email: feedback@roadtrip-app.com
- TestFlight/Play Console feedback

## MVP Success Metrics

### Target Metrics
- Crash-free rate: >99%
- Voice success rate: >90%
- Response time: <3 seconds
- Daily active users: 10+
- Session length: >5 minutes

### Key Features to Monitor
1. Voice command success/failure
2. Story completion rate
3. Navigation accuracy
4. Audio playback issues
5. Performance on older devices

## Next Steps

### After MVP Validation
1. Enable Phase 2 features
2. Add more personalities
3. Implement booking
4. Add games and entertainment
5. Integrate music services

### Gradual Rollout
1. 10 beta testers (Week 1)
2. 100 beta testers (Week 2)
3. 1000 early access (Week 3)
4. Public launch (Week 4)

## Support

### User Support
- Email: support@roadtrip-app.com
- FAQ: https://roadtrip-app.com/faq
- In-app help

### Developer Support
- GitHub Issues
- Slack: #roadtrip-dev
- Documentation: /docs