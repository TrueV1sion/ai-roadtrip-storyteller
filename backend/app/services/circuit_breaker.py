"""
Circuit Breaker Pattern Implementation
Provides fault tolerance for external service calls
"""

import asyncio
import time
from functools import wraps
from typing import Callable, Optional, Any
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta

import logging
logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half-open"  # Testing if service recovered


@dataclass
class CircuitStats:
    """Statistics for circuit breaker monitoring"""
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_successes: int = 0
    consecutive_failures: int = 0


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for fault tolerance
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        success_threshold: Number of successes needed to close circuit
        expected_exception: Exception type to catch (default: Exception)
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.expected_exception = expected_exception
        
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._half_open_lock = asyncio.Lock()
        
    @property
    def state(self) -> str:
        """Get current circuit state as string"""
        return self._state.value
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)"""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (failing)"""
        return self._state == CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (
            self._stats.last_failure_time and
            time.time() - self._stats.last_failure_time >= self.recovery_timeout
        )
    
    def _record_success(self):
        """Record a successful call"""
        self._stats.success_count += 1
        self._stats.consecutive_successes += 1
        self._stats.consecutive_failures = 0
        self._stats.last_success_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            if self._stats.consecutive_successes >= self.success_threshold:
                self._close()
    
    def _record_failure(self):
        """Record a failed call"""
        self._stats.failure_count += 1
        self._stats.consecutive_failures += 1
        self._stats.consecutive_successes = 0
        self._stats.last_failure_time = time.time()
        
        if self._state == CircuitState.CLOSED:
            if self._stats.consecutive_failures >= self.failure_threshold:
                self._trip()
        elif self._state == CircuitState.HALF_OPEN:
            self._trip()
    
    def _trip(self):
        """Trip the circuit breaker to OPEN state"""
        self._state = CircuitState.OPEN
        logger.warning(
            f"Circuit breaker opened after {self._stats.consecutive_failures} failures"
        )
    
    def _close(self):
        """Close the circuit breaker to CLOSED state"""
        self._state = CircuitState.CLOSED
        self._stats.consecutive_failures = 0
        logger.info("Circuit breaker closed after successful recovery")
    
    def _attempt_reset(self):
        """Attempt to reset the circuit to HALF_OPEN state"""
        self._state = CircuitState.HALF_OPEN
        self._stats.consecutive_successes = 0
        logger.info("Circuit breaker attempting reset (half-open)")
    
    def __call__(self, func: Callable) -> Callable:
        """Decorator for wrapping functions with circuit breaker"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if circuit is open
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    async with self._half_open_lock:
                        # Double-check state in case another coroutine reset it
                        if self._state == CircuitState.OPEN:
                            self._attempt_reset()
                else:
                    raise Exception(
                        f"Circuit breaker is open. Service unavailable for "
                        f"{self.recovery_timeout - (time.time() - self._stats.last_failure_time):.0f} seconds"
                    )
            
            # Attempt the call
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                self._record_success()
                return result
                
            except self.expected_exception as e:
                self._record_failure()
                raise e
        
        # Add method to get circuit stats
        wrapper.get_stats = lambda: {
            "state": self._state.value,
            "failure_count": self._stats.failure_count,
            "success_count": self._stats.success_count,
            "consecutive_failures": self._stats.consecutive_failures,
            "consecutive_successes": self._stats.consecutive_successes,
            "last_failure": datetime.fromtimestamp(self._stats.last_failure_time).isoformat()
                if self._stats.last_failure_time else None,
            "last_success": datetime.fromtimestamp(self._stats.last_success_time).isoformat()
                if self._stats.last_success_time else None,
        }
        
        # Add method to manually reset circuit
        wrapper.reset = lambda: self._close()
        
        return wrapper
    
    def call_with_circuit_breaker(self, func: Callable, *args, **kwargs) -> Any:
        """
        Alternative way to use circuit breaker without decorator
        Useful for dynamic function calls
        """
        wrapped = self(func)
        return wrapped(*args, **kwargs)


class AdvancedCircuitBreaker(CircuitBreaker):
    """
    Advanced circuit breaker with additional features:
    - Sliding window for failure rate calculation
    - Gradual recovery with increasing success threshold
    - Exponential backoff for recovery timeout
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        expected_exception: type = Exception,
        failure_rate_threshold: float = 0.5,
        window_size: int = 100
    ):
        super().__init__(failure_threshold, recovery_timeout, success_threshold, expected_exception)
        self.failure_rate_threshold = failure_rate_threshold
        self.window_size = window_size
        self._call_history = []  # Track recent calls for sliding window
        self._recovery_attempts = 0
        
    def _add_to_history(self, success: bool):
        """Add call result to sliding window history"""
        self._call_history.append((time.time(), success))
        
        # Keep only recent history
        cutoff_time = time.time() - 300  # 5 minutes
        self._call_history = [
            (t, s) for t, s in self._call_history 
            if t > cutoff_time
        ][-self.window_size:]
    
    def _calculate_failure_rate(self) -> float:
        """Calculate failure rate in sliding window"""
        if len(self._call_history) < 10:  # Need minimum calls
            return 0.0
        
        failures = sum(1 for _, success in self._call_history if not success)
        return failures / len(self._call_history)
    
    def _get_recovery_timeout(self) -> int:
        """Calculate recovery timeout with exponential backoff"""
        return self.recovery_timeout * (2 ** min(self._recovery_attempts, 5))
    
    def _record_success(self):
        """Enhanced success recording with sliding window"""
        super()._record_success()
        self._add_to_history(True)
        
        if self._state == CircuitState.HALF_OPEN:
            self._recovery_attempts = 0  # Reset on successful recovery
    
    def _record_failure(self):
        """Enhanced failure recording with failure rate check"""
        super()._record_failure()
        self._add_to_history(False)
        
        # Check failure rate in addition to consecutive failures
        if self._state == CircuitState.CLOSED:
            failure_rate = self._calculate_failure_rate()
            if failure_rate >= self.failure_rate_threshold:
                self._trip()
                logger.warning(
                    f"Circuit breaker opened due to {failure_rate:.1%} failure rate"
                )
    
    def _should_attempt_reset(self) -> bool:
        """Check with exponential backoff timeout"""
        if not self._stats.last_failure_time:
            return False
        
        timeout = self._get_recovery_timeout()
        return time.time() - self._stats.last_failure_time >= timeout
    
    def _attempt_reset(self):
        """Attempt reset with tracking"""
        super()._attempt_reset()
        self._recovery_attempts += 1


# Convenience factory functions
def create_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    advanced: bool = False
) -> CircuitBreaker:
    """
    Factory function to create circuit breakers
    
    Args:
        name: Name for logging
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before attempting recovery
        advanced: Use advanced circuit breaker with more features
    """
    if advanced:
        breaker = AdvancedCircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    else:
        breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout
        )
    
    logger.info(f"Created {'advanced' if advanced else 'basic'} circuit breaker: {name}")
    return breaker