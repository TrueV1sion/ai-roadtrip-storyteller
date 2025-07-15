"""
Comprehensive unit tests for the reservation management system
Tests cover: ReservationManagementService, multi-provider integration, booking lifecycle
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import json
from typing import Dict, List, Any

from backend.app.services.reservation_management_service import (
    ReservationManagementService, BookingProvider, ReservationStatus,
    ProviderConfig, SearchResult, BookingResult
)


class TestReservationManagementService:
    """Test suite for ReservationManagementService"""
    
    @pytest.fixture
    def reservation_service(self):
        """Create a ReservationManagementService instance with mocked providers"""
        service = ReservationManagementService()
        
        # Mock all provider clients
        service.providers = {
            BookingProvider.OPENTABLE: Mock(),
            BookingProvider.YELP: Mock(),
            BookingProvider.RESY: Mock(),
            BookingProvider.GOOGLE: Mock()
        }
        
        return service
    
    @pytest.fixture
    def sample_search_params(self):
        """Sample search parameters"""
        return {
            "query": "Italian restaurant",
            "location": {"lat": 40.7128, "lng": -74.0060},
            "date": datetime.now() + timedelta(days=1),
            "party_size": 4,
            "cuisine": ["Italian"],
            "price_range": "2-3",
            "amenities": ["outdoor seating", "parking"]
        }
    
    @pytest.fixture
    def sample_venue(self):
        """Sample venue data"""
        return {
            "venue_id": "venue123",
            "name": "Mario's Italian Restaurant",
            "cuisine": "Italian",
            "rating": 4.5,
            "price_range": "3",
            "distance": 0.5,
            "available_times": ["18:00", "18:30", "19:00", "20:00"],
            "image_url": "http://example.com/image.jpg",
            "description": "Authentic Italian cuisine",
            "amenities": ["outdoor seating", "parking", "bar"]
        }
    
    @pytest.mark.asyncio
    async def test_search_all_providers_success(self, reservation_service, sample_search_params, sample_venue):
        """Test searching across all providers successfully"""
        # Mock provider responses
        opentable_results = [sample_venue.copy()]
        opentable_results[0]["provider"] = "opentable"
        
        yelp_results = [sample_venue.copy()]
        yelp_results[0]["provider"] = "yelp"
        yelp_results[0]["venue_id"] = "yelp_venue456"
        
        reservation_service.providers[BookingProvider.OPENTABLE].search = AsyncMock(
            return_value=opentable_results
        )
        reservation_service.providers[BookingProvider.YELP].search = AsyncMock(
            return_value=yelp_results
        )
        reservation_service.providers[BookingProvider.RESY].search = AsyncMock(
            return_value=[]
        )
        reservation_service.providers[BookingProvider.GOOGLE].search = AsyncMock(
            return_value=[]
        )
        
        # Execute search
        results = await reservation_service.search_all_providers(**sample_search_params)
        
        assert len(results) == 2
        assert results[0]["provider"] == "opentable"
        assert results[1]["provider"] == "yelp"
        
        # Verify all providers were called
        for provider in reservation_service.providers.values():
            provider.search.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_search_with_provider_failure(self, reservation_service, sample_search_params):
        """Test search handling when some providers fail"""
        # OpenTable succeeds
        reservation_service.providers[BookingProvider.OPENTABLE].search = AsyncMock(
            return_value=[{"venue_id": "123", "name": "Test Restaurant", "provider": "opentable"}]
        )
        
        # Yelp fails
        reservation_service.providers[BookingProvider.YELP].search = AsyncMock(
            side_effect=Exception("Yelp API error")
        )
        
        # Others return empty
        reservation_service.providers[BookingProvider.RESY].search = AsyncMock(return_value=[])
        reservation_service.providers[BookingProvider.GOOGLE].search = AsyncMock(return_value=[])
        
        results = await reservation_service.search_all_providers(**sample_search_params)
        
        # Should still return results from successful providers
        assert len(results) == 1
        assert results[0]["provider"] == "opentable"
    
    @pytest.mark.asyncio
    async def test_search_deduplication(self, reservation_service, sample_search_params):
        """Test deduplication of venues across providers"""
        # Same venue from multiple providers
        venue_base = {
            "name": "Mario's Italian",
            "address": "123 Main St",
            "cuisine": "Italian"
        }
        
        opentable_venue = {**venue_base, "venue_id": "ot_123", "provider": "opentable"}
        yelp_venue = {**venue_base, "venue_id": "yelp_456", "provider": "yelp"}
        
        reservation_service.providers[BookingProvider.OPENTABLE].search = AsyncMock(
            return_value=[opentable_venue]
        )
        reservation_service.providers[BookingProvider.YELP].search = AsyncMock(
            return_value=[yelp_venue]
        )
        reservation_service.providers[BookingProvider.RESY].search = AsyncMock(return_value=[])
        reservation_service.providers[BookingProvider.GOOGLE].search = AsyncMock(return_value=[])
        
        # Mock deduplication logic
        reservation_service._deduplicate_venues = Mock(return_value=[opentable_venue])
        
        results = await reservation_service.search_all_providers(**sample_search_params)
        
        reservation_service._deduplicate_venues.assert_called_once()
        assert len(results) == 1
    
    @pytest.mark.asyncio
    async def test_create_reservation_success(self, reservation_service):
        """Test successful reservation creation"""
        # Mock provider response
        booking_result = {
            "confirmation_number": "CONF123456",
            "status": "confirmed",
            "venue_name": "Mario's Italian",
            "reservation_time": datetime.now() + timedelta(days=1),
            "party_size": 4,
            "special_requests": "Window seat please",
            "cancellation_policy": "Cancel up to 2 hours before",
            "modification_allowed": True
        }
        
        reservation_service.providers[BookingProvider.OPENTABLE].create_reservation = AsyncMock(
            return_value=booking_result
        )
        
        result = await reservation_service.create_reservation(
            user_id="user123",
            provider=BookingProvider.OPENTABLE,
            venue_id="venue123",
            date_time=datetime.now() + timedelta(days=1),
            party_size=4,
            customer_info={
                "firstName": "John",
                "lastName": "Doe",
                "email": "john@example.com",
                "phone": "555-1234"
            },
            special_requests="Window seat please"
        )
        
        assert result["confirmation_number"] == "CONF123456"
        assert result["status"] == "confirmed"
        reservation_service.providers[BookingProvider.OPENTABLE].create_reservation.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_reservation_failure(self, reservation_service):
        """Test reservation creation failure handling"""
        reservation_service.providers[BookingProvider.OPENTABLE].create_reservation = AsyncMock(
            side_effect=Exception("Restaurant fully booked")
        )
        
        with pytest.raises(Exception, match="Restaurant fully booked"):
            await reservation_service.create_reservation(
                user_id="user123",
                provider=BookingProvider.OPENTABLE,
                venue_id="venue123",
                date_time=datetime.now() + timedelta(days=1),
                party_size=4,
                customer_info={"firstName": "John", "lastName": "Doe"}
            )
    
    @pytest.mark.asyncio
    async def test_modify_reservation(self, reservation_service):
        """Test modifying an existing reservation"""
        modification_result = {
            "confirmation_number": "CONF123456",
            "status": "modified",
            "new_time": datetime.now() + timedelta(days=2),
            "new_party_size": 6
        }
        
        reservation_service.providers[BookingProvider.OPENTABLE].modify_reservation = AsyncMock(
            return_value=modification_result
        )
        
        result = await reservation_service.modify_reservation(
            user_id="user123",
            provider=BookingProvider.OPENTABLE,
            confirmation_number="CONF123456",
            new_date_time=datetime.now() + timedelta(days=2),
            new_party_size=6
        )
        
        assert result["status"] == "modified"
        assert result["new_party_size"] == 6
    
    @pytest.mark.asyncio
    async def test_cancel_reservation(self, reservation_service):
        """Test cancelling a reservation"""
        cancellation_result = {
            "confirmation_number": "CONF123456",
            "status": "cancelled",
            "cancellation_time": datetime.now(),
            "refund_status": "full_refund"
        }
        
        reservation_service.providers[BookingProvider.OPENTABLE].cancel_reservation = AsyncMock(
            return_value=cancellation_result
        )
        
        result = await reservation_service.cancel_reservation(
            user_id="user123",
            provider=BookingProvider.OPENTABLE,
            confirmation_number="CONF123456"
        )
        
        assert result["status"] == "cancelled"
        assert result["refund_status"] == "full_refund"
    
    @pytest.mark.asyncio
    async def test_check_availability(self, reservation_service):
        """Test checking availability for a specific venue"""
        available_times = ["17:00", "17:30", "18:00", "19:00", "20:00", "20:30"]
        
        reservation_service.providers[BookingProvider.RESY].check_availability = AsyncMock(
            return_value=available_times
        )
        
        result = await reservation_service.check_availability(
            provider=BookingProvider.RESY,
            venue_id="venue789",
            date=datetime.now() + timedelta(days=3),
            party_size=2
        )
        
        assert len(result) == 6
        assert "18:00" in result
    
    @pytest.mark.asyncio
    async def test_add_to_waitlist(self, reservation_service):
        """Test adding user to waitlist"""
        waitlist_result = {
            "waitlist_id": "WL123456",
            "position": 3,
            "estimated_wait": "15-30 minutes",
            "notification_preferences": ["email", "sms"]
        }
        
        reservation_service.providers[BookingProvider.OPENTABLE].add_to_waitlist = AsyncMock(
            return_value=waitlist_result
        )
        
        result = await reservation_service.add_to_waitlist(
            user_id="user123",
            venue_id="venue123",
            provider=BookingProvider.OPENTABLE,
            desired_date=datetime.now() + timedelta(hours=2),
            party_size=4,
            time_flexibility="1_hour"
        )
        
        assert result["position"] == 3
        assert "waitlist_id" in result
    
    @pytest.mark.asyncio
    async def test_provider_priority_ordering(self, reservation_service):
        """Test that search results are ordered by provider priority"""
        # Set provider priorities
        reservation_service.provider_priority = {
            BookingProvider.OPENTABLE: 1,
            BookingProvider.RESY: 2,
            BookingProvider.YELP: 3,
            BookingProvider.GOOGLE: 4
        }
        
        # Mock results from different providers
        results = [
            {"provider": "yelp", "venue_id": "y1", "rating": 4.5},
            {"provider": "opentable", "venue_id": "ot1", "rating": 4.0},
            {"provider": "resy", "venue_id": "r1", "rating": 4.3}
        ]
        
        sorted_results = reservation_service._sort_by_relevance(results)
        
        # Should be ordered by provider priority
        assert sorted_results[0]["provider"] == "opentable"
        assert sorted_results[1]["provider"] == "resy"
        assert sorted_results[2]["provider"] == "yelp"


class TestProviderIntegration:
    """Test individual provider integrations"""
    
    @pytest.mark.asyncio
    async def test_opentable_search_formatting(self):
        """Test OpenTable-specific search parameter formatting"""
        from backend.app.services.providers.opentable_provider import OpenTableProvider
        
        provider = OpenTableProvider(api_key="test_key")
        provider._make_request = AsyncMock(return_value={
            "restaurants": [
                {
                    "id": "123",
                    "name": "Test Restaurant",
                    "cuisine": "Italian",
                    "rating": 4.5,
                    "price_range": 3,
                    "available_times": ["18:00", "19:00"]
                }
            ]
        })
        
        results = await provider.search(
            location={"lat": 40.7128, "lng": -74.0060},
            date=datetime.now() + timedelta(days=1),
            party_size=2,
            cuisine=["Italian"]
        )
        
        assert len(results) == 1
        assert results[0]["venue_id"] == "123"
        provider._make_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_yelp_fusion_integration(self):
        """Test Yelp Fusion API integration"""
        from backend.app.services.providers.yelp_provider import YelpProvider
        
        provider = YelpProvider(api_key="test_key")
        
        # Mock Yelp API responses
        provider._search_businesses = AsyncMock(return_value={
            "businesses": [
                {
                    "id": "mario-italian-nyc",
                    "name": "Mario's Italian",
                    "categories": [{"title": "Italian"}],
                    "rating": 4.5,
                    "price": "$$$",
                    "distance": 500.0,
                    "image_url": "http://example.com/image.jpg"
                }
            ]
        })
        
        provider._get_availability = AsyncMock(return_value=["18:00", "19:00", "20:00"])
        
        results = await provider.search(
            location={"lat": 40.7128, "lng": -74.0060},
            date=datetime.now() + timedelta(days=1),
            party_size=4
        )
        
        assert len(results) == 1
        assert results[0]["name"] == "Mario's Italian"
        assert results[0]["distance"] == 0.31  # 500m converted to miles
    
    @pytest.mark.asyncio
    async def test_provider_error_handling(self):
        """Test provider-specific error handling"""
        from backend.app.services.providers.resy_provider import ResyProvider
        
        provider = ResyProvider(api_key="test_key")
        
        # Mock API error
        provider._make_request = AsyncMock(
            side_effect=Exception("401 Unauthorized")
        )
        
        with pytest.raises(Exception, match="401 Unauthorized"):
            await provider.search(
                location={"lat": 40.7128, "lng": -74.0060},
                date=datetime.now(),
                party_size=2
            )


class TestReservationLifecycle:
    """Test complete reservation lifecycle scenarios"""
    
    @pytest.mark.asyncio
    async def test_complete_booking_flow(self):
        """Test complete flow: search -> book -> modify -> cancel"""
        service = ReservationManagementService()
        
        # Mock provider
        mock_provider = Mock()
        service.providers[BookingProvider.OPENTABLE] = mock_provider
        
        # 1. Search
        search_results = [{
            "venue_id": "venue123",
            "name": "Test Restaurant",
            "available_times": ["18:00", "19:00"],
            "provider": "opentable"
        }]
        mock_provider.search = AsyncMock(return_value=search_results)
        
        results = await service.search_all_providers(
            query="restaurant",
            location={"lat": 0, "lng": 0},
            date=datetime.now() + timedelta(days=1),
            party_size=2
        )
        assert len(results) == 1
        
        # 2. Book
        booking_result = {
            "confirmation_number": "CONF123",
            "status": "confirmed"
        }
        mock_provider.create_reservation = AsyncMock(return_value=booking_result)
        
        booking = await service.create_reservation(
            user_id="user1",
            provider=BookingProvider.OPENTABLE,
            venue_id="venue123",
            date_time=datetime.now() + timedelta(days=1, hours=18),
            party_size=2,
            customer_info={"firstName": "John", "lastName": "Doe"}
        )
        assert booking["confirmation_number"] == "CONF123"
        
        # 3. Modify
        modification_result = {
            "confirmation_number": "CONF123",
            "status": "modified",
            "new_party_size": 4
        }
        mock_provider.modify_reservation = AsyncMock(return_value=modification_result)
        
        modified = await service.modify_reservation(
            user_id="user1",
            provider=BookingProvider.OPENTABLE,
            confirmation_number="CONF123",
            new_party_size=4
        )
        assert modified["new_party_size"] == 4
        
        # 4. Cancel
        cancellation_result = {
            "confirmation_number": "CONF123",
            "status": "cancelled"
        }
        mock_provider.cancel_reservation = AsyncMock(return_value=cancellation_result)
        
        cancelled = await service.cancel_reservation(
            user_id="user1",
            provider=BookingProvider.OPENTABLE,
            confirmation_number="CONF123"
        )
        assert cancelled["status"] == "cancelled"
    
    @pytest.mark.asyncio
    async def test_waitlist_to_booking_flow(self):
        """Test waitlist notification and conversion to booking"""
        service = ReservationManagementService()
        mock_provider = Mock()
        service.providers[BookingProvider.RESY] = mock_provider
        
        # 1. Add to waitlist
        waitlist_result = {
            "waitlist_id": "WL789",
            "position": 2,
            "estimated_wait": "10-20 minutes"
        }
        mock_provider.add_to_waitlist = AsyncMock(return_value=waitlist_result)
        
        waitlist = await service.add_to_waitlist(
            user_id="user1",
            venue_id="venue456",
            provider=BookingProvider.RESY,
            desired_date=datetime.now() + timedelta(hours=3),
            party_size=2
        )
        assert waitlist["position"] == 2
        
        # 2. Simulate waitlist notification
        mock_provider.check_waitlist_status = AsyncMock(return_value={
            "status": "available",
            "hold_until": datetime.now() + timedelta(minutes=10),
            "booking_token": "TOKEN123"
        })
        
        # 3. Convert to booking
        booking_result = {
            "confirmation_number": "CONF789",
            "status": "confirmed"
        }
        mock_provider.convert_waitlist_to_booking = AsyncMock(
            return_value=booking_result
        )
        
        # This would typically be triggered by a notification
        status = await mock_provider.check_waitlist_status("WL789")
        if status["status"] == "available":
            booking = await mock_provider.convert_waitlist_to_booking(
                waitlist_id="WL789",
                booking_token=status["booking_token"]
            )
            assert booking["confirmation_number"] == "CONF789"


class TestReservationValidation:
    """Test input validation and business rules"""
    
    @pytest.mark.asyncio
    async def test_party_size_validation(self):
        """Test party size limits"""
        service = ReservationManagementService()
        
        # Test minimum party size
        with pytest.raises(ValueError, match="Party size must be at least 1"):
            await service.create_reservation(
                user_id="user1",
                provider=BookingProvider.OPENTABLE,
                venue_id="venue1",
                date_time=datetime.now() + timedelta(days=1),
                party_size=0,
                customer_info={}
            )
        
        # Test maximum party size
        with pytest.raises(ValueError, match="Party size cannot exceed"):
            await service.create_reservation(
                user_id="user1",
                provider=BookingProvider.OPENTABLE,
                venue_id="venue1",
                date_time=datetime.now() + timedelta(days=1),
                party_size=25,
                customer_info={}
            )
    
    @pytest.mark.asyncio
    async def test_booking_time_validation(self):
        """Test booking time constraints"""
        service = ReservationManagementService()
        
        # Test booking in the past
        with pytest.raises(ValueError, match="Cannot book in the past"):
            await service.create_reservation(
                user_id="user1",
                provider=BookingProvider.OPENTABLE,
                venue_id="venue1",
                date_time=datetime.now() - timedelta(hours=1),
                party_size=2,
                customer_info={}
            )
        
        # Test booking too far in advance
        with pytest.raises(ValueError, match="Cannot book more than"):
            await service.create_reservation(
                user_id="user1",
                provider=BookingProvider.OPENTABLE,
                venue_id="venue1",
                date_time=datetime.now() + timedelta(days=91),
                party_size=2,
                customer_info={}
            )
    
    @pytest.mark.asyncio
    async def test_modification_deadline_validation(self):
        """Test modification deadline enforcement"""
        service = ReservationManagementService()
        mock_provider = Mock()
        service.providers[BookingProvider.OPENTABLE] = mock_provider
        
        # Mock existing reservation
        existing_reservation = {
            "confirmation_number": "CONF123",
            "reservation_time": datetime.now() + timedelta(hours=1),
            "modification_deadline": datetime.now() - timedelta(minutes=30)
        }
        
        mock_provider.get_reservation = AsyncMock(return_value=existing_reservation)
        
        with pytest.raises(ValueError, match="Modification deadline has passed"):
            await service.modify_reservation(
                user_id="user1",
                provider=BookingProvider.OPENTABLE,
                confirmation_number="CONF123",
                new_party_size=4
            )
    
    def test_customer_info_validation(self):
        """Test customer information validation"""
        service = ReservationManagementService()
        
        # Test missing required fields
        invalid_info = {
            "firstName": "John"
            # Missing lastName, email, phone
        }
        
        errors = service._validate_customer_info(invalid_info)
        assert "lastName" in errors
        assert "email" in errors
        assert "phone" in errors
        
        # Test invalid email format
        invalid_email_info = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "invalid-email",
            "phone": "555-1234"
        }
        
        errors = service._validate_customer_info(invalid_email_info)
        assert "email" in errors
        
        # Test valid info
        valid_info = {
            "firstName": "John",
            "lastName": "Doe",
            "email": "john@example.com",
            "phone": "555-1234"
        }
        
        errors = service._validate_customer_info(valid_info)
        assert len(errors) == 0


class TestReservationCaching:
    """Test caching mechanisms for performance"""
    
    @pytest.mark.asyncio
    async def test_search_result_caching(self):
        """Test caching of search results"""
        service = ReservationManagementService()
        service.cache = Mock()
        
        # Mock cache miss
        service.cache.get = Mock(return_value=None)
        service.cache.set = Mock()
        
        # Mock provider
        mock_results = [{"venue_id": "1", "name": "Test"}]
        service.providers[BookingProvider.OPENTABLE] = Mock()
        service.providers[BookingProvider.OPENTABLE].search = AsyncMock(
            return_value=mock_results
        )
        
        # First search (cache miss)
        results1 = await service.search_all_providers(
            query="test",
            location={"lat": 0, "lng": 0},
            date=datetime.now() + timedelta(days=1),
            party_size=2
        )
        
        service.cache.set.assert_called_once()
        
        # Mock cache hit
        service.cache.get = Mock(return_value=mock_results)
        
        # Second search (cache hit)
        results2 = await service.search_all_providers(
            query="test",
            location={"lat": 0, "lng": 0},
            date=datetime.now() + timedelta(days=1),
            party_size=2
        )
        
        # Provider shouldn't be called again
        assert service.providers[BookingProvider.OPENTABLE].search.call_count == 1
    
    @pytest.mark.asyncio
    async def test_availability_caching(self):
        """Test caching of availability checks"""
        service = ReservationManagementService()
        service.cache = Mock()
        
        # Setup
        cache_key = "availability:opentable:venue123:2024-01-01:4"
        cached_times = ["18:00", "19:00", "20:00"]
        
        # Cache hit scenario
        service.cache.get = Mock(return_value=cached_times)
        
        result = await service.check_availability(
            provider=BookingProvider.OPENTABLE,
            venue_id="venue123",
            date=datetime(2024, 1, 1),
            party_size=4
        )
        
        assert result == cached_times
        # Provider shouldn't be called when cache hit
        assert BookingProvider.OPENTABLE not in service.providers


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])