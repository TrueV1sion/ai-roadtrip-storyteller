#!/usr/bin/env python3
"""
Simple test script to verify OpenTable client implementation.
"""

import asyncio
import sys
sys.path.insert(0, '.')

from backend.app.integrations.booking.opentable_client import OpenTableClient


async def test_opentable_client():
    """Test OpenTable client in mock mode."""
    print("Testing OpenTable Client...")
    
    # Initialize client (will use mock mode without API key)
    client = OpenTableClient()
    print(f"✓ Client initialized (mock_mode: {client.mock_mode})")
    
    # Test 1: Search restaurants
    print("\n1. Testing restaurant search...")
    try:
        results = await client.search_restaurants(
            location={"latitude": 37.7749, "longitude": -122.4194},
            cuisine="Italian",
            party_size=2,
            date="2024-02-20",
            time="19:00"
        )
        print(f"✓ Found {results['total']} restaurants")
        if results['restaurants']:
            print(f"  First result: {results['restaurants'][0]['name']} - {results['restaurants'][0]['cuisine']}")
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return
    
    # Test 2: Check availability
    print("\n2. Testing availability check...")
    try:
        restaurant_id = results['restaurants'][0]['id'] if results['restaurants'] else "test_restaurant"
        availability = await client.get_availability(
            restaurant_id=restaurant_id,
            date="2024-02-20",
            time="19:00",
            party_size=2
        )
        print(f"✓ Available times: {availability['available_times']}")
    except Exception as e:
        print(f"✗ Availability check failed: {e}")
    
    # Test 3: Create reservation
    print("\n3. Testing reservation creation...")
    try:
        if availability.get('available_times'):
            reservation = await client.create_reservation(
                restaurant_id=restaurant_id,
                date="2024-02-20",
                time=availability['available_times'][0],
                party_size=2,
                guest_info={
                    "first_name": "Test",
                    "last_name": "User",
                    "email": "test@example.com",
                    "phone": "+14155551234"
                },
                special_requests="Booth seating preferred"
            )
            print(f"✓ Reservation created: {reservation['confirmation_number']}")
            print(f"  Restaurant: {reservation['restaurant_name']}")
            print(f"  Commission: ${reservation['commission_amount']}")
            
            # Test 4: Get reservation
            print("\n4. Testing get reservation...")
            details = await client.get_reservation(reservation['confirmation_number'])
            if details:
                print(f"✓ Retrieved reservation: {details['confirmation_number']}")
            
            # Test 5: Cancel reservation
            print("\n5. Testing cancellation...")
            cancel_result = await client.cancel_reservation(
                reservation['confirmation_number'],
                reason="Testing"
            )
            print(f"✓ Reservation cancelled: {cancel_result['status']}")
            
    except Exception as e:
        print(f"✗ Reservation operations failed: {e}")
    
    # Test 6: Commission calculation
    print("\n6. Testing commission calculations...")
    test_cases = [
        (2, "standard", 5.00),
        (4, "standard", 10.00),
        (2, "premium", 10.00),
        (2, "special_event", 15.00)
    ]
    
    for party_size, rate_type, expected in test_cases:
        commission = client._calculate_commission(
            party_size=party_size,
            date="2024-02-17",  # Saturday
            time="19:00",  # Prime time
            restaurant_type=rate_type
        )
        print(f"  Party of {party_size} ({rate_type}): ${commission:.2f}")
    
    print("\n✓ All tests completed!")


if __name__ == "__main__":
    asyncio.run(test_opentable_client())