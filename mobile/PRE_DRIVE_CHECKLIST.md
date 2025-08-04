# AI Road Trip - Pre-Drive Test Checklist

## Before You Leave

### 🔋 Device Preparation
- [ ] **Phone fully charged** (100% recommended)
- [ ] **Car charger available** (for longer drives)
- [ ] **Phone mount installed** (hands-free is essential)
- [ ] **Bluetooth connected** to car audio system
- [ ] **Do Not Disturb** mode OFF (app needs notifications)
- [ ] **Screen timeout** set to "Never" or 10+ minutes

### 📱 App Setup
- [ ] **App installed** and launches without errors
- [ ] **Backend accessible**: 
  ```bash
  curl https://roadtrip-mvp-792001900150.us-central1.run.app/health
  ```
- [ ] **Permissions granted**:
  - ✅ Location (Always or While Using App)
  - ✅ Microphone
  - ✅ Speech Recognition
  - ✅ Background App Refresh (iOS)

### 🗺️ Route Planning
- [ ] **Test route selected** (start with familiar 15-20 min route)
- [ ] **Offline maps downloaded** (if available in your map app)
- [ ] **Backup navigation ready** (Google Maps/Apple Maps)
- [ ] **Key destinations noted**:
  - Start point: ________________
  - Test destination: ________________
  - Interesting landmarks along route: ________________

### 🎙️ Voice Setup Test
- [ ] **Wake word test**: Say "Hey Roadtrip" (should respond)
- [ ] **Basic commands tested**:
  ```
  "Hey Roadtrip, hello"
  "Hey Roadtrip, what can you do"
  "Hey Roadtrip, tell me a story"
  ```
- [ ] **Audio output verified** (can hear responses)
- [ ] **Voice personality selected** (if prompted)

### 🔧 Technical Checks
- [ ] **API connection verified**:
  - Stories load
  - Voice commands work
  - No network errors
- [ ] **Location services working**:
  - Current location shown
  - GPS accuracy good
- [ ] **Mock mode ready** (in case of connection issues):
  ```env
  EXPO_PUBLIC_ENABLE_MOCK_FALLBACK=true
  ```

### 🚗 In-Car Setup
- [ ] **Phone mounted** at eye level
- [ ] **Audio connected** (Bluetooth/AUX)
- [ ] **Volume adjusted** (test before driving)
- [ ] **Screen brightness** appropriate
- [ ] **Air vent** not blowing on phone (overheating prevention)

## Quick Start Commands

Once everything is checked, here are the commands to start:

1. **Launch the app**
2. **Start navigation**: "Hey Roadtrip, navigate to [destination]"
3. **Test story**: "Hey Roadtrip, tell me about this area"
4. **Adjust volume**: "Hey Roadtrip, louder/quieter"

## During the Drive

### Monitor These:
- [ ] Voice recognition success rate
- [ ] Story trigger frequency (every 2-3 minutes ideal)
- [ ] Navigation accuracy
- [ ] Audio quality and volume
- [ ] Battery drain rate
- [ ] Temperature (phone not overheating)

### Test These Features:
- [ ] Wake word detection while driving
- [ ] Story interruption and resumption
- [ ] Navigation rerouting
- [ ] Different voice personalities
- [ ] Offline mode (if connection drops)

### Note Any Issues:
- [ ] Commands that didn't work: ________________
- [ ] Areas with no stories: ________________
- [ ] Connection dead zones: ________________
- [ ] UI/UX difficulties: ________________

## Emergency Procedures

### If App Becomes Unresponsive:
1. Say "Hey Roadtrip, emergency"
2. Pull over safely
3. Force quit app
4. Restart if needed

### If Voice Commands Stop Working:
1. Check microphone indicator
2. Increase volume
3. Use manual controls
4. Switch to backup navigation

### Safety First:
- **Never** interact with screen while driving
- **Always** use voice commands
- **Pull over** if manual interaction needed
- **Have backup** navigation ready

## Post-Drive Review

### Data to Collect:
- [ ] Total drive time: ________________
- [ ] Number of stories heard: ________________
- [ ] Voice command success rate: _____%
- [ ] Battery used: _____%
- [ ] Data used: ____MB
- [ ] Overall experience rating: ___/10

### Log Files Location:
```javascript
// Check console logs
Settings > About > Logs

// Or in app
Developer Settings > Export Logs
```

### Feedback Notes:
- What worked well: ________________
- What needs improvement: ________________
- Feature requests: ________________
- Bugs encountered: ________________

## Ready to Drive?

If all items are checked:
1. Take a deep breath
2. Start your engine
3. Say "Hey Roadtrip, let's go!"
4. Enjoy your AI-powered journey! 🚗✨

Remember: This is a test drive. Focus on safety first, and don't hesitate to pull over if you need to troubleshoot anything.