"""
Email service for sending password reset and other transactional emails.
"""

from app.core.logger import get_logger

logger = get_logger(__name__)


async def send_password_reset_email(email: str, name: str, reset_url: str) -> bool:
    """
    Send password reset email to user.
    
    Args:
        email: User's email address
        name: User's name
        reset_url: Password reset URL
        
    Returns:
        True if email sent successfully
    """
    # TODO: Implement actual email sending (SendGrid, SES, etc.)
    logger.info(f"Password reset email would be sent to {email} with URL: {reset_url}")
    
    # In production, this would use an email service like:
    # - SendGrid
    # - AWS SES
    # - Mailgun
    # - etc.
    
    email_content = f"""
    Hello {name},
    
    We received a request to reset your password for your AI Road Trip Storyteller account.
    
    Click the link below to reset your password:
    {reset_url}
    
    This link will expire in 1 hour for security reasons.
    
    If you didn't request this password reset, please ignore this email.
    
    Best regards,
    The AI Road Trip Storyteller Team
    """
    
    # For now, just log it
    logger.info(f"Email content: {email_content}")
    
    return True