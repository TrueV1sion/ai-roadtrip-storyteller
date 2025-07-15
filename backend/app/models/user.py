from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, JSON, Integer, Table, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
import uuid
import enum
import logging

from app.db.base import Base
from app.core.enums import UserRole
from app.core.encryption import encrypt_field, decrypt_field

logger = logging.getLogger(__name__)


class User(Base):
    """User model for authentication and profile information."""
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    # User role for authorization
    role = Column(Enum(UserRole), default=UserRole.STANDARD, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Security fields
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    _two_factor_secret_encrypted = Column("two_factor_secret", String, nullable=True)  # Encrypted storage
    two_factor_backup_codes = Column(JSON, nullable=True, default=list)  # List of hashed codes
    two_factor_enabled_at = Column(DateTime, nullable=True)
    two_factor_last_used = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    last_login_ip = Column(String, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    
    @hybrid_property
    def two_factor_secret(self):
        """Get decrypted 2FA secret."""
        if self._two_factor_secret_encrypted:
            try:
                return decrypt_field(self._two_factor_secret_encrypted)
            except Exception as e:
                logger.error(f"Failed to decrypt 2FA secret for user {self.id}: {e}")
                # Return the raw value if it's not encrypted (for migration purposes)
                return self._two_factor_secret_encrypted
        return None
    
    @two_factor_secret.setter
    def two_factor_secret(self, value):
        """Set encrypted 2FA secret."""
        if value:
            try:
                self._two_factor_secret_encrypted = encrypt_field(value)
            except Exception as e:
                logger.error(f"Failed to encrypt 2FA secret for user {self.id}: {e}")
                # Store unencrypted in development if encryption fails
                if self.role == UserRole.STANDARD:
                    raise ValueError("Failed to encrypt 2FA secret")
                self._two_factor_secret_encrypted = value
        else:
            self._two_factor_secret_encrypted = None
    
    # Store additional user data as JSON
    user_metadata = Column(JSON, nullable=True)
    
    # User interests stored as JSON
    interests = Column(JSON, nullable=True)
    
    # Relationships
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    stories = relationship("Story", back_populates="user", cascade="all, delete-orphan")
    reservations = relationship("Reservation", back_populates="user", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")
    event_journeys = relationship("EventJourney", back_populates="user", cascade="all, delete-orphan")
    # Side quests are handled through UserSideQuest relationship
    
    def __repr__(self):
        return f"<User {self.email}>"
