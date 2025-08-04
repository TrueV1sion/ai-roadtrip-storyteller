"""
Comprehensive unit tests for the location service.
Tests geocoding, reverse geocoding, location tracking, and geofencing.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any
import math

from app.services.location_service import (
    LocationService,
    Location,
    LocationUpdate,
    Geofence,
    LocationHistory,
    LocationAccuracy,
    LocationSource,
    GeofenceEvent,
    LocationCluster
)
from app.models.user import User


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock(spec=User)
    user.id = "test-user-123"
    user.preferences = {
        "location_sharing": True,
        "high_accuracy_mode": True
    }
    return user


@pytest.fixture
def mock_maps_client():
    """Create a mock Google Maps client."""
    client = Mock()
    client.geocode = Mock()
    client.reverse_geocode = Mock()
    client.places_nearby = Mock()
    client.elevation = Mock()
    client.timezone = Mock()
    return client


@pytest.fixture
def sample_location():
    """Create a sample location."""
    return Location(
        latitude=37.7749,
        longitude=-122.4194,
        accuracy=LocationAccuracy.HIGH,
        altitude=52.0,
        speed=0.0,
        heading=0.0,
        timestamp=datetime.now(),
        source=LocationSource.GPS,
        address="Market St, San Francisco, CA 94103",
        place_name="Downtown San Francisco"
    )


@pytest.fixture
def location_history():
    """Create sample location history."""
    base_time = datetime.now()
    return LocationHistory(
        user_id="test-user-123",
        locations=[
            Location(
                latitude=37.7749,
                longitude=-122.4194,
                timestamp=base_time - timedelta(minutes=10)
            ),
            Location(
                latitude=37.7759,
                longitude=-122.4184,
                timestamp=base_time - timedelta(minutes=5)
            ),
            Location(
                latitude=37.7769,
                longitude=-122.4174,
                timestamp=base_time
            )
        ]
    )


@pytest.fixture
async def location_service(mock_maps_client):
    """Create a location service with mocks."""
    with patch('backend.app.services.location_service.googlemaps.Client', return_value=mock_maps_client):
        service = LocationService()
        service.maps_client = mock_maps_client
        yield service


class TestLocationBasics:
    """Test basic location functionality."""
    
    def test_location_creation(self):
        """Test creating a location object."""
        location = Location(
            latitude=37.7749,
            longitude=-122.4194,
            accuracy=LocationAccuracy.HIGH,
            timestamp=datetime.now()
        )
        
        assert location.latitude == 37.7749
        assert location.longitude == -122.4194
        assert location.accuracy == LocationAccuracy.HIGH
        assert location.is_valid()
    
    def test_location_validation(self):
        """Test location validation."""
        # Valid location
        valid_location = Location(latitude=37.7749, longitude=-122.4194)
        assert valid_location.is_valid()
        
        # Invalid latitude
        invalid_lat = Location(latitude=91.0, longitude=-122.4194)
        assert not invalid_lat.is_valid()
        
        # Invalid longitude
        invalid_lng = Location(latitude=37.7749, longitude=181.0)
        assert not invalid_lng.is_valid()
    
    def test_location_distance_calculation(self):
        """Test calculating distance between locations."""
        loc1 = Location(latitude=37.7749, longitude=-122.4194)  # SF
        loc2 = Location(latitude=37.7849, longitude=-122.4094)  # ~1.4km away
        
        distance = loc1.distance_to(loc2)
        
        assert 1300 < distance < 1500  # meters
    
    def test_location_bearing_calculation(self):
        """Test calculating bearing between locations."""
        loc1 = Location(latitude=37.7749, longitude=-122.4194)
        loc2 = Location(latitude=37.7849, longitude=-122.4094)  # Northeast
        
        bearing = loc1.bearing_to(loc2)
        
        assert 30 < bearing < 60  # Northeast bearing


class TestGeocoding:
    """Test geocoding and reverse geocoding."""
    
    @pytest.mark.asyncio
    async def test_geocode_address(self, location_service, mock_maps_client):
        """Test geocoding an address to coordinates."""
        address = "1600 Amphitheatre Parkway, Mountain View, CA"
        
        # Mock geocoding response
        mock_maps_client.geocode.return_value = [{
            "geometry": {
                "location": {"lat": 37.4224764, "lng": -122.0842499}
            },
            "formatted_address": "1600 Amphitheatre Pkwy, Mountain View, CA 94043, USA",
            "place_id": "ChIJ2eUgeAK6j4ARbn5u_wAGqWA",
            "types": ["street_address"]
        }]
        
        location = await location_service.geocode_address(address)
        
        assert isinstance(location, Location)
        assert location.latitude == 37.4224764
        assert location.longitude == -122.0842499
        assert "Mountain View" in location.address
    
    @pytest.mark.asyncio
    async def test_reverse_geocode_coordinates(self, location_service, mock_maps_client):
        """Test reverse geocoding coordinates to address."""
        lat, lng = 37.7749, -122.4194
        
        # Mock reverse geocoding response
        mock_maps_client.reverse_geocode.return_value = [{
            "formatted_address": "Market St, San Francisco, CA 94103, USA",
            "address_components": [
                {"long_name": "Market Street", "types": ["route"]},
                {"long_name": "San Francisco", "types": ["locality"]},
                {"long_name": "California", "types": ["administrative_area_level_1"]}
            ],
            "place_id": "ChIJKYQPiLqAhYARJYQP"
        }]
        
        location = await location_service.reverse_geocode(lat, lng)
        
        assert isinstance(location, Location)
        assert location.latitude == lat
        assert location.longitude == lng
        assert "Market St" in location.address
        assert location.place_name == "Market Street, San Francisco"
    
    @pytest.mark.asyncio
    async def test_batch_geocoding(self, location_service, mock_maps_client):
        """Test geocoding multiple addresses."""
        addresses = [
            "Golden Gate Bridge, San Francisco, CA",
            "Alcatraz Island, San Francisco, CA",
            "Fisherman's Wharf, San Francisco, CA"
        ]
        
        # Mock batch responses
        mock_maps_client.geocode.side_effect = [
            [{"geometry": {"location": {"lat": 37.8199, "lng": -122.4783}}}],
            [{"geometry": {"location": {"lat": 37.8267, "lng": -122.4230}}}],
            [{"geometry": {"location": {"lat": 37.8080, "lng": -122.4177}}}]
        ]
        
        locations = await location_service.batch_geocode(addresses)
        
        assert len(locations) == 3
        assert all(isinstance(loc, Location) for loc in locations)
        assert locations[0].latitude == 37.8199  # Golden Gate


class TestLocationTracking:
    """Test location tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_update_user_location(self, location_service, mock_user):
        """Test updating user's current location."""
        location_update = LocationUpdate(
            latitude=37.7749,
            longitude=-122.4194,
            accuracy=10.0,
            speed=30.0,
            heading=180.0,
            source=LocationSource.GPS
        )
        
        updated = await location_service.update_user_location(mock_user, location_update)
        
        assert updated.user_id == mock_user.id
        assert updated.location.latitude == 37.7749
        assert updated.location.speed == 30.0
        assert updated.location.source == LocationSource.GPS
    
    @pytest.mark.asyncio
    async def test_location_history_tracking(self, location_service, mock_user):
        """Test tracking location history."""
        # Add multiple location updates
        updates = [
            LocationUpdate(latitude=37.7749, longitude=-122.4194, timestamp=datetime.now() - timedelta(minutes=5)),
            LocationUpdate(latitude=37.7759, longitude=-122.4184, timestamp=datetime.now() - timedelta(minutes=3)),
            LocationUpdate(latitude=37.7769, longitude=-122.4174, timestamp=datetime.now())
        ]
        
        for update in updates:
            await location_service.update_user_location(mock_user, update)
        
        # Get location history
        history = await location_service.get_location_history(
            mock_user.id,
            start_time=datetime.now() - timedelta(minutes=10),
            end_time=datetime.now()
        )
        
        assert len(history.locations) == 3
        assert history.locations[0].timestamp < history.locations[-1].timestamp
        assert history.total_distance > 0
        assert history.average_speed >= 0
    
    @pytest.mark.asyncio
    async def test_location_filtering(self, location_service, mock_user):
        """Test filtering out invalid or duplicate locations."""
        # Add updates including invalid/duplicate
        updates = [
            LocationUpdate(latitude=37.7749, longitude=-122.4194),
            LocationUpdate(latitude=37.7749, longitude=-122.4194),  # Duplicate
            LocationUpdate(latitude=91.0, longitude=-122.4194),    # Invalid
            LocationUpdate(latitude=37.7759, longitude=-122.4184)
        ]
        
        valid_count = 0
        for update in updates:
            result = await location_service.update_user_location(mock_user, update)
            if result:
                valid_count += 1
        
        assert valid_count == 2  # Only non-duplicate, valid locations
    
    @pytest.mark.asyncio
    async def test_location_interpolation(self, location_service, location_history):
        """Test interpolating missing location points."""
        # Test interpolation between sparse points
        interpolated = await location_service.interpolate_locations(
            location_history,
            interval_seconds=60  # 1 minute intervals
        )
        
        assert len(interpolated.locations) > len(location_history.locations)
        # Check interpolated points are between originals
        for i in range(1, len(interpolated.locations) - 1):
            loc = interpolated.locations[i]
            assert location_history.locations[0].latitude <= loc.latitude <= location_history.locations[-1].latitude


class TestGeofencing:
    """Test geofencing functionality."""
    
    @pytest.mark.asyncio
    async def test_create_geofence(self, location_service):
        """Test creating a geofence."""
        geofence = await location_service.create_geofence(
            name="Home",
            center_lat=37.7749,
            center_lng=-122.4194,
            radius_meters=100,
            trigger_on_enter=True,
            trigger_on_exit=True
        )
        
        assert isinstance(geofence, Geofence)
        assert geofence.name == "Home"
        assert geofence.radius_meters == 100
        assert geofence.is_active
    
    @pytest.mark.asyncio
    async def test_check_geofence_entry(self, location_service):
        """Test detecting geofence entry."""
        # Create geofence
        geofence = Geofence(
            id="test-fence",
            name="Test Zone",
            center=Location(latitude=37.7749, longitude=-122.4194),
            radius_meters=100,
            trigger_on_enter=True
        )
        
        # Location outside fence
        outside = Location(latitude=37.7740, longitude=-122.4200)
        # Location inside fence
        inside = Location(latitude=37.7749, longitude=-122.4194)
        
        # Check transition
        event = await location_service.check_geofence_transition(
            geofence, outside, inside
        )
        
        assert isinstance(event, GeofenceEvent)
        assert event.event_type == "enter"
        assert event.geofence_id == "test-fence"
    
    @pytest.mark.asyncio
    async def test_check_geofence_exit(self, location_service):
        """Test detecting geofence exit."""
        geofence = Geofence(
            id="test-fence",
            name="Test Zone",
            center=Location(latitude=37.7749, longitude=-122.4194),
            radius_meters=100,
            trigger_on_exit=True
        )
        
        # Location inside fence
        inside = Location(latitude=37.7749, longitude=-122.4194)
        # Location outside fence
        outside = Location(latitude=37.7730, longitude=-122.4210)
        
        event = await location_service.check_geofence_transition(
            geofence, inside, outside
        )
        
        assert event.event_type == "exit"
    
    @pytest.mark.asyncio
    async def test_monitor_multiple_geofences(self, location_service, mock_user):
        """Test monitoring multiple geofences simultaneously."""
        # Create multiple geofences
        geofences = [
            Geofence(
                id="home",
                name="Home",
                center=Location(latitude=37.7749, longitude=-122.4194),
                radius_meters=100
            ),
            Geofence(
                id="work",
                name="Work",
                center=Location(latitude=37.7849, longitude=-122.4094),
                radius_meters=200
            ),
            Geofence(
                id="gym",
                name="Gym",
                center=Location(latitude=37.7649, longitude=-122.4294),
                radius_meters=50
            )
        ]
        
        # User location near work
        location = Location(latitude=37.7850, longitude=-122.4090)
        
        active_geofences = await location_service.get_active_geofences(
            location, geofences
        )
        
        assert len(active_geofences) == 1
        assert active_geofences[0].id == "work"


class TestLocationClustering:
    """Test location clustering for frequently visited places."""
    
    @pytest.mark.asyncio
    async def test_identify_location_clusters(self, location_service):
        """Test identifying clusters from location history."""
        # Create location history with clusters
        locations = []
        
        # Cluster 1: Home (many points)
        for i in range(20):
            locations.append(Location(
                latitude=37.7749 + (i % 3) * 0.0001,
                longitude=-122.4194 + (i % 3) * 0.0001,
                timestamp=datetime.now() - timedelta(days=i)
            ))
        
        # Cluster 2: Work (many points)
        for i in range(15):
            locations.append(Location(
                latitude=37.7849 + (i % 3) * 0.0001,
                longitude=-122.4094 + (i % 3) * 0.0001,
                timestamp=datetime.now() - timedelta(days=i)
            ))
        
        # Random locations (few points)
        for i in range(5):
            locations.append(Location(
                latitude=37.7949 + i * 0.01,
                longitude=-122.3994 + i * 0.01,
                timestamp=datetime.now() - timedelta(days=i)
            ))
        
        history = LocationHistory(user_id="test", locations=locations)
        clusters = await location_service.identify_location_clusters(history)
        
        assert len(clusters) >= 2  # At least home and work
        assert clusters[0].visit_count >= 15  # Most visited
        assert clusters[0].confidence > 0.8
    
    @pytest.mark.asyncio
    async def test_label_frequent_locations(self, location_service, mock_maps_client):
        """Test automatically labeling frequent locations."""
        cluster = LocationCluster(
            center=Location(latitude=37.7749, longitude=-122.4194),
            radius_meters=50,
            visit_count=30,
            confidence=0.95,
            typical_arrival_time="08:00",
            typical_departure_time="18:00",
            typical_duration_minutes=600
        )
        
        # Mock places nearby for labeling
        mock_maps_client.places_nearby.return_value = {
            "results": [{
                "name": "Acme Corporation",
                "types": ["establishment", "point_of_interest"],
                "geometry": {"location": {"lat": 37.7749, "lng": -122.4194}}
            }]
        }
        
        labeled = await location_service.label_cluster(cluster)
        
        assert labeled.label == "Work"  # Based on arrival/departure pattern
        assert labeled.place_name == "Acme Corporation"


class TestLocationPrivacy:
    """Test location privacy features."""
    
    @pytest.mark.asyncio
    async def test_location_fuzzing(self, location_service):
        """Test location fuzzing for privacy."""
        precise_location = Location(
            latitude=37.774923,
            longitude=-122.419415,
            accuracy=LocationAccuracy.HIGH
        )
        
        # Fuzz location for privacy
        fuzzed = await location_service.fuzz_location(
            precise_location,
            fuzzing_radius_meters=50
        )
        
        # Should be within fuzzing radius but not exact
        distance = precise_location.distance_to(fuzzed)
        assert 0 < distance <= 50
        assert fuzzed.accuracy == LocationAccuracy.FUZZY
    
    @pytest.mark.asyncio
    async def test_location_sharing_preferences(self, location_service, mock_user):
        """Test respecting user's location sharing preferences."""
        # User with sharing disabled
        private_user = Mock(spec=User)
        private_user.id = "private-user"
        private_user.preferences = {"location_sharing": False}
        
        location = Location(latitude=37.7749, longitude=-122.4194)
        
        # Should not share exact location
        shared = await location_service.get_shareable_location(private_user, location)
        
        assert shared is None or shared.accuracy == LocationAccuracy.FUZZY
    
    @pytest.mark.asyncio
    async def test_location_data_retention(self, location_service, mock_user):
        """Test location data retention policies."""
        # Add old location data
        old_location = LocationUpdate(
            latitude=37.7749,
            longitude=-122.4194,
            timestamp=datetime.now() - timedelta(days=40)  # Older than retention
        )
        
        await location_service.update_user_location(mock_user, old_location)
        
        # Clean old data
        cleaned = await location_service.clean_old_location_data(
            retention_days=30
        )
        
        assert cleaned > 0  # Should have cleaned old data


class TestLocationEnrichment:
    """Test location data enrichment."""
    
    @pytest.mark.asyncio
    async def test_enrich_with_elevation(self, location_service, mock_maps_client):
        """Test enriching location with elevation data."""
        location = Location(latitude=37.7749, longitude=-122.4194)
        
        # Mock elevation API
        mock_maps_client.elevation.return_value = [{
            "elevation": 52.09,
            "resolution": 4.77
        }]
        
        enriched = await location_service.enrich_with_elevation(location)
        
        assert enriched.altitude == 52.09
    
    @pytest.mark.asyncio
    async def test_enrich_with_timezone(self, location_service, mock_maps_client):
        """Test enriching location with timezone data."""
        location = Location(latitude=37.7749, longitude=-122.4194)
        
        # Mock timezone API
        mock_maps_client.timezone.return_value = {
            "timeZoneId": "America/Los_Angeles",
            "timeZoneName": "Pacific Standard Time"
        }
        
        enriched = await location_service.enrich_with_timezone(location)
        
        assert enriched.timezone == "America/Los_Angeles"
    
    @pytest.mark.asyncio
    async def test_enrich_with_place_details(self, location_service, mock_maps_client):
        """Test enriching location with place details."""
        location = Location(latitude=37.7749, longitude=-122.4194)
        
        # Mock places nearby
        mock_maps_client.places_nearby.return_value = {
            "results": [{
                "name": "Union Square",
                "types": ["point_of_interest", "establishment"],
                "vicinity": "San Francisco"
            }]
        }
        
        enriched = await location_service.enrich_with_places(location)
        
        assert enriched.nearby_places is not None
        assert len(enriched.nearby_places) > 0
        assert enriched.nearby_places[0]["name"] == "Union Square"


class TestLocationUtilities:
    """Test location utility functions."""
    
    def test_format_coordinates(self):
        """Test formatting coordinates for display."""
        location = Location(latitude=37.7749295, longitude=-122.4194155)
        
        # Decimal degrees
        dd = location.format_coordinates("DD")
        assert dd == "37.7749° N, 122.4194° W"
        
        # Degrees minutes seconds
        dms = location.format_coordinates("DMS")
        assert "37° 46'" in dms
        assert "122° 25'" in dms
    
    def test_location_bounding_box(self):
        """Test calculating bounding box around location."""
        center = Location(latitude=37.7749, longitude=-122.4194)
        
        bbox = center.get_bounding_box(radius_meters=1000)
        
        assert bbox["north"] > center.latitude
        assert bbox["south"] < center.latitude
        assert bbox["east"] > center.longitude
        assert bbox["west"] < center.longitude
        
        # Verify approximately 1km in each direction
        north_dist = center.distance_to(Location(latitude=bbox["north"], longitude=center.longitude))
        assert 900 < north_dist < 1100
    
    def test_location_grid_snap(self):
        """Test snapping location to grid for privacy/clustering."""
        location = Location(latitude=37.774923, longitude=-122.419415)
        
        # Snap to 0.001 degree grid (~100m)
        snapped = location.snap_to_grid(precision=0.001)
        
        assert snapped.latitude == 37.775
        assert snapped.longitude == -122.419