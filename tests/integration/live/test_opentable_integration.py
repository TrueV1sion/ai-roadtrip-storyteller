"""
OpenTable Integration Test Suite

This test suite supports both mock and live modes for testing OpenTable integration.
Set OPENTABLE_TEST_MODE=live and provide valid credentials to run live tests.
"""

import os
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import Mock, AsyncMock, patch
import json

from backend.app.integrations.booking.opentable_client import OpenTableClient
from backend.app.core.config import settings

# Test configuration
TEST_MODE = os.getenv("OPENTABLE_TEST_MODE", "mock")
GENERATE_REPORT = os.getenv("GENERATE_TEST_REPORTS", "true").lower() == "true"


class TestOpenTableIntegration:
    """Comprehensive test suite for OpenTable integration"""
    
    @pytest.fixture
    def client(self):
        """Create OpenTable client instance"""
        if TEST_MODE == "live":
            # Use real credentials for live testing
            return OpenTableClient(
                api_key=os.getenv("OPENTABLE_API_KEY"),
                partner_id=os.getenv("OPENTABLE_PARTNER_ID")
            )
        else:
            # Create mock client for testing
            mock_client = Mock(spec=OpenTableClient)
            mock_client.search_restaurants = AsyncMock()
            mock_client.get_availability = AsyncMock()
            mock_client.create_reservation = AsyncMock()
            mock_client.cancel_reservation = AsyncMock()
            mock_client.get_reservation = AsyncMock()
            return mock_client
    
    @pytest.fixture
    def test_data(self):
        """Test data for various scenarios"""
        return {
            "search_params": {
                "location": {
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "city": "San Francisco",
                    "state": "CA"
                },
                "cuisine": "Italian",
                "party_size": 2,
                "date": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                "time": "19:00"
            },
            "voice_commands": [
                "Find me an Italian restaurant in San Francisco for 2 people next Friday at 7pm",
                "Book a table for 4 at a steakhouse near me tomorrow night",
                "I need a reservation for dinner tonight, somewhere romantic"
            ],
            "expected_restaurant": {
                "id": "test_restaurant_123",
                "name": "Test Italian Bistro",
                "cuisine": "Italian",
                "price_range": "$$",
                "rating": 4.5
            }
        }
    
    @pytest.fixture
    def report_generator(self):
        """Generate test reports"""
        class ReportGenerator:
            def __init__(self):
                self.results = []
                
            def add_result(self, test_name: str, status: str, details: Dict):
                self.results.append({
                    "test_name": test_name,
                    "status": status,
                    "timestamp": datetime.now().isoformat(),
                    "mode": TEST_MODE,
                    "details": details
                })
            
            def generate_report(self):
                if not GENERATE_REPORT:
                    return
                    
                report = {
                    "test_suite": "OpenTable Integration",
                    "execution_time": datetime.now().isoformat(),
                    "mode": TEST_MODE,
                    "total_tests": len(self.results),
                    "passed": len([r for r in self.results if r["status"] == "passed"]),
                    "failed": len([r for r in self.results if r["status"] == "failed"]),
                    "results": self.results
                }
                
                report_path = f"/mnt/c/users/jared/onedrive/desktop/roadtrip/tests/integration/live/reports/opentable_{TEST_MODE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                os.makedirs(os.path.dirname(report_path), exist_ok=True)
                
                with open(report_path, 'w') as f:
                    json.dump(report, f, indent=2)
                    
        return ReportGenerator()
    
    # Critical Path Tests
    
    @pytest.mark.asyncio
    async def test_restaurant_search(self, client, test_data, report_generator):
        """Test restaurant search functionality"""
        try:
            if TEST_MODE == "mock":
                # Configure mock response
                client.search_restaurants.return_value = {
                    "restaurants": [
                        {
                            "id": "123",
                            "name": "Test Italian Bistro",
                            "cuisine": "Italian",
                            "location": test_data["search_params"]["location"],
                            "rating": 4.5,
                            "price_range": "$$"
                        }
                    ],
                    "total": 1
                }
            
            # Execute search
            results = await client.search_restaurants(**test_data["search_params"])
            
            # Validate results
            assert results is not None
            assert "restaurants" in results
            assert len(results["restaurants"]) > 0
            
            if TEST_MODE == "live":
                # Additional validation for live mode
                restaurant = results["restaurants"][0]
                assert "id" in restaurant
                assert "name" in restaurant
                assert "cuisine" in restaurant
            
            report_generator.add_result(
                "test_restaurant_search",
                "passed",
                {"restaurants_found": len(results["restaurants"])}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_restaurant_search",
                "failed",
                {"error": str(e)}
            )
            raise
    
    @pytest.mark.asyncio
    async def test_availability_check(self, client, test_data, report_generator):
        """Test availability checking"""
        try:
            restaurant_id = test_data["expected_restaurant"]["id"]
            
            if TEST_MODE == "mock":
                # Configure mock response
                client.get_availability.return_value = {
                    "available_times": [
                        "18:30", "19:00", "19:30", "20:00"
                    ],
                    "restaurant_id": restaurant_id
                }
            
            # Check availability
            availability = await client.get_availability(
                restaurant_id=restaurant_id,
                date=test_data["search_params"]["date"],
                time=test_data["search_params"]["time"],
                party_size=test_data["search_params"]["party_size"]
            )
            
            # Validate results
            assert availability is not None
            assert "available_times" in availability
            assert len(availability["available_times"]) > 0
            
            report_generator.add_result(
                "test_availability_check",
                "passed",
                {"available_slots": len(availability["available_times"])}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_availability_check",
                "failed",
                {"error": str(e)}
            )
            raise
    
    @pytest.mark.asyncio
    async def test_create_reservation(self, client, test_data, report_generator):
        """Test reservation creation"""
        try:
            if TEST_MODE == "mock":
                # Configure mock response
                client.create_reservation.return_value = {
                    "confirmation_number": "OT123456789",
                    "restaurant_name": "Test Italian Bistro",
                    "date": test_data["search_params"]["date"],
                    "time": test_data["search_params"]["time"],
                    "party_size": test_data["search_params"]["party_size"],
                    "status": "confirmed",
                    "commission_amount": 2.50
                }
            
            # Create reservation
            reservation = await client.create_reservation(
                restaurant_id=test_data["expected_restaurant"]["id"],
                date=test_data["search_params"]["date"],
                time=test_data["search_params"]["time"],
                party_size=test_data["search_params"]["party_size"],
                guest_info={
                    "first_name": "Test",
                    "last_name": "User",
                    "email": "test@example.com",
                    "phone": "+14155551234"
                }
            )
            
            # Validate results
            assert reservation is not None
            assert "confirmation_number" in reservation
            assert reservation["status"] == "confirmed"
            assert "commission_amount" in reservation
            
            report_generator.add_result(
                "test_create_reservation",
                "passed",
                {
                    "confirmation_number": reservation["confirmation_number"],
                    "commission": reservation["commission_amount"]
                }
            )
            
            # Store confirmation for cleanup
            if TEST_MODE == "live":
                return reservation["confirmation_number"]
            
        except Exception as e:
            report_generator.add_result(
                "test_create_reservation",
                "failed",
                {"error": str(e)}
            )
            raise
    
    @pytest.mark.asyncio
    async def test_cancel_reservation(self, client, report_generator):
        """Test reservation cancellation"""
        try:
            confirmation_number = "OT123456789"
            
            if TEST_MODE == "mock":
                # Configure mock response
                client.cancel_reservation.return_value = {
                    "status": "cancelled",
                    "confirmation_number": confirmation_number,
                    "refund_amount": 0
                }
            
            # Cancel reservation
            result = await client.cancel_reservation(confirmation_number)
            
            # Validate results
            assert result is not None
            assert result["status"] == "cancelled"
            
            report_generator.add_result(
                "test_cancel_reservation",
                "passed",
                {"cancelled": True}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_cancel_reservation",
                "failed",
                {"error": str(e)}
            )
            raise
    
    # Error Scenario Tests
    
    @pytest.mark.asyncio
    async def test_invalid_location(self, client, report_generator):
        """Test handling of invalid location"""
        try:
            if TEST_MODE == "mock":
                client.search_restaurants.side_effect = ValueError("Invalid location")
            
            with pytest.raises(ValueError):
                await client.search_restaurants(
                    location={"latitude": 999, "longitude": 999}
                )
            
            report_generator.add_result(
                "test_invalid_location",
                "passed",
                {"error_handled": True}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_invalid_location",
                "failed",
                {"error": str(e)}
            )
            raise
    
    @pytest.mark.asyncio
    async def test_no_availability(self, client, test_data, report_generator):
        """Test handling when no tables available"""
        try:
            if TEST_MODE == "mock":
                client.get_availability.return_value = {
                    "available_times": [],
                    "restaurant_id": "123"
                }
            
            # Check availability for fully booked restaurant
            availability = await client.get_availability(
                restaurant_id="fully_booked_restaurant",
                date=test_data["search_params"]["date"],
                time="20:00",
                party_size=10  # Large party size
            )
            
            # Should return empty availability
            assert availability["available_times"] == []
            
            report_generator.add_result(
                "test_no_availability",
                "passed",
                {"handled_no_availability": True}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_no_availability",
                "failed",
                {"error": str(e)}
            )
            raise
    
    # Commission Tracking Tests
    
    @pytest.mark.asyncio
    async def test_commission_calculation(self, client, report_generator):
        """Test commission tracking and calculation"""
        try:
            test_bookings = [
                {"party_size": 2, "expected_commission": 2.50},
                {"party_size": 4, "expected_commission": 5.00},
                {"party_size": 8, "expected_commission": 10.00}
            ]
            
            total_commission = 0
            
            for booking in test_bookings:
                if TEST_MODE == "mock":
                    client.create_reservation.return_value = {
                        "confirmation_number": f"OT{booking['party_size']}",
                        "commission_amount": booking["expected_commission"]
                    }
                
                reservation = await client.create_reservation(
                    restaurant_id="123",
                    party_size=booking["party_size"],
                    date=datetime.now().strftime("%Y-%m-%d"),
                    time="19:00",
                    guest_info={"first_name": "Test", "last_name": "User"}
                )
                
                assert reservation["commission_amount"] == booking["expected_commission"]
                total_commission += reservation["commission_amount"]
            
            report_generator.add_result(
                "test_commission_calculation",
                "passed",
                {"total_commission": total_commission}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_commission_calculation",
                "failed",
                {"error": str(e)}
            )
            raise
    
    # Voice-to-Booking Flow Tests
    
    @pytest.mark.asyncio
    async def test_voice_to_booking_flow(self, client, test_data, report_generator):
        """Test complete voice command to booking flow"""
        try:
            for voice_command in test_data["voice_commands"]:
                # Simulate voice command processing
                parsed_intent = self._parse_voice_command(voice_command)
                
                if TEST_MODE == "mock":
                    # Mock the entire flow
                    client.search_restaurants.return_value = {
                        "restaurants": [test_data["expected_restaurant"]]
                    }
                    client.get_availability.return_value = {
                        "available_times": ["19:00", "19:30"]
                    }
                    client.create_reservation.return_value = {
                        "confirmation_number": f"OT{hash(voice_command)}",
                        "status": "confirmed"
                    }
                
                # Execute flow
                # 1. Search restaurants
                restaurants = await client.search_restaurants(**parsed_intent["search_params"])
                
                # 2. Check availability for first result
                if restaurants["restaurants"]:
                    restaurant = restaurants["restaurants"][0]
                    availability = await client.get_availability(
                        restaurant_id=restaurant["id"],
                        **parsed_intent["availability_params"]
                    )
                    
                    # 3. Book first available time
                    if availability["available_times"]:
                        reservation = await client.create_reservation(
                            restaurant_id=restaurant["id"],
                            time=availability["available_times"][0],
                            **parsed_intent["booking_params"]
                        )
                        
                        assert reservation["status"] == "confirmed"
            
            report_generator.add_result(
                "test_voice_to_booking_flow",
                "passed",
                {"voice_commands_tested": len(test_data["voice_commands"])}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_voice_to_booking_flow",
                "failed",
                {"error": str(e)}
            )
            raise
    
    def _parse_voice_command(self, command: str) -> Dict:
        """Parse voice command into booking parameters"""
        # Simplified parsing logic for testing
        return {
            "search_params": {
                "location": {"city": "San Francisco", "state": "CA"},
                "cuisine": "Italian" if "Italian" in command else "Any",
                "party_size": 2
            },
            "availability_params": {
                "date": datetime.now().strftime("%Y-%m-%d"),
                "party_size": 2
            },
            "booking_params": {
                "party_size": 2,
                "guest_info": {
                    "first_name": "Voice",
                    "last_name": "User",
                    "email": "voice@test.com"
                }
            }
        }
    
    # Test Execution and Reporting
    
    @pytest.mark.asyncio
    async def test_full_integration_suite(self, client, test_data, report_generator):
        """Run full integration test suite"""
        # Run all tests in sequence
        await self.test_restaurant_search(client, test_data, report_generator)
        await self.test_availability_check(client, test_data, report_generator)
        
        confirmation = await self.test_create_reservation(client, test_data, report_generator)
        
        if confirmation and TEST_MODE == "live":
            # Clean up live reservation
            await self.test_cancel_reservation(client, report_generator)
        
        await self.test_invalid_location(client, report_generator)
        await self.test_no_availability(client, test_data, report_generator)
        await self.test_commission_calculation(client, report_generator)
        await self.test_voice_to_booking_flow(client, test_data, report_generator)
        
        # Generate final report
        report_generator.generate_report()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])