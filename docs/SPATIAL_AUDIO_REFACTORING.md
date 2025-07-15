# Spatial Audio Engine Refactoring Guide

## Overview

The spatial audio engine has been refactored from a single 1570-line file into a modular architecture with specialized components. This improves maintainability, testability, and performance.

## Architecture Changes

### Before (Monolithic)
```
spatial_audio_engine.py (1570 lines)
├── All sound definitions
├── Binaural processing
├── Ambient generation
├── Audio mixing
├── Effects processing
└── Scene orchestration
```

### After (Modular)
```
spatial_audio_engine_v2.py (400 lines) - Main orchestrator
├── audio/
│   ├── sound_library.py (100 lines) - Sound definitions
│   ├── binaural_processor.py (350 lines) - 3D audio processing
│   ├── ambient_generator.py (380 lines) - Soundscape generation
│   └── audio_mixer.py (400 lines) - Mixing and effects
```

## Migration Steps

### 1. Update Imports

Replace old imports:
```python
# Old
from backend.app.services.spatial_audio_engine import SpatialAudioEngine

# New
from backend.app.services.spatial_audio_engine_v2 import SpatialAudioEngineV2
```

### 2. Update Dependency Injection

```python
# Old
@router.post("/generate-audio")
async def generate_audio(
    engine: SpatialAudioEngine = Depends(get_spatial_audio_engine)
):
    ...

# New
@router.post("/generate-audio")
async def generate_audio(
    engine: SpatialAudioEngineV2 = Depends(get_spatial_audio_engine)
):
    ...
```

### 3. API Changes

#### Generate Ambient Soundscape
```python
# Old
result = await engine.generate_ambient_soundscape(
    environment_type="forest",
    weather_conditions={"type": "rain"},
    time_of_day="morning",
    activity_level=0.7
)

# New
result = await engine.generate_spatial_scene(
    environment="forest",
    context={
        "weather": "rain",
        "time_of_day": "morning",
        "activity_level": 0.7
    }
)
```

#### Environment Transitions
```python
# Old
transition = await engine.generate_transition_soundscape(
    from_environment="city",
    to_environment="forest",
    transition_duration=5.0
)

# New
transition = await engine.generate_environment_transition(
    from_env="city",
    to_env="forest",
    duration=5.0
)
```

## Benefits

### 1. Improved Maintainability
- Each module has a single responsibility
- Easier to locate and fix bugs
- Reduced cognitive load

### 2. Better Testing
- Can unit test each component independently
- Mock dependencies easily
- Faster test execution

### 3. Performance
- Lazy loading of components
- Better caching strategies per module
- Parallel processing opportunities

### 4. Extensibility
- Easy to add new sound types
- Simple to implement new effects
- Clear interfaces for extensions

## Testing the Refactored Code

### Unit Tests
```python
# Test individual components
def test_binaural_processor():
    processor = BinauralProcessor()
    left, right = processor.apply_hrtf(
        audio_data=test_audio,
        azimuth=45,
        elevation=0,
        distance=5
    )
    assert len(left) == len(test_audio)
    assert len(right) == len(test_audio)

def test_ambient_generator():
    library = SoundLibrary()
    generator = AmbientGenerator(library)
    soundscape = await generator.generate_soundscape(
        environment="forest",
        weather="sunny"
    )
    assert soundscape["environment"] == "forest"
    assert len(soundscape["layers"]) > 0
```

### Integration Tests
```python
# Test the complete pipeline
async def test_spatial_scene_generation():
    engine = SpatialAudioEngineV2(mock_db)
    scene = await engine.generate_spatial_scene(
        environment="beach",
        duration=10.0
    )
    assert scene["duration"] == 10.0
    assert scene["processing_info"]["binaural"] is True
```

## Rollback Plan

If issues arise:

1. Keep the old `spatial_audio_engine.py` file temporarily
2. Use feature flags to switch between implementations:
```python
if settings.USE_NEW_AUDIO_ENGINE:
    from .spatial_audio_engine_v2 import SpatialAudioEngineV2 as SpatialAudioEngine
else:
    from .spatial_audio_engine import SpatialAudioEngine
```

3. Monitor performance and error rates
4. Gradually migrate endpoints

## Performance Considerations

### Memory Usage
- Old: Single large object in memory
- New: Components loaded as needed

### Processing Time
- Old: All processing in one pass
- New: Can parallelize component processing

### Caching
- Old: Cache entire scenes
- New: Cache at component level for better hit rates

## Future Enhancements

1. **Plugin Architecture**: Allow third-party sound libraries
2. **GPU Acceleration**: Use CUDA for audio processing
3. **Real-time Processing**: Stream processing for live audio
4. **AI Enhancement**: ML-based soundscape generation

## Checklist

- [ ] Update all imports in codebase
- [ ] Run unit tests for each component
- [ ] Run integration tests
- [ ] Update API documentation
- [ ] Performance benchmarking
- [ ] Deploy with feature flag
- [ ] Monitor error rates
- [ ] Remove old implementation after stability confirmed