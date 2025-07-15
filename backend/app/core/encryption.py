"""
Data Encryption Utilities
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
import base64
import os
import json
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """Handle data encryption/decryption"""
    
    def __init__(self, master_key: Optional[str] = None):
        if master_key:
            self.master_key = master_key.encode()
        else:
            # Generate from environment or key file
            self.master_key = self._get_or_create_master_key()
        
        self.fernet = self._create_fernet()
    
    def _get_or_create_master_key(self) -> bytes:
        """Get or create master encryption key"""
        key_path = "keys/master.key"
        
        if os.path.exists(key_path):
            with open(key_path, "rb") as f:
                return f.read()
        else:
            # Generate new key
            key = Fernet.generate_key()
            
            # Save securely
            os.makedirs("keys", exist_ok=True)
            with open(key_path, "wb") as f:
                f.write(key)
            
            # Set restrictive permissions
            os.chmod(key_path, 0o600)
            
            logger.info("Generated new master encryption key")
            return key
    
    def _create_fernet(self) -> Fernet:
        """Create Fernet instance from master key"""
        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'roadtrip-salt',  # In production, use random salt
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key))
        return Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """Encrypt string data"""
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt string data"""
        try:
            decoded = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self.fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """Encrypt dictionary data"""
        json_str = json.dumps(data)
        return self.encrypt(json_str)
    
    def decrypt_dict(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt dictionary data"""
        json_str = self.decrypt(encrypted_data)
        return json.loads(json_str)
    
    def encrypt_field(self, value: Any, field_type: str = "string") -> str:
        """Encrypt specific field types"""
        if field_type == "email":
            # Encrypt but maintain searchability with hash
            return self._encrypt_searchable(value)
        elif field_type == "phone":
            # Encrypt phone numbers
            return self.encrypt(value)
        elif field_type == "ssn":
            # Extra protection for SSN
            return self._encrypt_sensitive(value)
        else:
            return self.encrypt(str(value))
    
    def _encrypt_searchable(self, value: str) -> Dict[str, str]:
        """Encrypt while maintaining searchability"""
        import hashlib
        
        # Create searchable hash
        search_hash = hashlib.sha256(value.lower().encode()).hexdigest()
        
        return {
            "encrypted": self.encrypt(value),
            "search_hash": search_hash
        }
    
    def _encrypt_sensitive(self, value: str) -> str:
        """Extra encryption for sensitive data"""
        # Double encryption with different key
        first_pass = self.encrypt(value)
        
        # Create secondary key
        secondary_kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'sensitive-salt',
            iterations=100000,
            backend=default_backend()
        )
        
        secondary_key = base64.urlsafe_b64encode(
            secondary_kdf.derive(self.master_key)
        )
        secondary_fernet = Fernet(secondary_key)
        
        # Second encryption
        return base64.urlsafe_b64encode(
            secondary_fernet.encrypt(first_pass.encode())
        ).decode()


# PII Field Encryption
class PIIEncryption:
    """Automatic PII field encryption"""
    
    PII_FIELDS = {
        "email",
        "phone",
        "ssn",
        "credit_card",
        "driver_license",
        "passport",
        "address",
        "date_of_birth"
    }
    
    def __init__(self, encryption_service: EncryptionService):
        self.encryption = encryption_service
    
    def encrypt_model(self, model_instance: Any) -> Any:
        """Encrypt PII fields in model instance"""
        for field in self.PII_FIELDS:
            if hasattr(model_instance, field):
                value = getattr(model_instance, field)
                if value:
                    encrypted = self.encryption.encrypt_field(value, field)
                    setattr(model_instance, f"{field}_encrypted", encrypted)
                    setattr(model_instance, field, None)  # Clear plaintext
        
        return model_instance
    
    def decrypt_model(self, model_instance: Any) -> Any:
        """Decrypt PII fields in model instance"""
        for field in self.PII_FIELDS:
            encrypted_field = f"{field}_encrypted"
            if hasattr(model_instance, encrypted_field):
                encrypted_value = getattr(model_instance, encrypted_field)
                if encrypted_value:
                    if isinstance(encrypted_value, dict):
                        decrypted = self.encryption.decrypt(
                            encrypted_value["encrypted"]
                        )
                    else:
                        decrypted = self.encryption.decrypt(encrypted_value)
                    setattr(model_instance, field, decrypted)
        
        return model_instance


# Voice Recording Encryption
class VoiceEncryption:
    """Encrypt voice recordings and audio data"""
    
    def __init__(self, encryption_service: EncryptionService):
        self.encryption = encryption_service
    
    def encrypt_audio_file(self, file_path: str) -> str:
        """Encrypt audio file"""
        with open(file_path, "rb") as f:
            audio_data = f.read()
        
        # Encrypt binary data
        encrypted = self.encryption.fernet.encrypt(audio_data)
        
        # Save encrypted file
        encrypted_path = f"{file_path}.enc"
        with open(encrypted_path, "wb") as f:
            f.write(encrypted)
        
        # Remove original
        os.remove(file_path)
        
        return encrypted_path
    
    def decrypt_audio_file(self, encrypted_path: str) -> bytes:
        """Decrypt audio file for playback"""
        with open(encrypted_path, "rb") as f:
            encrypted_data = f.read()
        
        # Decrypt
        audio_data = self.encryption.fernet.decrypt(encrypted_data)
        
        return audio_data


# Initialize services
encryption_service = EncryptionService()
pii_encryption = PIIEncryption(encryption_service)
voice_encryption = VoiceEncryption(encryption_service)
