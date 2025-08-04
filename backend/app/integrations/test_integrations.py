"""Test script to demonstrate enhanced API client features."""

import asyncio
import os
from datetime import datetime, timedelta

from app.integrations.open_table_client import OpenTableClient
from app.integrations.recreation_gov_client import RecreationGovClient
from app.integrations.shell_recharge_client import ShellRechargeClient
from app.core.logger import logger


async def test_opentable_client():
    """Test OpenTable API client features."""
    logger.info("Testing OpenTable Client...")
    
    # Enable mock mode for testing
    os.environ["OPENTABLE_MOCK_MODE"] = "true"
    
    client = OpenTableClient()
    
    try:
        # Test restaurant search
        restaurants = await client.search_restaurants(
            latitude=37.7749,
            longitude=-122.4194,
            radius_miles=10,
            cuisine_type="Italian",
            party_size=4
        )
        logger.info(f"Found {len(restaurants)} restaurants")
        
        if restaurants:
            # Test availability check
            restaurant_id = restaurants[0]["id"]
            availability = await client.check_availability(
                restaurant_id=restaurant_id,
                party_size=4,
                date="2025-02-01",
                time_preference="19:00"
            )
            logger.info(f"Found {len(availability['available_slots'])} time slots")
            
            # Test reservation creation
            if availability["available_slots"]:
                reservation = await client.create_reservation(
                    restaurant_id=restaurant_id,
                    party_size=4,
                    date="2025-02-01",
                    time=availability["available_slots"][0]["time"],
                    customer_info={
                        "name": "John Doe",
                        "email": "john@example.com",
                        "phone": "+1-555-0123",
                        "special_requests": "Window table please"
                    }
                )
                logger.info(f"Created reservation: {reservation['reservation_id']}")
                
    except Exception as e:
        logger.error(f"OpenTable test failed: {str(e)}")


async def test_recreation_gov_client():
    """Test Recreation.gov API client features."""
    logger.info("Testing Recreation.gov Client...")
    
    # Enable mock mode for testing
    os.environ["RECREATION_GOV_MOCK_MODE"] = "true"
    
    client = RecreationGovClient()
    
    try:
        # Test campground search
        campgrounds = await client.search_campgrounds(
            latitude=39.5296,
            longitude=-121.5524,
            radius_miles=50,
            amenities=["Restrooms", "Drinking Water"],
            campground_type="National Forest"
        )
        logger.info(f"Found {len(campgrounds)} campgrounds")
        
        if campgrounds:
            # Test availability check
            campground_id = campgrounds[0]["id"]
            availability = await client.check_availability(
                campground_id=campground_id,
                start_date="2025-06-01",
                end_date="2025-06-03",
                equipment_type="tent"
            )
            logger.info(f"Found {len(availability['available_sites'])} available sites")
            
            # Test reservation creation
            if availability["available_sites"]:
                site = availability["available_sites"][0]
                reservation = await client.create_reservation(
                    campground_id=campground_id,
                    site_id=site["site_id"],
                    start_date="2025-06-01",
                    end_date="2025-06-03",
                    customer_info={
                        "name": "Jane Smith",
                        "email": "jane@example.com",
                        "phone": "+1-555-0124",
                        "party_size": 4,
                        "equipment_type": "tent",
                        "vehicles": 1
                    }
                )
                logger.info(f"Created reservation: {reservation['reservation_id']}")
                
        # Test permit search
        permits = await client.search_permits(
            activity_type="hiking",
            location="Yosemite",
            date="2025-07-15"
        )
        logger.info(f"Found {len(permits)} permits required")
        
    except Exception as e:
        logger.error(f"Recreation.gov test failed: {str(e)}")


async def test_shell_recharge_client():
    """Test Shell Recharge API client features."""
    logger.info("Testing Shell Recharge Client...")
    
    # Enable mock mode for testing
    os.environ["SHELL_RECHARGE_MOCK_MODE"] = "true"
    
    client = ShellRechargeClient()
    
    try:
        # Test station search
        stations = await client.search_charging_stations(
            latitude=37.7749,
            longitude=-122.4194,
            radius_miles=25,
            connector_type="CCS",
            min_power_kw=100,
            available_only=True
        )
        logger.info(f"Found {len(stations)} charging stations")
        
        if stations:
            # Test availability check
            station = stations[0]
            connector = station["connectors"][0] if station["connectors"] else None
            
            if connector:
                availability = await client.check_availability(
                    station_id=station["id"],
                    connector_id=connector["id"],
                    duration_minutes=30
                )
                logger.info(f"Connector status: {availability['current_status']}")
                
                # Test reservation creation
                if availability["reservation_available"]:
                    start_time = (datetime.now() + timedelta(hours=2)).isoformat() + "Z"
                    reservation = await client.create_reservation(
                        station_id=station["id"],
                        connector_id=connector["id"],
                        start_time=start_time,
                        duration_minutes=30,
                        vehicle_info={
                            "make": "Tesla",
                            "model": "Model 3",
                            "year": 2023,
                            "battery_capacity": 75,
                            "connector_type": "CCS",
                            "driver_name": "Bob Johnson",
                            "driver_email": "bob@example.com",
                            "driver_phone": "+1-555-0125",
                            "target_soc": 80
                        }
                    )
                    logger.info(f"Created reservation: {reservation['reservation_id']}")
                    
                    # Test session start
                    session = await client.start_charging_session(
                        reservation_id=reservation["reservation_id"],
                        connector_id=connector["id"]
                    )
                    logger.info(f"Started charging session: {session['session_id']}")
                    
        # Test station details
        if stations:
            details = await client.get_station_details(stations[0]["id"])
            logger.info(f"Station {details['name']} has {details['total_connectors']} connectors")
            
    except Exception as e:
        logger.error(f"Shell Recharge test failed: {str(e)}")


async def main():
    """Run all integration tests."""
    logger.info("Starting API Integration Tests...")
    
    # Test all clients
    await test_opentable_client()
    logger.info("-" * 50)
    
    await test_recreation_gov_client()
    logger.info("-" * 50)
    
    await test_shell_recharge_client()
    
    logger.info("API Integration Tests Complete!")


if __name__ == "__main__":
    asyncio.run(main())