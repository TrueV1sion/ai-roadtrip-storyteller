"""
Notification Service - Handles user notifications via multiple channels
"""

import logging
from typing import Dict, List, Any, Optional
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..core.config import settings

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationService:
    """Service for sending notifications to users."""
    
    def __init__(self):
        self.email_enabled = bool(settings.SMTP_HOST)
        self.sms_enabled = False  # Would need SMS provider setup
        self.push_enabled = False  # Would need push notification setup
    
    async def send_notification(
        self,
        user_id: str,
        notification_type: str,
        message: str,
        title: str = None,
        user_email: str = None,
        user_phone: str = None
    ) -> bool:
        """Send a notification to a user."""
        
        try:
            if notification_type == "email" and self.email_enabled and user_email:
                return await self._send_email(user_email, title or "Road Trip Update", message)
            
            elif notification_type == "sms" and self.sms_enabled and user_phone:
                return await self._send_sms(user_phone, message)
            
            elif notification_type == "push" and self.push_enabled:
                return await self._send_push_notification(user_id, title or "Update", message)
            
            else:
                # Fallback to in-app notification (just logging for now)
                logger.info(f"In-app notification for user {user_id}: {message}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    async def _send_email(self, to_email: str, subject: str, message: str) -> bool:
        """Send email notification."""
        
        try:
            if not settings.SMTP_HOST:
                logger.warning("SMTP not configured, skipping email notification")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_FROM_EMAIL
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(message, 'plain'))
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    async def _send_sms(self, phone_number: str, message: str) -> bool:
        """Send SMS notification."""
        
        # TODO: Implement SMS provider integration (Twilio, AWS SNS, etc.)
        logger.info(f"SMS notification to {phone_number}: {message}")
        return True
    
    async def _send_push_notification(self, user_id: str, title: str, message: str) -> bool:
        """Send push notification."""
        
        # TODO: Implement push notification service (Firebase, Apple Push, etc.)
        logger.info(f"Push notification to user {user_id}: {title} - {message}")
        return True
    
    async def send_reservation_confirmation(
        self,
        user_email: str,
        reservation_details: Dict[str, Any]
    ) -> bool:
        """Send reservation confirmation email."""
        
        subject = "Reservation Confirmed - AI Road Trip Storyteller"
        message = f"""
        Your reservation has been confirmed!
        
        Details:
        - Restaurant: {reservation_details.get('restaurant_name', 'N/A')}
        - Date: {reservation_details.get('reservation_time', 'N/A')}
        - Party Size: {reservation_details.get('party_size', 'N/A')}
        - Confirmation Number: {reservation_details.get('confirmation_number', 'N/A')}
        
        Thank you for using AI Road Trip Storyteller!
        """
        
        return await self._send_email(user_email, subject, message)
    
    async def send_journey_update(
        self,
        user_email: str,
        update_message: str
    ) -> bool:
        """Send journey update notification."""
        
        subject = "Journey Update - AI Road Trip Storyteller"
        return await self._send_email(user_email, subject, update_message)
