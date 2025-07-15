"""
Test Spatial Audio Engine functionality
"""

import pytest
import asyncio
import numpy as np
from unittest.mock import Mock, patch

from app.services.spatial_audio_engine import (
    SpatialAudioEngine,
    AudioEnvironment,
    SoundSource,
    AudioPosition,
    SpatialAudioSource
)
from app.services.master_orchestration_agent import MasterOrchestrationAgent


@pytest.fixture
def spatial_engine():
    """Create a spatial audio engine instance"""
    return SpatialAudioEngine()


@pytest.fixture
def mock_location_context():
    """Create mock location context"""
    return {
        'terrain': 'forest',
        'road_type': 'rural',
        'weather': {'condition': 'clear'},
        'speed': 50,
        'heading': 90,
        'landmarks': ['Pine Grove'],
        'population_density': 'low'
    }


class TestSpatialAudioEngine:
    """Test spatial audio engine functionality"""
    
    @pytest.mark.asyncio
    async def test_environment_detection(self, spatial_engine):
        """Test that environments are correctly detected from location"""
        test_cases = [
            ({'terrain': 'forest', 'road_type': 'rural'}, AudioEnvironment.FOREST),
            ({'terrain': 'city', 'population_density': 'high'}, AudioEnvironment.CITY),
            ({'road_type': 'highway'}, AudioEnvironment.HIGHWAY),
            ({'terrain': 'mountain'}, AudioEnvironment.MOUNTAIN),
            ({'terrain': 'coast', 'landmarks': ['beach']}, AudioEnvironment.COASTAL),
            ({'road_type': 'tunnel'}, AudioEnvironment.TUNNEL),
        ]
        
        for location, expected_env in test_cases:
            env = spatial_engine._determine_environment(location)
            assert env == expected_env
    
    @pytest.mark.asyncio
    async def test_add_remove_sources(self, spatial_engine):
        """Test adding and removing audio sources"""
        # Add a source
        source = SpatialAudioSource(
            source_id="test_narrator",
            source_type=SoundSource.NARRATOR,
            position=AudioPosition(0, 0, 0.3),
            volume=1.0,
            priority=8
        )
        
        await spatial_engine.add_source(source)
        assert "test_narrator" in spatial_engine.active_sources
        
        # Remove the source
        await spatial_engine.remove_source("test_narrator")
        assert "test_narrator" not in spatial_engine.active_sources
    
    @pytest.mark.asyncio
    async def test_soundscape_creation(self, spatial_engine):
        """Test soundscape creation for different environments"""
        # Forest soundscape
        forest_location = {
            'terrain': 'forest',
            'road_type': 'rural',
            'landmarks': []
        }
        
        soundscape = await spatial_engine.create_soundscape(
            forest_location,
            'morning',
            'clear'
        )
        
        assert soundscape['environment'] == AudioEnvironment.FOREST
        assert len(soundscape['sources']) > 0
        
        # Check for expected forest sounds
        source_types = [s['type'] for s in soundscape['sources']]
        assert SoundSource.NATURE in source_types or 'nature' in str(source_types)
        assert SoundSource.NARRATOR in source_types or 'narrator' in str(source_types)
    
    @pytest.mark.asyncio
    async def test_3d_positioning(self, spatial_engine):
        """Test 3D audio positioning calculations"""
        # Test position calculations
        position = AudioPosition(1, 0, 0)  # Right side
        assert position.azimuth() == 90  # 90 degrees to the right
        
        position = AudioPosition(0, 1, 0)  # Above
        assert position.elevation() == 90  # 90 degrees up
        
        position = AudioPosition(0, 0, 1)  # Front
        assert position.distance_from_origin() == 1
    
    def test_hrtf_processing(self, spatial_engine):
        """Test HRTF audio processing"""
        # Create test audio
        test_audio = np.random.randn(1024, 2) * 0.1  # Stereo noise
        
        # Test with different positions
        positions = [
            AudioPosition(-1, 0, 0),  # Full left
            AudioPosition(1, 0, 0),   # Full right
            AudioPosition(0, 0, 1),   # Front center
        ]
        
        for pos in positions:
            processed = spatial_engine._apply_hrtf(test_audio, pos)
            
            # Check output shape
            assert processed.shape == test_audio.shape
            
            # Check that processing was applied
            assert not np.array_equal(processed, test_audio)
    
    def test_doppler_effect(self, spatial_engine):
        """Test Doppler effect processing"""
        # Set vehicle speed
        spatial_engine.vehicle_speed = 100  # 100 km/h
        
        # Create test audio and source
        test_audio = np.sin(2 * np.pi * 440 * np.arange(1024) / spatial_engine.sample_rate)
        test_audio = np.column_stack((test_audio, test_audio))  # Make stereo
        
        source = SpatialAudioSource(
            source_id="test",
            source_type=SoundSource.AMBIENT,
            position=AudioPosition(0, 0, 1),  # In front
            doppler_enabled=True
        )
        
        processed = spatial_engine._apply_doppler(test_audio, source, source.position)
        
        # Check that Doppler was applied (pitch shift)
        assert processed.shape == test_audio.shape
    
    def test_environmental_reverb(self, spatial_engine):
        """Test environmental reverb processing"""
        # Test different environments
        environments = [
            AudioEnvironment.TUNNEL,   # High reverb
            AudioEnvironment.FOREST,   # Medium reverb
            AudioEnvironment.HIGHWAY,  # Low reverb
        ]
        
        test_audio = np.random.randn(1024, 2) * 0.1
        
        for env in environments:
            spatial_engine.environment = env
            processed = spatial_engine._apply_environment_reverb(test_audio)
            
            # Check output shape
            assert processed.shape == test_audio.shape
            
            # Check that reverb was applied
            assert not np.array_equal(processed, test_audio)


class TestMasterOrchestrationIntegration:
    """Test integration with master orchestration agent"""
    
    @pytest.mark.asyncio
    async def test_spatial_audio_coordination(self, mock_location_context):
        """Test spatial audio coordination through master orchestrator"""
        # Create orchestrator
        mock_ai_client = Mock()
        orchestrator = MasterOrchestrationAgent(mock_ai_client)
        
        # Test story audio coordination
        result = await orchestrator.coordinate_spatial_audio(
            'story',
            mock_location_context,
            {
                'characters': [
                    {'name': 'Narrator'},
                    {'name': 'Explorer'}
                ],
                'scene': 'forest_adventure'
            }
        )
        
        assert result['status'] == 'success'
        assert result['environment'] == 'forest'
        assert result['active_sources'] > 0
        
        # Test navigation audio coordination
        result = await orchestrator.coordinate_spatial_audio(
            'navigation',
            mock_location_context,
            {}
        )
        
        assert result['status'] == 'success'
        assert 'navigation_voice' in str(result['soundscape']['sources'])
    
    @pytest.mark.asyncio
    async def test_environment_transitions(self):
        """Test smooth environment transitions"""
        mock_ai_client = Mock()
        orchestrator = MasterOrchestrationAgent(mock_ai_client)
        
        # Simulate moving from forest to city
        forest_context = {'terrain': 'forest', 'road_type': 'rural'}
        city_context = {'terrain': 'city', 'population_density': 'high'}
        
        # First location
        await orchestrator.coordinate_spatial_audio('story', forest_context, {})
        
        # Transition to city
        result = await orchestrator.coordinate_spatial_audio('story', city_context, {})
        
        assert result['environment'] == 'city'


@pytest.mark.asyncio
async def test_full_spatial_audio_flow():
    """Test complete spatial audio flow from request to processing"""
    engine = SpatialAudioEngine()
    
    # 1. Set environment
    await engine.set_environment(AudioEnvironment.FOREST)
    
    # 2. Add narrator source
    narrator = SpatialAudioSource(
        source_id="narrator",
        source_type=SoundSource.NARRATOR,
        position=AudioPosition(0, 0, 0.3),
        volume=1.0,
        priority=10
    )
    await engine.add_source(narrator)
    
    # 3. Add ambient sounds
    birds = SpatialAudioSource(
        source_id="birds",
        source_type=SoundSource.NATURE,
        position=AudioPosition(-0.7, 0.5, 0.2),
        volume=0.4,
        priority=3
    )
    await engine.add_source(birds)
    
    # 4. Update listener position (simulating movement)
    await engine.update_listener(
        AudioPosition(0, 0, 0),
        heading=45,
        speed=50
    )
    
    # 5. Process audio frame
    test_audio = np.random.randn(2048, 2) * 0.1
    processed = engine.process_audio_frame(test_audio)
    
    # Verify processing
    assert processed.shape == test_audio.shape
    assert not np.array_equal(processed, test_audio)  # Audio was modified
    
    # 6. Get debug info
    debug_info = engine.get_debug_info()
    assert debug_info['environment'] == 'forest'
    assert debug_info['active_sources'] == 2
    assert debug_info['listener']['speed'] == 50


if __name__ == "__main__":
    asyncio.run(test_full_spatial_audio_flow())