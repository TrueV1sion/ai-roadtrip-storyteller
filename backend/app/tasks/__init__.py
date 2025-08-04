"""
Asynchronous tasks for the AI Road Trip Storyteller.

This package contains all Celery tasks organized by domain:
- booking: Reservation processing and confirmations
- ai: Story generation and personality management
- analytics: Revenue and usage analytics
- notifications: Email and push notifications
- maintenance: System maintenance tasks
"""

from app.core.celery_app import celery_app

__all__ = ['celery_app']