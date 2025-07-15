"""
Production-ready JWT Manager with RS256 algorithm and key rotation support.
Implements FAANG-level security practices for token management.
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
from app.core.token_blacklist import token_blacklist

logger = logging.getLogger(__name__)

# Token types
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
PARTIAL_TOKEN_TYPE = "partial"  # For 2FA flow

class JWTManager:
    """
    Production JWT manager with RS256 algorithm support and key rotation.
    """
    
    def __init__(self):
        self.algorithm = "RS256"
        self.key_size = 4096  # Strong key size for production
        self.keys_dir = Path("backend/app/core/keys")
        self.keys_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize keys
        self.current_key_id = None
        self.private_keys = {}
        self.public_keys = {}
        
        # Load or generate keys
        self._initialize_keys()
        
    def _initialize_keys(self):
        """Initialize RSA keys for JWT signing."""
        # In production, keys should be loaded from Google Secret Manager
        # This is a local implementation for development
        
        key_file = self.keys_dir / "jwt_keys.json"
        
        if key_file.exists() and not settings.DEBUG:
            # Load existing keys in production
            self._load_keys_from_file(key_file)
        else:
            # Generate new keys (development or first run)
            self._generate_new_key_pair()
            if not settings.DEBUG:
                self._save_keys_to_file(key_file)
    
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
        
        # Store keys
        self.private_keys[key_id] = private_pem
        self.public_keys[key_id] = public_pem
        self.current_key_id = key_id
        
        logger.info(f"Generated new JWT key pair with ID: {key_id}")
        return key_id
    
    def _load_keys_from_file(self, key_file: Path):
        """Load keys from file (development only)."""
        try:
            with open(key_file, 'r') as f:
                data = json.load(f)
                
            for key_id, key_data in data['keys'].items():
                self.private_keys[key_id] = key_data['private'].encode()
                self.public_keys[key_id] = key_data['public'].encode()
                
            self.current_key_id = data['current_key_id']
            logger.info(f"Loaded {len(self.private_keys)} JWT key pairs")
        except Exception as e:
            logger.error(f"Failed to load JWT keys: {e}")
            self._generate_new_key_pair()
    
    def _save_keys_to_file(self, key_file: Path):
        """Save keys to file (development only)."""
        try:
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
            logger.info("Saved JWT keys to file")
        except Exception as e:
            logger.error(f"Failed to save JWT keys: {e}")
    
    def rotate_keys(self) -> str:
        """Rotate JWT signing keys."""
        # Generate new key pair
        new_key_id = self._generate_new_key_pair()
        
        # Keep old keys for validation of existing tokens
        # In production, implement key expiration logic
        
        # Save updated keys
        if not settings.DEBUG:
            key_file = self.keys_dir / "jwt_keys.json"
            self._save_keys_to_file(key_file)
            
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


# Global JWT manager instance
jwt_manager = JWTManager()


# Convenience functions for backward compatibility
def create_access_token(
    subject: Union[str, Any], 
    expires_delta: Optional[timedelta] = None,
    extras: Optional[Dict[str, Any]] = None
) -> str:
    """Create a JWT access token."""
    return jwt_manager.create_token(
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
    return jwt_manager.create_token(
        subject=subject,
        token_type=REFRESH_TOKEN_TYPE,
        expires_delta=expires_delta,
        extras=extras
    )


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode a JWT token."""
    return jwt_manager.decode_token(token)


def validate_token(token: str, expected_type: str) -> Optional[Dict[str, Any]]:
    """Validate a token and check its type."""
    return jwt_manager.validate_token(token, expected_type)


def revoke_token(token: str) -> bool:
    """Revoke a token."""
    return jwt_manager.revoke_token(token)


def get_token_subject(token: str) -> Optional[str]:
    """Extract the subject from a token."""
    payload = decode_token(token)
    if payload:
        return payload.get("sub")
    return None