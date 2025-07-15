# MVP Integration Test Plan - Day 4

## Overview
Complete end-to-end testing of the AI Road Trip Storyteller MVP with real devices and deployed backend.

## Pre-Testing Setup

### 1. Deploy Backend (if not already done)
```bash
cd deploy/mvp
./setup_gcp_infrastructure.sh
# Update API keys in Secret Manager
./deploy_to_cloud_run.sh
```

### 2. Get Backend URL
```bash
# Note your Cloud Run URL
SERVICE_URL=$(gcloud run services describe roadtrip-mvp --region=us-central1 --format="value(status.url)")
echo "Backend URL: $SERVICE_URL"
```

### 3. Update Mobile Configuration
```typescript
// mobile/src/config/api.ts
// Update the production URL
return 'https://roadtrip-mvp-xxxxx.run.app'; // Your actual URL
```

### 4. Prepare Test Devices
- iOS: iPhone with iOS 14+ 
- Android: Device with Android 10+
- Both devices should have:
  - GPS enabled
  - Microphone access allowed
  - Internet connection (WiFi or cellular)

## Test Scenarios

### Scenario 1: First Launch Experience
**Steps:**
1. Fresh install the app
2. Launch app
3. Accept location permission
4. Accept microphone permission

**Expected Results:**
- [ ] App launches in <3 seconds
- [ ] Map shows current location
- [ ] Voice button is visible and enabled
- [ ] No crashes or errors

**Actual Results:**
- Launch time: _____ seconds
- Permissions handled: Yes/No
- Issues: _____

### Scenario 2: Basic Voice Navigation
**Test Input:** "Navigate to the nearest Starbucks"

**Steps:**
1. Tap voice button
2. Wait for listening indicator
3. Say command clearly
4. Release button or wait for auto-stop

**Expected Results:**
- [ ] Voice recognition captures input
- [ ] "Processing..." message appears
- [ ] Response received in <3 seconds
- [ ] Story text appears with fade-in animation
- [ ] Audio starts playing automatically
- [ ] Map shows route to Starbucks

**Actual Results:**
- Recognition success: Yes/No
- Response time: _____ seconds
- Story quality: _____
- Audio played: Yes/No
- Route shown: Yes/No

### Scenario 3: Story Request
**Test Input:** "Tell me about the history of this area"

**Steps:**
1. Ensure you're in a known location
2. Tap voice button
3. Say command
4. Wait for response

**Expected Results:**
- [ ] Relevant historical story about current location
- [ ] Audio narration matches text
- [ ] No navigation route shown
- [ ] Story is engaging and accurate

**Actual Results:**
- Story relevance: _____
- Audio quality: _____
- Accuracy: _____

### Scenario 4: Safety Features
**Test:** Auto-pause during movement

**Steps:**
1. Start a story playing
2. Begin driving/walking quickly
3. Make a sharp turn or sudden stop
4. Observe audio behavior

**Expected Results:**
- [ ] Audio pauses during rapid movement
- [ ] Audio resumes when movement stabilizes
- [ ] No crashes during GPS updates

**Actual Results:**
- Auto-pause worked: Yes/No
- Resume worked: Yes/No
- Issues: _____

### Scenario 5: Error Handling
**Test A:** No Internet Connection

**Steps:**
1. Enable airplane mode
2. Try voice command
3. Observe behavior

**Expected:**
- [ ] Clear error message
- [ ] App doesn't crash
- [ ] Can retry when connected

**Test B:** Invalid Command

**Input:** "Blah blah blah"

**Expected:**
- [ ] Polite response asking for clarification
- [ ] App remains responsive

### Scenario 6: Performance Testing
**Measure these metrics:**

1. **Voice Recognition**
   - Time from tap to "Listening": _____ ms
   - Recognition accuracy: _____%

2. **Backend Response**
   - Time from input to response: _____ seconds
   - Success rate: _____%

3. **Audio Playback**
   - Time from response to audio start: _____ ms
   - Audio quality: Good/Fair/Poor

4. **Map Performance**
   - FPS during route display: _____
   - Smooth panning: Yes/No

### Scenario 7: Extended Usage
**Test:** 10-minute continuous usage

**Steps:**
1. Make 5-10 different voice requests
2. Mix navigation and story requests
3. Monitor app performance

**Track:**
- [ ] Memory usage stable
- [ ] No performance degradation
- [ ] All requests handled
- [ ] Battery usage reasonable

## Platform-Specific Tests

### iOS Specific
- [ ] Works on iPhone X and newer
- [ ] Notch/Dynamic Island doesn't block UI
- [ ] Audio plays through car Bluetooth
- [ ] Background audio handling

### Android Specific  
- [ ] Works on Android 10+
- [ ] Handles back button properly
- [ ] Audio focus management
- [ ] Various screen sizes

## Integration Points

### Backend API
Test each integration:

1. **Voice Assistant Endpoint**
   ```bash
   curl -X POST "$SERVICE_URL/api/voice-assistant/interact" \
     -H "Content-Type: application/json" \
     -d '{"user_input": "test", "context": {}}'
   ```
   - Response time: _____ ms
   - Success: Yes/No

2. **Health Check**
   ```bash
   curl "$SERVICE_URL/health"
   ```
   - Status: _____

### Google Cloud Services
Verify working:
- [ ] Cloud TTS generates audio
- [ ] Audio URLs from GCS load
- [ ] Vertex AI responses appropriate
- [ ] Maps API returns routes

## Load Testing

### Concurrent Users
Test with multiple devices simultaneously:

1. 2 devices making requests
2. 5 devices making requests  
3. 10 devices making requests

**Measure:**
- Response time degradation
- Error rate
- Backend scaling

## Bug Report Template

### Bug #___
**Description:**

**Steps to Reproduce:**
1.
2.
3.

**Expected:**

**Actual:**

**Device:** iPhone/Android ___
**OS Version:** ___
**App Version:** 1.0.0-mvp
**Backend URL:** ___

**Severity:** Critical/High/Medium/Low

**Screenshot/Video:** [Attach]

## Performance Benchmarks

### Target Metrics
| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| App Launch | <3s | ___s | __ |
| Voice Recognition | <1s | ___s | __ |
| Backend Response | <3s | ___s | __ |
| Audio Start | <1s | ___s | __ |
| Crash Rate | <0.1% | ___% | __ |
| Success Rate | >90% | ___% | __ |

### User Experience Metrics
| Metric | Target | Actual | Pass/Fail |
|--------|--------|--------|-----------|
| Story Relevance | >80% | ___% | __ |
| Voice Accuracy | >95% | ___% | __ |
| Audio Quality | Good | ___ | __ |
| Map Accuracy | 100% | ___% | __ |

## Test Completion Checklist

### Core Features
- [ ] Voice navigation works E2E
- [ ] Stories are relevant and engaging
- [ ] Audio plays reliably
- [ ] Map shows accurate routes
- [ ] Safety features activate

### Performance
- [ ] All responses <3 seconds
- [ ] No memory leaks
- [ ] Smooth UI animations
- [ ] Stable over time

### Edge Cases
- [ ] Handles errors gracefully
- [ ] Works offline (appropriate errors)
- [ ] Recovers from failures
- [ ] Permissions handled well

### Ready for Beta?
- [ ] Zero critical bugs
- [ ] <3 high severity bugs
- [ ] Performance meets targets
- [ ] UX is delightful

## Sign-off

**Tested by:** _____________
**Date:** _____________
**Version:** Backend _____ / Mobile _____
**Result:** PASS / FAIL

**Notes:**

**Recommendation:** Ready for Beta / Needs Fixes

## Next Steps
If PASS → Proceed to Day 5 (Beta Deployment)
If FAIL → Fix critical issues, retest