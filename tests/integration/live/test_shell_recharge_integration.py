"""
Shell Recharge Integration Test Suite

This test suite supports both mock and live modes for testing Shell Recharge integration.
Set SHELL_RECHARGE_TEST_MODE=live and provide valid credentials to run live tests.
"""

import os
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import Mock, AsyncMock, patch
import json

from backend.app.integrations.booking.shell_recharge_client import ShellRechargeClient
from backend.app.core.config import settings

# Test configuration
TEST_MODE = os.getenv("SHELL_RECHARGE_TEST_MODE", "mock")
GENERATE_REPORT = os.getenv("GENERATE_TEST_REPORTS", "true").lower() == "true"


class TestShellRechargeIntegration:
    """Comprehensive test suite for Shell Recharge integration"""
    
    @pytest.fixture
    def client(self):
        """Create Shell Recharge client instance"""
        if TEST_MODE == "live":
            # Use real credentials for live testing
            return ShellRechargeClient(
                api_key=os.getenv("SHELL_RECHARGE_API_KEY"),
                partner_id=os.getenv("SHELL_RECHARGE_PARTNER_ID"),
                environment="production" if os.getenv("SHELL_RECHARGE_ENV") == "production" else "sandbox"
            )
        else:
            # Create mock client for testing
            mock_client = Mock(spec=ShellRechargeClient)
            mock_client.search_stations = AsyncMock()
            mock_client.get_station_details = AsyncMock()
            mock_client.check_availability = AsyncMock()
            mock_client.create_reservation = AsyncMock()
            mock_client.start_charging_session = AsyncMock()
            mock_client.stop_charging_session = AsyncMock()
            mock_client.get_session_status = AsyncMock()
            return mock_client
    
    @pytest.fixture
    def test_data(self):
        """Test data for various scenarios"""
        return {
            "station_search": {
                "location": {
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "radius_miles": 5
                },
                "connector_types": ["CCS", "CHAdeMO"],
                "min_power_kw": 50,
                "amenities": ["restroom", "food"]
            },
            "route_search": {
                "origin": {
                    "latitude": 37.7749,
                    "longitude": -122.4194
                },
                "destination": {
                    "latitude": 34.0522,
                    "longitude": -118.2437
                },
                "vehicle_range_miles": 250,
                "current_soc": 80  # State of charge percentage
            },
            "voice_commands": [
                "Find me a fast charging station nearby",
                "I need to charge my Tesla on the way to Los Angeles",
                "Book a charging spot at the nearest Shell station",
                "Reserve a CCS charger for 30 minutes from now"
            ],
            "vehicle_info": {
                "make": "Tesla",
                "model": "Model 3",
                "year": 2023,
                "battery_capacity_kwh": 75,
                "connector_type": "CCS"
            },
            "expected_station": {
                "id": "SHELL-SF-001",
                "name": "Shell Recharge Market Street",
                "address": "123 Market St, San Francisco, CA",
                "chargers": [
                    {
                        "id": "CHG-001",
                        "type": "CCS",
                        "power_kw": 150,
                        "status": "available"
                    }
                ]
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
                    "test_suite": "Shell Recharge Integration",
                    "execution_time": datetime.now().isoformat(),
                    "mode": TEST_MODE,
                    "total_tests": len(self.results),
                    "passed": len([r for r in self.results if r["status"] == "passed"]),
                    "failed": len([r for r in self.results if r["status"] == "failed"]),
                    "results": self.results
                }
                
                report_path = f"/mnt/c/users/jared/onedrive/desktop/roadtrip/tests/integration/live/reports/shell_recharge_{TEST_MODE}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                os.makedirs(os.path.dirname(report_path), exist_ok=True)
                
                with open(report_path, 'w') as f:
                    json.dump(report, f, indent=2)
                    
        return ReportGenerator()
    
    # Critical Path Tests
    
    @pytest.mark.asyncio
    async def test_station_search(self, client, test_data, report_generator):
        """Test charging station search functionality"""
        try:
            if TEST_MODE == "mock":
                # Configure mock response
                client.search_stations.return_value = {
                    "stations": [
                        {
                            "id": "SHELL-SF-001",
                            "name": "Shell Recharge Market Street",
                            "location": {
                                "latitude": 37.7749,
                                "longitude": -122.4194,
                                "address": "123 Market St, San Francisco, CA 94103"
                            },
                            "distance_miles": 0.5,
                            "chargers": [
                                {
                                    "type": "CCS",
                                    "power_kw": 150,
                                    "count": 4,
                                    "available": 2
                                }
                            ],
                            "amenities": ["restroom", "convenience_store", "food"],
                            "pricing": {
                                "per_kwh": 0.48,
                                "per_minute": 0.32,
                                "session_fee": 1.00
                            }
                        }
                    ],
                    "total": 1
                }
            
            # Execute search
            results = await client.search_stations(**test_data["station_search"])
            
            # Validate results
            assert results is not None
            assert "stations" in results
            assert len(results["stations"]) > 0
            
            if TEST_MODE == "live":
                # Additional validation for live mode
                station = results["stations"][0]
                assert "id" in station
                assert "name" in station
                assert "chargers" in station
                assert "pricing" in station
            
            report_generator.add_result(
                "test_station_search",
                "passed",
                {"stations_found": len(results["stations"])}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_station_search",
                "failed",
                {"error": str(e)}
            )
            raise
    
    @pytest.mark.asyncio
    async def test_charger_availability(self, client, test_data, report_generator):
        """Test real-time charger availability checking"""
        try:
            station_id = test_data["expected_station"]["id"]
            
            if TEST_MODE == "mock":
                # Configure mock response
                client.check_availability.return_value = {
                    "station_id": station_id,
                    "chargers": [
                        {
                            "id": "CHG-001",
                            "type": "CCS",
                            "power_kw": 150,
                            "status": "available",
                            "estimated_wait": 0
                        },
                        {
                            "id": "CHG-002",
                            "type": "CCS",
                            "power_kw": 150,
                            "status": "occupied",
                            "estimated_wait": 15,
                            "session_end_time": (datetime.now() + timedelta(minutes=15)).isoformat()
                        }
                    ],
                    "updated_at": datetime.now().isoformat()
                }
            
            # Check availability
            availability = await client.check_availability(station_id=station_id)
            
            # Validate results
            assert availability is not None
            assert "chargers" in availability
            assert len(availability["chargers"]) > 0
            
            available_chargers = [c for c in availability["chargers"] if c["status"] == "available"]
            
            report_generator.add_result(
                "test_charger_availability",
                "passed",
                {
                    "total_chargers": len(availability["chargers"]),
                    "available_chargers": len(available_chargers)
                }
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_charger_availability",
                "failed",
                {"error": str(e)}
            )
            raise
    
    @pytest.mark.asyncio
    async def test_create_charging_reservation(self, client, test_data, report_generator):
        """Test charging reservation creation"""
        try:
            if TEST_MODE == "mock":
                # Configure mock response
                client.create_reservation.return_value = {
                    "reservation_id": "RES-123456789",
                    "station_name": "Shell Recharge Market Street",
                    "charger_id": "CHG-001",
                    "start_time": (datetime.now() + timedelta(minutes=30)).isoformat(),
                    "duration_minutes": 30,
                    "status": "confirmed",
                    "qr_code": "data:image/png;base64,iVBORw0KG...",
                    "estimated_cost": {
                        "session_fee": 1.00,
                        "energy_cost": 12.00,  # 25 kWh @ $0.48
                        "time_cost": 9.60,      # 30 min @ $0.32
                        "total": 22.60,
                        "commission": 1.13      # 5% commission
                    }
                }
            
            # Create reservation
            reservation = await client.create_reservation(
                station_id=test_data["expected_station"]["id"],
                charger_id="CHG-001",
                start_time=(datetime.now() + timedelta(minutes=30)).isoformat(),
                duration_minutes=30,
                vehicle_info=test_data["vehicle_info"],
                user_info={
                    "first_name": "Test",
                    "last_name": "User",
                    "email": "test@example.com",
                    "phone": "+14155551234"
                }
            )
            
            # Validate results
            assert reservation is not None
            assert "reservation_id" in reservation
            assert reservation["status"] == "confirmed"
            assert "estimated_cost" in reservation
            assert "commission" in reservation["estimated_cost"]
            
            report_generator.add_result(
                "test_create_charging_reservation",
                "passed",
                {
                    "reservation_id": reservation["reservation_id"],
                    "estimated_cost": reservation["estimated_cost"]["total"],
                    "commission": reservation["estimated_cost"]["commission"]
                }
            )
            
            # Store reservation for cleanup
            if TEST_MODE == "live":
                return reservation["reservation_id"]
            
        except Exception as e:
            report_generator.add_result(
                "test_create_charging_reservation",
                "failed",
                {"error": str(e)}
            )
            raise
    
    @pytest.mark.asyncio
    async def test_charging_session_flow(self, client, test_data, report_generator):
        """Test complete charging session flow"""
        try:
            reservation_id = "RES-123456789"
            
            if TEST_MODE == "mock":
                # Mock start session response
                client.start_charging_session.return_value = {
                    "session_id": "SES-987654321",
                    "status": "charging",
                    "start_time": datetime.now().isoformat(),
                    "charger_id": "CHG-001",
                    "power_kw": 147.5
                }
                
                # Mock session status response
                client.get_session_status.return_value = {
                    "session_id": "SES-987654321",
                    "status": "charging",
                    "energy_delivered_kwh": 15.2,
                    "duration_minutes": 12,
                    "current_power_kw": 145.8,
                    "estimated_completion": (datetime.now() + timedelta(minutes=18)).isoformat()
                }
                
                # Mock stop session response
                client.stop_charging_session.return_value = {
                    "session_id": "SES-987654321",
                    "status": "completed",
                    "final_energy_kwh": 25.5,
                    "duration_minutes": 31,
                    "final_cost": {
                        "session_fee": 1.00,
                        "energy_cost": 12.24,
                        "time_cost": 9.92,
                        "total": 23.16,
                        "commission": 1.16
                    },
                    "receipt_url": "https://shell-recharge.com/receipts/SES-987654321"
                }
            
            # 1. Start charging session
            session = await client.start_charging_session(
                reservation_id=reservation_id,
                charger_id="CHG-001"
            )
            assert session["status"] == "charging"
            
            # 2. Check session status
            status = await client.get_session_status(session["session_id"])
            assert status["status"] == "charging"
            assert "energy_delivered_kwh" in status
            
            # 3. Stop charging session
            final_session = await client.stop_charging_session(session["session_id"])
            assert final_session["status"] == "completed"
            assert "final_cost" in final_session
            
            report_generator.add_result(
                "test_charging_session_flow",
                "passed",
                {
                    "energy_delivered": final_session["final_energy_kwh"],
                    "total_cost": final_session["final_cost"]["total"],
                    "commission": final_session["final_cost"]["commission"]
                }
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_charging_session_flow",
                "failed",
                {"error": str(e)}
            )
            raise
    
    # Route Planning Tests
    
    @pytest.mark.asyncio
    async def test_route_charging_planning(self, client, test_data, report_generator):
        """Test route-based charging station planning"""
        try:
            if TEST_MODE == "mock":
                # Configure mock response
                client.plan_route_charging = AsyncMock(return_value={
                    "route": {
                        "total_distance_miles": 382,
                        "estimated_duration_hours": 6.5,
                        "charging_stops": [
                            {
                                "station_id": "SHELL-GILROY-001",
                                "station_name": "Shell Recharge Gilroy",
                                "location": {
                                    "latitude": 37.0058,
                                    "longitude": -121.5683
                                },
                                "arrival_soc": 25,
                                "departure_soc": 80,
                                "charging_duration_minutes": 28,
                                "distance_from_start_miles": 120
                            }
                        ],
                        "total_charging_time_minutes": 28,
                        "estimated_charging_cost": 26.40
                    }
                })
            
            # Plan route with charging stops
            route_plan = await client.plan_route_charging(
                origin=test_data["route_search"]["origin"],
                destination=test_data["route_search"]["destination"],
                vehicle_info=test_data["vehicle_info"],
                current_soc=test_data["route_search"]["current_soc"],
                target_arrival_soc=20  # Minimum 20% on arrival
            )
            
            # Validate results
            assert route_plan is not None
            assert "route" in route_plan
            assert "charging_stops" in route_plan["route"]
            
            report_generator.add_result(
                "test_route_charging_planning",
                "passed",
                {
                    "charging_stops": len(route_plan["route"]["charging_stops"]),
                    "total_charging_time": route_plan["route"]["total_charging_time_minutes"],
                    "estimated_cost": route_plan["route"]["estimated_charging_cost"]
                }
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_route_charging_planning",
                "failed",
                {"error": str(e)}
            )
            raise
    
    # Error Scenario Tests
    
    @pytest.mark.asyncio
    async def test_invalid_connector_type(self, client, report_generator):
        """Test handling of incompatible connector types"""
        try:
            if TEST_MODE == "mock":
                client.create_reservation.side_effect = ValueError("Incompatible connector type")
            
            with pytest.raises(ValueError):
                await client.create_reservation(
                    station_id="SHELL-SF-001",
                    charger_id="CHG-TESLA",  # Tesla Supercharger
                    vehicle_info={
                        "connector_type": "CCS"  # Incompatible
                    }
                )
            
            report_generator.add_result(
                "test_invalid_connector_type",
                "passed",
                {"error_handled": True}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_invalid_connector_type",
                "failed",
                {"error": str(e)}
            )
            raise
    
    @pytest.mark.asyncio
    async def test_all_chargers_occupied(self, client, test_data, report_generator):
        """Test handling when all chargers are occupied"""
        try:
            if TEST_MODE == "mock":
                client.check_availability.return_value = {
                    "station_id": "SHELL-BUSY-001",
                    "chargers": [
                        {
                            "id": "CHG-001",
                            "status": "occupied",
                            "estimated_wait": 45
                        },
                        {
                            "id": "CHG-002",
                            "status": "occupied",
                            "estimated_wait": 30
                        }
                    ]
                }
            
            # Check availability at busy station
            availability = await client.check_availability(station_id="SHELL-BUSY-001")
            
            # All chargers should be occupied
            available = [c for c in availability["chargers"] if c["status"] == "available"]
            assert len(available) == 0
            
            # Should provide wait time estimates
            min_wait = min(c["estimated_wait"] for c in availability["chargers"])
            assert min_wait > 0
            
            report_generator.add_result(
                "test_all_chargers_occupied",
                "passed",
                {"min_wait_minutes": min_wait}
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_all_chargers_occupied",
                "failed",
                {"error": str(e)}
            )
            raise
    
    # Commission Tracking Tests
    
    @pytest.mark.asyncio
    async def test_commission_calculation(self, client, report_generator):
        """Test commission tracking for different charging scenarios"""
        try:
            test_sessions = [
                {
                    "energy_kwh": 20,
                    "duration_minutes": 25,
                    "expected_commission": 1.06  # 5% of ~$21.20
                },
                {
                    "energy_kwh": 50,
                    "duration_minutes": 40,
                    "expected_commission": 2.14  # 5% of ~$42.80
                },
                {
                    "energy_kwh": 75,
                    "duration_minutes": 60,
                    "expected_commission": 3.02  # 5% of ~$60.40
                }
            ]
            
            total_commission = 0
            
            for session in test_sessions:
                if TEST_MODE == "mock":
                    # Calculate costs based on pricing
                    energy_cost = session["energy_kwh"] * 0.48
                    time_cost = session["duration_minutes"] * 0.32
                    session_fee = 1.00
                    total_cost = energy_cost + time_cost + session_fee
                    
                    client.stop_charging_session.return_value = {
                        "session_id": f"SES-{session['energy_kwh']}",
                        "final_cost": {
                            "total": total_cost,
                            "commission": session["expected_commission"]
                        }
                    }
                
                result = await client.stop_charging_session(f"SES-{session['energy_kwh']}")
                
                assert abs(result["final_cost"]["commission"] - session["expected_commission"]) < 0.10
                total_commission += result["final_cost"]["commission"]
            
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
    async def test_voice_to_charging_flow(self, client, test_data, report_generator):
        """Test complete voice command to charging reservation flow"""
        try:
            successful_reservations = 0
            
            for voice_command in test_data["voice_commands"]:
                # Simulate voice command processing
                parsed_intent = self._parse_voice_command(voice_command)
                
                if TEST_MODE == "mock":
                    # Mock the entire flow
                    client.search_stations.return_value = {
                        "stations": [{
                            "id": "SHELL-VOICE-001",
                            "name": "Shell Recharge Voice Test",
                            "chargers": [{"type": "CCS", "available": 1}]
                        }]
                    }
                    client.check_availability.return_value = {
                        "chargers": [{
                            "id": "CHG-001",
                            "status": "available"
                        }]
                    }
                    client.create_reservation.return_value = {
                        "reservation_id": f"RES-{hash(voice_command)}",
                        "status": "confirmed"
                    }
                
                # Execute flow
                # 1. Search nearby stations
                stations = await client.search_stations(**parsed_intent["search_params"])
                
                # 2. Check availability at first station
                if stations["stations"]:
                    station = stations["stations"][0]
                    availability = await client.check_availability(station_id=station["id"])
                    
                    # 3. Book first available charger
                    available = [c for c in availability["chargers"] if c["status"] == "available"]
                    if available:
                        charger = available[0]
                        reservation = await client.create_reservation(
                            station_id=station["id"],
                            charger_id=charger["id"],
                            **parsed_intent["reservation_params"]
                        )
                        
                        if reservation["status"] == "confirmed":
                            successful_reservations += 1
            
            report_generator.add_result(
                "test_voice_to_charging_flow",
                "passed",
                {
                    "voice_commands_tested": len(test_data["voice_commands"]),
                    "successful_reservations": successful_reservations
                }
            )
            
        except Exception as e:
            report_generator.add_result(
                "test_voice_to_charging_flow",
                "failed",
                {"error": str(e)}
            )
            raise
    
    def _parse_voice_command(self, command: str) -> Dict:
        """Parse voice command into charging parameters"""
        # Determine urgency
        if "now" in command or "nearby" in command:
            start_time = (datetime.now() + timedelta(minutes=10)).isoformat()
        else:
            start_time = (datetime.now() + timedelta(minutes=30)).isoformat()
        
        # Determine connector type
        connector_type = "CCS"  # Default
        if "Tesla" in command:
            connector_type = "Tesla"
        elif "CHAdeMO" in command:
            connector_type = "CHAdeMO"
        
        return {
            "search_params": {
                "location": {
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "radius_miles": 5
                },
                "connector_types": [connector_type],
                "min_power_kw": 50 if "fast" in command else None
            },
            "reservation_params": {
                "start_time": start_time,
                "duration_minutes": 30,
                "vehicle_info": {
                    "connector_type": connector_type
                },
                "user_info": {
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
        await self.test_station_search(client, test_data, report_generator)
        await self.test_charger_availability(client, test_data, report_generator)
        
        reservation_id = await self.test_create_charging_reservation(client, test_data, report_generator)
        await self.test_charging_session_flow(client, test_data, report_generator)
        
        await self.test_route_charging_planning(client, test_data, report_generator)
        await self.test_invalid_connector_type(client, report_generator)
        await self.test_all_chargers_occupied(client, test_data, report_generator)
        await self.test_commission_calculation(client, report_generator)
        await self.test_voice_to_charging_flow(client, test_data, report_generator)
        
        # Generate final report
        report_generator.generate_report()


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "-s"])