"""
Comprehensive unit tests for the directions service.
Tests route planning, navigation, real-time updates, and POI detection.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, List, Any

from app.services.directions_service import (
    DirectionsService,
    Route,
    RouteSegment,
    NavigationInstruction,
    PointOfInterest,
    TrafficCondition,
    RoutePreference,
    NavigationState,
    RouteOptimizer
)
from app.models.user import User


@pytest.fixture
def mock_user():
    """Create a mock user for testing."""
    user = Mock(spec=User)
    user.id = "test-user-123"
    user.preferences = {
        "avoid_highways": False,
        "avoid_tolls": False,
        "preferred_routes": ["scenic"]
    }
    return user


@pytest.fixture
def mock_maps_client():
    """Create a mock Google Maps client."""
    client = Mock()
    client.directions = Mock()
    client.distance_matrix = Mock()
    client.places_nearby = Mock()
    client.geocode = Mock()
    client.roads.snap_to_roads = Mock()
    return client


@pytest.fixture
def sample_location():
    """Create a sample location."""
    return {
        "lat": 37.7749,
        "lng": -122.4194,
        "address": "San Francisco, CA",
        "place_id": "ChIJIQBpAG2ahYAR_6128GcTUEo"
    }


@pytest.fixture
def sample_route():
    """Create a sample route for testing."""
    return Route(
        origin={"lat": 37.7749, "lng": -122.4194, "address": "San Francisco, CA"},
        destination={"lat": 34.0522, "lng": -118.2437, "address": "Los Angeles, CA"},
        distance_meters=616000,
        duration_seconds=21600,
        polyline="encoded_polyline_string",
        segments=[
            RouteSegment(
                start_location={"lat": 37.7749, "lng": -122.4194},
                end_location={"lat": 37.7849, "lng": -122.4094},
                distance_meters=1500,
                duration_seconds=180,
                instruction="Head south on Market St",
                maneuver="turn-right"
            )
        ],
        traffic_condition=TrafficCondition.MODERATE,
        estimated_arrival=datetime.now() + timedelta(hours=6)
    )


@pytest.fixture
async def directions_service(mock_maps_client):
    """Create a directions service with mocks."""
    with patch('backend.app.services.directions_service.googlemaps.Client', return_value=mock_maps_client):
        service = DirectionsService()
        service.maps_client = mock_maps_client
        yield service


class TestRouteCalculation:
    """Test route calculation functionality."""
    
    @pytest.mark.asyncio
    async def test_calculate_route_basic(self, directions_service, mock_maps_client):
        """Test basic route calculation."""
        origin = {"lat": 37.7749, "lng": -122.4194}
        destination = {"lat": 34.0522, "lng": -118.2437}
        
        # Mock Google Maps response
        mock_maps_client.directions.return_value = [{
            "legs": [{
                "distance": {"value": 616000},
                "duration": {"value": 21600},
                "steps": [
                    {
                        "distance": {"value": 1500},
                        "duration": {"value": 180},
                        "html_instructions": "Head <b>south</b> on Market St",
                        "polyline": {"points": "abc123"},
                        "start_location": {"lat": 37.7749, "lng": -122.4194},
                        "end_location": {"lat": 37.7849, "lng": -122.4094},
                        "maneuver": "turn-right"
                    }
                ]
            }],
            "overview_polyline": {"points": "encoded_polyline"},
            "warnings": [],
            "waypoint_order": []
        }]
        
        route = await directions_service.calculate_route(origin, destination)
        
        assert isinstance(route, Route)
        assert route.distance_meters == 616000
        assert route.duration_seconds == 21600
        assert len(route.segments) == 1
        assert route.segments[0].instruction == "Head south on Market St"
    
    @pytest.mark.asyncio
    async def test_calculate_route_with_waypoints(self, directions_service, mock_maps_client):
        """Test route calculation with waypoints."""
        origin = {"lat": 37.7749, "lng": -122.4194}
        destination = {"lat": 34.0522, "lng": -118.2437}
        waypoints = [
            {"lat": 36.1699, "lng": -119.7462, "name": "Fresno, CA"}
        ]
        
        mock_maps_client.directions.return_value = [{
            "legs": [
                {  # SF to Fresno
                    "distance": {"value": 300000},
                    "duration": {"value": 10800},
                    "steps": [{"distance": {"value": 1000}, "duration": {"value": 120}}]
                },
                {  # Fresno to LA
                    "distance": {"value": 316000},
                    "duration": {"value": 10800},
                    "steps": [{"distance": {"value": 1000}, "duration": {"value": 120}}]
                }
            ],
            "overview_polyline": {"points": "encoded"},
            "waypoint_order": [0]
        }]
        
        route = await directions_service.calculate_route(
            origin, destination, waypoints=waypoints
        )
        
        assert route.distance_meters == 616000  # Total distance
        assert len(route.waypoints) == 1
        assert route.waypoints[0]["name"] == "Fresno, CA"
    
    @pytest.mark.asyncio
    async def test_calculate_route_with_preferences(self, directions_service, mock_maps_client):
        """Test route calculation with user preferences."""
        origin = {"lat": 37.7749, "lng": -122.4194}
        destination = {"lat": 34.0522, "lng": -118.2437}
        
        preferences = RoutePreference(
            avoid_highways=True,
            avoid_tolls=True,
            prefer_scenic=True
        )
        
        # Should be called with avoid parameters
        mock_maps_client.directions.return_value = [{
            "legs": [{"distance": {"value": 650000}, "duration": {"value": 25000}}],
            "overview_polyline": {"points": "scenic_route"}
        }]
        
        route = await directions_service.calculate_route(
            origin, destination, preferences=preferences
        )
        
        # Verify API was called with correct parameters
        call_args = mock_maps_client.directions.call_args[1]
        assert call_args.get("avoid") == ["highways", "tolls"]
        assert route.distance_meters == 650000  # Longer scenic route
    
    @pytest.mark.asyncio
    async def test_calculate_route_with_traffic(self, directions_service, mock_maps_client):
        """Test route calculation with real-time traffic."""
        origin = {"lat": 37.7749, "lng": -122.4194}
        destination = {"lat": 34.0522, "lng": -118.2437}
        
        # Mock response with traffic
        mock_maps_client.directions.return_value = [{
            "legs": [{
                "distance": {"value": 616000},
                "duration": {"value": 21600},
                "duration_in_traffic": {"value": 25200}  # 7 hours with traffic
            }],
            "overview_polyline": {"points": "traffic_route"}
        }]
        
        route = await directions_service.calculate_route(
            origin, destination, 
            departure_time="now",
            use_real_time_traffic=True
        )
        
        assert route.duration_seconds == 25200  # Uses traffic duration
        assert route.traffic_condition == TrafficCondition.HEAVY
        assert route.traffic_delay_seconds == 3600  # 1 hour delay
    
    @pytest.mark.asyncio
    async def test_calculate_alternative_routes(self, directions_service, mock_maps_client):
        """Test calculating alternative routes."""
        origin = {"lat": 37.7749, "lng": -122.4194}
        destination = {"lat": 34.0522, "lng": -118.2437}
        
        # Mock multiple route alternatives
        mock_maps_client.directions.return_value = [
            {  # Route 1 - Fastest
                "legs": [{"distance": {"value": 616000}, "duration": {"value": 21600}}],
                "summary": "I-5 S"
            },
            {  # Route 2 - Scenic
                "legs": [{"distance": {"value": 650000}, "duration": {"value": 24000}}],
                "summary": "US-101 S"
            },
            {  # Route 3 - Shortest
                "legs": [{"distance": {"value": 600000}, "duration": {"value": 22000}}],
                "summary": "CA-99 S"
            }
        ]
        
        routes = await directions_service.calculate_alternative_routes(
            origin, destination, max_alternatives=3
        )
        
        assert len(routes) == 3
        assert routes[0].summary == "I-5 S"
        assert routes[1].distance_meters == 650000
        assert all(isinstance(r, Route) for r in routes)


class TestNavigation:
    """Test real-time navigation functionality."""
    
    @pytest.mark.asyncio
    async def test_start_navigation(self, directions_service, sample_route, mock_user):
        """Test starting navigation."""
        nav_state = await directions_service.start_navigation(
            sample_route, mock_user
        )
        
        assert isinstance(nav_state, NavigationState)
        assert nav_state.is_active is True
        assert nav_state.current_segment_index == 0
        assert nav_state.route == sample_route
        assert nav_state.start_time is not None
    
    @pytest.mark.asyncio
    async def test_update_navigation_position(self, directions_service, sample_route):
        """Test updating position during navigation."""
        # Start navigation
        nav_state = await directions_service.start_navigation(sample_route, Mock())
        
        # Update position
        new_position = {"lat": 37.7799, "lng": -122.4144}
        updated_state = await directions_service.update_navigation_position(
            nav_state, new_position
        )
        
        assert updated_state.current_position == new_position
        assert updated_state.distance_traveled > 0
        assert updated_state.distance_to_destination < sample_route.distance_meters
    
    @pytest.mark.asyncio
    async def test_get_next_instruction(self, directions_service, sample_route):
        """Test getting next navigation instruction."""
        nav_state = NavigationState(
            route=sample_route,
            current_segment_index=0,
            current_position={"lat": 37.7749, "lng": -122.4194},
            is_active=True
        )
        
        instruction = await directions_service.get_next_instruction(nav_state)
        
        assert isinstance(instruction, NavigationInstruction)
        assert instruction.text == "Head south on Market St"
        assert instruction.distance_meters == 1500
        assert instruction.maneuver == "turn-right"
    
    @pytest.mark.asyncio
    async def test_check_off_route(self, directions_service, sample_route, mock_maps_client):
        """Test detecting when user is off route."""
        nav_state = NavigationState(
            route=sample_route,
            current_position={"lat": 37.7749, "lng": -122.4194},
            is_active=True
        )
        
        # Position far from route
        off_route_position = {"lat": 37.8049, "lng": -122.4494}
        
        # Mock snap to roads showing position is far from route
        mock_maps_client.roads.snap_to_roads.return_value = {
            "snappedPoints": [{
                "location": {"latitude": 37.7849, "longitude": -122.4294},
                "originalIndex": 0
            }]
        }
        
        is_off_route = await directions_service.check_off_route(
            nav_state, off_route_position
        )
        
        assert is_off_route is True
    
    @pytest.mark.asyncio
    async def test_recalculate_route(self, directions_service, sample_route, mock_maps_client):
        """Test route recalculation when off route."""
        current_position = {"lat": 37.8049, "lng": -122.4494}
        destination = sample_route.destination
        
        # Mock new route
        mock_maps_client.directions.return_value = [{
            "legs": [{"distance": {"value": 620000}, "duration": {"value": 22000}}],
            "overview_polyline": {"points": "new_route"}
        }]
        
        new_route = await directions_service.recalculate_route(
            current_position, destination
        )
        
        assert isinstance(new_route, Route)
        assert new_route.distance_meters == 620000
        assert new_route.origin == current_position


class TestPointsOfInterest:
    """Test POI detection and information."""
    
    @pytest.mark.asyncio
    async def test_find_nearby_pois(self, directions_service, mock_maps_client):
        """Test finding nearby points of interest."""
        location = {"lat": 37.7749, "lng": -122.4194}
        
        # Mock places API response
        mock_maps_client.places_nearby.return_value = {
            "results": [
                {
                    "name": "Golden Gate Park",
                    "place_id": "ChIJY_gHs22HhYARZ7zHDiusuWk",
                    "geometry": {"location": {"lat": 37.7694, "lng": -122.4862}},
                    "types": ["park", "tourist_attraction"],
                    "rating": 4.7,
                    "user_ratings_total": 50000
                },
                {
                    "name": "Alcatraz Island",
                    "place_id": "ChIJmRyMs_mAhYARpViaf6JEWNE",
                    "geometry": {"location": {"lat": 37.8267, "lng": -122.4230}},
                    "types": ["tourist_attraction"],
                    "rating": 4.6,
                    "user_ratings_total": 40000
                }
            ]
        }
        
        pois = await directions_service.find_nearby_pois(
            location,
            radius_meters=5000,
            types=["tourist_attraction", "park"]
        )
        
        assert len(pois) == 2
        assert all(isinstance(poi, PointOfInterest) for poi in pois)
        assert pois[0].name == "Golden Gate Park"
        assert pois[0].rating == 4.7
        assert "tourist_attraction" in pois[1].types
    
    @pytest.mark.asyncio
    async def test_find_pois_along_route(self, directions_service, sample_route, mock_maps_client):
        """Test finding POIs along a route."""
        # Mock multiple places calls along route
        mock_maps_client.places_nearby.side_effect = [
            {  # POIs near start
                "results": [
                    {"name": "Start Restaurant", "geometry": {"location": {"lat": 37.7749, "lng": -122.4194}}}
                ]
            },
            {  # POIs midway
                "results": [
                    {"name": "Midway Gas Station", "geometry": {"location": {"lat": 36.7749, "lng": -121.4194}}}
                ]
            },
            {  # POIs near end
                "results": [
                    {"name": "End Hotel", "geometry": {"location": {"lat": 34.0522, "lng": -118.2437}}}
                ]
            }
        ]
        
        pois = await directions_service.find_pois_along_route(
            sample_route,
            types=["restaurant", "gas_station", "lodging"],
            max_detour_meters=5000
        )
        
        assert len(pois) >= 3
        assert any("Restaurant" in poi.name for poi in pois)
        assert any("Gas Station" in poi.name for poi in pois)
    
    @pytest.mark.asyncio
    async def test_get_poi_details(self, directions_service, mock_maps_client):
        """Test getting detailed POI information."""
        place_id = "ChIJY_gHs22HhYARZ7zHDiusuWk"
        
        # Mock place details response
        mock_maps_client.place.return_value = {
            "result": {
                "name": "Golden Gate Park",
                "formatted_address": "San Francisco, CA 94122",
                "formatted_phone_number": "(415) 831-2700",
                "opening_hours": {
                    "open_now": True,
                    "weekday_text": [
                        "Monday: 6:00 AM – 10:00 PM",
                        "Tuesday: 6:00 AM – 10:00 PM"
                    ]
                },
                "website": "https://goldengatepark.com",
                "photos": [{"photo_reference": "photo123"}],
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Beautiful park!",
                        "time": 1234567890
                    }
                ]
            }
        }
        
        details = await directions_service.get_poi_details(place_id)
        
        assert details["name"] == "Golden Gate Park"
        assert details["phone"] == "(415) 831-2700"
        assert details["open_now"] is True
        assert len(details["reviews"]) == 1


class TestRouteOptimization:
    """Test route optimization features."""
    
    @pytest.mark.asyncio
    async def test_optimize_waypoint_order(self, directions_service, mock_maps_client):
        """Test optimizing order of waypoints."""
        origin = {"lat": 37.7749, "lng": -122.4194}
        destination = {"lat": 34.0522, "lng": -118.2437}
        waypoints = [
            {"lat": 36.7783, "lng": -119.4179, "name": "Fresno"},
            {"lat": 35.3733, "lng": -119.0187, "name": "Bakersfield"},
            {"lat": 36.1699, "lng": -115.1398, "name": "Las Vegas"}
        ]
        
        # Mock distance matrix for optimization
        mock_maps_client.distance_matrix.return_value = {
            "rows": [
                {"elements": [{"distance": {"value": 100000}}, {"distance": {"value": 200000}}, {"distance": {"value": 300000}}]},
                {"elements": [{"distance": {"value": 150000}}, {"distance": {"value": 100000}}, {"distance": {"value": 250000}}]},
                {"elements": [{"distance": {"value": 200000}}, {"distance": {"value": 150000}}, {"distance": {"value": 100000}}]}
            ]
        }
        
        optimized = await directions_service.optimize_waypoint_order(
            origin, destination, waypoints
        )
        
        assert len(optimized) == len(waypoints)
        # Should be reordered for efficiency
        assert optimized != waypoints  # Order should change
    
    @pytest.mark.asyncio
    async def test_find_optimal_departure_time(self, directions_service, mock_maps_client):
        """Test finding optimal departure time to avoid traffic."""
        origin = {"lat": 37.7749, "lng": -122.4194}
        destination = {"lat": 34.0522, "lng": -118.2437}
        
        # Mock different traffic conditions at different times
        mock_maps_client.directions.side_effect = [
            # Morning - heavy traffic
            [{"legs": [{"duration_in_traffic": {"value": 28800}}]}],  # 8 hours
            # Midday - moderate traffic
            [{"legs": [{"duration_in_traffic": {"value": 23400}}]}],  # 6.5 hours
            # Evening - heavy traffic
            [{"legs": [{"duration_in_traffic": {"value": 27000}}]}],  # 7.5 hours
            # Night - light traffic
            [{"legs": [{"duration_in_traffic": {"value": 21600}}]}],  # 6 hours
        ]
        
        optimal_time = await directions_service.find_optimal_departure_time(
            origin, destination,
            target_arrival=datetime.now() + timedelta(days=1, hours=12)
        )
        
        assert optimal_time is not None
        # Should recommend night departure for least traffic
        assert optimal_time.hour in [22, 23, 0, 1, 2, 3, 4, 5]  # Night hours


class TestTrafficUpdates:
    """Test real-time traffic updates."""
    
    @pytest.mark.asyncio
    async def test_get_traffic_conditions(self, directions_service, sample_route, mock_maps_client):
        """Test getting current traffic conditions."""
        # Mock traffic update
        mock_maps_client.directions.return_value = [{
            "legs": [{
                "duration": {"value": 21600},
                "duration_in_traffic": {"value": 25200}  # Slower due to traffic
            }]
        }]
        
        traffic = await directions_service.get_traffic_conditions(sample_route)
        
        assert traffic["condition"] == TrafficCondition.HEAVY
        assert traffic["delay_seconds"] == 3600
        assert traffic["updated_eta"] > sample_route.estimated_arrival
    
    @pytest.mark.asyncio
    async def test_monitor_traffic_changes(self, directions_service, sample_route):
        """Test monitoring traffic changes during navigation."""
        # Create traffic monitor
        monitor = await directions_service.create_traffic_monitor(sample_route)
        
        # Simulate traffic updates
        updates = []
        
        async def collect_updates():
            async for update in monitor.get_updates():
                updates.append(update)
                if len(updates) >= 2:
                    break
        
        # Run monitor for a short time
        await asyncio.wait_for(collect_updates(), timeout=5.0)
        
        assert len(updates) >= 1
        assert all("condition" in u for u in updates)


class TestErrorHandling:
    """Test error handling in directions service."""
    
    @pytest.mark.asyncio
    async def test_handle_api_error(self, directions_service, mock_maps_client):
        """Test handling Google Maps API errors."""
        origin = {"lat": 37.7749, "lng": -122.4194}
        destination = {"lat": 34.0522, "lng": -118.2437}
        
        # Mock API error
        mock_maps_client.directions.side_effect = Exception("API quota exceeded")
        
        with pytest.raises(Exception) as exc_info:
            await directions_service.calculate_route(origin, destination)
        
        assert "quota exceeded" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_handle_no_route_found(self, directions_service, mock_maps_client):
        """Test handling when no route can be found."""
        origin = {"lat": 37.7749, "lng": -122.4194}
        destination = {"lat": 90.0000, "lng": 0.0000}  # North Pole
        
        # Mock empty response
        mock_maps_client.directions.return_value = []
        
        route = await directions_service.calculate_route(origin, destination)
        
        assert route is None
    
    @pytest.mark.asyncio
    async def test_handle_invalid_location(self, directions_service):
        """Test handling invalid location data."""
        invalid_origin = {"latitude": 37.7749}  # Wrong key
        destination = {"lat": 34.0522, "lng": -118.2437}
        
        with pytest.raises(ValueError) as exc_info:
            await directions_service.calculate_route(invalid_origin, destination)
        
        assert "invalid location" in str(exc_info.value).lower()


class TestDirectionsIntegration:
    """Test full directions service integration."""
    
    @pytest.mark.asyncio
    async def test_complete_navigation_flow(self, directions_service, mock_maps_client, mock_user):
        """Test complete navigation flow from start to finish."""
        origin = {"lat": 37.7749, "lng": -122.4194}
        destination = {"lat": 37.7849, "lng": -122.4094}  # Short trip
        
        # Step 1: Calculate route
        mock_maps_client.directions.return_value = [{
            "legs": [{
                "distance": {"value": 2000},
                "duration": {"value": 300},
                "steps": [
                    {
                        "distance": {"value": 1000},
                        "duration": {"value": 150},
                        "html_instructions": "Head south",
                        "start_location": origin,
                        "end_location": {"lat": 37.7799, "lng": -122.4144}
                    },
                    {
                        "distance": {"value": 1000},
                        "duration": {"value": 150},
                        "html_instructions": "Turn left",
                        "start_location": {"lat": 37.7799, "lng": -122.4144},
                        "end_location": destination
                    }
                ]
            }]
        }]
        
        route = await directions_service.calculate_route(origin, destination)
        assert route is not None
        
        # Step 2: Start navigation
        nav_state = await directions_service.start_navigation(route, mock_user)
        assert nav_state.is_active
        
        # Step 3: Simulate movement
        positions = [
            origin,
            {"lat": 37.7799, "lng": -122.4144},  # Midpoint
            destination
        ]
        
        for pos in positions:
            nav_state = await directions_service.update_navigation_position(
                nav_state, pos
            )
            
            # Get instruction for current position
            if nav_state.is_active:
                instruction = await directions_service.get_next_instruction(nav_state)
                assert instruction is not None
        
        # Step 4: Complete navigation
        completed = await directions_service.complete_navigation(nav_state)
        assert completed["success"] is True
        assert completed["total_distance"] == 2000
        assert completed["total_duration"] >= 300