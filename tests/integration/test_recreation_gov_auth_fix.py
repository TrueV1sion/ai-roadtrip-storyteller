"""
Test Recreation.gov API authentication fix
Verifies that API key is properly sent in headers
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from backend.app.integrations.recreation_gov_client import RecreationGovClient


class TestRecreationGovAuthentication:
    """Test Recreation.gov API authentication improvements."""
    
    @pytest.fixture
    def client(self):
        """Create a Recreation.gov client instance."""
        # Set environment variables for testing
        os.environ["RECREATION_GOV_API_KEY"] = "test_api_key_12345"
        os.environ["RECREATION_GOV_MOCK_MODE"] = "false"
        
        client = RecreationGovClient()
        yield client
        
        # Cleanup
        os.environ.pop("RECREATION_GOV_API_KEY", None)
        os.environ.pop("RECREATION_GOV_MOCK_MODE", None)
    
    @pytest.mark.asyncio
    async def test_api_key_headers_are_set(self, client):
        """Test that all required API key headers are set."""
        with patch('aiohttp.ClientSession') as mock_session:
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value='{"RECDATA": []}')
            mock_response.request_info = MagicMock()
            mock_response.history = []
            
            # Setup mock session
            mock_session_instance = AsyncMock()
            mock_session_instance.request = AsyncMock(return_value=mock_response)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            # Make a test request
            await client._make_request("GET", "facilities", params={"test": "param"})
            
            # Verify request was made with correct headers
            mock_session_instance.request.assert_called_once()
            call_args = mock_session_instance.request.call_args
            
            # Check headers
            headers = call_args[1]['headers']
            assert headers['apikey'] == 'test_api_key_12345'
            assert headers['X-Api-Key'] == 'test_api_key_12345'
            assert headers['Authorization'] == 'Bearer test_api_key_12345'
            assert headers['Accept'] == 'application/json'
            assert headers['Content-Type'] == 'application/json'
            assert 'X-Request-ID' in headers
            assert 'X-Timestamp' in headers
    
    @pytest.mark.asyncio
    async def test_warning_when_no_api_key(self, caplog):
        """Test that warning is logged when no API key is configured."""
        # Create client without API key
        os.environ.pop("RECREATION_GOV_API_KEY", None)
        client = RecreationGovClient()
        
        with patch('aiohttp.ClientSession') as mock_session:
            # Setup mock response
            mock_response = AsyncMock()
            mock_response.status = 401  # Unauthorized
            mock_response.text = AsyncMock(return_value='{"error": "Unauthorized"}')
            mock_response.request_info = MagicMock()
            mock_response.history = []
            
            # Setup mock session
            mock_session_instance = AsyncMock()
            mock_session_instance.request = AsyncMock(return_value=mock_response)
            mock_session_instance.__aenter__ = AsyncMock(return_value=mock_session_instance)
            mock_session_instance.__aexit__ = AsyncMock()
            mock_session.return_value = mock_session_instance
            
            # Make a test request (expect it to fail)
            with pytest.raises(Exception):
                await client._make_request("GET", "facilities")
            
            # Check for warning in logs
            assert "Recreation.gov API key not configured" in caplog.text
    
    @pytest.mark.asyncio
    async def test_search_campgrounds_with_auth(self, client):
        """Test that search_campgrounds properly authenticates."""
        with patch.object(client, '_make_request') as mock_request:
            # Mock response data
            mock_request.return_value = [
                {
                    "FacilityID": "1234",
                    "FacilityName": "Test Campground",
                    "FacilityLatitude": 37.7749,
                    "FacilityLongitude": -122.4194,
                    "TotalSites": 50
                }
            ]
            
            # Search campgrounds
            results = await client.search_campgrounds(
                latitude=37.7749,
                longitude=-122.4194,
                radius_miles=25
            )
            
            # Verify API was called with authentication
            mock_request.assert_called_once_with(
                "GET",
                "facilities",
                params={
                    "latitude": 37.7749,
                    "longitude": -122.4194,
                    "radius": 25,
                    "limit": 50,
                    "offset": 0
                },
                use_cache=True,
                cache_ttl=1800
            )
            
            # Verify results
            assert len(results) == 1
            assert results[0]["name"] == "Test Campground"
    
    @pytest.mark.asyncio
    async def test_check_availability_with_auth(self, client):
        """Test that check_availability properly authenticates."""
        with patch.object(client, '_make_request') as mock_request:
            # Mock response data
            mock_request.return_value = {
                "facility_name": "Test Campground",
                "campsites": {
                    "A12": {
                        "availabilities": {
                            "2025-06-01T00:00:00Z": "Available",
                            "2025-06-02T00:00:00Z": "Available"
                        },
                        "site": {
                            "name": "A12",
                            "type": "Standard",
                            "rate": "25.00"
                        }
                    }
                }
            }
            
            # Check availability
            result = await client.check_availability(
                campground_id="1234",
                start_date="2025-06-01",
                end_date="2025-06-03",
                equipment_type="tent"
            )
            
            # Verify API was called with authentication
            mock_request.assert_called()
            call_args = mock_request.call_args
            assert call_args[0][0] == "GET"
            assert "availability" in call_args[0][1]
            assert call_args[1]["use_booking_api"] == True
            
            # Verify results
            assert result["total_sites_available"] == 1
            assert result["available_sites"][0]["site_name"] == "A12"
    
    @pytest.mark.asyncio
    async def test_create_reservation_with_auth(self, client):
        """Test that create_reservation properly authenticates."""
        with patch.object(client, '_make_request') as mock_request:
            # Mock response data
            mock_request.return_value = {
                "order_id": "RG20250601123456",
                "order_number": "CONF12345",
                "facility_name": "Test Campground",
                "site_total": 50.00,
                "booking_fee": 8.00
            }
            
            # Create reservation
            customer_info = {
                "name": "John Doe",
                "email": "john@example.com",
                "phone": "555-1234",
                "adults": 2,
                "equipment_type": "tent"
            }
            
            result = await client.create_reservation(
                campground_id="1234",
                site_id="A12",
                start_date="2025-06-01",
                end_date="2025-06-03",
                customer_info=customer_info
            )
            
            # Verify API was called with authentication
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert call_args[0][1] == "reservations"
            assert call_args[1]["use_booking_api"] == True
            
            # Verify reservation data
            json_data = call_args[1]["json_data"]
            assert json_data["campground_id"] == "1234"
            assert json_data["campsite_id"] == "A12"
            assert json_data["customer"]["email"] == "john@example.com"
            
            # Verify results
            assert result["reservation_id"] == "RG20250601123456"
            assert result["total_price"] == 58.00
    
    @pytest.mark.asyncio
    async def test_api_key_rotation(self):
        """Test that API key can be rotated without restarting."""
        # Create client with initial key
        os.environ["RECREATION_GOV_API_KEY"] = "old_key"
        client = RecreationGovClient()
        assert client.api_key == "old_key"
        
        # Update environment variable
        os.environ["RECREATION_GOV_API_KEY"] = "new_key"
        
        # Create new client instance (simulating key rotation)
        new_client = RecreationGovClient()
        assert new_client.api_key == "new_key"
        
        # Cleanup
        os.environ.pop("RECREATION_GOV_API_KEY", None)
    
    def test_mock_mode_bypasses_auth(self):
        """Test that mock mode bypasses authentication."""
        os.environ["RECREATION_GOV_MOCK_MODE"] = "true"
        os.environ["RECREATION_GOV_API_KEY"] = ""  # No API key
        
        client = RecreationGovClient()
        assert client.mock_mode == True
        assert client.api_key == ""
        
        # This should not raise an error even without API key
        # because mock mode is enabled
        asyncio.run(client.search_campgrounds(37.7749, -122.4194))
        
        # Cleanup
        os.environ.pop("RECREATION_GOV_MOCK_MODE", None)
        os.environ.pop("RECREATION_GOV_API_KEY", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])