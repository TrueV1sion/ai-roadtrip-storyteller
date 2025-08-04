#!/usr/bin/env python3
"""
Generate new JWT RSA keys and store them in Google Secret Manager.
This script should be run once to initialize production JWT keys.
"""
import os
import sys
import json
import argparse
from datetime import datetime
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


def main():
    parser = argparse.ArgumentParser(description='Generate JWT keys for production')
    parser.add_argument('--project-id', required=True, help='Google Cloud project ID')
    parser.add_argument('--key-size', type=int, default=4096, help='RSA key size (default: 4096)')
    parser.add_argument('--force', action='store_true', help='Force regeneration of keys')
    
    args = parser.parse_args()
    
    # Set project ID
    os.environ['GOOGLE_CLOUD_PROJECT'] = args.project_id
    
    # Check if keys already exist
    if not args.force:
        existing_metadata = secret_manager.get_secret('roadtrip-jwt-key-metadata')
        if existing_metadata:
            logger.warning("JWT keys already exist in Secret Manager. Use --force to regenerate.")
            return
    
    logger.info(f"Generating new JWT keys with key size: {args.key_size}")
    
    # Generate new key pair
    key_id = str(uuid.uuid4())
    private_key, public_key = generate_rsa_key_pair(args.key_size)
    
    # Prepare metadata
    metadata = {
        "current_key_id": key_id,
        "keys": [{
            "key_id": key_id,
            "created_at": datetime.utcnow().isoformat(),
            "active": True,
            "key_size": args.key_size
        }],
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Store in Secret Manager
    logger.info("Storing keys in Google Secret Manager...")
    
    # Store private key
    if secret_manager.create_or_update_secret(f"roadtrip-jwt-private-key-{key_id}", private_key):
        logger.info(f"✓ Stored private key: roadtrip-jwt-private-key-{key_id}")
    else:
        logger.error("Failed to store private key")
        return
    
    # Store public key
    if secret_manager.create_or_update_secret(f"roadtrip-jwt-public-key-{key_id}", public_key):
        logger.info(f"✓ Stored public key: roadtrip-jwt-public-key-{key_id}")
    else:
        logger.error("Failed to store public key")
        return
    
    # Store metadata
    if secret_manager.create_or_update_secret("roadtrip-jwt-key-metadata", json.dumps(metadata)):
        logger.info("✓ Stored key metadata: roadtrip-jwt-key-metadata")
    else:
        logger.error("Failed to store metadata")
        return
    
    logger.info(f"""
JWT keys successfully generated and stored in Secret Manager!

Key ID: {key_id}
Key Size: {args.key_size} bits
Project: {args.project_id}

Next steps:
1. Update your deployment to use the new jwt_secret_manager module
2. Remove any local key files from version control
3. Test JWT token creation and validation
4. Consider setting up key rotation schedule
""")
    
    # Save a local backup (optional)
    backup_dir = Path("jwt_key_backup")
    backup_dir.mkdir(exist_ok=True)
    
    with open(backup_dir / f"jwt_keys_{key_id}.json", 'w') as f:
        json.dump({
            "key_id": key_id,
            "private_key": private_key,
            "public_key": public_key,
            "created_at": metadata["created_at"]
        }, f, indent=2)
    
    logger.info(f"Local backup saved to: {backup_dir / f'jwt_keys_{key_id}.json'}")
    logger.warning("⚠️  Keep this backup secure and delete after verifying Secret Manager access!")


if __name__ == "__main__":
    main()