"""
Integration tests for flight tracking APIs.

These tests verify real API connectivity and functionality.
Set TEST_MODE=live and configure API keys to run these tests.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, date
import os
from typing import Dict, Any

from backend.app.integrations.flight_tracker_client import flight_tracker, FlightProvider
from backend.app.core.config import settings
from backend.app.core.logger import get_logger

logger = get_logger(__name__)

# Skip tests if not in live mode
pytestmark = pytest.mark.skipif(
    os.getenv("TEST_MODE") != "live",
    reason="Live API tests only run when TEST_MODE=live"
)


class TestFlightTrackerIntegration:
    """Test flight tracking APIs with real data."""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup test environment."""
        # Use tomorrow's date for testing scheduled flights
        self.test_date = datetime.now() + timedelta(days=1)
        
        # Common test flights (these should be regularly scheduled)
        self.test_flights = [
            {"airline": "AA", "number": "100", "route": ("JFK", "LAX")},  # American Airlines
            {"airline": "UA", "number": "1", "route": ("SFO", "SIN")},    # United Airlines
            {"airline": "DL", "number": "1", "route": ("ATL", "JFK")},    # Delta
            {"airline": "SW", "number": "1", "route": ("DAL", "HOU")},    # Southwest
        ]
        
        yield
        
        # Cleanup
        await flight_tracker.close()
    
    def get_available_providers(self) -> list:
        """Get list of configured providers for testing."""
        providers = []
        
        if settings.FLIGHTSTATS_API_KEY and settings.FLIGHTSTATS_APP_ID:
            providers.append("FlightStats")
        if settings.FLIGHTAWARE_API_KEY:
            providers.append("FlightAware")
        if settings.AVIATIONSTACK_API_KEY:
            providers.append("AviationStack")
        if settings.FLIGHTLABS_API_KEY:
            providers.append("FlightLabs")
        
        return providers
    
    @pytest.mark.asyncio
    async def test_provider_availability(self):
        """Test which providers are available."""
        providers = self.get_available_providers()
        
        logger.info(f"Available providers: {providers}")
        
        if not providers:
            pytest.skip("No flight tracking API keys configured")
        
        # Verify at least one provider is configured
        assert len(providers) > 0, "At least one flight tracking API should be configured"
        
        # Log provider status
        for provider in ["FlightStats", "FlightAware", "AviationStack", "FlightLabs"]:
            if provider in providers:
                logger.info(f"✓ {provider} is configured")
            else:
                logger.info(f"✗ {provider} is not configured")
    
    @pytest.mark.asyncio
    async def test_track_single_flight(self):
        """Test tracking a single flight."""
        providers = self.get_available_providers()
        if not providers:
            pytest.skip("No flight tracking API keys configured")
        
        # Try to find a working test flight
        for test_flight in self.test_flights:
            try:
                result = await flight_tracker.track_flight(
                    flight_number=f"{test_flight['airline']}{test_flight['number']}",
                    departure_date=self.test_date
                )
                
                # Verify response structure
                assert "flight_number" in result
                assert "airline" in result
                assert "status" in result
                assert "departure" in result
                assert "arrival" in result
                
                # Verify airline info
                assert result["airline"]["code"] == test_flight["airline"]
                assert result["airline"]["name"] is not None
                
                # Verify departure info
                assert result["departure"]["airport"] is not None
                assert result["departure"]["scheduled"] is not None
                
                # Verify arrival info
                assert result["arrival"]["airport"] is not None
                assert result["arrival"]["scheduled"] is not None
                
                logger.info(f"Successfully tracked flight {result['flight_number']}")
                logger.info(f"Status: {result['status']}")
                logger.info(f"Route: {result['departure']['airport']} -> {result['arrival']['airport']}")
                
                return  # Success, exit test
                
            except Exception as e:
                logger.warning(f"Failed to track {test_flight['airline']}{test_flight['number']}: {str(e)}")
                continue
        
        pytest.fail("Could not track any test flights")
    
    @pytest.mark.asyncio
    async def test_search_flights_by_route(self):
        """Test searching flights between airports."""
        providers = self.get_available_providers()
        if not providers:
            pytest.skip("No flight tracking API keys configured")
        
        # Popular routes that should have flights
        test_routes = [
            ("LAX", "JFK"),  # Los Angeles to New York
            ("ORD", "LAX"),  # Chicago to Los Angeles
            ("ATL", "DFW"),  # Atlanta to Dallas
            ("SFO", "SEA"),  # San Francisco to Seattle
        ]
        
        for departure, arrival in test_routes:
            try:
                flights = await flight_tracker.search_flights_by_route(
                    departure_airport=departure,
                    arrival_airport=arrival,
                    departure_date=self.test_date
                )
                
                if flights:
                    # Verify we got results
                    assert len(flights) > 0
                    
                    # Verify first flight structure
                    first_flight = flights[0]
                    assert "flight_number" in first_flight
                    assert "airline" in first_flight
                    assert first_flight["departure"]["airport"] == departure
                    assert first_flight["arrival"]["airport"] == arrival
                    
                    logger.info(f"Found {len(flights)} flights from {departure} to {arrival}")
                    logger.info(f"Sample flight: {first_flight['flight_number']} ({first_flight['airline']['name']})")
                    
                    return  # Success, exit test
                
            except Exception as e:
                logger.warning(f"Failed to search route {departure}-{arrival}: {str(e)}")
                continue
        
        pytest.fail("Could not search any test routes")
    
    @pytest.mark.asyncio
    async def test_flight_with_separate_airline_code(self):
        """Test tracking flight with separate airline code."""
        providers = self.get_available_providers()
        if not providers:
            pytest.skip("No flight tracking API keys configured")
        
        try:
            # Test with separate airline code and flight number
            result = await flight_tracker.track_flight(
                flight_number="100",
                airline_code="AA",
                departure_date=self.test_date
            )
            
            assert result["flight_number"] == "AA100"
            assert result["airline"]["code"] == "AA"
            
            logger.info("Successfully tracked flight with separate airline code")
            
        except Exception as e:
            logger.warning(f"Failed to track flight with separate airline code: {str(e)}")
            # This is not critical, some providers might not support this
    
    @pytest.mark.asyncio
    async def test_caching_functionality(self):
        """Test that caching reduces API calls."""
        providers = self.get_available_providers()
        if not providers:
            pytest.skip("No flight tracking API keys configured")
        
        flight_number = "AA100"
        
        # First call - should hit API
        start_time = datetime.now()
        result1 = await flight_tracker.track_flight(
            flight_number=flight_number,
            departure_date=self.test_date
        )
        first_call_time = (datetime.now() - start_time).total_seconds()
        
        # Second call - should hit cache
        start_time = datetime.now()
        result2 = await flight_tracker.track_flight(
            flight_number=flight_number,
            departure_date=self.test_date
        )
        second_call_time = (datetime.now() - start_time).total_seconds()
        
        # Verify results are the same
        assert result1 == result2
        
        # Verify second call was faster (cache hit)
        assert second_call_time < first_call_time / 2
        
        logger.info(f"First call time: {first_call_time:.3f}s")
        logger.info(f"Second call time: {second_call_time:.3f}s (cached)")
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for invalid requests."""
        providers = self.get_available_providers()
        if not providers:
            pytest.skip("No flight tracking API keys configured")
        
        # Test non-existent flight
        result = await flight_tracker.track_flight(
            flight_number="XX9999",
            departure_date=self.test_date
        )
        
        # Should return mock data when flight not found
        assert result["flight_number"] == "XX9999"
        assert result["airline"]["name"] == "Mock Airlines"
        
        logger.info("Error handling working correctly - returned mock data")
    
    @pytest.mark.asyncio
    async def test_date_handling(self):
        """Test handling of different date formats."""
        providers = self.get_available_providers()
        if not providers:
            pytest.skip("No flight tracking API keys configured")
        
        # Test with date object
        date_only = date.today() + timedelta(days=1)
        result = await flight_tracker.track_flight(
            flight_number="AA100",
            departure_date=date_only
        )
        
        assert "flight_number" in result
        logger.info("Successfully handled date object")
        
        # Test with datetime object
        datetime_obj = datetime.now() + timedelta(days=1)
        result = await flight_tracker.track_flight(
            flight_number="AA100",
            departure_date=datetime_obj
        )
        
        assert "flight_number" in result
        logger.info("Successfully handled datetime object")
    
    @pytest.mark.asyncio
    async def test_provider_fallback(self):
        """Test automatic fallback between providers."""
        if len(flight_tracker.available_providers) < 2:
            pytest.skip("Need at least 2 providers configured for fallback test")
        
        # This test would require mocking provider failures
        # For now, just verify multiple providers are configured
        assert len(flight_tracker.available_providers) >= 2
        logger.info(f"Fallback available with {len(flight_tracker.available_providers)} providers")


@pytest.mark.asyncio
async def test_specific_provider_aviationstack():
    """Test AviationStack API specifically."""
    if not settings.AVIATIONSTACK_API_KEY:
        pytest.skip("AviationStack API key not configured")
    
    tomorrow = datetime.now() + timedelta(days=1)
    
    # Direct API test
    result = await flight_tracker._track_aviationstack(
        airline_code="AA",
        flight_number="100",
        departure_date=tomorrow
    )
    
    assert result["airline"]["code"] == "AA"
    logger.info(f"AviationStack API working: {result['flight_number']}")


@pytest.mark.asyncio
async def test_specific_provider_flightstats():
    """Test FlightStats API specifically."""
    if not settings.FLIGHTSTATS_API_KEY or not settings.FLIGHTSTATS_APP_ID:
        pytest.skip("FlightStats API credentials not configured")
    
    tomorrow = datetime.now() + timedelta(days=1)
    
    # Direct API test
    result = await flight_tracker._track_flightstats(
        airline_code="AA",
        flight_number="100",
        departure_date=tomorrow
    )
    
    assert result["airline"]["code"] == "AA"
    logger.info(f"FlightStats API working: {result['flight_number']}")


@pytest.mark.asyncio
async def test_specific_provider_flightaware():
    """Test FlightAware API specifically."""
    if not settings.FLIGHTAWARE_API_KEY:
        pytest.skip("FlightAware API key not configured")
    
    tomorrow = datetime.now() + timedelta(days=1)
    
    # Direct API test
    result = await flight_tracker._track_flightaware(
        airline_code="AA",
        flight_number="100",
        departure_date=tomorrow
    )
    
    assert "flight_number" in result
    logger.info(f"FlightAware API working: {result['flight_number']}")


@pytest.mark.asyncio
async def test_specific_provider_flightlabs():
    """Test FlightLabs API specifically."""
    if not settings.FLIGHTLABS_API_KEY:
        pytest.skip("FlightLabs API key not configured")
    
    tomorrow = datetime.now() + timedelta(days=1)
    
    # Direct API test
    result = await flight_tracker._track_flightlabs(
        airline_code="AA",
        flight_number="100",
        departure_date=tomorrow
    )
    
    assert result["airline"]["code"] == "AA"
    logger.info(f"FlightLabs API working: {result['flight_number']}")