"""
Resilience and Error Handling System
Provides circuit breakers, fallback mechanisms, and graceful degradation
"""

import asyncio
import time
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
from dataclasses import dataclass
from enum import Enum
import functools
from contextlib import asynccontextmanager

from app.core.logger import get_logger

logger = get_logger(__name__)
T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: int = 60
    expected_exception: type = Exception
    success_threshold: int = 3  # For half-open state


class CircuitBreaker:
    """Circuit breaker for handling service failures."""
    
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0
        
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time < self.config.recovery_timeout:
                raise CircuitBreakerOpenException("Circuit breaker is open")
            else:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("Circuit breaker moved to half-open state")
        
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            self._on_success()
            return result
            
        except self.config.expected_exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                logger.info("Circuit breaker closed after successful recovery")
        elif self.state == CircuitState.CLOSED:
            self.failure_count = 0
    
    def _on_failure(self):
        """Handle failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            logger.warning("Circuit breaker opened from half-open state")
        elif self.failure_count >= self.config.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout
            }
        }


class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class FallbackService:
    """Service for providing fallback responses when primary services fail."""
    
    def __init__(self):
        self.fallback_responses = {}
    
    def register_fallback(self, service_name: str, fallback_func: Callable):
        """Register a fallback function for a service."""
        self.fallback_responses[service_name] = fallback_func
        logger.info(f"Registered fallback for service: {service_name}")
    
    async def get_fallback_response(self, service_name: str, *args, **kwargs) -> Any:
        """Get fallback response for a service."""
        fallback_func = self.fallback_responses.get(service_name)
        if not fallback_func:
            raise ValueError(f"No fallback registered for service: {service_name}")
        
        try:
            if asyncio.iscoroutinefunction(fallback_func):
                return await fallback_func(*args, **kwargs)
            else:
                return fallback_func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Fallback function failed for {service_name}: {e}")
            return self._get_default_fallback(service_name)
    
    def _get_default_fallback(self, service_name: str) -> Dict[str, Any]:
        """Get default fallback response."""
        return {
            "error": "service_unavailable",
            "message": f"The {service_name} service is temporarily unavailable. Please try again later.",
            "fallback": True,
            "timestamp": time.time()
        }


class RetryPolicy:
    """Configurable retry policy with backoff strategies."""
    
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
    
    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with retry policy."""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.max_attempts} attempts failed: {e}")
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next attempt."""
        delay = self.base_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        
        return delay


class ResilientService:
    """Service wrapper that combines circuit breaker, retry policy, and fallbacks."""
    
    def __init__(
        self,
        name: str,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
        retry_policy: Optional[RetryPolicy] = None,
        fallback_service: Optional[FallbackService] = None
    ):
        self.name = name
        self.circuit_breaker = CircuitBreaker(
            circuit_breaker_config or CircuitBreakerConfig()
        )
        self.retry_policy = retry_policy or RetryPolicy()
        self.fallback_service = fallback_service or FallbackService()
        
        # Metrics
        self.call_count = 0
        self.success_count = 0
        self.failure_count = 0
        self.fallback_count = 0
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with full resilience stack."""
        self.call_count += 1
        
        try:
            # Execute with circuit breaker and retry policy
            result = await self.circuit_breaker.call(
                self.retry_policy.execute, func, *args, **kwargs
            )
            self.success_count += 1
            return result
            
        except (CircuitBreakerOpenException, Exception) as e:
            self.failure_count += 1
            logger.warning(f"Service {self.name} failed, attempting fallback: {e}")
            
            try:
                # Attempt fallback
                fallback_result = await self.fallback_service.get_fallback_response(
                    self.name, *args, **kwargs
                )
                self.fallback_count += 1
                return fallback_result
                
            except Exception as fallback_error:
                logger.error(f"Fallback also failed for {self.name}: {fallback_error}")
                raise e  # Raise original exception
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics."""
        success_rate = (self.success_count / self.call_count * 100) if self.call_count > 0 else 0
        
        return {
            "service_name": self.name,
            "call_count": self.call_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "fallback_count": self.fallback_count,
            "success_rate": round(success_rate, 2),
            "circuit_breaker": self.circuit_breaker.get_state()
        }


class GracefulDegradationManager:
    """Manages graceful degradation of application features."""
    
    def __init__(self):
        self.feature_states = {}
        self.degradation_rules = {}
    
    def register_feature(
        self,
        feature_name: str,
        dependencies: List[str],
        degraded_implementation: Optional[Callable] = None
    ):
        """Register a feature with its dependencies."""
        self.feature_states[feature_name] = {
            "enabled": True,
            "dependencies": dependencies,
            "degraded_implementation": degraded_implementation,
            "last_check": time.time()
        }
    
    def set_service_health(self, service_name: str, is_healthy: bool):
        """Update service health status."""
        for feature_name, feature_state in self.feature_states.items():
            if service_name in feature_state["dependencies"]:
                if not is_healthy and feature_state["enabled"]:
                    self._degrade_feature(feature_name)
                elif is_healthy and not feature_state["enabled"]:
                    self._restore_feature(feature_name)
    
    def _degrade_feature(self, feature_name: str):
        """Degrade a feature to fallback mode."""
        self.feature_states[feature_name]["enabled"] = False
        logger.warning(f"Feature {feature_name} degraded due to dependency failure")
    
    def _restore_feature(self, feature_name: str):
        """Restore a feature to full functionality."""
        self.feature_states[feature_name]["enabled"] = True
        logger.info(f"Feature {feature_name} restored to full functionality")
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is fully enabled."""
        return self.feature_states.get(feature_name, {}).get("enabled", False)
    
    async def execute_feature(
        self,
        feature_name: str,
        primary_func: Callable[..., T],
        *args,
        **kwargs
    ) -> T:
        """Execute feature with graceful degradation."""
        feature_state = self.feature_states.get(feature_name)
        if not feature_state:
            # Feature not registered, execute normally
            if asyncio.iscoroutinefunction(primary_func):
                return await primary_func(*args, **kwargs)
            else:
                return primary_func(*args, **kwargs)
        
        if feature_state["enabled"]:
            # Feature fully enabled, execute primary function
            try:
                if asyncio.iscoroutinefunction(primary_func):
                    return await primary_func(*args, **kwargs)
                else:
                    return primary_func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Primary function failed for {feature_name}: {e}")
                # Fall through to degraded mode
        
        # Use degraded implementation
        degraded_func = feature_state.get("degraded_implementation")
        if degraded_func:
            logger.info(f"Using degraded implementation for {feature_name}")
            if asyncio.iscoroutinefunction(degraded_func):
                return await degraded_func(*args, **kwargs)
            else:
                return degraded_func(*args, **kwargs)
        else:
            raise Exception(f"Feature {feature_name} is unavailable and no degraded implementation provided")
    
    def get_feature_status(self) -> Dict[str, Any]:
        """Get status of all features."""
        return {
            "features": self.feature_states,
            "healthy_features": sum(1 for f in self.feature_states.values() if f["enabled"]),
            "total_features": len(self.feature_states),
            "timestamp": time.time()
        }


# Global instances
fallback_service = FallbackService()
degradation_manager = GracefulDegradationManager()

# Service instances
ai_service = ResilientService("ai_service")
tts_service = ResilientService("tts_service")
maps_service = ResilientService("maps_service")
booking_service = ResilientService("booking_service")


def resilient(
    service_name: str,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    retry_policy: Optional[RetryPolicy] = None,
    fallback_func: Optional[Callable] = None
):
    """Decorator to make a function resilient."""
    def decorator(func):
        # Create or get service
        if service_name not in _resilient_services:
            _resilient_services[service_name] = ResilientService(
                service_name, circuit_breaker_config, retry_policy, fallback_service
            )
        
        service = _resilient_services[service_name]
        
        # Register fallback if provided
        if fallback_func:
            fallback_service.register_fallback(service_name, fallback_func)
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await service.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


# Registry for resilient services
_resilient_services: Dict[str, ResilientService] = {}