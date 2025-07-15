#!/usr/bin/env python3
"""
Generate a new encryption master key for Google Secret Manager.
This should be run once during initial setup.
"""
import sys
import argparse
from cryptography.fernet import Fernet
from google.cloud import secretmanager


def create_encryption_key_secret(project_id: str, dry_run: bool = False):
    """Create encryption master key in Google Secret Manager."""
    # Generate a new Fernet key
    key = Fernet.generate_key()
    key_str = key.decode()
    
    print(f"Generated new encryption key: {key_str[:10]}...")
    
    if dry_run:
        print("[DRY RUN] Would create secret: roadtrip-encryption-master-key")
        return key_str
    
    # Create secret in Google Secret Manager
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{project_id}"
    secret_id = "roadtrip-encryption-master-key"
    
    try:
        # Check if secret already exists
        secret_name = f"{parent}/secrets/{secret_id}"
        client.get_secret(request={"name": secret_name})
        print(f"Secret {secret_id} already exists. Adding new version...")
        
        # Add new version
        response = client.add_secret_version(
            request={
                "parent": secret_name,
                "payload": {"data": key_str.encode("UTF-8")},
            }
        )
        print(f"Added new version: {response.name}")
        
    except Exception:
        # Create new secret
        print(f"Creating new secret: {secret_id}")
        
        secret = client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {
                    "replication": {"automatic": {}},
                    "labels": {
                        "app": "roadtrip",
                        "purpose": "encryption",
                        "managed-by": "script"
                    }
                },
            }
        )
        
        # Add the secret version
        version = client.add_secret_version(
            request={
                "parent": secret.name,
                "payload": {"data": key_str.encode("UTF-8")},
            }
        )
        print(f"Created secret with version: {version.name}")
    
    print(f"\nIMPORTANT: Store this key securely as backup: {key_str}")
    return key_str


def main():
    parser = argparse.ArgumentParser(description='Generate encryption master key')
    parser.add_argument('--project-id', required=True, help='GCP Project ID')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    args = parser.parse_args()
    
    try:
        create_encryption_key_secret(args.project_id, args.dry_run)
        print("\nEncryption key setup completed successfully")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())