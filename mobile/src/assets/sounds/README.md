# Sound Assets

This directory contains audio files for the application.

## Required Files

### emergency-beep.mp3
- **Purpose**: Emergency stop notification sound
- **Duration**: 0.5-1 second
- **Characteristics**: Clear, attention-grabbing beep
- **Volume**: Should be audible over road noise
- **Format**: MP3, 128kbps minimum

## Sound Guidelines

1. **Emergency Sounds**
   - Must be immediately recognizable
   - Should not startle the driver
   - Clear and distinct from other app sounds

2. **Notification Sounds**
   - Brief and non-intrusive
   - Different tones for different safety levels
   - Consistent volume levels

3. **Voice Feedback**
   - Clear speech synthesis
   - Appropriate speed for driving context
   - Minimal cognitive load

## Implementation Notes

To add the emergency beep sound:
1. Create or obtain a suitable beep sound
2. Save as `emergency-beep.mp3` in this directory
3. Ensure file size is optimized for mobile (< 100KB)
4. Test in various noise conditions