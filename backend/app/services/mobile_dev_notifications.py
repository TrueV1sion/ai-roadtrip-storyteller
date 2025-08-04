"""
Mobile Development Notifications Service
Enables remote development monitoring and control via SMS/mobile notifications.
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, asdict
import hashlib
import secrets

from app.core.logger import logger
from app.core.config import settings
from app.core.cache import cache_manager


class NotificationType(str, Enum):
    """Types of development notifications."""
    BUILD_STATUS = "build_status"
    DEPLOYMENT_UPDATE = "deployment_update"
    SECURITY_ALERT = "security_alert"
    ERROR_CRITICAL = "error_critical"
    TASK_COMPLETE = "task_complete"
    APPROVAL_REQUEST = "approval_request"
    SYSTEM_STATUS = "system_status"


class ResponseAction(str, Enum):
    """Available SMS response actions."""
    APPROVE = "approve"
    REJECT = "reject"
    STATUS = "status"
    PAUSE = "pause"
    RESUME = "resume"
    DEPLOY = "deploy"
    ROLLBACK = "rollback"
    HELP = "help"


@dataclass
class DevNotification:
    """Development notification structure."""
    id: str
    type: NotificationType
    title: str
    message: str
    priority: str  # low, medium, high, critical
    timestamp: datetime
    requires_response: bool = False
    response_timeout: Optional[int] = None  # minutes
    context: Dict[str, Any] = None
    phone_number: Optional[str] = None
    
    def to_sms_format(self) -> str:
        """Format notification for SMS."""
        priority_emoji = {
            "low": "ℹ️",
            "medium": "⚠️",
            "high": "🚨",
            "critical": "🔥"
        }
        
        emoji = priority_emoji.get(self.priority, "📱")
        sms = f"{emoji} {self.title}\n\n{self.message}"
        
        if self.requires_response:
            sms += f"\n\nReply with action or 'help' for options"
            if self.response_timeout:
                sms += f" (timeout: {self.response_timeout}m)"
        
        return sms[:1000]  # SMS length limit


class MobileDevNotificationService:
    """Service for mobile development notifications and SMS responses."""
    
    def __init__(self):
        self.pending_notifications: Dict[str, DevNotification] = {}
        self.response_handlers: Dict[ResponseAction, Callable] = {}
        self.authorized_numbers: List[str] = []
        self.session_tokens: Dict[str, str] = {}
        
        # Register default response handlers
        self._register_default_handlers()
        
        # Load authorized numbers from environment
        self._load_authorized_numbers()
        
        logger.info("Mobile Development Notification Service initialized")
    
    def _register_default_handlers(self):
        """Register default SMS response handlers."""
        self.response_handlers = {
            ResponseAction.STATUS: self._handle_status_request,
            ResponseAction.APPROVE: self._handle_approval,
            ResponseAction.REJECT: self._handle_rejection,
            ResponseAction.PAUSE: self._handle_pause_development,
            ResponseAction.RESUME: self._handle_resume_development,
            ResponseAction.DEPLOY: self._handle_deploy_request,
            ResponseAction.ROLLBACK: self._handle_rollback_request,
            ResponseAction.HELP: self._handle_help_request,
        }
    
    def _load_authorized_numbers(self):
        """Load authorized phone numbers from configuration."""
        # In production, load from Secret Manager
        # For now, use environment variable
        numbers = getattr(settings, 'DEV_AUTHORIZED_PHONES', '').split(',')
        self.authorized_numbers = [n.strip() for n in numbers if n.strip()]
        
        if not self.authorized_numbers:
            logger.warning("No authorized phone numbers configured for mobile dev notifications")
    
    async def send_notification(
        self,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: str = "medium",
        requires_response: bool = False,
        response_timeout: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
        phone_number: Optional[str] = None
    ) -> str:
        """Send a development notification via SMS."""
        notification_id = self._generate_notification_id()
        
        notification = DevNotification(
            id=notification_id,
            type=notification_type,
            title=title,
            message=message,
            priority=priority,
            timestamp=datetime.utcnow(),
            requires_response=requires_response,
            response_timeout=response_timeout,
            context=context or {},
            phone_number=phone_number
        )
        
        # Store notification for potential responses
        if requires_response:
            self.pending_notifications[notification_id] = notification
            
            # Set timeout for cleanup
            if response_timeout:
                asyncio.create_task(self._cleanup_expired_notification(notification_id, response_timeout))
        
        # Send via configured providers
        await self._send_via_providers(notification)
        
        logger.info(f"Development notification sent: {notification_id}")
        return notification_id
    
    async def _send_via_providers(self, notification: DevNotification):
        """Send notification via available providers."""
        target_numbers = [notification.phone_number] if notification.phone_number else self.authorized_numbers
        
        for phone_number in target_numbers:
            if not phone_number:
                continue
                
            try:
                # Try multiple providers in order of preference
                success = await self._try_send_sms(phone_number, notification.to_sms_format())
                
                if success:
                    logger.info(f"SMS sent successfully to {phone_number[-4:]}")
                else:
                    logger.warning(f"Failed to send SMS to {phone_number[-4:]}")
                    
                    # Fallback to email if SMS fails
                    await self._send_email_fallback(phone_number, notification)
                    
            except Exception as e:
                logger.error(f"Error sending notification to {phone_number[-4:]}: {e}")
    
    async def _try_send_sms(self, phone_number: str, message: str) -> bool:
        """Try to send SMS via available providers."""
        providers = [
            self._send_via_twilio,
            self._send_via_aws_sns,
            self._send_via_google_sms,
        ]
        
        for provider in providers:
            try:
                success = await provider(phone_number, message)
                if success:
                    return True
            except Exception as e:
                logger.warning(f"SMS provider failed: {e}")
                continue
        
        return False
    
    async def _send_via_twilio(self, phone_number: str, message: str) -> bool:
        """Send SMS via Twilio (placeholder implementation)."""
        # In production, implement actual Twilio integration
        twilio_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        twilio_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        twilio_from = getattr(settings, 'TWILIO_FROM_NUMBER', None)
        
        if not all([twilio_sid, twilio_token, twilio_from]):
            logger.debug("Twilio credentials not configured")
            return False
        
        # Simulated Twilio API call
        logger.info(f"[TWILIO SIMULATION] Sending SMS to {phone_number[-4:]}: {message[:50]}...")
        
        # In production:
        # from twilio.rest import Client
        # client = Client(twilio_sid, twilio_token)
        # client.messages.create(body=message, from_=twilio_from, to=phone_number)
        
        return True
    
    async def _send_via_aws_sns(self, phone_number: str, message: str) -> bool:
        """Send SMS via AWS SNS (placeholder implementation)."""
        aws_region = getattr(settings, 'AWS_REGION', None)
        if not aws_region:
            logger.debug("AWS SNS not configured")
            return False
        
        logger.info(f"[AWS SNS SIMULATION] Sending SMS to {phone_number[-4:]}: {message[:50]}...")
        
        # In production:
        # import boto3
        # sns = boto3.client('sns', region_name=aws_region)
        # sns.publish(PhoneNumber=phone_number, Message=message)
        
        return True
    
    async def _send_via_google_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS via Google Cloud SMS (placeholder implementation)."""
        project_id = getattr(settings, 'GOOGLE_CLOUD_PROJECT', None)
        if not project_id:
            logger.debug("Google Cloud SMS not configured")
            return False
        
        logger.info(f"[GOOGLE SMS SIMULATION] Sending SMS to {phone_number[-4:]}: {message[:50]}...")
        return True
    
    async def _send_email_fallback(self, phone_number: str, notification: DevNotification):
        """Send email as fallback when SMS fails."""
        # Convert phone to email if configured
        email_mapping = getattr(settings, 'DEV_PHONE_EMAIL_MAPPING', {})
        email = email_mapping.get(phone_number)
        
        if email:
            logger.info(f"Sending email fallback to {email}")
            # Implement email sending here
    
    async def handle_sms_response(self, from_number: str, message_body: str) -> str:
        """Handle incoming SMS response."""
        # Verify authorized number
        if from_number not in self.authorized_numbers:
            logger.warning(f"Unauthorized SMS response from {from_number[-4:]}")
            return "Unauthorized number"
        
        # Parse response
        response_action, params = self._parse_sms_response(message_body)
        
        if not response_action:
            return await self._handle_help_request(from_number, [])
        
        # Handle the response
        handler = self.response_handlers.get(response_action)
        if handler:
            try:
                response = await handler(from_number, params)
                logger.info(f"SMS response handled: {response_action} from {from_number[-4:]}")
                return response
            except Exception as e:
                logger.error(f"Error handling SMS response: {e}")
                return f"Error processing command: {str(e)}"
        else:
            return f"Unknown command: {response_action}. Reply 'help' for options."
    
    def _parse_sms_response(self, message: str) -> tuple[Optional[ResponseAction], List[str]]:
        """Parse SMS response into action and parameters."""
        message = message.strip().lower()
        parts = message.split()
        
        if not parts:
            return None, []
        
        command = parts[0]
        params = parts[1:] if len(parts) > 1 else []
        
        # Map common variations
        command_mapping = {
            'yes': ResponseAction.APPROVE,
            'y': ResponseAction.APPROVE,
            'ok': ResponseAction.APPROVE,
            'approve': ResponseAction.APPROVE,
            'no': ResponseAction.REJECT,
            'n': ResponseAction.REJECT,
            'reject': ResponseAction.REJECT,
            'status': ResponseAction.STATUS,
            'stat': ResponseAction.STATUS,
            'pause': ResponseAction.PAUSE,
            'stop': ResponseAction.PAUSE,
            'resume': ResponseAction.RESUME,
            'continue': ResponseAction.RESUME,
            'deploy': ResponseAction.DEPLOY,
            'rollback': ResponseAction.ROLLBACK,
            'help': ResponseAction.HELP,
            '?': ResponseAction.HELP,
        }
        
        action = command_mapping.get(command)
        return action, params
    
    async def _handle_status_request(self, from_number: str, params: List[str]) -> str:
        """Handle status request via SMS."""
        # Get current development status
        status_info = await self._get_development_status()
        
        response = f"🚀 Development Status:\n"
        response += f"• Environment: {status_info.get('environment', 'unknown')}\n"
        response += f"• Last Deploy: {status_info.get('last_deploy', 'never')}\n"
        response += f"• Active Tasks: {status_info.get('active_tasks', 0)}\n"
        response += f"• System Health: {status_info.get('health', 'unknown')}\n"
        
        if status_info.get('pending_approvals'):
            response += f"• Pending Approvals: {len(status_info['pending_approvals'])}\n"
        
        return response
    
    async def _handle_approval(self, from_number: str, params: List[str]) -> str:
        """Handle approval response."""
        if not self.pending_notifications:
            return "No pending approvals"
        
        # Find most recent approval request
        latest_notification = max(
            [n for n in self.pending_notifications.values() if n.requires_response],
            key=lambda x: x.timestamp,
            default=None
        )
        
        if latest_notification:
            # Process approval
            await self._process_approval(latest_notification.id, True)
            del self.pending_notifications[latest_notification.id]
            
            return f"✅ Approved: {latest_notification.title}"
        
        return "No pending approvals found"
    
    async def _handle_rejection(self, from_number: str, params: List[str]) -> str:
        """Handle rejection response."""
        if not self.pending_notifications:
            return "No pending approvals"
        
        latest_notification = max(
            [n for n in self.pending_notifications.values() if n.requires_response],
            key=lambda x: x.timestamp,
            default=None
        )
        
        if latest_notification:
            await self._process_approval(latest_notification.id, False)
            del self.pending_notifications[latest_notification.id]
            
            return f"❌ Rejected: {latest_notification.title}"
        
        return "No pending approvals found"
    
    async def _handle_pause_development(self, from_number: str, params: List[str]) -> str:
        """Handle pause development request."""
        await cache_manager.set("dev_status:paused", "true", ttl=3600*24)  # 24 hours
        logger.info(f"Development paused via SMS from {from_number[-4:]}")
        return "⏸️ Development paused. Reply 'resume' to continue."
    
    async def _handle_resume_development(self, from_number: str, params: List[str]) -> str:
        """Handle resume development request."""
        await cache_manager.delete("dev_status:paused")
        logger.info(f"Development resumed via SMS from {from_number[-4:]}")
        return "▶️ Development resumed."
    
    async def _handle_deploy_request(self, from_number: str, params: List[str]) -> str:
        """Handle deployment request."""
        # Check if deployment is safe
        status = await self._get_development_status()
        
        if not status.get('ready_for_deploy', False):
            return f"❌ Deployment blocked: {status.get('deploy_blocker', 'Unknown issue')}"
        
        # In production, trigger actual deployment
        logger.info(f"Deployment requested via SMS from {from_number[-4:]}")
        
        # Store deployment request for processing
        await cache_manager.set("dev_action:deploy_requested", "true", ttl=300)  # 5 minutes
        
        return "🚀 Deployment initiated. You'll receive status updates."
    
    async def _handle_rollback_request(self, from_number: str, params: List[str]) -> str:
        """Handle rollback request."""
        version = params[0] if params else "previous"
        
        logger.info(f"Rollback to {version} requested via SMS from {from_number[-4:]}")
        
        # Store rollback request
        await cache_manager.set("dev_action:rollback_requested", version, ttl=300)
        
        return f"🔄 Rollback to {version} initiated."
    
    async def _handle_help_request(self, from_number: str, params: List[str]) -> str:
        """Handle help request."""
        help_text = """📱 Mobile Dev Commands:
        
• status - Get current status
• approve/yes - Approve pending action
• reject/no - Reject pending action
• pause/stop - Pause development
• resume - Resume development
• deploy - Deploy to production
• rollback - Rollback deployment
• help - Show this help

Reply with any command to control development remotely."""
        
        return help_text
    
    async def _get_development_status(self) -> Dict[str, Any]:
        """Get current development status."""
        # In production, check actual system status
        status = {
            "environment": getattr(settings, 'ENVIRONMENT', 'development'),
            "last_deploy": "2024-01-15 10:30 UTC",  # From deployment logs
            "active_tasks": len(self.pending_notifications),
            "health": "healthy",  # From health checks
            "ready_for_deploy": False,  # From deployment checks
            "deploy_blocker": "Credentials rotation required",
            "pending_approvals": list(self.pending_notifications.keys())
        }
        
        return status
    
    async def _process_approval(self, notification_id: str, approved: bool):
        """Process approval/rejection of a pending action."""
        # Store approval decision
        await cache_manager.set(
            f"approval:{notification_id}",
            json.dumps({"approved": approved, "timestamp": datetime.utcnow().isoformat()}),
            ttl=3600
        )
        
        logger.info(f"Approval processed: {notification_id} = {approved}")
    
    def _generate_notification_id(self) -> str:
        """Generate unique notification ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        random_suffix = secrets.token_hex(4)
        return f"dev_{timestamp}_{random_suffix}"
    
    async def _cleanup_expired_notification(self, notification_id: str, timeout_minutes: int):
        """Clean up expired notification after timeout."""
        await asyncio.sleep(timeout_minutes * 60)
        
        if notification_id in self.pending_notifications:
            del self.pending_notifications[notification_id]
            logger.info(f"Cleaned up expired notification: {notification_id}")


# Global service instance
mobile_dev_service = MobileDevNotificationService()


# Development notification helpers
async def send_build_status(status: str, details: str = ""):
    """Send build status notification."""
    priority = "high" if "failed" in status.lower() else "medium"
    return await mobile_dev_service.send_notification(
        NotificationType.BUILD_STATUS,
        f"Build {status}",
        details or f"Development build {status}",
        priority=priority
    )


async def send_deployment_update(stage: str, status: str, details: str = ""):
    """Send deployment update notification."""
    return await mobile_dev_service.send_notification(
        NotificationType.DEPLOYMENT_UPDATE,
        f"Deployment {stage}: {status}",
        details,
        priority="high"
    )


async def request_approval(action: str, details: str, timeout_minutes: int = 30):
    """Request approval for an action via SMS."""
    return await mobile_dev_service.send_notification(
        NotificationType.APPROVAL_REQUEST,
        f"Approval Required: {action}",
        f"{details}\n\nReply 'approve' or 'reject'",
        priority="high",
        requires_response=True,
        response_timeout=timeout_minutes
    )


async def send_security_alert(alert_type: str, details: str):
    """Send security alert notification."""
    return await mobile_dev_service.send_notification(
        NotificationType.SECURITY_ALERT,
        f"Security Alert: {alert_type}",
        details,
        priority="critical"
    )


async def send_critical_error(error_type: str, details: str):
    """Send critical error notification."""
    return await mobile_dev_service.send_notification(
        NotificationType.ERROR_CRITICAL,
        f"Critical Error: {error_type}",
        details,
        priority="critical"
    )


async def notify_task_complete(task_name: str, duration: str = ""):
    """Notify when a development task completes."""
    message = f"Task completed: {task_name}"
    if duration:
        message += f" (took {duration})"
    
    return await mobile_dev_service.send_notification(
        NotificationType.TASK_COMPLETE,
        "Task Complete",
        message,
        priority="medium"
    )