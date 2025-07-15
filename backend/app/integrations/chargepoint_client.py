"""
ChargePoint API client for EV charging station integration.
ChargePoint is one of the largest EV charging networks in North America.
"""

import httpx
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import base64
from urllib.parse import urlencode

from backend.app.core.config import settings
from backend.app.core.cache import cache_manager
from backend.app.core.logger import logger
from backend.app.core.resilience import CircuitBreaker, circuit_breaker_factory


class ChargePointClient:
    """Client for ChargePoint API integration."""
    
    BASE_URL = "https://api.chargepoint.com"
    AUTH_URL = "https://api.chargepoint.com/oauth/token"
    
    def __init__(self):
        self.client_id = settings.CHARGEPOINT_CLIENT_ID
        self.client_secret = settings.CHARGEPOINT_CLIENT_SECRET
        self.api_key = settings.CHARGEPOINT_API_KEY
        
        # Basic auth for OAuth
        credentials = f"{self.client_id}:{self.client_secret}"
        self.basic_auth = base64.b64encode(credentials.encode()).decode()
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "X-API-Key": self.api_key
            }
        )
        
        # Circuit breaker for fault tolerance
        self.circuit_breaker = circuit_breaker_factory.create("chargepoint_api")
        
        # Token management
        self._access_token = None
        self._token_expires_at = None
    
    async def find_stations(
        self,
        lat: float,
        lon: float,
        radius_miles: float = 25.0,
        connector_types: Optional[List[str]] = None,
        power_level: Optional[str] = None,
        available_only: bool = True,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Find charging stations near a location.
        
        Args:
            lat/lon: Geographic coordinates
            radius_miles: Search radius
            connector_types: Filter by connector types (CCS, CHAdeMO, J1772)
            power_level: Filter by power level (Level2, DC_Fast)
            available_only: Only show available stations
            limit: Number of results
            
        Returns:
            List of charging stations with availability
        """
        cache_params = f"{lat}:{lon}:{radius_miles}:{available_only}"
        cache_key = f"chargepoint:stations:{cache_params}"
        
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            await self._ensure_authenticated()
            
            params = {
                "lat": lat,
                "lon": lon,
                "radius": radius_miles,
                "limit": limit
            }
            
            if connector_types:
                params["connector_types"] = ",".join(connector_types)
            
            if power_level:
                params["power_level"] = power_level
                
            if available_only:
                params["status"] = "available"
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                "/v1/stations/nearby",
                params=params
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Enhance with pricing and wait time estimates
                stations = result.get("stations", [])
                for station in stations:
                    # Add estimated pricing
                    power_kw = station.get("max_power_kw", 50)
                    if power_kw > 100:  # DC Fast
                        station["estimated_cost_per_kwh"] = 0.35
                        station["estimated_wait_time_min"] = 5
                    else:  # Level 2
                        station["estimated_cost_per_kwh"] = 0.20
                        station["estimated_wait_time_min"] = 0
                    
                    # Commission eligible
                    station["commission_eligible"] = True
                    station["commission_rate"] = 0.10  # 10% commission
                
                # Cache for 5 minutes (availability changes frequently)
                await cache_manager.set(cache_key, result, ttl=300)
                
                logger.info(f"ChargePoint search returned {len(stations)} stations")
                return result
            else:
                logger.error(f"Station search failed: {response.status_code}")
                return {"stations": [], "error": "Search failed"}
                
        except Exception as e:
            logger.error(f"ChargePoint search error: {str(e)}")
            return {"stations": [], "error": str(e)}
    
    async def get_station_details(
        self,
        station_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get detailed information about a charging station."""
        cache_key = f"chargepoint:station:{station_id}"
        
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            await self._ensure_authenticated()
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                f"/v1/stations/{station_id}"
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Add real-time port availability
                ports = result.get("ports", [])
                available_ports = sum(1 for p in ports if p.get("status") == "AVAILABLE")
                result["available_ports"] = available_ports
                result["total_ports"] = len(ports)
                
                # Cache for 2 minutes
                await cache_manager.set(cache_key, result, ttl=120)
                
                return result
            else:
                logger.error(f"Failed to get station details: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting station details: {str(e)}")
            return None
    
    async def get_real_time_status(
        self,
        station_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """Get real-time status for multiple stations."""
        try:
            await self._ensure_authenticated()
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "POST",
                "/v1/stations/status",
                json={"station_ids": station_ids}
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Format response as dict keyed by station_id
                status_dict = {}
                for status in result.get("statuses", []):
                    station_id = status.get("station_id")
                    status_dict[station_id] = {
                        "available": status.get("available_ports", 0),
                        "occupied": status.get("occupied_ports", 0),
                        "total": status.get("total_ports", 0),
                        "status": status.get("station_status"),
                        "last_updated": status.get("last_updated")
                    }
                
                return status_dict
            else:
                logger.error(f"Failed to get real-time status: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting real-time status: {str(e)}")
            return {}
    
    async def start_session(
        self,
        station_id: str,
        port_id: str,
        user_id: str,
        payment_method_id: str
    ) -> Dict[str, Any]:
        """
        Start a charging session.
        
        Args:
            station_id: ChargePoint station ID
            port_id: Specific port ID
            user_id: User identifier
            payment_method_id: Payment method to use
            
        Returns:
            Session details or error
        """
        try:
            await self._ensure_authenticated()
            
            session_data = {
                "station_id": station_id,
                "port_id": port_id,
                "user_id": user_id,
                "payment_method_id": payment_method_id,
                "auto_stop": True,  # Auto-stop when fully charged
                "max_kwh": 100,  # Safety limit
                "notification_preferences": {
                    "session_start": True,
                    "session_complete": True,
                    "charging_stopped": True
                }
            }
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "POST",
                "/v1/sessions/start",
                json=session_data
            )
            
            if response.status_code in (200, 201):
                result = response.json()
                
                logger.info(f"Charging session started: {result.get('session_id')}")
                
                # Calculate estimated commission
                # ChargePoint typically offers 10-15% on charging revenue
                commission_rate = 0.10
                result["commission"] = {
                    "rate": commission_rate,
                    "estimated_per_kwh": 0.035,  # $0.035 per kWh
                    "currency": "USD"
                }
                
                return result
            else:
                logger.error(f"Failed to start session: {response.status_code}")
                error_data = response.json()
                return {
                    "success": False,
                    "error": error_data.get("message", "Session start failed"),
                    "details": error_data
                }
                
        except Exception as e:
            logger.error(f"Error starting session: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_session_status(
        self,
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current charging session status."""
        try:
            await self._ensure_authenticated()
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                f"/v1/sessions/{session_id}"
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Calculate current cost
                kwh_delivered = result.get("energy_delivered_kwh", 0)
                rate_per_kwh = result.get("rate_per_kwh", 0.35)
                current_cost = kwh_delivered * rate_per_kwh
                
                result["current_cost"] = {
                    "amount": current_cost,
                    "currency": "USD",
                    "kwh_delivered": kwh_delivered,
                    "rate_per_kwh": rate_per_kwh
                }
                
                # Add commission earned so far
                result["commission_earned"] = current_cost * 0.10
                
                return result
            else:
                logger.error(f"Failed to get session status: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting session status: {str(e)}")
            return None
    
    async def stop_session(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """Stop a charging session."""
        try:
            await self._ensure_authenticated()
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "POST",
                f"/v1/sessions/{session_id}/stop"
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Calculate final commission
                total_cost = result.get("total_cost", {}).get("amount", 0)
                commission = total_cost * 0.10
                
                result["commission"] = {
                    "amount": commission,
                    "rate": 0.10,
                    "currency": "USD"
                }
                
                logger.info(f"Charging session stopped: {session_id}")
                return result
            else:
                logger.error(f"Failed to stop session: {response.status_code}")
                return {
                    "success": False,
                    "error": f"Failed to stop session: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"Error stopping session: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_pricing(
        self,
        station_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get pricing information for a station."""
        cache_key = f"chargepoint:pricing:{station_id}"
        
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
            
        try:
            await self._ensure_authenticated()
            
            response = await self.circuit_breaker.call(
                self._make_request,
                "GET",
                f"/v1/stations/{station_id}/pricing"
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Cache for 1 hour
                await cache_manager.set(cache_key, result, ttl=3600)
                
                return result
            else:
                logger.error(f"Failed to get pricing: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting pricing: {str(e)}")
            return None
    
    async def estimate_charging_time(
        self,
        vehicle_model: str,
        current_soc: float,  # State of charge (0-100)
        target_soc: float,   # Target state of charge
        station_power_kw: float
    ) -> Dict[str, Any]:
        """Estimate charging time for a vehicle."""
        try:
            # Simple estimation (would be more complex in production)
            # This is a simplified calculation
            battery_capacity = {
                "Tesla Model 3": 75,
                "Tesla Model Y": 75,
                "Chevrolet Bolt": 65,
                "Nissan Leaf": 40,
                "Ford Mustang Mach-E": 88,
                "default": 60
            }.get(vehicle_model, 60)
            
            kwh_needed = battery_capacity * (target_soc - current_soc) / 100
            
            # Account for charging curve (slower as battery fills)
            if target_soc > 80:
                effective_power = station_power_kw * 0.7
            else:
                effective_power = station_power_kw * 0.9
            
            charging_time_hours = kwh_needed / effective_power
            charging_time_minutes = int(charging_time_hours * 60)
            
            # Estimate cost
            cost_per_kwh = 0.35 if station_power_kw > 50 else 0.20
            estimated_cost = kwh_needed * cost_per_kwh
            
            return {
                "estimated_time_minutes": charging_time_minutes,
                "kwh_to_add": round(kwh_needed, 2),
                "estimated_cost": round(estimated_cost, 2),
                "effective_charging_rate_kw": round(effective_power, 2)
            }
            
        except Exception as e:
            logger.error(f"Error estimating charging time: {str(e)}")
            return {
                "error": str(e)
            }
    
    async def _ensure_authenticated(self):
        """Ensure we have a valid access token."""
        if self._access_token and self._token_expires_at:
            if datetime.utcnow() < self._token_expires_at:
                return
        
        # Get new token
        await self._authenticate()
    
    async def _authenticate(self):
        """Authenticate and get access token."""
        try:
            auth_headers = {
                "Authorization": f"Basic {self.basic_auth}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            auth_data = {
                "grant_type": "client_credentials",
                "scope": "read write"
            }
            
            response = await self.client.post(
                self.AUTH_URL,
                headers=auth_headers,
                data=urlencode(auth_data)
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self._access_token = token_data["access_token"]
                
                # Calculate expiration
                expires_in = token_data.get("expires_in", 3600)
                self._token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 60)
                
                # Update client headers
                self.client.headers["Authorization"] = f"Bearer {self._access_token}"
                
                logger.info("ChargePoint authentication successful")
            else:
                logger.error(f"ChargePoint authentication failed: {response.status_code}")
                raise Exception("Authentication failed")
                
        except Exception as e:
            logger.error(f"Error during authentication: {str(e)}")
            raise
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> httpx.Response:
        """Make HTTP request to ChargePoint API."""
        url = f"{self.BASE_URL}{endpoint}"
        
        response = await self.client.request(
            method,
            url,
            **kwargs
        )
        
        return response
    
    def __del__(self):
        """Cleanup when client is destroyed."""
        if hasattr(self, 'client'):
            asyncio.create_task(self.client.aclose())


# Singleton instance
chargepoint_client = ChargePointClient()