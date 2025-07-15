"""
Recreation.gov Integration Test Suite

This test suite supports both mock and live modes for testing Recreation.gov integration.
Set RECREATION_GOV_TEST_MODE=live and provide valid credentials to run live tests.
"""

import os
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import Mock, AsyncMock, patch
import json

from backend.app.integrations.booking.recreation_gov_client import RecreationGovClient
from backend.app.core.config import settings

# Test configuration
TEST_MODE = os.getenv("RECREATION_GOV_TEST_MODE", "mock")
GENERATE_REPORT = os.getenv("GENERATE_TEST_REPORTS", "true").lower() == "true"


class TestRecreationGovIntegration:
    """Comprehensive test suite for Recreation.gov integration"""
    
    @pytest.fixture
    def client(self):
        """Create Recreation.gov client instance"""
        if TEST_MODE == "live":
            # Use real credentials for live testing
            return RecreationGovClient(
                api_key=os.getenv("RECREATION_GOV_API_KEY"),
                affiliate_id=os.getenv("RECREATION_GOV_AFFILIATE_ID")
            )
        else:
            # Create mock client for testing
            mock_client = Mock(spec=RecreationGovClient)
            mock_client.search_campgrounds = AsyncMock()
            mock_client.get_availability = AsyncMock()
            mock_client.create_reservation = AsyncMock()
            mock_client.cancel_reservation = AsyncMock()
            mock_client.get_reservation = AsyncMock()
            mock_client.search_activities = AsyncMock()
            return mock_client
    
    @pytest.fixture
    def test_data(self):
        """Test data for various scenarios"""
        return {
            "campground_search": {
                "location": {
                    "latitude": 37.8651,
                    "longitude": -119.5383,
                    "state": "CA",
                    "park": "Yosemite"
                },
                "start_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                "end_date": (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%d"),
                "equipment": "tent",
                "party_size": 4
            },
            "activity_search": {
                "activity_type": "hiking",
                "location": {
                    "latitude": 36.5054,
                    "longitude": -118.5658,
                    "park": "Sequoia"
                },
                "date": (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
            },
            "voice_commands": [
                "Find me a campsite in Yosemite for next weekend",
                "Book a tent site at Grand Canyon for 4 people in July",
                "I need a campground with RV hookups near Yellowstone",
                "Reserve a backcountry permit for hiking Half Dome"
            ],
            "expected_campground": {
                "id": "test_campground_123",
                "name": "Test Valley Campground",
                "park": "Yosemite",
                "site_types": ["tent", "rv"],
                "amenities": ["restrooms", "water", "fire_rings"]
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
                    "test_suite": "Recreation.gov Integration",
                    "execution_time": datetime.now().isoformat(),
                    "mode": TEST_MODE,
                    "total_tests": len(self.results),
                    "passed": len([r for r in self.results if r["status"] == "passed"]),
                    "failed": len([r for r in self.results if r["status"] == "failed"]),
                    "results": self.results
                }
                
                report_path = f"/mnt/c/users/jared/onedrive/desktop/roadtrip/tests/integration/live/reports/recreation_gov_{TEST_MODE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                os.makedirs(os.path.dirname(report_path), exist_ok=True)
                
                with open(report_path, 'w') as f:
                    json.dump(report, f, indent=2)
                    
        return ReportGenerator()
    
    # Critical Path Tests
    
    @pytest.mark.asyncio
    async def test_campground_search(self, client, test_data, report_generator):
        """Test campground search functionality"""
        try:
            if TEST_MODE == "mock":
                # Configure mock response
                client.search_campgrounds.return_value = {
                    "campgrounds": [
                        {
                            "id": "232447",
                            "name": "Upper Pines",
                            "park": "Yosemite National Park",
                            "location": test_data["campground_search"]["location"],
                            "site_types": ["tent", "rv_limited"],
                            "max_occupancy": 6,
                            "amenities": ["restrooms", "water", "bear_lockers"]
                        }
                    ],
                    "total": 1
                }
            
            # Execute search
            results = await client.search_campgrounds(**test_data["campground_search"])
            
            # Validate results
            assert results is not None
            assert "campgrounds" in results
            assert len(results["campgrounds"]) > 0
            
            if TEST_MODE == "live":
                # Additional validation for live mode
                campground = results["campgrounds"][0]
                assert "id" in campground
                assert "name" in campground
                assert "park" in campground
                assert "site_types" in campground
            
            report_generator.add_result(
                "test_campground_search",
                "passed",
                {"campgrounds_found": len(results["campgrounds"])}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_campground_search",
                "failed",
                {"error": str(e)}
            )
            raise
    
    @pytest.mark.asyncio
    async def test_campsite_availability(self, client, test_data, report_generator):
        """Test campsite availability checking"""
        try:
            campground_id = test_data["expected_campground"]["id"]
            
            if TEST_MODE == "mock":
                # Configure mock response
                client.get_availability.return_value = {
                    "available_sites": [
                        {
                            "site_id": "001",
                            "site_number": "A01",
                            "site_type": "tent",
                            "dates_available": [
                                test_data["campground_search"]["start_date"],
                                test_data["campground_search"]["end_date"]
                            ],
                            "max_occupancy": 6,
                            "price_per_night": 35.00
                        }
                    ],
                    "campground_id": campground_id
                }
            
            # Check availability
            availability = await client.get_availability(
                campground_id=campground_id,
                start_date=test_data["campground_search"]["start_date"],
                end_date=test_data["campground_search"]["end_date"],
                equipment_type=test_data["campground_search"]["equipment"]
            )
            
            # Validate results
            assert availability is not None
            assert "available_sites" in availability
            assert len(availability["available_sites"]) > 0
            
            if TEST_MODE == "live":
                site = availability["available_sites"][0]
                assert "site_id" in site
                assert "price_per_night" in site
            
            report_generator.add_result(
                "test_campsite_availability",
                "passed",
                {"available_sites": len(availability["available_sites"])}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_campsite_availability",
                "failed",
                {"error": str(e)}
            )
            raise
    
    @pytest.mark.asyncio
    async def test_create_campsite_reservation(self, client, test_data, report_generator):
        """Test campsite reservation creation"""
        try:
            if TEST_MODE == "mock":
                # Configure mock response
                client.create_reservation.return_value = {
                    "confirmation_number": "RG123456789",
                    "campground_name": "Upper Pines",
                    "site_number": "A01",
                    "start_date": test_data["campground_search"]["start_date"],
                    "end_date": test_data["campground_search"]["end_date"],
                    "total_cost": 70.00,
                    "status": "confirmed",
                    "commission_amount": 3.50
                }
            
            # Create reservation
            reservation = await client.create_reservation(
                campground_id=test_data["expected_campground"]["id"],
                site_id="001",
                start_date=test_data["campground_search"]["start_date"],
                end_date=test_data["campground_search"]["end_date"],
                guest_info={
                    "first_name": "Test",
                    "last_name": "User",
                    "email": "test@example.com",
                    "phone": "+14155551234",
                    "party_size": test_data["campground_search"]["party_size"]
                }
            )
            
            # Validate results
            assert reservation is not None
            assert "confirmation_number" in reservation
            assert reservation["status"] == "confirmed"
            assert "commission_amount" in reservation
            assert "total_cost" in reservation
            
            report_generator.add_result(
                "test_create_campsite_reservation",
                "passed",
                {
                    "confirmation_number": reservation["confirmation_number"],
                    "total_cost": reservation["total_cost"],
                    "commission": reservation["commission_amount"]
                }
            )
            
            # Store confirmation for cleanup
            if TEST_MODE == "live":
                return reservation["confirmation_number"]
            
        except Exception as e:
            report_generator.add_result(
                "test_create_campsite_reservation",
                "failed",
                {"error": str(e)}
            )
            raise
    
    @pytest.mark.asyncio
    async def test_activity_search(self, client, test_data, report_generator):
        """Test activity/permit search"""
        try:
            if TEST_MODE == "mock":
                # Configure mock response
                client.search_activities.return_value = {
                    "activities": [
                        {
                            "id": "act_123",
                            "name": "Half Dome Day Hike Permit",
                            "type": "hiking_permit",
                            "park": "Yosemite National Park",
                            "description": "Day hiking permit for Half Dome cables",
                            "price": 10.00,
                            "availability": "lottery"
                        }
                    ],
                    "total": 1
                }
            
            # Search activities
            results = await client.search_activities(**test_data["activity_search"])
            
            # Validate results
            assert results is not None
            assert "activities" in results
            
            report_generator.add_result(
                "test_activity_search",
                "passed",
                {"activities_found": len(results["activities"])}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_activity_search",
                "failed",
                {"error": str(e)}
            )
            raise
    
    # Error Scenario Tests
    
    @pytest.mark.asyncio
    async def test_invalid_park_location(self, client, report_generator):
        """Test handling of invalid park location"""
        try:
            if TEST_MODE == "mock":
                client.search_campgrounds.side_effect = ValueError("Invalid park location")
            
            with pytest.raises(ValueError):
                await client.search_campgrounds(
                    location={"park": "NonexistentPark"}
                )
            
            report_generator.add_result(
                "test_invalid_park_location",
                "passed",
                {"error_handled": True}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_invalid_park_location",
                "failed",
                {"error": str(e)}
            )
            raise
    
    @pytest.mark.asyncio
    async def test_fully_booked_campground(self, client, test_data, report_generator):
        """Test handling when campground is fully booked"""
        try:
            if TEST_MODE == "mock":
                client.get_availability.return_value = {
                    "available_sites": [],
                    "campground_id": "232447",
                    "message": "No sites available for selected dates"
                }
            
            # Check availability for peak season
            availability = await client.get_availability(
                campground_id="232447",  # Popular campground
                start_date=(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                end_date=(datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d")
            )
            
            # Should return empty availability
            assert availability["available_sites"] == []
            
            report_generator.add_result(
                "test_fully_booked_campground",
                "passed",
                {"handled_no_availability": True}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_fully_booked_campground",
                "failed",
                {"error": str(e)}
            )
            raise
    
    # Commission Tracking Tests
    
    @pytest.mark.asyncio
    async def test_commission_calculation(self, client, report_generator):
        """Test commission tracking for different reservation types"""
        try:
            test_bookings = [
                {
                    "nights": 2,
                    "price_per_night": 35.00,
                    "expected_commission": 3.50  # 5% of total
                },
                {
                    "nights": 7,
                    "price_per_night": 45.00,
                    "expected_commission": 15.75  # 5% of total
                },
                {
                    "activity_type": "permit",
                    "price": 10.00,
                    "expected_commission": 0.50  # 5% of permit
                }
            ]
            
            total_commission = 0
            
            for booking in test_bookings:
                if TEST_MODE == "mock":
                    if "activity_type" in booking:
                        # Activity/permit booking
                        client.create_reservation.return_value = {
                            "confirmation_number": f"RG-ACT-{booking['price']}",
                            "commission_amount": booking["expected_commission"],
                            "total_cost": booking["price"]
                        }
                    else:
                        # Campsite booking
                        total_cost = booking["nights"] * booking["price_per_night"]
                        client.create_reservation.return_value = {
                            "confirmation_number": f"RG-CAMP-{booking['nights']}",
                            "commission_amount": booking["expected_commission"],
                            "total_cost": total_cost
                        }
                
                reservation = await client.create_reservation(
                    campground_id="123",
                    site_id="001",
                    start_date=datetime.now().strftime("%Y-%m-%d"),
                    end_date=(datetime.now() + timedelta(days=booking.get("nights", 1))).strftime("%Y-%m-%d"),
                    guest_info={"first_name": "Test", "last_name": "User"}
                )
                
                assert abs(reservation["commission_amount"] - booking["expected_commission"]) < 0.01
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
            successful_bookings = 0
            
            for voice_command in test_data["voice_commands"]:
                # Simulate voice command processing
                parsed_intent = self._parse_voice_command(voice_command)
                
                if TEST_MODE == "mock":
                    # Mock the entire flow
                    client.search_campgrounds.return_value = {
                        "campgrounds": [{
                            "id": "232447",
                            "name": "Test Campground",
                            "park": parsed_intent["park"]
                        }]
                    }
                    client.get_availability.return_value = {
                        "available_sites": [{
                            "site_id": "001",
                            "site_number": "A01",
                            "price_per_night": 35.00
                        }]
                    }
                    client.create_reservation.return_value = {
                        "confirmation_number": f"RG{hash(voice_command)}",
                        "status": "confirmed"
                    }
                
                # Execute flow
                # 1. Search campgrounds
                campgrounds = await client.search_campgrounds(**parsed_intent["search_params"])
                
                # 2. Check availability for first result
                if campgrounds["campgrounds"]:
                    campground = campgrounds["campgrounds"][0]
                    availability = await client.get_availability(
                        campground_id=campground["id"],
                        **parsed_intent["availability_params"]
                    )
                    
                    # 3. Book first available site
                    if availability["available_sites"]:
                        site = availability["available_sites"][0]
                        reservation = await client.create_reservation(
                            campground_id=campground["id"],
                            site_id=site["site_id"],
                            **parsed_intent["booking_params"]
                        )
                        
                        if reservation["status"] == "confirmed":
                            successful_bookings += 1
            
            report_generator.add_result(
                "test_voice_to_booking_flow",
                "passed",
                {
                    "voice_commands_tested": len(test_data["voice_commands"]),
                    "successful_bookings": successful_bookings
                }
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
        # Extract park name
        park = "Yosemite"
        if "Grand Canyon" in command:
            park = "Grand Canyon"
        elif "Yellowstone" in command:
            park = "Yellowstone"
        
        # Extract dates
        if "next weekend" in command:
            start_date = (datetime.now() + timedelta(days=(5 - datetime.now().weekday()))).strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=(7 - datetime.now().weekday()))).strftime("%Y-%m-%d")
        else:
            start_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%d")
        
        return {
            "search_params": {
                "location": {"park": park},
                "equipment": "rv" if "RV" in command else "tent"
            },
            "availability_params": {
                "start_date": start_date,
                "end_date": end_date
            },
            "booking_params": {
                "start_date": start_date,
                "end_date": end_date,
                "guest_info": {
                    "first_name": "Voice",
                    "last_name": "User",
                    "email": "voice@test.com",
                    "party_size": 4
                }
            },
            "park": park
        }
    
    # Test Execution and Reporting
    
    @pytest.mark.asyncio
    async def test_full_integration_suite(self, client, test_data, report_generator):
        """Run full integration test suite"""
        # Run all tests in sequence
        await self.test_campground_search(client, test_data, report_generator)
        await self.test_campsite_availability(client, test_data, report_generator)
        
        confirmation = await self.test_create_campsite_reservation(client, test_data, report_generator)
        
        if confirmation and TEST_MODE == "live":
            # Note: Recreation.gov may have cancellation restrictions
            # Only attempt cancellation if within allowed window
            pass
        
        await self.test_activity_search(client, test_data, report_generator)
        await self.test_invalid_park_location(client, report_generator)
        await self.test_fully_booked_campground(client, test_data, report_generator)
        await self.test_commission_calculation(client, report_generator)
        await self.test_voice_to_booking_flow(client, test_data, report_generator)
        
        # Generate final report
        report_generator.generate_report()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])