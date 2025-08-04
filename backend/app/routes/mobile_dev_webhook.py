"""
Mobile Development Webhook Routes
Handles incoming SMS responses and webhook integrations for mobile development control.
"""

from fastapi import APIRouter, Request, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse
from typing import Dict, Any, Optional
import hmac
import hashlib
import json
from datetime import datetime

from app.core.logger import logger
from app.core.config import settings
from app.services.mobile_dev_notifications import mobile_dev_service
from app.core.auth import get_current_admin_user
from app.models.user import User


router = APIRouter(prefix="/api/mobile-dev", tags=["Mobile Development"])


@router.post("/webhook/twilio-sms")
async def handle_twilio_sms(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming SMS responses via Twilio webhook."""
    try:
        # Get form data from Twilio
        form_data = await request.form()
        
        # Extract Twilio SMS data
        from_number = form_data.get("From", "")
        message_body = form_data.get("Body", "")
        sms_sid = form_data.get("SmsSid", "")
        
        logger.info(f"Received SMS from {from_number[-4:]} (SID: {sms_sid})")
        
        # Verify Twilio signature if configured
        twilio_auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        if twilio_auth_token:
            signature = request.headers.get("X-Twilio-Signature", "")
            if not _verify_twilio_signature(str(request.url), dict(form_data), signature, twilio_auth_token):
                logger.warning(f"Invalid Twilio signature from {from_number[-4:]}")
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Process SMS response in background
        background_tasks.add_task(
            _process_sms_response,
            from_number,
            message_body,
            {"sms_sid": sms_sid, "provider": "twilio"}
        )
        
        # Return TwiML response
        return PlainTextResponse(
            '<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
            media_type="application/xml"
        )
        
    except Exception as e:
        logger.error(f"Error handling Twilio SMS webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook/aws-sns")
async def handle_aws_sns_response(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming SMS responses via AWS SNS."""
    try:
        body = await request.json()
        
        # Handle SNS message types
        message_type = request.headers.get("x-amz-sns-message-type")
        
        if message_type == "SubscriptionConfirmation":
            # Auto-confirm SNS subscription
            subscribe_url = body.get("SubscribeURL")
            if subscribe_url:
                # In production, make HTTP request to subscribe_url
                logger.info(f"SNS subscription confirmation: {subscribe_url}")
            return {"status": "confirmed"}
        
        elif message_type == "Notification":
            # Parse SMS response from SNS
            sns_message = json.loads(body.get("Message", "{}"))
            
            from_number = sns_message.get("originationNumber", "")
            message_body = sns_message.get("messageBody", "")
            
            background_tasks.add_task(
                _process_sms_response,
                from_number,
                message_body,
                {"provider": "aws_sns", "message_id": sns_message.get("messageId")}
            )
            
            return {"status": "processed"}
        
        return {"status": "ignored"}
        
    except Exception as e:
        logger.error(f"Error handling AWS SNS webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook/generic-sms")
async def handle_generic_sms(request: Request, background_tasks: BackgroundTasks):
    """Handle incoming SMS from generic providers."""
    try:
        body = await request.json()
        
        from_number = body.get("from") or body.get("phone") or body.get("number")
        message_body = body.get("message") or body.get("body") or body.get("text")
        
        if not from_number or not message_body:
            raise HTTPException(status_code=400, detail="Missing required fields")
        
        background_tasks.add_task(
            _process_sms_response,
            from_number,
            message_body,
            {"provider": "generic", "webhook_body": body}
        )
        
        return {"status": "processed"}
        
    except Exception as e:
        logger.error(f"Error handling generic SMS webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/test-notification")
async def send_test_notification(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_admin_user)
):
    """Send a test notification (admin only)."""
    try:
        notification_type = request.get("type", "system_status")
        title = request.get("title", "Test Notification")
        message = request.get("message", "This is a test notification from the development system.")
        priority = request.get("priority", "medium")
        phone_number = request.get("phone_number")
        
        notification_id = await mobile_dev_service.send_notification(
            notification_type,
            title,
            message,
            priority=priority,
            phone_number=phone_number
        )
        
        return {
            "status": "sent",
            "notification_id": notification_id,
            "message": "Test notification sent successfully"
        }
        
    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate-sms-response")
async def simulate_sms_response(
    request: Dict[str, Any],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user)
):
    """Simulate an SMS response for testing (admin only)."""
    try:
        from_number = request.get("from_number")
        message = request.get("message")
        
        if not from_number or not message:
            raise HTTPException(status_code=400, detail="Missing from_number or message")
        
        background_tasks.add_task(
            _process_sms_response,
            from_number,
            message,
            {"provider": "simulation", "admin_user": current_user.id}
        )
        
        return {
            "status": "processed",
            "message": "SMS response simulated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error simulating SMS response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_mobile_dev_status(current_user: User = Depends(get_current_admin_user)):
    """Get mobile development system status (admin only)."""
    try:
        status = {
            "service_active": True,
            "authorized_numbers": len(mobile_dev_service.authorized_numbers),
            "pending_notifications": len(mobile_dev_service.pending_notifications),
            "response_handlers": list(mobile_dev_service.response_handlers.keys()),
            "last_updated": datetime.utcnow().isoformat()
        }
        
        # Get pending notifications (without sensitive data)
        pending = []
        for notification_id, notification in mobile_dev_service.pending_notifications.items():
            pending.append({
                "id": notification_id,
                "type": notification.type,
                "title": notification.title,
                "priority": notification.priority,
                "timestamp": notification.timestamp.isoformat(),
                "requires_response": notification.requires_response
            })
        
        status["pending_details"] = pending
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting mobile dev status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/configure")
async def configure_mobile_dev(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_admin_user)
):
    """Configure mobile development settings (admin only)."""
    try:
        # Update authorized numbers
        if "authorized_numbers" in request:
            mobile_dev_service.authorized_numbers = request["authorized_numbers"]
            logger.info(f"Updated authorized numbers: {len(mobile_dev_service.authorized_numbers)} numbers")
        
        # Update other settings as needed
        
        return {
            "status": "configured",
            "message": "Mobile development settings updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error configuring mobile dev: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_sms_response(from_number: str, message_body: str, context: Dict[str, Any]):
    """Process SMS response in background task."""
    try:
        logger.info(f"Processing SMS response from {from_number[-4:]}: {message_body[:50]}...")
        
        # Handle the SMS response
        response = await mobile_dev_service.handle_sms_response(from_number, message_body)
        
        # Log the interaction
        logger.info(f"SMS response processed. Reply: {response[:100]}...")
        
        # Send response back via SMS if needed
        if response and len(response) > 0:
            # In production, send response SMS back
            logger.info(f"Would send SMS response to {from_number[-4:]}: {response[:50]}...")
            
            # For now, just log - in production implement actual SMS sending
            
    except Exception as e:
        logger.error(f"Error processing SMS response from {from_number[-4:]}: {e}")


def _verify_twilio_signature(url: str, params: Dict[str, str], signature: str, auth_token: str) -> bool:
    """Verify Twilio webhook signature."""
    try:
        # Create the signature string
        signature_string = url
        for key in sorted(params.keys()):
            signature_string += f"{key}{params[key]}"
        
        # Generate HMAC-SHA1 signature
        expected_signature = hmac.new(
            auth_token.encode('utf-8'),
            signature_string.encode('utf-8'),
            hashlib.sha1
        ).digest()
        
        # Base64 encode and compare
        import base64
        expected_signature_b64 = base64.b64encode(expected_signature).decode()
        
        return hmac.compare_digest(expected_signature_b64, signature)
        
    except Exception as e:
        logger.error(f"Error verifying Twilio signature: {e}")
        return False