"""
Circuit Breaker Monitoring Endpoints

Provides real-time visibility into circuit breaker states and statistics.
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List
from datetime import datetime

from app.core.auth import get_current_admin_user
from app.models.user import User
from app.core.circuit_breaker import circuit_breaker_manager, CircuitState
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/monitoring/circuit-breakers", tags=["Circuit Breaker Monitoring"])


@router.get("/status")
async def get_all_circuit_breakers_status(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get status of all circuit breakers in the system.
    
    Returns comprehensive statistics for each circuit breaker including:
    - Current state (CLOSED, OPEN, HALF_OPEN)
    - Failure count
    - Success count
    - Average response time
    - Last failure time
    - Last state change
    """
    try:
        all_stats = circuit_breaker_manager.get_all_stats()
        
        # Calculate summary statistics
        total_breakers = len(all_stats)
        open_count = sum(1 for stats in all_stats.values() if stats['state'] == 'open')
        half_open_count = sum(1 for stats in all_stats.values() if stats['state'] == 'half_open')
        closed_count = sum(1 for stats in all_stats.values() if stats['state'] == 'closed')
        
        # Calculate health score (0-100)
        health_score = ((closed_count + half_open_count * 0.5) / total_breakers * 100) if total_breakers > 0 else 100
        
        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_circuit_breakers": total_breakers,
                "states": {
                    "closed": closed_count,
                    "open": open_count,
                    "half_open": half_open_count
                },
                "health_score": round(health_score, 2),
                "critical_services_affected": open_count > 0
            },
            "circuit_breakers": all_stats
        }
    except Exception as e:
        logger.error(f"Error getting circuit breaker status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve circuit breaker status")


@router.get("/status/{circuit_name}")
async def get_circuit_breaker_status(
    circuit_name: str,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get detailed status of a specific circuit breaker.
    
    Args:
        circuit_name: Name of the circuit breaker (e.g., 'vertex-ai', 'google-maps')
    """
    try:
        all_stats = circuit_breaker_manager.get_all_stats()
        
        if circuit_name not in all_stats:
            raise HTTPException(status_code=404, detail=f"Circuit breaker '{circuit_name}' not found")
        
        stats = all_stats[circuit_name]
        
        # Add recommendations based on state
        recommendations = []
        if stats['state'] == 'open':
            recommendations.append("Service is currently failing. Check external service status.")
            recommendations.append("Consider implementing fallback mechanisms.")
        elif stats['state'] == 'half_open':
            recommendations.append("Service is being tested for recovery.")
            recommendations.append("Monitor closely for successful requests.")
        
        return {
            "circuit_name": circuit_name,
            "status": stats,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting circuit breaker {circuit_name} status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve circuit breaker status")


@router.post("/reset/{circuit_name}")
async def reset_circuit_breaker(
    circuit_name: str,
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Manually reset a circuit breaker to CLOSED state.
    
    This should be used with caution, only after verifying the external service
    is functioning properly.
    
    Args:
        circuit_name: Name of the circuit breaker to reset
    """
    try:
        breakers = circuit_breaker_manager._breakers
        
        if circuit_name not in breakers:
            raise HTTPException(status_code=404, detail=f"Circuit breaker '{circuit_name}' not found")
        
        breaker = breakers[circuit_name]
        breaker.reset()
        
        logger.info(f"Circuit breaker '{circuit_name}' manually reset by admin {current_user.id}")
        
        return {
            "message": f"Circuit breaker '{circuit_name}' has been reset to CLOSED state",
            "circuit_name": circuit_name,
            "new_state": "closed",
            "reset_by": current_user.email,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting circuit breaker {circuit_name}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset circuit breaker")


@router.post("/reset-all")
async def reset_all_circuit_breakers(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Reset all circuit breakers to CLOSED state.
    
    This is a dangerous operation and should only be used in emergency situations
    or after confirming all external services are operational.
    """
    try:
        circuit_breaker_manager.reset_all()
        
        logger.warning(f"All circuit breakers reset by admin {current_user.id}")
        
        return {
            "message": "All circuit breakers have been reset to CLOSED state",
            "reset_by": current_user.email,
            "timestamp": datetime.now().isoformat(),
            "warning": "This is a dangerous operation. Monitor external service calls closely."
        }
    except Exception as e:
        logger.error(f"Error resetting all circuit breakers: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset circuit breakers")


@router.get("/thresholds")
async def get_circuit_breaker_thresholds(
    current_user: User = Depends(get_current_admin_user)
) -> Dict[str, Any]:
    """
    Get configured thresholds for all circuit breakers.
    
    Returns the configuration parameters for each circuit breaker including:
    - Failure threshold
    - Recovery timeout
    - Success threshold
    - Request timeout
    """
    try:
        breakers = circuit_breaker_manager._breakers
        
        thresholds = {}
        for name, breaker in breakers.items():
            thresholds[name] = {
                "failure_threshold": breaker.failure_threshold,
                "recovery_timeout": breaker.recovery_timeout,
                "success_threshold": breaker.success_threshold,
                "timeout": breaker.timeout,
                "expected_exception": breaker.expected_exception.__name__
            }
        
        return {
            "circuit_breakers": thresholds,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting circuit breaker thresholds: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve thresholds")


@router.get("/alerts")
async def get_circuit_breaker_alerts(
    current_user: User = Depends(get_current_admin_user)
) -> List[Dict[str, Any]]:
    """
    Get active alerts for circuit breakers.
    
    Returns a list of circuit breakers that are currently in OPEN or HALF_OPEN state,
    indicating potential issues with external services.
    """
    try:
        all_stats = circuit_breaker_manager.get_all_stats()
        
        alerts = []
        for name, stats in all_stats.items():
            if stats['state'] in ['open', 'half_open']:
                alert = {
                    "circuit_name": name,
                    "state": stats['state'],
                    "severity": "critical" if stats['state'] == 'open' else "warning",
                    "message": f"Circuit breaker '{name}' is {stats['state'].upper()}",
                    "failure_count": stats['failure_count'],
                    "last_failure_time": stats['last_failure_time'],
                    "last_state_change": stats['last_state_change'],
                    "recommended_action": (
                        "Check external service status and logs" 
                        if stats['state'] == 'open' 
                        else "Monitor for successful recovery"
                    )
                }
                alerts.append(alert)
        
        return alerts
    except Exception as e:
        logger.error(f"Error getting circuit breaker alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve alerts")