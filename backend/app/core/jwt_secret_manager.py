"""
Enhanced JWT Manager with Google Secret Manager integration.
Production-ready implementation with secure key storage and rotation.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union, Tuple, List
from jose import jwt, jwk
from jose.exceptions import JWTError, ExpiredSignatureError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import json
import os
import uuid
from pathlib import Path
import logging
from app.core.config import settings
from app.core.secret_manager import secret_manager
from app.core.token_blacklist import token_blacklist

logger = logging.getLogger(__name__)

# Token types
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
PARTIAL_TOKEN_TYPE = "partial"  # For 2FA flow

# Secret Manager keys
JWT_PRIVATE_KEY_SECRET = "roadtrip-jwt-private-key"
JWT_PUBLIC_KEY_SECRET = "roadtrip-jwt-public-key"
JWT_KEY_METADATA_SECRET = "roadtrip-jwt-key-metadata"


class SecureJWTManager:
    """
    Production JWT manager with Google Secret Manager integration.
    Implements secure key storage, rotation, and caching.
    """
    
    def __init__(self):
        self.algorithm = "RS256"
        self.key_size = 4096  # Strong key size for production
        
        # In-memory key cache
        self.current_key_id = None
        self.private_keys = {}
        self.public_keys = {}
        self._keys_loaded = False
        
        # Fallback directory for local development
        self.local_keys_dir = Path("backend/app/core/keys")
        self.local_keys_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize keys
        self._initialize_keys()
        
    def _initialize_keys(self):
        """Initialize RSA keys from Secret Manager or generate new ones."""
        try:
            # Try to load from Secret Manager first
            if self._load_keys_from_secret_manager():
                logger.info("Successfully loaded JWT keys from Secret Manager")
                self._keys_loaded = True
                return
        except Exception as e:
            logger.warning(f"Failed to load keys from Secret Manager: {e}")
        
        # Fallback to local keys for development
        if settings.ENVIRONMENT == "development":
            logger.info("Development environment: using local key storage")
            if not self._load_local_keys():
                # Generate new keys if none exist
                self._generate_new_key_pair()
                self._save_local_keys()
        else:
            # In production, we must have keys in Secret Manager
            raise RuntimeError(
                "JWT keys not found in Secret Manager. "
                "Please run the key generation script first."
            )
    
    def _load_keys_from_secret_manager(self) -> bool:
        """
        Load JWT keys from Google Secret Manager.
        
        Returns:
            bool: True if keys were successfully loaded
        """
        try:
            # Load key metadata
            metadata_json = secret_manager.get_secret(JWT_KEY_METADATA_SECRET)
            if not metadata_json:
                return False
                
            metadata = json.loads(metadata_json)
            self.current_key_id = metadata.get("current_key_id")
            
            # Load all key pairs from metadata
            for key_info in metadata.get("keys", []):
                key_id = key_info["key_id"]
                
                # Load private key
                private_key_pem = secret_manager.get_secret(
                    f"{JWT_PRIVATE_KEY_SECRET}-{key_id}"
                )
                if private_key_pem:
                    self.private_keys[key_id] = private_key_pem.encode()
                
                # Load public key
                public_key_pem = secret_manager.get_secret(
                    f"{JWT_PUBLIC_KEY_SECRET}-{key_id}"
                )
                if public_key_pem:
                    self.public_keys[key_id] = public_key_pem.encode()
            
            # Verify we have at least one complete key pair
            if (self.current_key_id and 
                self.current_key_id in self.private_keys and 
                self.current_key_id in self.public_keys):
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error loading keys from Secret Manager: {e}")
            return False
    
    def _save_keys_to_secret_manager(self) -> bool:
        """
        Save JWT keys to Google Secret Manager.
        
        Returns:
            bool: True if keys were successfully saved
        """
        try:
            # Prepare metadata
            metadata = {
                "current_key_id": self.current_key_id,
                "keys": [],
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Save each key pair
            for key_id in self.private_keys:
                # Save private key
                private_secret_id = f"{JWT_PRIVATE_KEY_SECRET}-{key_id}"
                secret_manager.create_or_update_secret(
                    private_secret_id,
                    self.private_keys[key_id].decode()
                )
                
                # Save public key
                public_secret_id = f"{JWT_PUBLIC_KEY_SECRET}-{key_id}"
                secret_manager.create_or_update_secret(
                    public_secret_id,
                    self.public_keys[key_id].decode()
                )
                
                # Add to metadata
                metadata["keys"].append({
                    "key_id": key_id,
                    "created_at": datetime.utcnow().isoformat(),
                    "active": key_id == self.current_key_id
                })
            
            # Save metadata
            secret_manager.create_or_update_secret(
                JWT_KEY_METADATA_SECRET,
                json.dumps(metadata)
            )
            
            logger.info(f"Saved {len(self.private_keys)} JWT key pairs to Secret Manager")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save keys to Secret Manager: {e}")
            return False
    
    def _load_local_keys(self) -> bool:
        """Load keys from local file system (development only)."""
        key_file = self.local_keys_dir / "jwt_keys.json"
        
        if not key_file.exists():
            return False
            
        try:
            with open(key_file, 'r') as f:
                data = json.load(f)
                
            for key_id, key_data in data['keys'].items():
                self.private_keys[key_id] = key_data['private'].encode()
                self.public_keys[key_id] = key_data['public'].encode()
                
            self.current_key_id = data['current_key_id']
            logger.info(f"Loaded {len(self.private_keys)} JWT key pairs from local storage")
            return True
        except Exception as e:
            logger.error(f"Failed to load local JWT keys: {e}")
            return False
    
    def _save_local_keys(self):
        """Save keys to local file system (development only)."""
        if settings.ENVIRONMENT != "development":
            return
            
        try:
            key_file = self.local_keys_dir / "jwt_keys.json"
            data = {
                'current_key_id': self.current_key_id,
                'keys': {}
            }
            
            for key_id in self.private_keys:
                data['keys'][key_id] = {
                    'private': self.private_keys[key_id].decode(),
                    'public': self.public_keys[key_id].decode(),
                    'created_at': datetime.utcnow().isoformat()
                }
                
            with open(key_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            # Set restrictive permissions
            os.chmod(key_file, 0o600)
            logger.info("Saved JWT keys to local storage")
        except Exception as e:
            logger.error(f"Failed to save local JWT keys: {e}")
    
    def _generate_new_key_pair(self) -> str:
        """Generate a new RSA key pair for JWT signing."""
        key_id = str(uuid.uuid4())
        
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=self.key_size,
            backend=default_backend()
        )
        
        # Serialize keys
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        # Store keys in memory
        self.private_keys[key_id] = private_pem
        self.public_keys[key_id] = public_pem
        self.current_key_id = key_id
        
        logger.info(f"Generated new JWT key pair with ID: {key_id}")
        return key_id
    
    def rotate_keys(self) -> str:
        """
        Rotate JWT signing keys and update Secret Manager.
        
        Returns:
            str: New key ID
        """
        # Generate new key pair
        new_key_id = self._generate_new_key_pair()
        
        # Save to appropriate storage
        if settings.ENVIRONMENT == "production":
            if not self._save_keys_to_secret_manager():
                raise RuntimeError("Failed to save rotated keys to Secret Manager")
        else:
            self._save_local_keys()
        
        # Clear Secret Manager cache to ensure fresh keys are loaded
        secret_manager.clear_cache()
        
        logger.info(f"Rotated JWT keys. New key ID: {new_key_id}")
        return new_key_id
    
    def create_token(
        self,
        subject: Union[str, Any],
        token_type: str,
        expires_delta: Optional[timedelta] = None,
        extras: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a JWT token with RS256 algorithm.
        
        Args:
            subject: Token subject (usually user ID)
            token_type: Type of token (access, refresh, partial)
            expires_delta: Optional expiration delta
            extras: Additional claims to include
            
        Returns:
            str: Encoded JWT token
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            # Default expiration based on token type
            if token_type == REFRESH_TOKEN_TYPE:
                expire = datetime.utcnow() + timedelta(days=30)
            elif token_type == PARTIAL_TOKEN_TYPE:
                expire = datetime.utcnow() + timedelta(minutes=10)
            else:
                expire = datetime.utcnow() + timedelta(
                    minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
                )
        
        # Base token payload
        to_encode = {
            "exp": expire,
            "iat": datetime.utcnow(),
            "nbf": datetime.utcnow(),  # Not before
            "sub": str(subject),
            "type": token_type,
            "jti": str(uuid.uuid4()),  # Unique token ID for revocation
            "iss": settings.JWT_ISSUER,  # Token issuer
            "aud": settings.JWT_AUDIENCE  # Token audience
        }
        
        # Add any extra claims
        if extras:
            to_encode.update(extras)
        
        # Get current private key
        private_key = self.private_keys[self.current_key_id]
        
        # Add key ID to header for key rotation support
        headers = {"kid": self.current_key_id}
        
        # Encode token
        encoded_jwt = jwt.encode(
            to_encode,
            private_key,
            algorithm=self.algorithm,
            headers=headers
        )
        
        return encoded_jwt
    
    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: JWT token
            
        Returns:
            Optional[Dict[str, Any]]: Token payload or None if invalid
        """
        try:
            # Get unverified header to find key ID
            unverified = jwt.get_unverified_header(token)
            key_id = unverified.get("kid")
            
            # If key not in cache, try reloading from Secret Manager
            if key_id and key_id not in self.public_keys:
                logger.info(f"Key {key_id} not in cache, reloading from Secret Manager")
                self._load_keys_from_secret_manager()
            
            if not key_id or key_id not in self.public_keys:
                logger.warning(f"Invalid key ID in token: {key_id}")
                return None
            
            # Get public key for verification
            public_key = self.public_keys[key_id]
            
            # Decode and validate token
            payload = jwt.decode(
                token,
                public_key,
                algorithms=[self.algorithm],
                issuer=settings.JWT_ISSUER,
                audience=settings.JWT_AUDIENCE,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iat": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "require_exp": True,
                    "require_iat": True,
                    "require_nbf": True
                }
            )
            
            # Check if token is blacklisted
            token_id = payload.get("jti")
            if token_id and token_blacklist.contains(token_id):
                logger.info(f"Attempted to use blacklisted token: {token_id}")
                return None
                
            return payload
            
        except ExpiredSignatureError:
            logger.debug("Token has expired")
            return None
        except JWTError as e:
            logger.warning(f"JWT validation error: {e}")
            return None
    
    def validate_token(self, token: str, expected_type: str) -> Optional[Dict[str, Any]]:
        """
        Validate a token and check its type.
        
        Args:
            token: JWT token
            expected_type: Expected token type
            
        Returns:
            Optional[Dict[str, Any]]: Token payload if valid
        """
        payload = self.decode_token(token)
        if not payload:
            return None
            
        # Check token type
        if payload.get("type") != expected_type:
            logger.warning(f"Token type mismatch. Expected: {expected_type}, Got: {payload.get('type')}")
            return None
            
        return payload
    
    def revoke_token(self, token: str) -> bool:
        """
        Revoke a token by adding it to the blacklist.
        
        Args:
            token: JWT token
            
        Returns:
            bool: True if token was revoked
        """
        try:
            # Decode without expiration check for revocation
            unverified = jwt.get_unverified_header(token)
            key_id = unverified.get("kid")
            
            if key_id and key_id in self.public_keys:
                payload = jwt.decode(
                    token,
                    self.public_keys[key_id],
                    algorithms=[self.algorithm],
                    options={"verify_exp": False}
                )
                
                # Add token ID to blacklist
                token_id = payload.get("jti")
                if token_id:
                    expires_at = datetime.utcfromtimestamp(payload.get("exp", 0))
                    success = token_blacklist.add(token_id, expires_at)
                    if success:
                        logger.info(f"Revoked token: {token_id}")
                    return success
                    
            return False
        except JWTError as e:
            logger.error(f"Failed to revoke token: {e}")
            return False
    
    def get_public_keys(self) -> Dict[str, str]:
        """
        Get public keys for token verification (JWKS endpoint).
        
        Returns:
            Dict[str, str]: Public keys in JWKS format
        """
        jwks = {"keys": []}
        
        for key_id, public_key_pem in self.public_keys.items():
            # Convert PEM to JWK format
            public_key = serialization.load_pem_public_key(
                public_key_pem,
                backend=default_backend()
            )
            
            # Create JWK
            key_jwk = jwk.construct(public_key, algorithm=self.algorithm)
            key_dict = key_jwk.to_dict()
            key_dict["kid"] = key_id
            key_dict["use"] = "sig"
            key_dict["alg"] = self.algorithm
            
            jwks["keys"].append(key_dict)
            
        return jwks


# Global secure JWT manager instance
secure_jwt_manager = SecureJWTManager()


# Convenience functions maintaining backward compatibility
def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None,
    extras: Optional[Dict[str, Any]] = None
) -> str:
    """Create a JWT access token."""
    return secure_jwt_manager.create_token(
        subject=subject,
        token_type=ACCESS_TOKEN_TYPE,
        expires_delta=expires_delta,
        extras=extras
    )


def create_refresh_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None,
    extras: Optional[Dict[str, Any]] = None
) -> str:
    """Create a JWT refresh token."""
    return secure_jwt_manager.create_token(
        subject=subject,
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=expires_delta,
        extras=extras
    )


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode a JWT token."""
    return secure_jwt_manager.decode_token(token)


def validate_token(token: str, expected_type: str) -> Optional[Dict[str, Any]]:
    """Validate a token and check its type."""
    return secure_jwt_manager.validate_token(token, expected_type)


def revoke_token(token: str) -> bool:
    """Revoke a token."""
    return secure_jwt_manager.revoke_token(token)


def get_token_subject(token: str) -> Optional[str]:
    """Extract the subject from a token."""
    payload = decode_token(token)
    if payload:
        return payload.get("sub")
    return None