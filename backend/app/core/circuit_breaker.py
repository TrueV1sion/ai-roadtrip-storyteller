"""
Circuit Breaker implementation for external service calls.
Prevents cascading failures when external services are unavailable.
"""
import asyncio
import time
from enum import Enum
from typing import Callable, Optional, Any, Dict
from datetime import datetime, timedelta
import functools
from collections import deque

from backend.app.core.logger import logger
from backend.app.core.cache import cache_manager


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker pattern implementation.
    
    The circuit breaker has three states:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, requests are rejected immediately
    - HALF_OPEN: Testing if service has recovered
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        success_threshold: int = 2,
        timeout: float = 30.0
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Identifier for this circuit breaker
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            expected_exception: Exception type to catch
            success_threshold: Successes needed to close from half-open
            timeout: Request timeout in seconds
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        self.timeout = timeout
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._last_state_change = datetime.now()
        
        # Track recent response times for monitoring
        self._response_times = deque(maxlen=100)
        
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, with automatic half-open transition."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and \
               time.time() - self._last_failure_time > self.recovery_timeout:
                logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing)."""
        return self.state == CircuitState.OPEN
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker (synchronous).
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitOpenError: If circuit is open
            Original exception: If function fails
        """
        if self.is_open:
            raise CircuitOpenError(f"Circuit breaker {self.name} is OPEN")
        
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            self._on_success()
            response_time = time.time() - start_time
            self._response_times.append(response_time)
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function through circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitOpenError: If circuit is open
            asyncio.TimeoutError: If function times out
            Original exception: If function fails
        """
        if self.is_open:
            raise CircuitOpenError(
                f"Circuit breaker {self.name} is OPEN. "
                f"Service has been failing. Retry after {self.recovery_timeout}s"
            )
        
        start_time = time.time()
        try:
            # Apply timeout to prevent hanging
            result = await asyncio.wait_for(
                func(*args, **kwargs),
                timeout=self.timeout
            )
            self._on_success()
            response_time = time.time() - start_time
            self._response_times.append(response_time)
            return result
        except asyncio.TimeoutError:
            self._on_failure()
            logger.error(f"Circuit breaker {self.name}: Request timed out after {self.timeout}s")
            raise
        except self.expected_exception as e:
            self._on_failure()
            logger.error(f"Circuit breaker {self.name}: Expected exception {type(e).__name__}: {e}")
            raise
    
    def _on_success(self):
        """Handle successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                logger.info(f"Circuit breaker {self.name} transitioning to CLOSED")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._last_state_change = datetime.now()
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self._failure_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker {self.name} failed in HALF_OPEN, reopening")
            self._state = CircuitState.OPEN
            self._last_state_change = datetime.now()
        elif self._failure_count >= self.failure_threshold:
            logger.error(
                f"Circuit breaker {self.name} threshold reached ({self._failure_count} failures), "
                f"transitioning to OPEN"
            )
            self._state = CircuitState.OPEN
            self._last_state_change = datetime.now()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        avg_response_time = (
            sum(self._response_times) / len(self._response_times)
            if self._response_times else 0
        )
        
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_time": self._last_failure_time,
            "last_state_change": self._last_state_change.isoformat(),
            "avg_response_time": avg_response_time,
            "response_time_samples": len(self._response_times)
        }
    
    def reset(self):
        """Manually reset circuit breaker to closed state."""
        logger.info(f"Manually resetting circuit breaker {self.name}")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._last_state_change = datetime.now()


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
    
    def get_or_create(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        success_threshold: int = 2,
        timeout: float = 30.0
    ) -> CircuitBreaker:
        """Get existing circuit breaker or create new one."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
                success_threshold=success_threshold,
                timeout=timeout
            )
        return self._breakers[name]
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all circuit breakers."""
        return {
            name: breaker.get_stats()
            for name, breaker in self._breakers.items()
        }
    
    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()


def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type = Exception,
    success_threshold: int = 2,
    timeout: float = 30.0
):
    """
    Decorator to add circuit breaker to async functions.
    
    Usage:
        @with_circuit_breaker("external-api", timeout=10.0)
        async def call_external_api():
            ...
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            breaker = circuit_breaker_manager.get_or_create(
                name=name,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                expected_exception=expected_exception,
                success_threshold=success_threshold,
                timeout=timeout
            )
            return await breaker.call_async(func, *args, **kwargs)
        return wrapper
    return decorator


# Pre-configured circuit breakers for common services
def get_ai_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for AI services (Vertex AI)."""
    return circuit_breaker_manager.get_or_create(
        name="vertex-ai",
        failure_threshold=3,
        recovery_timeout=120,
        timeout=60.0
    )


def get_maps_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for Google Maps API."""
    return circuit_breaker_manager.get_or_create(
        name="google-maps",
        failure_threshold=5,
        recovery_timeout=60,
        timeout=10.0
    )


def get_weather_circuit_breaker() -> CircuitBreaker:
    """Get circuit breaker for weather API."""
    return circuit_breaker_manager.get_or_create(
        name="weather-api",
        failure_threshold=5,
        recovery_timeout=30,
        timeout=5.0
    )


def get_booking_circuit_breaker(partner: str) -> CircuitBreaker:
    """Get circuit breaker for booking partner APIs."""
    return circuit_breaker_manager.get_or_create(
        name=f"booking-{partner}",
        failure_threshold=3,
        recovery_timeout=90,
        timeout=15.0
    )