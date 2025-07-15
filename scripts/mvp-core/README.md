# MVP Core Testing Scripts

Essential scripts for validating MVP functionality. These scripts test ONLY the core features needed for launch:
- Voice navigation
- AI storytelling
- GPS tracking
- Safety features

## Scripts

### 1. `validate_mvp.py`
Checks if MVP requirements are met:
```bash
python scripts/mvp-core/validate_mvp.py
```

Validates:
- Mobile location service (not hardcoded)
- Native voice recognition setup
- Vertex AI configuration
- TTS service availability
- Deployment readiness

### 2. `test_voice_flow.py`
End-to-end test of voice command flow:
```bash
# Start backend first
cd backend && uvicorn app.main:app --reload

# Run voice flow test
python scripts/mvp-core/test_voice_flow.py
```

Tests:
- Voice command processing
- Story generation time (<3s)
- Audio URL generation
- Navigation updates

### 3. `test_core_features.py`
Comprehensive MVP feature testing:
```bash
python scripts/mvp-core/test_core_features.py
```

Tests:
- GPS tracking accuracy
- Voice recognition setup
- Story generation quality
- Audio playback readiness
- Safety feature response time

## MVP Success Criteria

All tests must pass for MVP readiness:
- ✅ Real GPS (no hardcoded coordinates)
- ✅ Native voice recognition
- ✅ Story generation <3 seconds
- ✅ Safety pause <100ms
- ✅ Works on real devices

## What's NOT Tested

These features are excluded from MVP:
- ❌ Bookings/reservations
- ❌ Commission tracking
- ❌ Games/trivia
- ❌ Music integration
- ❌ Spatial audio
- ❌ AR features
- ❌ Social sharing

## Quick MVP Check

Run all validations:
```bash
# Check everything at once
python scripts/mvp-core/validate_mvp.py && \
python scripts/mvp-core/test_core_features.py
```

If all pass, MVP is ready for real device testing!