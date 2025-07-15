"""Photo storage service for parking photos using Google Cloud Storage."""

import os
import uuid
import mimetypes
from datetime import datetime, timedelta
from typing import Optional, BinaryIO, Dict
from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError

from backend.app.core.config import settings
from backend.app.core.logger import logger


class PhotoStorageService:
    """Service for handling photo uploads and storage in Google Cloud Storage."""
    
    def __init__(self):
        """Initialize the photo storage service."""
        self.bucket_name = settings.GCS_BUCKET_NAME
        self.storage_client = None
        self.bucket = None
        
        if settings.GOOGLE_CLOUD_PROJECT and settings.GCS_BUCKET_NAME:
            try:
                self.storage_client = storage.Client(project=settings.GOOGLE_CLOUD_PROJECT)
                self.bucket = self.storage_client.bucket(self.bucket_name)
            except Exception as e:
                logger.error(f"Failed to initialize Google Cloud Storage: {str(e)}")
    
    def upload_parking_photo(
        self,
        file: BinaryIO,
        user_id: str,
        booking_reference: str,
        file_extension: str = "jpg"
    ) -> Optional[str]:
        """
        Upload a parking photo to Google Cloud Storage.
        
        Args:
            file: The file object to upload
            user_id: The ID of the user uploading the photo
            booking_reference: The booking reference for the parking reservation
            file_extension: The file extension (default: jpg)
            
        Returns:
            The public URL of the uploaded photo, or None if upload failed
        """
        if not self.bucket:
            logger.error("Google Cloud Storage bucket not initialized")
            return None
        
        try:
            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"parking/{user_id}/{booking_reference}_{timestamp}.{file_extension}"
            
            # Create blob and upload
            blob = self.bucket.blob(filename)
            
            # Set content type based on file extension
            content_type = mimetypes.guess_type(f"file.{file_extension}")[0] or "image/jpeg"
            blob.upload_from_file(file, content_type=content_type)
            
            # Make the blob publicly accessible
            blob.make_public()
            
            # Return the public URL
            return blob.public_url
            
        except GoogleCloudError as e:
            logger.error(f"Google Cloud Storage error uploading photo: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading photo: {str(e)}")
            return None
    
    def generate_signed_url(
        self,
        blob_name: str,
        expiration_hours: int = 24
    ) -> Optional[str]:
        """
        Generate a signed URL for temporary access to a photo.
        
        Args:
            blob_name: The name of the blob in the bucket
            expiration_hours: Hours until the URL expires (default: 24)
            
        Returns:
            A signed URL for accessing the photo, or None if generation failed
        """
        if not self.bucket:
            logger.error("Google Cloud Storage bucket not initialized")
            return None
        
        try:
            blob = self.bucket.blob(blob_name)
            
            # Generate signed URL
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(hours=expiration_hours),
                method="GET"
            )
            
            return url
            
        except Exception as e:
            logger.error(f"Error generating signed URL: {str(e)}")
            return None
    
    def delete_photo(self, blob_name: str) -> bool:
        """
        Delete a photo from Google Cloud Storage.
        
        Args:
            blob_name: The name of the blob to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.bucket:
            logger.error("Google Cloud Storage bucket not initialized")
            return False
        
        try:
            blob = self.bucket.blob(blob_name)
            blob.delete()
            return True
            
        except Exception as e:
            logger.error(f"Error deleting photo: {str(e)}")
            return False
    
    def get_photo_metadata(self, blob_name: str) -> Optional[Dict]:
        """
        Get metadata for a stored photo.
        
        Args:
            blob_name: The name of the blob
            
        Returns:
            Dictionary containing photo metadata, or None if not found
        """
        if not self.bucket:
            logger.error("Google Cloud Storage bucket not initialized")
            return None
        
        try:
            blob = self.bucket.blob(blob_name)
            if blob.exists():
                return {
                    "name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_type,
                    "created": blob.time_created,
                    "updated": blob.updated,
                    "public_url": blob.public_url if blob.public_url else None
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting photo metadata: {str(e)}")
            return None


# Singleton instance
photo_storage_service = PhotoStorageService()