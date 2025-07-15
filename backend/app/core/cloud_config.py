"""
Cloud Run specific configuration utilities
"""
import os
import logging
from typing import Optional
from google.cloud import secretmanager
from google.api_core import exceptions

logger = logging.getLogger(__name__)


def is_cloud_run() -> bool:
    """Check if running on Cloud Run"""
    return bool(os.environ.get('K_SERVICE'))


def get_project_id() -> Optional[str]:
    """Get the Google Cloud project ID"""
    # Try environment variables in order of preference
    return (
        os.environ.get('GOOGLE_CLOUD_PROJECT') or
        os.environ.get('GCP_PROJECT') or
        os.environ.get('GCLOUD_PROJECT')
    )


def get_secret(secret_id: str, default: Optional[str] = None) -> Optional[str]:
    """
    Fetch secret from Google Secret Manager
    
    Args:
        secret_id: The secret identifier
        default: Default value if secret not found
        
    Returns:
        Secret value or default
    """
    if not is_cloud_run():
        # Not on Cloud Run, return default
        return default
        
    project_id = get_project_id()
    if not project_id:
        logger.warning("No project ID found, cannot fetch secrets")
        return default
    
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        secret_value = response.payload.data.decode("UTF-8")
        logger.info(f"Successfully fetched secret: {secret_id}")
        return secret_value
    except exceptions.NotFound:
        logger.warning(f"Secret not found: {secret_id}")
        return default
    except exceptions.PermissionDenied:
        logger.error(f"Permission denied accessing secret: {secret_id}")
        return default
    except Exception as e:
        logger.error(f"Error fetching secret {secret_id}: {str(e)}")
        return default


def get_cloud_sql_connection_string(
    instance_connection_name: str,
    database_name: str,
    username: str,
    password: str
) -> str:
    """
    Build Cloud SQL connection string for Cloud Run
    
    Args:
        instance_connection_name: Format: project:region:instance
        database_name: Name of the database
        username: Database username
        password: Database password
        
    Returns:
        PostgreSQL connection string
    """
    # For Cloud SQL proxy (used by Cloud Run)
    return (
        f"postgresql://{username}:{password}@/{database_name}"
        f"?host=/cloudsql/{instance_connection_name}"
    )


def configure_cloud_run_logging():
    """Configure logging for Cloud Run"""
    # Cloud Run captures stdout/stderr automatically
    # Configure root logger to output to stdout
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Reduce noise from some libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    
    logger.info("Cloud Run logging configured")


# Cloud Run specific environment variables
CLOUD_RUN_SERVICE = os.environ.get('K_SERVICE', 'unknown')
CLOUD_RUN_REVISION = os.environ.get('K_REVISION', 'unknown')
CLOUD_RUN_CONFIGURATION = os.environ.get('K_CONFIGURATION', 'unknown')
CLOUD_RUN_SERVICE_ACCOUNT = os.environ.get('K_SERVICE_ACCOUNT', 'unknown')

# Export convenience functions
__all__ = [
    'is_cloud_run',
    'get_project_id',
    'get_secret',
    'get_cloud_sql_connection_string',
    'configure_cloud_run_logging',
    'CLOUD_RUN_SERVICE',
    'CLOUD_RUN_REVISION',
]