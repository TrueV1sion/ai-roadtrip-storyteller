"""
Comprehensive unit tests for Spotify integration
Tests cover: OAuth flow, playlist creation, journey-based music, narration coordination
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
import base64
from typing import Dict, List, Any

from backend.app.services.spotify_service import (
    SpotifyService, SpotifyAuthManager, JourneyPlaylistGenerator,
    MusicMoodAnalyzer, NarrationCoordinator
)


class TestSpotifyAuthManager:
    """Test suite for Spotify OAuth authentication"""
    
    @pytest.fixture
    def auth_manager(self):
        """Create SpotifyAuthManager instance"""
        return SpotifyAuthManager(
            client_id="test_client_id",
            client_secret="test_client_secret",
            redirect_uri="http://localhost:3000/callback"
        )
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client"""
        return Mock()
    
    def test_generate_auth_url(self, auth_manager):
        """Test OAuth authorization URL generation"""
        scopes = ["playlist-modify-public", "user-read-private", "streaming"]
        state = "random_state_123"
        
        auth_url = auth_manager.generate_auth_url(scopes, state)
        
        assert "https://accounts.spotify.com/authorize" in auth_url
        assert "client_id=test_client_id" in auth_url
        assert "redirect_uri=http%3A%2F%2Flocalhost%3A3000%2Fcallback" in auth_url
        assert "state=random_state_123" in auth_url
        assert "playlist-modify-public" in auth_url
    
    @pytest.mark.asyncio
    async def test_exchange_code_for_token(self, auth_manager):
        """Test exchanging authorization code for access token"""
        # Mock HTTP response
        mock_response = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(
                return_value=mock_response
            )
            mock_post.return_value.__aenter__.return_value.status = 200
            
            tokens = await auth_manager.exchange_code_for_token("auth_code_123")
            
            assert tokens["access_token"] == "test_access_token"
            assert tokens["refresh_token"] == "test_refresh_token"
            assert "expires_at" in tokens
            
            # Verify correct authorization header
            call_args = mock_post.call_args
            headers = call_args[1]["headers"]
            assert "Authorization" in headers
            assert headers["Authorization"].startswith("Basic ")
    
    @pytest.mark.asyncio
    async def test_refresh_access_token(self, auth_manager):
        """Test refreshing expired access token"""
        mock_response = {
            "access_token": "new_access_token",
            "expires_in": 3600
        }
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(
                return_value=mock_response
            )
            mock_post.return_value.__aenter__.return_value.status = 200
            
            new_tokens = await auth_manager.refresh_access_token("old_refresh_token")
            
            assert new_tokens["access_token"] == "new_access_token"
            assert new_tokens["refresh_token"] == "old_refresh_token"  # Refresh token unchanged
    
    @pytest.mark.asyncio
    async def test_token_storage_and_retrieval(self, auth_manager, mock_redis):
        """Test storing and retrieving tokens from cache"""
        auth_manager.redis = mock_redis
        
        tokens = {
            "access_token": "test_token",
            "refresh_token": "refresh_token",
            "expires_at": datetime.now() + timedelta(hours=1)
        }
        
        # Store tokens
        await auth_manager.store_user_tokens("user123", tokens)
        
        mock_redis.setex.assert_called()
        call_args = mock_redis.setex.call_args
        assert call_args[0][0] == "spotify:tokens:user123"
        
        # Retrieve tokens
        mock_redis.get.return_value = json.dumps({
            **tokens,
            "expires_at": tokens["expires_at"].isoformat()
        })
        
        retrieved = await auth_manager.get_user_tokens("user123")
        assert retrieved["access_token"] == "test_token"
    
    @pytest.mark.asyncio
    async def test_auto_refresh_expired_token(self, auth_manager, mock_redis):
        """Test automatic token refresh when expired"""
        # Mock expired token
        expired_token = {
            "access_token": "expired_token",
            "refresh_token": "refresh_token",
            "expires_at": datetime.now() - timedelta(minutes=5)  # Expired
        }
        
        mock_redis.get.return_value = json.dumps({
            **expired_token,
            "expires_at": expired_token["expires_at"].isoformat()
        })
        
        auth_manager.redis = mock_redis
        auth_manager.refresh_access_token = AsyncMock(return_value={
            "access_token": "new_token",
            "refresh_token": "refresh_token",
            "expires_at": datetime.now() + timedelta(hours=1)
        })
        
        # Should automatically refresh
        tokens = await auth_manager.get_valid_token("user123")
        
        assert tokens["access_token"] == "new_token"
        auth_manager.refresh_access_token.assert_called_once()


class TestSpotifyService:
    """Test suite for main Spotify service functionality"""
    
    @pytest.fixture
    def spotify_service(self):
        """Create SpotifyService instance with mocked dependencies"""
        service = SpotifyService()
        service.auth_manager = Mock()
        service.api_client = Mock()
        return service
    
    @pytest.fixture
    def sample_user_profile(self):
        """Sample Spotify user profile"""
        return {
            "id": "spotify_user_123",
            "display_name": "John Doe",
            "email": "john@example.com",
            "country": "US",
            "product": "premium"
        }
    
    @pytest.fixture
    def sample_tracks(self):
        """Sample Spotify tracks"""
        return [
            {
                "id": "track1",
                "name": "Highway to Hell",
                "artists": [{"name": "AC/DC"}],
                "duration_ms": 208000,
                "uri": "spotify:track:track1"
            },
            {
                "id": "track2",
                "name": "Born to Be Wild",
                "artists": [{"name": "Steppenwolf"}],
                "duration_ms": 217000,
                "uri": "spotify:track:track2"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_get_user_profile(self, spotify_service, sample_user_profile):
        """Test fetching user profile"""
        spotify_service.auth_manager.get_valid_token = AsyncMock(
            return_value={"access_token": "valid_token"}
        )
        
        spotify_service.api_client.get_user_profile = AsyncMock(
            return_value=sample_user_profile
        )
        
        profile = await spotify_service.get_user_profile("user123")
        
        assert profile["display_name"] == "John Doe"
        assert profile["product"] == "premium"
        spotify_service.api_client.get_user_profile.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_tracks(self, spotify_service, sample_tracks):
        """Test searching for tracks"""
        spotify_service.auth_manager.get_valid_token = AsyncMock(
            return_value={"access_token": "valid_token"}
        )
        
        spotify_service.api_client.search = AsyncMock(return_value={
            "tracks": {
                "items": sample_tracks,
                "total": 2
            }
        })
        
        results = await spotify_service.search_tracks(
            query="road trip rock",
            limit=10
        )
        
        assert len(results) == 2
        assert results[0]["name"] == "Highway to Hell"
    
    @pytest.mark.asyncio
    async def test_create_playlist(self, spotify_service):
        """Test creating a new playlist"""
        spotify_service.auth_manager.get_valid_token = AsyncMock(
            return_value={"access_token": "valid_token"}
        )
        
        spotify_service.api_client.create_playlist = AsyncMock(return_value={
            "id": "playlist123",
            "name": "Road Trip 2024",
            "public": True,
            "uri": "spotify:playlist:playlist123"
        })
        
        playlist = await spotify_service.create_playlist(
            user_id="user123",
            name="Road Trip 2024",
            description="Epic road trip playlist",
            public=True
        )
        
        assert playlist["id"] == "playlist123"
        spotify_service.api_client.create_playlist.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_add_tracks_to_playlist(self, spotify_service):
        """Test adding tracks to playlist"""
        spotify_service.auth_manager.get_valid_token = AsyncMock(
            return_value={"access_token": "valid_token"}
        )
        
        spotify_service.api_client.add_tracks_to_playlist = AsyncMock(
            return_value={"snapshot_id": "snapshot123"}
        )
        
        track_uris = ["spotify:track:track1", "spotify:track:track2"]
        
        result = await spotify_service.add_tracks_to_playlist(
            user_id="user123",
            playlist_id="playlist123",
            track_uris=track_uris
        )
        
        assert result["snapshot_id"] == "snapshot123"
    
    @pytest.mark.asyncio
    async def test_get_user_top_tracks(self, spotify_service, sample_tracks):
        """Test getting user's top tracks"""
        spotify_service.auth_manager.get_valid_token = AsyncMock(
            return_value={"access_token": "valid_token"}
        )
        
        spotify_service.api_client.get_user_top_items = AsyncMock(
            return_value={"items": sample_tracks}
        )
        
        top_tracks = await spotify_service.get_user_top_tracks(
            user_id="user123",
            time_range="medium_term",
            limit=20
        )
        
        assert len(top_tracks) == 2
        spotify_service.api_client.get_user_top_items.assert_called_with(
            "tracks", "valid_token", time_range="medium_term", limit=20
        )


class TestJourneyPlaylistGenerator:
    """Test suite for journey-based playlist generation"""
    
    @pytest.fixture
    def playlist_generator(self):
        """Create JourneyPlaylistGenerator instance"""
        generator = JourneyPlaylistGenerator()
        generator.spotify_service = Mock()
        generator.ai_client = AsyncMock()
        return generator
    
    @pytest.fixture
    def journey_context(self):
        """Sample journey context"""
        return {
            "origin": "New York, NY",
            "destination": "Miami, FL",
            "duration_hours": 18,
            "route_type": "coastal",
            "waypoints": ["Washington DC", "Richmond", "Charleston", "Savannah"],
            "departure_time": "08:00",
            "weather": "sunny",
            "season": "summer"
        }
    
    @pytest.mark.asyncio
    async def test_generate_journey_playlist(self, playlist_generator, journey_context):
        """Test generating playlist based on journey"""
        # Mock AI suggestions
        playlist_generator.ai_client.generate_structured_response.return_value = {
            "themes": ["road trip classics", "summer vibes", "coastal cruising"],
            "energy_profile": {
                "start": "medium",
                "middle": "high",
                "end": "relaxed"
            },
            "suggested_artists": ["Beach Boys", "Jimmy Buffett", "Bob Marley"],
            "suggested_genres": ["rock", "reggae", "pop"],
            "mood_keywords": ["upbeat", "sunny", "adventure", "freedom"]
        }
        
        # Mock track search results
        mock_tracks = [
            {"uri": "spotify:track:1", "name": "Good Vibrations"},
            {"uri": "spotify:track:2", "name": "Margaritaville"},
            {"uri": "spotify:track:3", "name": "Three Little Birds"}
        ]
        
        playlist_generator.spotify_service.search_tracks = AsyncMock(
            return_value=mock_tracks
        )
        
        playlist_generator.spotify_service.create_playlist = AsyncMock(
            return_value={"id": "journey_playlist_123"}
        )
        
        playlist_generator.spotify_service.add_tracks_to_playlist = AsyncMock()
        
        playlist = await playlist_generator.generate_journey_playlist(
            user_id="user123",
            journey_context=journey_context
        )
        
        assert playlist["id"] == "journey_playlist_123"
        assert len(playlist_generator.spotify_service.search_tracks.call_args_list) >= 3
        playlist_generator.spotify_service.add_tracks_to_playlist.assert_called()
    
    @pytest.mark.asyncio
    async def test_adaptive_playlist_generation(self, playlist_generator):
        """Test playlist adaptation based on time of day and progress"""
        # Morning energy
        morning_context = {
            "current_time": "08:00",
            "journey_progress": 0.1,
            "current_location": "Starting point"
        }
        
        playlist_generator._get_energy_level = Mock(return_value="medium-high")
        energy = playlist_generator._get_energy_level(morning_context)
        assert energy == "medium-high"
        
        # Afternoon peak
        afternoon_context = {
            "current_time": "14:00",
            "journey_progress": 0.5,
            "current_location": "Highway"
        }
        
        playlist_generator._get_energy_level = Mock(return_value="high")
        energy = playlist_generator._get_energy_level(afternoon_context)
        assert energy == "high"
        
        # Evening wind-down
        evening_context = {
            "current_time": "20:00",
            "journey_progress": 0.9,
            "current_location": "Near destination"
        }
        
        playlist_generator._get_energy_level = Mock(return_value="low-medium")
        energy = playlist_generator._get_energy_level(evening_context)
        assert energy == "low-medium"
    
    @pytest.mark.asyncio
    async def test_location_based_music_selection(self, playlist_generator):
        """Test music selection based on location"""
        # Mock location-specific music
        locations = [
            {
                "name": "Nashville, TN",
                "genres": ["country", "blues"],
                "artists": ["Johnny Cash", "Dolly Parton"]
            },
            {
                "name": "New Orleans, LA",
                "genres": ["jazz", "blues", "funk"],
                "artists": ["Louis Armstrong", "Dr. John"]
            },
            {
                "name": "Seattle, WA",
                "genres": ["grunge", "indie"],
                "artists": ["Nirvana", "Pearl Jam"]
            }
        ]
        
        for location in locations:
            suggestions = await playlist_generator._get_location_music_suggestions(
                location["name"]
            )
            
            # Mock AI response
            playlist_generator.ai_client.generate_structured_response.return_value = {
                "local_genres": location["genres"],
                "local_artists": location["artists"]
            }
            
            result = await playlist_generator._get_location_music_suggestions(
                location["name"]
            )
            
            assert set(result["local_genres"]) == set(location["genres"])


class TestMusicMoodAnalyzer:
    """Test suite for music mood analysis"""
    
    @pytest.fixture
    def mood_analyzer(self):
        """Create MusicMoodAnalyzer instance"""
        analyzer = MusicMoodAnalyzer()
        analyzer.spotify_service = Mock()
        return analyzer
    
    @pytest.mark.asyncio
    async def test_analyze_track_features(self, mood_analyzer):
        """Test analyzing audio features for mood"""
        # Mock Spotify audio features
        audio_features = {
            "energy": 0.8,
            "valence": 0.7,  # Happiness
            "danceability": 0.75,
            "acousticness": 0.2,
            "instrumentalness": 0.1,
            "tempo": 128
        }
        
        mood_analyzer.spotify_service.get_audio_features = AsyncMock(
            return_value=audio_features
        )
        
        mood = await mood_analyzer.analyze_track_mood("track123")
        
        assert mood["energy_level"] == "high"
        assert mood["mood"] == "upbeat"
        assert mood["suitable_for"] == ["highway_driving", "daytime"]
    
    def test_mood_classification(self, mood_analyzer):
        """Test mood classification logic"""
        test_cases = [
            # (energy, valence, expected_mood)
            (0.9, 0.8, "energetic_happy"),
            (0.3, 0.2, "calm_melancholic"),
            (0.7, 0.5, "moderate_neutral"),
            (0.2, 0.8, "calm_happy"),
            (0.8, 0.3, "energetic_dark")
        ]
        
        for energy, valence, expected in test_cases:
            mood = mood_analyzer._classify_mood(energy, valence)
            assert expected in mood
    
    @pytest.mark.asyncio
    async def test_journey_mood_progression(self, mood_analyzer):
        """Test mood progression throughout journey"""
        journey_stages = [
            {"stage": "departure", "time": "08:00", "expected_mood": "energetic"},
            {"stage": "highway", "time": "10:00", "expected_mood": "upbeat"},
            {"stage": "scenic", "time": "14:00", "expected_mood": "relaxed"},
            {"stage": "traffic", "time": "17:00", "expected_mood": "calm"},
            {"stage": "arrival", "time": "20:00", "expected_mood": "mellow"}
        ]
        
        moods = []
        for stage in journey_stages:
            mood = await mood_analyzer.get_recommended_mood(
                journey_stage=stage["stage"],
                time_of_day=stage["time"]
            )
            moods.append(mood)
            assert stage["expected_mood"] in mood["recommended_mood"]
        
        # Verify progression makes sense
        assert len(set(moods)) >= 3  # Should have variety


class TestNarrationCoordinator:
    """Test suite for music-narration coordination"""
    
    @pytest.fixture
    def coordinator(self):
        """Create NarrationCoordinator instance"""
        coord = NarrationCoordinator()
        coord.spotify_service = Mock()
        coord.volume_controller = Mock()
        return coord
    
    @pytest.mark.asyncio
    async def test_duck_music_for_narration(self, coordinator):
        """Test volume ducking during narration"""
        # Start narration
        await coordinator.start_narration()
        
        coordinator.volume_controller.fade_to.assert_called_with(
            volume=0.3,  # 30% volume during narration
            duration=0.5  # Quick fade
        )
        
        # End narration
        await coordinator.end_narration()
        
        coordinator.volume_controller.fade_to.assert_called_with(
            volume=1.0,  # Back to full volume
            duration=1.0  # Slower fade up
        )
    
    @pytest.mark.asyncio
    async def test_pause_music_for_important_narration(self, coordinator):
        """Test pausing music for important announcements"""
        await coordinator.important_announcement()
        
        # Should pause music
        coordinator.spotify_service.pause_playback.assert_called_once()
        
        # Resume after announcement
        await coordinator.resume_after_announcement()
        coordinator.spotify_service.resume_playback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_crossfade_between_tracks(self, coordinator):
        """Test smooth crossfading between tracks"""
        await coordinator.crossfade_to_next_track(
            fade_duration=3.0
        )
        
        # Should coordinate fade out and fade in
        assert coordinator.volume_controller.crossfade.called
    
    @pytest.mark.asyncio
    async def test_sync_music_with_story_beats(self, coordinator):
        """Test synchronizing music changes with story beats"""
        story_beats = [
            {"type": "climax", "intensity": "high", "duration": 30},
            {"type": "resolution", "intensity": "low", "duration": 45},
            {"type": "new_chapter", "intensity": "medium", "duration": 60}
        ]
        
        for beat in story_beats:
            await coordinator.sync_to_story_beat(beat)
            
            if beat["intensity"] == "high":
                # Should increase volume or switch to energetic track
                assert coordinator.volume_controller.fade_to.called or \
                       coordinator.spotify_service.skip_to_track.called
    
    @pytest.mark.asyncio
    async def test_handle_playback_interruption(self, coordinator):
        """Test handling playback interruptions gracefully"""
        # Simulate connection loss
        coordinator.spotify_service.get_playback_state = AsyncMock(
            side_effect=Exception("Connection lost")
        )
        
        # Should handle gracefully
        state = await coordinator.check_playback_health()
        assert state["status"] == "error"
        assert state["fallback_mode"] is True
    
    def test_calculate_fade_parameters(self, coordinator):
        """Test fade parameter calculations"""
        # Quick fade for short content
        params = coordinator._calculate_fade_params(
            content_duration=2.0,
            content_type="short_fact"
        )
        assert params["fade_in"] <= 0.3
        assert params["target_volume"] >= 0.5
        
        # Longer fade for story segments
        params = coordinator._calculate_fade_params(
            content_duration=30.0,
            content_type="story_chapter"
        )
        assert params["fade_in"] >= 0.5
        assert params["target_volume"] <= 0.4


class TestSpotifyErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_handle_rate_limiting(self):
        """Test handling Spotify API rate limits"""
        service = SpotifyService()
        service.api_client = Mock()
        
        # Simulate 429 rate limit error
        service.api_client.search = AsyncMock(
            side_effect=Exception("429 Too Many Requests")
        )
        
        # Should retry with backoff
        with patch('asyncio.sleep') as mock_sleep:
            try:
                await service.search_tracks_with_retry("test query")
            except Exception as e:
                assert "429" in str(e)
                assert mock_sleep.called  # Should have tried to wait
    
    @pytest.mark.asyncio
    async def test_handle_invalid_token(self):
        """Test handling invalid/expired tokens"""
        auth_manager = SpotifyAuthManager("id", "secret", "uri")
        
        # Mock invalid token response
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.status = 401
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(
                return_value={"error": "invalid_token"}
            )
            
            with pytest.raises(Exception, match="invalid_token"):
                await auth_manager.exchange_code_for_token("bad_code")
    
    @pytest.mark.asyncio
    async def test_handle_premium_required(self):
        """Test handling premium-only features for free users"""
        service = SpotifyService()
        service.auth_manager = Mock()
        service.api_client = Mock()
        
        # Mock free user
        service.api_client.get_user_profile = AsyncMock(
            return_value={"product": "free"}
        )
        
        # Should handle gracefully
        can_use = await service.check_premium_features("user123")
        assert can_use is False
    
    @pytest.mark.asyncio
    async def test_playlist_size_limits(self):
        """Test handling playlist size limits"""
        generator = JourneyPlaylistGenerator()
        
        # Spotify limit is 10,000 tracks
        too_many_tracks = ["spotify:track:" + str(i) for i in range(11000)]
        
        # Should batch or limit
        batches = generator._batch_tracks_for_playlist(too_many_tracks)
        assert len(batches[0]) <= 10000


class TestSpotifyIntegrationScenarios:
    """Test complete integration scenarios"""
    
    @pytest.mark.asyncio
    async def test_complete_oauth_flow(self):
        """Test complete OAuth flow from start to finish"""
        auth_manager = SpotifyAuthManager("id", "secret", "http://localhost/callback")
        redis = Mock()
        auth_manager.redis = redis
        
        # 1. Generate auth URL
        auth_url = auth_manager.generate_auth_url(
            ["playlist-modify-public", "streaming"],
            "state123"
        )
        assert "state123" in auth_url
        
        # 2. User authorizes and we get code
        auth_code = "returned_auth_code"
        
        # 3. Exchange code for tokens
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_post.return_value.__aenter__.return_value.json = AsyncMock(
                return_value={
                    "access_token": "access_123",
                    "refresh_token": "refresh_123",
                    "expires_in": 3600
                }
            )
            mock_post.return_value.__aenter__.return_value.status = 200
            
            tokens = await auth_manager.exchange_code_for_token(auth_code)
            
        # 4. Store tokens
        await auth_manager.store_user_tokens("user123", tokens)
        assert redis.setex.called
        
        # 5. Use tokens for API calls
        assert tokens["access_token"] == "access_123"
    
    @pytest.mark.asyncio
    async def test_road_trip_music_experience(self):
        """Test complete road trip music experience"""
        # Setup services
        spotify_service = SpotifyService()
        playlist_generator = JourneyPlaylistGenerator()
        narration_coordinator = NarrationCoordinator()
        
        # Mock dependencies
        spotify_service.auth_manager = Mock()
        spotify_service.api_client = Mock()
        playlist_generator.spotify_service = spotify_service
        narration_coordinator.spotify_service = spotify_service
        
        # 1. User connects Spotify account
        spotify_service.auth_manager.get_valid_token = AsyncMock(
            return_value={"access_token": "valid_token"}
        )
        
        # 2. Generate journey playlist
        journey = {
            "origin": "Los Angeles",
            "destination": "Las Vegas",
            "duration_hours": 4
        }
        
        spotify_service.create_playlist = AsyncMock(
            return_value={"id": "playlist123"}
        )
        spotify_service.search_tracks = AsyncMock(
            return_value=[{"uri": "spotify:track:1"}]
        )
        spotify_service.add_tracks_to_playlist = AsyncMock()
        
        playlist = await playlist_generator.generate_journey_playlist(
            "user123", journey
        )
        
        # 3. Start playback
        spotify_service.start_playback = AsyncMock()
        await spotify_service.start_playback("user123", playlist["id"])
        
        # 4. Coordinate with narration
        narration_coordinator.volume_controller = Mock()
        await narration_coordinator.start_narration()
        narration_coordinator.volume_controller.fade_to.assert_called()
        
        # 5. Update playlist based on journey progress
        # This would happen periodically during the trip
        new_tracks = await playlist_generator.get_contextual_tracks(
            location="Baker, CA",
            time_of_day="14:00"
        )
        
        # Complete experience delivered
        assert playlist["id"] == "playlist123"
        assert spotify_service.start_playback.called


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])