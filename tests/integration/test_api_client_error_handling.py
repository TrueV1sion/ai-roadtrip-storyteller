"""Integration tests for API client error handling."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import aiohttp
import asyncio
from datetime import datetime, timedelta
import json

from backend.app.core.unified_ai_client import UnifiedAIClient
from backend.app.services.booking_service import BookingService
from backend.app.core.error_handler import (
    APIError,
    RateLimitError,
    NetworkError,
    ValidationError,
    AuthenticationError,
    BookingError
)


class TestAPIClientErrorHandling:
    """Test error handling in API clients."""
    
    @pytest.mark.asyncio
    async def test_network_error_retry(self):
        """Test retry logic for network errors."""
        client = UnifiedAIClient()
        
        # Simulate network errors that resolve after retries
        call_count = 0
        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise aiohttp.ClientError("Network error")
            return {"success": True}
        
        with patch.object(client, '_make_request', mock_request):
            result = await client.generate_story(
                location={"lat": 37.7749, "lng": -122.4194},
                theme="historical"
            )
            
            assert result is not None
            assert call_count == 3  # Failed twice, succeeded on third
    
    @pytest.mark.asyncio
    async def test_rate_limit_handling(self):
        """Test rate limit error handling with backoff."""
        client = UnifiedAIClient()
        
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status = 429
        mock_response.headers = {"Retry-After": "2"}
        mock_response.json = AsyncMock(return_value={
            "error": "Rate limit exceeded"
        })
        
        with patch('aiohttp.ClientSession.request', return_value=mock_response):
            start_time = datetime.now()
            
            with pytest.raises(RateLimitError) as exc_info:
                await client.generate_story(
                    location={"lat": 37.7749, "lng": -122.4194},
                    theme="historical"
                )
            
            # Should include retry after info
            assert exc_info.value.retry_after == 2
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test request timeout handling."""
        client = UnifiedAIClient()
        
        async def slow_request(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate slow response
        
        with patch.object(client, '_make_request', slow_request):
            with pytest.raises(asyncio.TimeoutError):
                await client.generate_story(
                    location={"lat": 37.7749, "lng": -122.4194},
                    theme="historical",
                    timeout=1  # 1 second timeout
                )
    
    @pytest.mark.asyncio
    async def test_invalid_response_handling(self):
        """Test handling of invalid API responses."""
        client = UnifiedAIClient()
        
        # Test various invalid responses
        invalid_responses = [
            None,  # Null response
            {},  # Empty response
            {"error": "Invalid request"},  # Error response
            {"data": None},  # Null data
            "Invalid JSON",  # String instead of object
        ]
        
        for invalid_response in invalid_responses:
            with patch.object(client, '_make_request', return_value=invalid_response):
                result = await client.generate_story(
                    location={"lat": 37.7749, "lng": -122.4194},
                    theme="historical"
                )
                
                # Should handle gracefully and return default/fallback
                assert result is not None
                if isinstance(result, dict):
                    assert "error" in result or "story" in result
    
    @pytest.mark.asyncio
    async def test_authentication_error_refresh(self):
        """Test automatic token refresh on authentication errors."""
        booking_service = BookingService()
        
        # Mock initial auth error then success after refresh
        call_count = 0
        async def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise AuthenticationError("Token expired")
            return {"restaurants": []}
        
        with patch.object(booking_service, '_make_authenticated_request', mock_request), \
             patch.object(booking_service, 'refresh_token', AsyncMock(return_value="new_token")):
            
            result = await booking_service.search_restaurants(
                location={"lat": 37.7749, "lng": -122.4194}
            )
            
            assert result is not None
            assert call_count == 2  # First failed, second succeeded
    
    @pytest.mark.asyncio
    async def test_partial_failure_handling(self):
        """Test handling of partial failures in batch operations."""
        booking_service = BookingService()
        
        # Mock mixed success/failure responses
        async def mock_batch_check(*args, **kwargs):
            return {
                "results": [
                    {"restaurant_id": "r1", "available": True},
                    {"restaurant_id": "r2", "error": "Service unavailable"},
                    {"restaurant_id": "r3", "available": False}
                ],
                "partial_failure": True
            }
        
        with patch.object(booking_service, 'check_batch_availability', mock_batch_check):
            results = await booking_service.check_multiple_restaurants(
                restaurant_ids=["r1", "r2", "r3"],
                date="2024-01-20",
                time="7:00 PM"
            )
            
            assert len(results) == 3
            assert results[0]["available"] == True
            assert "error" in results[1]
            assert results[2]["available"] == False
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """Test circuit breaker for repeated failures."""
        client = UnifiedAIClient()
        
        # Simulate repeated failures
        failure_count = 0
        async def failing_request(*args, **kwargs):
            nonlocal failure_count
            failure_count += 1
            raise NetworkError("Service unavailable")
        
        with patch.object(client, '_make_request', failing_request):
            # Make multiple requests
            for i in range(5):
                with pytest.raises(NetworkError):
                    await client.generate_story(
                        location={"lat": 37.7749, "lng": -122.4194},
                        theme="historical"
                    )
            
            # Circuit should be open now
            assert client._circuit_breaker.is_open
            
            # Further requests should fail fast
            with pytest.raises(NetworkError) as exc_info:
                await client.generate_story(
                    location={"lat": 37.7749, "lng": -122.4194},
                    theme="historical"
                )
            
            assert "Circuit breaker open" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test graceful degradation when services are unavailable."""
        client = UnifiedAIClient()
        
        # Mock service unavailability
        with patch.object(client, '_make_request', side_effect=NetworkError("Service down")):
            # Should fall back to cached or basic response
            result = await client.generate_story(
                location={"lat": 37.7749, "lng": -122.4194},
                theme="historical",
                allow_fallback=True
            )
            
            assert result is not None
            assert result.get("source") == "fallback"
            assert "story" in result
    
    @pytest.mark.asyncio
    async def test_validation_error_details(self):
        """Test detailed validation error reporting."""
        booking_service = BookingService()
        
        # Test various validation errors
        with pytest.raises(ValidationError) as exc_info:
            await booking_service.create_reservation(
                restaurant_id="",  # Empty ID
                date="invalid-date",  # Invalid date format
                time="25:00",  # Invalid time
                party_size=-1  # Invalid party size
            )
        
        error = exc_info.value
        assert len(error.validation_errors) >= 4
        assert "restaurant_id" in error.validation_errors
        assert "date" in error.validation_errors
        assert "time" in error.validation_errors
        assert "party_size" in error.validation_errors
    
    @pytest.mark.asyncio
    async def test_error_context_preservation(self):
        """Test that error context is preserved through the stack."""
        booking_service = BookingService()
        
        # Mock API error with context
        mock_error = {
            "error": "Restaurant not available",
            "error_code": "RESTAURANT_UNAVAILABLE",
            "context": {
                "restaurant_id": "r123",
                "requested_time": "7:00 PM",
                "suggested_times": ["6:00 PM", "8:30 PM"]
            }
        }
        
        with patch.object(booking_service, '_make_request', return_value=mock_error):
            with pytest.raises(BookingError) as exc_info:
                await booking_service.create_reservation(
                    restaurant_id="r123",
                    date="2024-01-20",
                    time="7:00 PM",
                    party_size=4
                )
            
            error = exc_info.value
            assert error.error_code == "RESTAURANT_UNAVAILABLE"
            assert error.context["restaurant_id"] == "r123"
            assert len(error.context["suggested_times"]) == 2
    
    @pytest.mark.asyncio
    async def test_error_aggregation_in_parallel_requests(self):
        """Test error aggregation when multiple parallel requests fail."""
        client = UnifiedAIClient()
        
        # Different errors for different requests
        errors = [
            NetworkError("Service 1 down"),
            RateLimitError("Service 2 rate limited"),
            ValidationError("Service 3 validation failed")
        ]
        
        async def mock_request_with_errors(endpoint, *args, **kwargs):
            if "story" in endpoint:
                raise errors[0]
            elif "recommendation" in endpoint:
                raise errors[1]
            else:
                raise errors[2]
        
        with patch.object(client, '_make_request', mock_request_with_errors):
            # Make parallel requests
            tasks = [
                client.generate_story(location={}, theme="historical"),
                client.get_recommendations(location={}),
                client.validate_input(data={})
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should be errors
            assert all(isinstance(r, Exception) for r in results)
            assert isinstance(results[0], NetworkError)
            assert isinstance(results[1], RateLimitError)
            assert isinstance(results[2], ValidationError)
    
    @pytest.mark.asyncio
    async def test_error_recovery_strategies(self):
        """Test different error recovery strategies."""
        booking_service = BookingService()
        
        # Test exponential backoff
        retry_delays = []
        async def track_retries(*args, **kwargs):
            retry_delays.append(datetime.now())
            if len(retry_delays) < 3:
                raise NetworkError("Temporary failure")
            return {"success": True}
        
        with patch.object(booking_service, '_make_request', track_retries):
            result = await booking_service.create_reservation(
                restaurant_id="r123",
                date="2024-01-20",
                time="7:00 PM",
                party_size=4,
                retry_strategy="exponential"
            )
            
            assert result["success"]
            assert len(retry_delays) == 3
            
            # Check exponential delays
            if len(retry_delays) >= 3:
                delay1 = (retry_delays[1] - retry_delays[0]).total_seconds()
                delay2 = (retry_delays[2] - retry_delays[1]).total_seconds()
                assert delay2 > delay1  # Exponential increase
    
    @pytest.mark.asyncio
    async def test_error_logging_and_monitoring(self):
        """Test that errors are properly logged and monitored."""
        client = UnifiedAIClient()
        
        with patch('backend.app.core.logger.logger') as mock_logger:
            with patch.object(client, '_make_request', side_effect=NetworkError("Test error")):
                try:
                    await client.generate_story(
                        location={"lat": 37.7749, "lng": -122.4194},
                        theme="historical"
                    )
                except NetworkError:
                    pass
            
            # Verify error was logged
            mock_logger.error.assert_called()
            error_log = mock_logger.error.call_args[0][0]
            assert "NetworkError" in error_log
            assert "Test error" in error_log
    
    @pytest.mark.asyncio
    async def test_error_notification_system(self):
        """Test error notification for critical failures."""
        booking_service = BookingService()
        
        critical_error = BookingError(
            "Payment processing failed",
            error_code="PAYMENT_FAILED",
            severity="critical"
        )
        
        with patch.object(booking_service, '_make_request', side_effect=critical_error), \
             patch('backend.app.services.notification_service.send_alert') as mock_alert:
            
            with pytest.raises(BookingError):
                await booking_service.create_reservation(
                    restaurant_id="r123",
                    date="2024-01-20",
                    time="7:00 PM",
                    party_size=4,
                    payment_required=True
                )
            
            # Critical error should trigger alert
            mock_alert.assert_called_once()
            alert_data = mock_alert.call_args[0][0]
            assert alert_data["severity"] == "critical"
            assert "PAYMENT_FAILED" in alert_data["message"]