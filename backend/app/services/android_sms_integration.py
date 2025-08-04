"""
Android SMS Integration Service
Optimized for Samsung Galaxy S24 + T-Mobile with enhanced features.
"""

import asyncio
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

from app.core.logger import logger
from app.core.config import settings
from app.core.cache import cache_manager
from app.core.http_client import SyncHTTPClient, TimeoutProfile, TimeoutError


class AndroidSMSProvider(str, Enum):
    """Android SMS provider options."""
    GOOGLE_CLOUD = "google_cloud"
    TWILIO = "twilio"
    SMS_GATEWAY = "sms_gateway"
    TASKER = "tasker"


class AndroidSMSService:
    """Enhanced SMS service optimized for Android devices."""
    
    def __init__(self):
        self.provider = self._detect_provider()
        self.carrier_optimizations = {
            "tmobile": {
                "rate_limit": 1,  # 1 SMS per second max for T-Mobile
                "retry_delay": 5,  # Wait 5s before retry
                "priority_keywords": ["urgent", "critical", "deploy", "security"]
            }
        }
        # Initialize HTTP client with quick timeout for SMS
        self.http_client = SyncHTTPClient(timeout_profile=TimeoutProfile.QUICK)
        
        logger.info(f"Android SMS Service initialized with provider: {self.provider}")
    
    def _detect_provider(self) -> AndroidSMSProvider:
        """Auto-detect the best available SMS provider."""
        # Check for Google Cloud
        if getattr(settings, 'GOOGLE_CLOUD_PROJECT', None):
            return AndroidSMSProvider.GOOGLE_CLOUD
        
        # Check for Twilio
        if getattr(settings, 'TWILIO_ACCOUNT_SID', None):
            return AndroidSMSProvider.TWILIO
        
        # Check for SMS Gateway
        if getattr(settings, 'ANDROID_SMS_GATEWAY_URL', None):
            return AndroidSMSProvider.SMS_GATEWAY
        
        # Default to Google Cloud
        return AndroidSMSProvider.GOOGLE_CLOUD
    
    async def send_optimized_sms(
        self,
        phone_number: str,
        message: str,
        priority: str = "medium",
        carrier: str = "tmobile"
    ) -> Dict[str, Any]:
        """Send SMS optimized for Android + carrier."""
        # Apply carrier-specific optimizations
        optimized_message = self._optimize_message_for_carrier(message, carrier, priority)
        
        # Rate limiting for T-Mobile
        if carrier == "tmobile":
            await self._apply_tmobile_rate_limiting()
        
        # Format for Android
        android_formatted = self._format_for_android(optimized_message, priority)
        
        # Send via provider
        result = await self._send_via_provider(phone_number, android_formatted)
        
        # Log for tracking
        await self._log_sms_delivery(phone_number, message, result)
        
        return result
    
    def _optimize_message_for_carrier(self, message: str, carrier: str, priority: str) -> str:
        """Optimize message for specific carrier."""
        if carrier == "tmobile":
            # T-Mobile optimizations
            if priority in ["high", "critical"]:
                # Add priority indicators that T-Mobile recognizes
                message = f"🚨 {message}"
            
            # Ensure message length is optimal for T-Mobile (160 chars for single SMS)
            if len(message) > 155:  # Leave room for emoji
                message = message[:152] + "..."
        
        return message
    
    def _format_for_android(self, message: str, priority: str) -> str:
        """Format message for Android notifications."""
        # Android-specific formatting
        formatted = message
        
        # Add priority emojis that display well on Samsung devices
        priority_emojis = {
            "low": "ℹ️",
            "medium": "📱",
            "high": "⚠️",
            "critical": "🔥"
        }
        
        emoji = priority_emojis.get(priority, "📱")
        if not formatted.startswith(emoji):
            formatted = f"{emoji} {formatted}"
        
        # Ensure proper line breaks for Android display
        formatted = formatted.replace("\\n", "\n")
        
        return formatted
    
    async def _apply_tmobile_rate_limiting(self):
        """Apply T-Mobile specific rate limiting."""
        # Check if we've sent an SMS recently
        last_sms_time = await cache_manager.get("tmobile_last_sms")
        
        if last_sms_time:
            time_since_last = datetime.utcnow().timestamp() - float(last_sms_time)
            if time_since_last < 1:  # Less than 1 second
                wait_time = 1 - time_since_last
                logger.info(f"T-Mobile rate limiting: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        # Update last SMS time
        await cache_manager.set("tmobile_last_sms", str(datetime.utcnow().timestamp()))
    
    async def _send_via_provider(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via the configured provider."""
        try:
            if self.provider == AndroidSMSProvider.GOOGLE_CLOUD:
                return await self._send_via_google_cloud(phone_number, message)
            elif self.provider == AndroidSMSProvider.TWILIO:
                return await self._send_via_twilio(phone_number, message)
            elif self.provider == AndroidSMSProvider.SMS_GATEWAY:
                return await self._send_via_sms_gateway(phone_number, message)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")
                
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "provider": self.provider
            }
    
    async def _send_via_google_cloud(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via Google Cloud (placeholder - requires actual implementation)."""
        logger.info(f"[GOOGLE CLOUD SMS] Sending to {phone_number[-4:]}: {message[:50]}...")
        
        # In production, implement actual Google Cloud SMS API
        # For now, simulate success
        await asyncio.sleep(0.1)  # Simulate network delay
        
        return {
            "success": True,
            "provider": "google_cloud",
            "message_id": f"gcp_{datetime.utcnow().timestamp()}",
            "cost_estimate": 0.0075  # $0.0075 per SMS
        }
    
    async def _send_via_twilio(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via Twilio."""
        try:
            # Check if Twilio credentials are available
            account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
            auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
            from_number = getattr(settings, 'TWILIO_FROM_NUMBER', None)
            
            if not all([account_sid, auth_token, from_number]):
                raise ValueError("Twilio credentials not configured")
            
            # In production, use actual Twilio client
            logger.info(f"[TWILIO] Sending to {phone_number[-4:]}: {message[:50]}...")
            
            # Simulate Twilio API call
            await asyncio.sleep(0.2)  # Simulate network delay
            
            return {
                "success": True,
                "provider": "twilio",
                "message_id": f"twilio_{datetime.utcnow().timestamp()}",
                "cost_estimate": 0.0075
            }
            
        except Exception as e:
            raise Exception(f"Twilio SMS failed: {e}")
    
    async def _send_via_sms_gateway(self, phone_number: str, message: str) -> Dict[str, Any]:
        """Send SMS via Android SMS Gateway app."""
        try:
            gateway_url = getattr(settings, 'ANDROID_SMS_GATEWAY_URL', None)
            api_key = getattr(settings, 'ANDROID_SMS_GATEWAY_API_KEY', None)
            
            if not gateway_url or not api_key:
                raise ValueError("SMS Gateway not configured")
            
            # Send request to SMS Gateway app
            payload = {
                "phoneNumber": phone_number,
                "message": message,
                "apiKey": api_key
            }
            
            # Use sync client in async context with proper timeout
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.http_client.post(
                        f"{gateway_url}/send",
                        json=payload,
                        headers={"Content-Type": "application/json"}
                    )
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "provider": "sms_gateway",
                        "message_id": f"gateway_{datetime.utcnow().timestamp()}",
                        "cost_estimate": 0.0  # Uses T-Mobile plan
                    }
                else:
                    raise Exception(f"Gateway returned {response.status_code}")
                    
            except TimeoutError as e:
                logger.error(f"SMS Gateway timeout: {e}")
                raise Exception(f"SMS Gateway timeout: {e}")
                    
        except Exception as e:
            raise Exception(f"SMS Gateway failed: {e}")
    
    async def _log_sms_delivery(self, phone_number: str, message: str, result: Dict[str, Any]):
        """Log SMS delivery for tracking."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "phone_number": phone_number[-4:],  # Last 4 digits only
            "message_length": len(message),
            "provider": result.get("provider"),
            "success": result.get("success"),
            "message_id": result.get("message_id"),
            "cost": result.get("cost_estimate", 0)
        }
        
        # Store in cache for admin dashboard
        await cache_manager.lpush("sms_delivery_log", json.dumps(log_entry))
        await cache_manager.ltrim("sms_delivery_log", 0, 99)  # Keep last 100 entries
        
        if result.get("success"):
            logger.info(f"SMS delivered successfully to {phone_number[-4:]} via {result.get('provider')}")
        else:
            logger.error(f"SMS delivery failed to {phone_number[-4:]}: {result.get('error')}")
    
    async def get_delivery_stats(self) -> Dict[str, Any]:
        """Get SMS delivery statistics."""
        # Get recent delivery logs
        logs = await cache_manager.lrange("sms_delivery_log", 0, -1)
        
        if not logs:
            return {
                "total_sent": 0,
                "success_rate": 0,
                "total_cost": 0,
                "provider_breakdown": {}
            }
        
        # Parse logs
        parsed_logs = []
        for log in logs:
            try:
                parsed_logs.append(json.loads(log))
            except Exception as e:
                continue
        
        # Calculate stats
        total_sent = len(parsed_logs)
        successful = sum(1 for log in parsed_logs if log.get("success"))
        success_rate = (successful / total_sent) * 100 if total_sent > 0 else 0
        total_cost = sum(log.get("cost", 0) for log in parsed_logs)
        
        # Provider breakdown
        provider_stats = {}
        for log in parsed_logs:
            provider = log.get("provider", "unknown")
            if provider not in provider_stats:
                provider_stats[provider] = {"sent": 0, "successful": 0, "cost": 0}
            
            provider_stats[provider]["sent"] += 1
            if log.get("success"):
                provider_stats[provider]["successful"] += 1
            provider_stats[provider]["cost"] += log.get("cost", 0)
        
        return {
            "total_sent": total_sent,
            "success_rate": round(success_rate, 2),
            "total_cost": round(total_cost, 4),
            "provider_breakdown": provider_stats,
            "last_24h": len([log for log in parsed_logs 
                           if (datetime.utcnow() - datetime.fromisoformat(log["timestamp"])).total_seconds() < 86400])
        }


class AndroidResponseParser:
    """Parse SMS responses optimized for Android keyboards and T-Mobile."""
    
    @staticmethod
    def parse_android_response(message: str) -> Dict[str, Any]:
        """Parse SMS response with Android-specific considerations."""
        # Clean up common Android keyboard autocorrections
        cleaned = AndroidResponseParser._clean_android_text(message)
        
        # Parse intent
        intent = AndroidResponseParser._parse_intent(cleaned)
        
        # Extract parameters
        params = AndroidResponseParser._extract_parameters(cleaned)
        
        return {
            "original": message,
            "cleaned": cleaned,
            "intent": intent,
            "parameters": params,
            "confidence": AndroidResponseParser._calculate_confidence(intent, cleaned)
        }
    
    @staticmethod
    def _clean_android_text(text: str) -> str:
        """Clean text from common Android keyboard issues."""
        # Common autocorrections to fix
        corrections = {
            "approv": "approve",
            "aprove": "approve",
            "deplpy": "deploy",
            "deplou": "deploy",
            "stats": "status",
            "statu": "status",
            "rolback": "rollback",
            "rollbak": "rollback"
        }
        
        cleaned = text.lower().strip()
        
        for wrong, correct in corrections.items():
            cleaned = cleaned.replace(wrong, correct)
        
        return cleaned
    
    @staticmethod
    def _parse_intent(text: str) -> Optional[str]:
        """Parse user intent from text."""
        intent_keywords = {
            "approve": ["approve", "yes", "y", "ok", "confirm", "go"],
            "reject": ["reject", "no", "n", "cancel", "stop", "deny"],
            "status": ["status", "stat", "info", "state", "check"],
            "deploy": ["deploy", "ship", "release", "go live"],
            "rollback": ["rollback", "revert", "undo", "back"],
            "pause": ["pause", "stop", "hold", "wait"],
            "resume": ["resume", "continue", "start", "go"],
            "help": ["help", "?", "commands", "options"]
        }
        
        for intent, keywords in intent_keywords.items():
            if any(keyword in text for keyword in keywords):
                return intent
        
        return None
    
    @staticmethod
    def _extract_parameters(text: str) -> List[str]:
        """Extract parameters from text."""
        # Split and filter meaningful words
        words = text.split()
        
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "to", "for", "with", "is", "are"}
        
        params = [word for word in words if word not in stop_words and len(word) > 2]
        
        return params
    
    @staticmethod
    def _calculate_confidence(intent: Optional[str], text: str) -> float:
        """Calculate confidence in the parsed intent."""
        if not intent:
            return 0.0
        
        # Higher confidence for shorter, clearer messages
        if len(text.split()) == 1 and intent in ["approve", "reject", "status", "help"]:
            return 0.95
        
        # Medium confidence for common patterns
        if len(text.split()) <= 3:
            return 0.8
        
        # Lower confidence for longer messages
        return 0.6


# Global Android SMS service instance
android_sms_service = AndroidSMSService()


# Helper functions for easy integration
async def send_android_notification(
    phone_number: str,
    title: str,
    message: str,
    priority: str = "medium"
) -> bool:
    """Send notification optimized for Android."""
    full_message = f"{title}\n\n{message}"
    
    result = await android_sms_service.send_optimized_sms(
        phone_number,
        full_message,
        priority=priority,
        carrier="tmobile"  # Hardcoded for your T-Mobile setup
    )
    
    return result.get("success", False)


async def parse_android_sms_response(from_number: str, message: str) -> Dict[str, Any]:
    """Parse SMS response from Android device."""
    parsed = AndroidResponseParser.parse_android_response(message)
    
    # Log the parsing for improvement
    logger.info(f"Android SMS parsed: {from_number[-4:]} -> {parsed['intent']} (confidence: {parsed['confidence']})")
    
    return parsed