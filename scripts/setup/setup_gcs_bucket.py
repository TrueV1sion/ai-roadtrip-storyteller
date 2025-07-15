"""Setup script for Google Cloud Storage bucket configuration."""

import os
import sys
from google.cloud import storage
from google.cloud.exceptions import Conflict, NotFound


def create_gcs_bucket(project_id: str, bucket_name: str, location: str = "us-central1"):
    """Create a Google Cloud Storage bucket for parking photos."""
    
    print(f"🪣 Setting up Google Cloud Storage bucket: {bucket_name}")
    
    try:
        # Initialize storage client
        storage_client = storage.Client(project=project_id)
        
        # Check if bucket already exists
        try:
            bucket = storage_client.get_bucket(bucket_name)
            print(f"✅ Bucket '{bucket_name}' already exists!")
            return bucket
        except NotFound:
            pass
        
        # Create new bucket
        bucket = storage_client.create_bucket(
            bucket_name,
            location=location
        )
        
        print(f"✅ Created bucket '{bucket_name}' in location '{location}'")
        
        # Set bucket permissions for public read access on photos
        # Note: In production, consider using signed URLs instead
        bucket.iam_configuration.uniform_bucket_level_access_enabled = True
        bucket.patch()
        
        # Create folder structure
        folders = ["parking/", "parking/archive/"]
        for folder in folders:
            blob = bucket.blob(folder)
            blob.upload_from_string("")
            print(f"📁 Created folder: {folder}")
        
        # Set lifecycle rules to archive old photos
        bucket.add_lifecycle_delete_rule(age=365)  # Delete after 1 year
        bucket.patch()
        print("♻️ Set lifecycle rule: Delete photos after 365 days")
        
        return bucket
        
    except Conflict:
        print(f"❌ Bucket name '{bucket_name}' is already taken globally.")
        print("   Please choose a different bucket name.")
        return None
    except Exception as e:
        print(f"❌ Error creating bucket: {str(e)}")
        return None


def setup_bucket_cors(bucket):
    """Configure CORS for the bucket to allow uploads from web/mobile apps."""
    
    cors_configuration = [{
        "origin": ["*"],  # In production, specify your app domains
        "method": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "responseHeader": ["Content-Type", "x-goog-resumable"],
        "maxAgeSeconds": 3600
    }]
    
    bucket.cors = cors_configuration
    bucket.patch()
    
    print("🌐 Configured CORS for web/mobile uploads")


def main():
    """Main setup function."""
    
    print("\n🚀 Google Cloud Storage Setup for Parking Photos\n")
    print("=" * 50)
    
    # Get configuration from environment or prompt
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        project_id = input("Enter your Google Cloud Project ID: ").strip()
    
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        bucket_name = input("Enter bucket name (e.g., 'roadtrip-parking-photos'): ").strip()
    
    # Validate inputs
    if not project_id or not bucket_name:
        print("❌ Project ID and bucket name are required!")
        sys.exit(1)
    
    # Create bucket
    bucket = create_gcs_bucket(project_id, bucket_name)
    
    if bucket:
        # Configure CORS
        setup_bucket_cors(bucket)
        
        print("\n✅ Setup Complete!")
        print(f"\n📝 Add these to your .env file:")
        print(f"   GOOGLE_CLOUD_PROJECT={project_id}")
        print(f"   GCS_BUCKET_NAME={bucket_name}")
        
        print("\n🔑 Authentication:")
        print("   1. Create a service account in Google Cloud Console")
        print("   2. Download the JSON key file")
        print("   3. Set GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json")
        print("   OR use Application Default Credentials (ADC)")
        
        print("\n📱 Mobile App Integration:")
        print("   - Use the /api/airport-parking/reservations/{ref}/upload-photo endpoint")
        print("   - Supports JPEG, PNG, HEIC formats")
        print("   - Photos are automatically organized by user and booking")
        
        print("\n🎉 Ready to store parking photos!")
    else:
        print("\n❌ Setup failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()