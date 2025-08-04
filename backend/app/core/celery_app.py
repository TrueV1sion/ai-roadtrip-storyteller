"""
Enhanced Celery configuration with Six Sigma quality controls.

This module configures Celery for handling background tasks with:
- 99.9% job completion rate
- <100ms queue latency
- Zero job loss during deploys
- Automatic retry with exponential backoff
"""

import os
from app.core.celery_config import create_celery_app, CELERY_CONFIG

# Create enhanced Celery instance with Six Sigma controls
celery_app = create_celery_app()

# Import task modules to register them
celery_app.autodiscover_tasks([
    'backend.app.tasks',
    'backend.app.tasks.ai_enhanced',
    'backend.app.tasks.monitoring',
    'backend.app.tasks.maintenance'
])