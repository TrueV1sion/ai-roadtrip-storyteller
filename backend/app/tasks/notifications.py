"""
Asynchronous notification tasks for email and push notifications.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from backend.app.core.celery_app import celery_app
from backend.app.core.logger import get_logger
from backend.app.core.config import settings

logger = get_logger(__name__)


@celery_app.task(
    name='notifications.send_booking_confirmation_email',
    max_retries=3,
    default_retry_delay=60
)
def send_booking_confirmation_email(booking_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send booking confirmation email to user."""
    try:
        logger.info(f"Sending booking confirmation email for booking {booking_data['booking_id']}")
        
        # In production, this would use a service like SendGrid or AWS SES
        # For now, we'll create the email structure
        email_content = {
            'to': booking_data.get('user_email'),
            'subject': f"Booking Confirmed - {booking_data['venue_name']}",
            'template': 'booking_confirmation',
            'data': {
                'confirmation_number': booking_data['confirmation_number'],
                'venue_name': booking_data['venue_name'],
                'booking_date': booking_data['booking_date'],
                'party_size': booking_data['party_size'],
                'special_requests': booking_data.get('special_requests')
            }
        }
        
        # Log email send (in production, actually send it)
        logger.info(f"Email sent to {email_content['to']}")
        
        return {
            'success': True,
            'email_id': f"email_{booking_data['booking_id']}",
            'sent_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending booking confirmation email: {str(e)}")
        raise


@celery_app.task(
    name='notifications.send_booking_cancellation_email',
    max_retries=3
)
def send_booking_cancellation_email(cancellation_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send booking cancellation notification email."""
    try:
        logger.info(f"Sending cancellation email for booking {cancellation_data['booking_id']}")
        
        email_content = {
            'to': cancellation_data.get('user_email'),
            'subject': f"Booking Cancelled - {cancellation_data['venue_name']}",
            'template': 'booking_cancellation',
            'data': cancellation_data
        }
        
        logger.info(f"Cancellation email sent to {email_content['to']}")
        
        return {
            'success': True,
            'email_id': f"cancel_email_{cancellation_data['booking_id']}",
            'sent_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending cancellation email: {str(e)}")
        raise


@celery_app.task(
    name='notifications.send_journey_reminder',
    max_retries=2
)
def send_journey_reminder(journey_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send journey reminder notification before trip."""
    try:
        logger.info(f"Sending journey reminder for user {journey_data['user_id']}")
        
        notification = {
            'user_id': journey_data['user_id'],
            'type': 'journey_reminder',
            'title': f"Ready for your trip to {journey_data['destination']}?",
            'body': f"Your journey starts tomorrow! We've prepared amazing stories and recommendations for your trip.",
            'data': {
                'journey_id': journey_data['journey_id'],
                'destination': journey_data['destination'],
                'departure_time': journey_data['departure_time']
            }
        }
        
        # Send push notification
        # In production, this would use FCM or APNS
        logger.info(f"Journey reminder sent: {notification}")
        
        return {
            'success': True,
            'notification_id': f"reminder_{journey_data['journey_id']}",
            'sent_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending journey reminder: {str(e)}")
        raise


@celery_app.task(
    name='notifications.send_milestone_notification',
    max_retries=2
)
def send_milestone_notification(milestone_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send milestone achievement notification during journey."""
    try:
        logger.info(f"Sending milestone notification: {milestone_data['milestone_type']}")
        
        notification = {
            'user_id': milestone_data['user_id'],
            'type': 'milestone',
            'title': milestone_data['title'],
            'body': milestone_data['message'],
            'priority': 'high' if milestone_data.get('is_major') else 'normal',
            'data': milestone_data
        }
        
        # Send in-app notification
        logger.info(f"Milestone notification sent: {notification}")
        
        return {
            'success': True,
            'notification_id': f"milestone_{milestone_data['journey_id']}_{milestone_data['milestone_id']}",
            'sent_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending milestone notification: {str(e)}")
        raise


@celery_app.task(
    name='notifications.send_commission_report',
    max_retries=2
)
def send_commission_report(report_data: Dict[str, Any]) -> Dict[str, Any]:
    """Send commission earnings report to admin."""
    try:
        logger.info(f"Sending commission report for period: {report_data['period']}")
        
        email_content = {
            'to': settings.ADMIN_EMAIL,
            'subject': f"Commission Report - {report_data['period']}",
            'template': 'commission_report',
            'data': {
                'total_bookings': report_data['total_bookings'],
                'total_revenue': report_data['total_revenue'],
                'total_commission': report_data['total_commission'],
                'top_partners': report_data['top_partners'],
                'period': report_data['period']
            }
        }
        
        logger.info(f"Commission report sent to admin")
        
        return {
            'success': True,
            'report_id': f"commission_report_{report_data['period']}",
            'sent_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error sending commission report: {str(e)}")
        raise


@celery_app.task(
    name='notifications.process_notification_batch',
    max_retries=3
)
def process_notification_batch(notifications: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Process a batch of notifications efficiently."""
    try:
        logger.info(f"Processing batch of {len(notifications)} notifications")
        
        successful = 0
        failed = 0
        
        # Group notifications by type for efficient processing
        grouped = {}
        for notif in notifications:
            notif_type = notif.get('type', 'general')
            if notif_type not in grouped:
                grouped[notif_type] = []
            grouped[notif_type].append(notif)
        
        # Process each group
        for notif_type, notif_list in grouped.items():
            try:
                if notif_type == 'email':
                    # Batch email sending
                    for notif in notif_list:
                        send_booking_confirmation_email.apply_async(
                            args=[notif['data']],
                            countdown=successful * 2  # Stagger sends
                        )
                        successful += 1
                        
                elif notif_type == 'push':
                    # Batch push notifications
                    # In production, use FCM/APNS batch APIs
                    successful += len(notif_list)
                    
                else:
                    # Handle other notification types
                    successful += len(notif_list)
                    
            except Exception as e:
                logger.error(f"Error processing {notif_type} notifications: {str(e)}")
                failed += len(notif_list)
        
        logger.info(f"Batch processing complete: {successful} successful, {failed} failed")
        
        return {
            'success': True,
            'total': len(notifications),
            'successful': successful,
            'failed': failed,
            'processed_at': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error processing notification batch: {str(e)}")
        raise