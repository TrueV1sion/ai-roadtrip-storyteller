"""
Google Cloud Authentication and Service Account Management
Handles service account authentication for Google Cloud APIs
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from google.auth import default
from google.auth.credentials import Credentials
from google.oauth2 import service_account
from google.cloud import secretmanager
import google.auth.exceptions

logger = logging.getLogger(__name__)


class GoogleCloudAuth:
    """Manages Google Cloud authentication for the application."""
    
    def __init__(self):
        self.credentials: Optional[Credentials] = None
        self.project_id: Optional[str] = None
        self.service_account_info: Optional[Dict[str, Any]] = None
        
    def initialize(self) -> bool:
        """
        Initialize Google Cloud authentication.
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        try:
            # Try different authentication methods in order of preference
            success = (
                self._try_service_account_file() or
                self._try_service_account_json() or
                self._try_application_default_credentials() or
                self._try_environment_variables()
            )
            
            if success:
                logger.info(f"Google Cloud authentication successful for project: {self.project_id}")
                return True
            else:
                logger.error("All Google Cloud authentication methods failed")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing Google Cloud authentication: {e}")
            return False
    
    def _try_service_account_file(self) -> bool:
        """Try to authenticate using a service account JSON file."""
        try:
            # Check for service account file in environment variable
            sa_file_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if not sa_file_path:
                # Check for common file locations
                possible_paths = [
                    'service-account.json',
                    'google-service-account.json',
                    'gcp-service-account.json',
                    'credentials/service-account.json',
                    os.path.expanduser('~/.config/gcloud/application_default_credentials.json')
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        sa_file_path = path
                        break
            
            if sa_file_path and os.path.exists(sa_file_path):
                logger.info(f"Attempting to load service account from: {sa_file_path}")
                
                with open(sa_file_path, 'r') as f:
                    service_account_info = json.load(f)
                
                self.credentials = service_account.Credentials.from_service_account_info(
                    service_account_info
                )
                self.project_id = service_account_info.get('project_id')
                self.service_account_info = service_account_info
                
                logger.info("Successfully loaded service account credentials from file")
                return True
                
        except Exception as e:
            logger.debug(f"Service account file authentication failed: {e}")
        
        return False
    
    def _try_service_account_json(self) -> bool:
        """Try to authenticate using service account JSON from environment variable."""
        try:
            # Check for service account JSON in environment variable
            sa_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
            if sa_json:
                logger.info("Attempting to load service account from environment variable")
                
                service_account_info = json.loads(sa_json)
                self.credentials = service_account.Credentials.from_service_account_info(
                    service_account_info
                )
                self.project_id = service_account_info.get('project_id')
                self.service_account_info = service_account_info
                
                logger.info("Successfully loaded service account credentials from environment")
                return True
                
        except Exception as e:
            logger.debug(f"Service account JSON environment authentication failed: {e}")
        
        return False
    
    def _try_application_default_credentials(self) -> bool:
        """Try to authenticate using Application Default Credentials."""
        try:
            logger.info("Attempting to use Application Default Credentials")
            
            # Try to get default credentials
            credentials, project_id = default()
            
            if credentials and project_id:
                self.credentials = credentials
                self.project_id = project_id
                logger.info("Successfully loaded Application Default Credentials")
                return True
                
        except google.auth.exceptions.DefaultCredentialsError as e:
            logger.debug(f"Application Default Credentials not available: {e}")
        except Exception as e:
            logger.debug(f"Application Default Credentials authentication failed: {e}")
        
        return False
    
    def _try_environment_variables(self) -> bool:
        """Try to get project ID from environment variables as fallback."""
        try:
            # If we have project ID but no credentials, we might be in a mock/dev mode
            project_id = os.getenv('GOOGLE_AI_PROJECT_ID') or os.getenv('GOOGLE_CLOUD_PROJECT')
            
            if project_id:
                self.project_id = project_id
                logger.warning(f"Using project ID from environment without authentication: {project_id}")
                logger.warning("This will only work with mock mode or if running on Google Cloud")
                return True
                
        except Exception as e:
            logger.debug(f"Environment variable fallback failed: {e}")
        
        return False
    
    def get_credentials(self) -> Optional[Credentials]:
        """Get the authenticated credentials."""
        if not self.credentials:
            self.initialize()
        return self.credentials
    
    def get_project_id(self) -> Optional[str]:
        """Get the project ID."""
        if not self.project_id:
            self.initialize()
        return self.project_id
    
    def is_authenticated(self) -> bool:
        """Check if authentication is successful."""
        return self.credentials is not None and self.project_id is not None
    
    def create_service_account_file(self, credentials_dict: Dict[str, Any], file_path: str = 'service-account.json') -> bool:
        """
        Create a service account file from credentials dictionary.
        
        Args:
            credentials_dict: Service account credentials as dictionary
            file_path: Path where to save the file
            
        Returns:
            bool: True if file created successfully
        """
        try:
            with open(file_path, 'w') as f:
                json.dump(credentials_dict, f, indent=2)
            
            # Set environment variable to point to the file
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = file_path
            
            logger.info(f"Service account file created at: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create service account file: {e}")
            return False
    
    def validate_permissions(self) -> Dict[str, bool]:
        """
        Validate that the service account has required permissions.
        
        Returns:
            Dict with permission check results
        """
        permissions = {
            'vertex_ai': False,
            'text_to_speech': False,
            'secret_manager': False,
            'storage': False
        }
        
        if not self.is_authenticated():
            logger.warning("Cannot validate permissions without authentication")
            return permissions
        
        try:
            # Test Vertex AI access
            try:
                import vertexai
                vertexai.init(project=self.project_id, credentials=self.credentials)
                permissions['vertex_ai'] = True
                logger.info("✅ Vertex AI access confirmed")
            except Exception as e:
                logger.warning(f"❌ Vertex AI access failed: {e}")
            
            # Test Text-to-Speech access
            try:
                from google.cloud import texttospeech
                client = texttospeech.TextToSpeechClient(credentials=self.credentials)
                # Try to list voices as a simple permission test
                client.list_voices()
                permissions['text_to_speech'] = True
                logger.info("✅ Text-to-Speech access confirmed")
            except Exception as e:
                logger.warning(f"❌ Text-to-Speech access failed: {e}")
            
            # Test Secret Manager access
            try:
                client = secretmanager.SecretManagerServiceClient(credentials=self.credentials)
                # Try to list secrets as a simple permission test
                parent = f"projects/{self.project_id}"
                client.list_secrets(request={"parent": parent})
                permissions['secret_manager'] = True
                logger.info("✅ Secret Manager access confirmed")
            except Exception as e:
                logger.warning(f"❌ Secret Manager access failed: {e}")
            
            # Test Storage access
            try:
                from google.cloud import storage
                client = storage.Client(project=self.project_id, credentials=self.credentials)
                # Try to list buckets as a simple permission test
                list(client.list_buckets(max_results=1))
                permissions['storage'] = True
                logger.info("✅ Cloud Storage access confirmed")
            except Exception as e:
                logger.warning(f"❌ Cloud Storage access failed: {e}")
                
        except Exception as e:
            logger.error(f"Error validating permissions: {e}")
        
        return permissions


# Global instance
google_cloud_auth = GoogleCloudAuth()


def get_authenticated_credentials() -> Optional[Credentials]:
    """Get authenticated Google Cloud credentials."""
    return google_cloud_auth.get_credentials()


def get_project_id() -> Optional[str]:
    """Get the Google Cloud project ID."""
    return google_cloud_auth.get_project_id()


def is_authenticated() -> bool:
    """Check if Google Cloud authentication is successful."""
    return google_cloud_auth.is_authenticated()


def initialize_auth() -> bool:
    """Initialize Google Cloud authentication."""
    return google_cloud_auth.initialize()


def validate_permissions() -> Dict[str, bool]:
    """Validate service account permissions."""
    return google_cloud_auth.validate_permissions()