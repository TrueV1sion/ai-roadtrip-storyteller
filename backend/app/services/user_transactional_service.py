"""
User Service with Transactional Support
Handles user operations with proper transaction management
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.user import User
from app.models.user_profile import UserProfile
from app.models.user_preferences import UserPreferences
from app.models.auth import RefreshToken
from app.core.logger import logger
from app.core.transaction_manager import transactional, TransactionValidator, bulk_transactional
from app.core.standardized_errors import DataIntegrityError
from app.services.password_service import PasswordService


class UserTransactionalService:
    """
    Service for managing user operations with transaction support.
    
    Ensures atomic operations for user creation, updates, and related data.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.password_service = PasswordService()
    
    @transactional(isolation_level="READ COMMITTED")
    def create_user_with_profile(
        self,
        email: str,
        password: str,
        name: str,
        profile_data: Optional[Dict[str, Any]] = None,
        preferences_data: Optional[Dict[str, Any]] = None
    ) -> User:
        """
        Create a user with profile and preferences in a single transaction.
        
        This ensures that either all user data is created or none of it is.
        """
        # Check if user already exists
        existing_user = self.db.query(User).filter(
            User.email == email
        ).first()
        
        if existing_user:
            raise DataIntegrityError(f"User with email {email} already exists")
        
        # Create user
        user = User(
            email=email,
            name=name,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Set password
        user.password_hash = self.password_service.hash_password(password)
        
        # Validate user model
        validator = TransactionValidator()
        if not validator.validate_foreign_keys(self.db, user):
            raise DataIntegrityError("User validation failed")
        
        self.db.add(user)
        self.db.flush()  # Get user ID
        
        # Create profile
        profile = UserProfile(
            user_id=user.id,
            bio=profile_data.get('bio', '') if profile_data else '',
            avatar_url=profile_data.get('avatar_url') if profile_data else None,
            location=profile_data.get('location') if profile_data else None,
            phone_number=profile_data.get('phone_number') if profile_data else None,
            date_of_birth=profile_data.get('date_of_birth') if profile_data else None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(profile)
        
        # Create preferences
        preferences = UserPreferences(
            user_id=user.id,
            language=preferences_data.get('language', 'en') if preferences_data else 'en',
            timezone=preferences_data.get('timezone', 'UTC') if preferences_data else 'UTC',
            notifications_enabled=preferences_data.get('notifications_enabled', True) if preferences_data else True,
            email_notifications=preferences_data.get('email_notifications', True) if preferences_data else True,
            sms_notifications=preferences_data.get('sms_notifications', False) if preferences_data else False,
            marketing_emails=preferences_data.get('marketing_emails', False) if preferences_data else False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.db.add(preferences)
        self.db.flush()
        
        logger.info(f"Created user {user.id} with profile and preferences")
        
        return user
    
    @transactional()
    def update_user_and_profile(
        self,
        user_id: int,
        user_updates: Optional[Dict[str, Any]] = None,
        profile_updates: Optional[Dict[str, Any]] = None,
        preferences_updates: Optional[Dict[str, Any]] = None
    ) -> User:
        """
        Update user, profile, and preferences atomically.
        """
        # Get user with lock for update
        user = self.db.query(User).filter(
            User.id == user_id
        ).with_for_update().first()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Update user fields
        if user_updates:
            for field, value in user_updates.items():
                if hasattr(user, field) and field not in ['id', 'created_at']:
                    setattr(user, field, value)
            user.updated_at = datetime.utcnow()
        
        # Update profile
        if profile_updates:
            profile = self.db.query(UserProfile).filter(
                UserProfile.user_id == user_id
            ).with_for_update().first()
            
            if profile:
                for field, value in profile_updates.items():
                    if hasattr(profile, field) and field not in ['id', 'user_id', 'created_at']:
                        setattr(profile, field, value)
                profile.updated_at = datetime.utcnow()
            else:
                # Create profile if it doesn't exist
                profile = UserProfile(
                    user_id=user_id,
                    **profile_updates,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(profile)
        
        # Update preferences
        if preferences_updates:
            preferences = self.db.query(UserPreferences).filter(
                UserPreferences.user_id == user_id
            ).with_for_update().first()
            
            if preferences:
                for field, value in preferences_updates.items():
                    if hasattr(preferences, field) and field not in ['id', 'user_id', 'created_at']:
                        setattr(preferences, field, value)
                preferences.updated_at = datetime.utcnow()
            else:
                # Create preferences if they don't exist
                preferences = UserPreferences(
                    user_id=user_id,
                    **preferences_updates,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                self.db.add(preferences)
        
        self.db.flush()
        
        logger.info(f"Updated user {user_id} with related data")
        
        return user
    
    @transactional()
    def deactivate_user(
        self,
        user_id: int,
        reason: Optional[str] = None,
        delete_sessions: bool = True
    ) -> User:
        """
        Deactivate a user and optionally clean up their sessions.
        """
        # Get user with lock
        user = self.db.query(User).filter(
            User.id == user_id
        ).with_for_update().first()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Deactivate user
        user.is_active = False
        user.updated_at = datetime.utcnow()
        
        # Add deactivation reason to metadata
        if reason:
            if user.metadata:
                user.metadata['deactivation_reason'] = reason
                user.metadata['deactivated_at'] = datetime.utcnow().isoformat()
            else:
                user.metadata = {
                    'deactivation_reason': reason,
                    'deactivated_at': datetime.utcnow().isoformat()
                }
        
        # Delete refresh tokens if requested
        if delete_sessions:
            self.db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id
            ).delete()
        
        self.db.flush()
        
        logger.info(f"Deactivated user {user_id}")
        
        return user
    
    @transactional()
    def change_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
        invalidate_sessions: bool = True
    ) -> User:
        """
        Change user password with proper validation and session management.
        """
        # Get user with lock
        user = self.db.query(User).filter(
            User.id == user_id
        ).with_for_update().first()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Verify old password
        if not self.password_service.verify_password(old_password, user.password_hash):
            raise ValueError("Invalid current password")
        
        # Validate new password
        if not self.password_service.validate_password_strength(new_password):
            raise ValueError("New password does not meet security requirements")
        
        # Update password
        user.password_hash = self.password_service.hash_password(new_password)
        user.password_changed_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        
        # Invalidate all refresh tokens if requested
        if invalidate_sessions:
            self.db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id
            ).delete()
        
        self.db.flush()
        
        logger.info(f"Changed password for user {user_id}")
        
        return user
    
    @bulk_transactional(batch_size=100)
    def bulk_update_user_preferences(
        self,
        user_ids: List[int],
        preferences_updates: Dict[str, Any]
    ) -> None:
        """
        Update preferences for multiple users in batches.
        
        This is decorated with @bulk_transactional which handles
        batch processing and error handling automatically.
        """
        # This method receives a batch of user_ids
        preferences_list = self.db.query(UserPreferences).filter(
            UserPreferences.user_id.in_(user_ids)
        ).all()
        
        for preferences in preferences_list:
            for field, value in preferences_updates.items():
                if hasattr(preferences, field) and field not in ['id', 'user_id', 'created_at']:
                    setattr(preferences, field, value)
            preferences.updated_at = datetime.utcnow()
        
        self.db.flush()
    
    @transactional()
    def merge_duplicate_users(
        self,
        primary_user_id: int,
        duplicate_user_id: int
    ) -> User:
        """
        Merge a duplicate user account into the primary account.
        
        This complex operation transfers all data from the duplicate
        to the primary account in a single transaction.
        """
        # Get both users with locks
        primary_user = self.db.query(User).filter(
            User.id == primary_user_id
        ).with_for_update().first()
        
        duplicate_user = self.db.query(User).filter(
            User.id == duplicate_user_id
        ).with_for_update().first()
        
        if not primary_user or not duplicate_user:
            raise ValueError("One or both users not found")
        
        # Transfer bookings
        from app.models.booking import Booking
        self.db.query(Booking).filter(
            Booking.user_id == duplicate_user_id
        ).update({Booking.user_id: primary_user_id})
        
        # Transfer reservations
        from app.services.reservation_agent import Reservation
        self.db.query(Reservation).filter(
            Reservation.user_id == str(duplicate_user_id)
        ).update({Reservation.user_id: str(primary_user_id)})
        
        # Merge profiles (keep primary, but copy missing data)
        primary_profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == primary_user_id
        ).first()
        
        duplicate_profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == duplicate_user_id
        ).first()
        
        if duplicate_profile and primary_profile:
            # Copy fields that are empty in primary but exist in duplicate
            if not primary_profile.phone_number and duplicate_profile.phone_number:
                primary_profile.phone_number = duplicate_profile.phone_number
            if not primary_profile.location and duplicate_profile.location:
                primary_profile.location = duplicate_profile.location
            
            # Delete duplicate profile
            self.db.delete(duplicate_profile)
        elif duplicate_profile and not primary_profile:
            # Transfer profile to primary user
            duplicate_profile.user_id = primary_user_id
        
        # Delete duplicate preferences
        self.db.query(UserPreferences).filter(
            UserPreferences.user_id == duplicate_user_id
        ).delete()
        
        # Delete duplicate refresh tokens
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == duplicate_user_id
        ).delete()
        
        # Mark duplicate user as merged
        duplicate_user.is_active = False
        duplicate_user.email = f"merged_{duplicate_user_id}_{duplicate_user.email}"
        duplicate_user.metadata = {
            'merged_into': primary_user_id,
            'merged_at': datetime.utcnow().isoformat()
        }
        
        # Update primary user
        primary_user.updated_at = datetime.utcnow()
        
        self.db.flush()
        
        logger.info(f"Merged user {duplicate_user_id} into {primary_user_id}")
        
        return primary_user