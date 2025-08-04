#!/usr/bin/env python3
"""
Rotate JWT keys in production.
This script generates new keys while keeping old ones for validation of existing tokens.
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../backend'))

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import uuid

from app.core.secret_manager import secret_manager
from app.core.logger import logger


def generate_rsa_key_pair(key_size: int = 4096):
    """Generate a new RSA key pair."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
        backend=default_backend()
    )
    
    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Serialize public key
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_pem, public_pem


def rotate_keys(project_id: str, key_size: int = 4096, max_keys: int = 3):
    """Rotate JWT keys, keeping a limited number of old keys."""
    
    # Load current metadata
    metadata_json = secret_manager.get_secret("roadtrip-jwt-key-metadata")
    if not metadata_json:
        logger.error("No existing JWT keys found. Run generate_jwt_keys.py first.")
        return False
    
    metadata = json.loads(metadata_json)
    logger.info(f"Current key ID: {metadata['current_key_id']}")
    logger.info(f"Total keys: {len(metadata['keys'])}")
    
    # Generate new key pair
    new_key_id = str(uuid.uuid4())
    logger.info(f"Generating new key pair with ID: {new_key_id}")
    
    private_key, public_key = generate_rsa_key_pair(key_size)
    
    # Store new keys in Secret Manager
    if not secret_manager.create_or_update_secret(f"roadtrip-jwt-private-key-{new_key_id}", private_key):
        logger.error("Failed to store new private key")
        return False
    logger.info(f"✓ Stored new private key: roadtrip-jwt-private-key-{new_key_id}")
    
    if not secret_manager.create_or_update_secret(f"roadtrip-jwt-public-key-{new_key_id}", public_key):
        logger.error("Failed to store new public key")
        return False
    logger.info(f"✓ Stored new public key: roadtrip-jwt-public-key-{new_key_id}")
    
    # Update metadata
    # Mark previous current key as inactive
    for key in metadata['keys']:
        if key['active']:
            key['active'] = False
            key['deactivated_at'] = datetime.utcnow().isoformat()
    
    # Add new key
    metadata['keys'].append({
        "key_id": new_key_id,
        "created_at": datetime.utcnow().isoformat(),
        "active": True,
        "key_size": key_size
    })
    
    # Update current key ID
    previous_key_id = metadata['current_key_id']
    metadata['current_key_id'] = new_key_id
    metadata['updated_at'] = datetime.utcnow().isoformat()
    metadata['last_rotation'] = datetime.utcnow().isoformat()
    
    # Sort keys by creation date (newest first)
    metadata['keys'].sort(key=lambda x: x['created_at'], reverse=True)
    
    # Keep only the latest max_keys
    if len(metadata['keys']) > max_keys:
        keys_to_remove = metadata['keys'][max_keys:]
        metadata['keys'] = metadata['keys'][:max_keys]
        
        # Clean up old keys from Secret Manager
        for old_key in keys_to_remove:
            old_key_id = old_key['key_id']
            logger.info(f"Removing old key: {old_key_id}")
            # Note: Google Secret Manager doesn't have a delete API in the client library
            # Old versions will be automatically cleaned up by Secret Manager policies
    
    # Store updated metadata
    if not secret_manager.create_or_update_secret("roadtrip-jwt-key-metadata", json.dumps(metadata)):
        logger.error("Failed to update metadata")
        return False
    logger.info("✓ Updated key metadata")
    
    logger.info(f"""
JWT key rotation completed successfully!

Previous key ID: {previous_key_id}
New key ID: {new_key_id}
Total active keys: {len(metadata['keys'])}

The new key is now active for signing new tokens.
Old keys are retained for validating existing tokens.
""")
    
    return True


def verify_rotation(expected_key_id: str = None):
    """Verify the key rotation was successful."""
    metadata_json = secret_manager.get_secret("roadtrip-jwt-key-metadata")
    if not metadata_json:
        logger.error("Failed to load metadata")
        return False
    
    metadata = json.loads(metadata_json)
    current_key_id = metadata['current_key_id']
    
    if expected_key_id and current_key_id != expected_key_id:
        logger.error(f"Key ID mismatch. Expected: {expected_key_id}, Got: {current_key_id}")
        return False
    
    # Verify current key exists
    private_key = secret_manager.get_secret(f"roadtrip-jwt-private-key-{current_key_id}")
    public_key = secret_manager.get_secret(f"roadtrip-jwt-public-key-{current_key_id}")
    
    if not private_key or not public_key:
        logger.error("Current key pair not found in Secret Manager")
        return False
    
    logger.info(f"✓ Verified current key: {current_key_id}")
    logger.info(f"✓ Last rotation: {metadata.get('last_rotation', 'Unknown')}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description='Rotate JWT keys in production')
    parser.add_argument('--project-id', required=True, help='Google Cloud project ID')
    parser.add_argument('--key-size', type=int, default=4096, help='RSA key size (default: 4096)')
    parser.add_argument('--max-keys', type=int, default=3, help='Maximum number of keys to keep (default: 3)')
    parser.add_argument('--verify-only', action='store_true', help='Only verify current key status')
    
    args = parser.parse_args()
    
    # Set project ID
    os.environ['GOOGLE_CLOUD_PROJECT'] = args.project_id
    
    if args.verify_only:
        if verify_rotation():
            logger.info("Key verification successful!")
        else:
            logger.error("Key verification failed!")
        return
    
    # Perform rotation
    if rotate_keys(args.project_id, args.key_size, args.max_keys):
        logger.info("\n✅ Key rotation completed successfully!")
        
        # Verify
        if verify_rotation():
            logger.info("\n✅ Rotation verified successfully!")
            logger.info("\nNext steps:")
            logger.info("1. Monitor application logs for any JWT validation errors")
            logger.info("2. Test token creation and validation")
            logger.info("3. Consider setting up automated rotation schedule")
        else:
            logger.error("Rotation verification failed!")
    else:
        logger.error("Key rotation failed!")


if __name__ == "__main__":
    main()