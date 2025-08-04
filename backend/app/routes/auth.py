from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    validate_token,
    revoke_token,
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE
)
from app.core.auth import get_current_active_user, get_current_user
from app.core.config import settings
from app.core.logger import get_logger
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import Token, TokenRefresh, TokenRevoke, TwoFactorLogin
from app.crud.crud_user import (
    create_user, get_user_by_email, get_user_by_username, 
    authenticate_user, update_user_last_login, get_user
)
from app.services.two_factor_service import two_factor_service
from app.services.session_manager import session_manager, DeviceInfo

logger = get_logger(__name__)
router = APIRouter()


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user with comprehensive password validation."""
    try:
        # Check if user exists by email
        if get_user_by_email(db, user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Check if user exists by username
        if hasattr(user_data, 'username') and user_data.username and get_user_by_username(db, user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create new user using CRUD operation (includes password validation)
        user = await create_user(db, user_data)
        
        logger.info(f"New user registered: {user.email}")
        return user
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/token", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None,
    response: Response = None
):
    """Login to get access token."""
    try:
        # Check for account lockout first
        from app.core.auth_rate_limiter import get_auth_rate_limiter
        rate_limiter = get_auth_rate_limiter()
        ip_address = request.client.host if request and request.client else "unknown"
        
        # Check if account is locked
        is_locked, lockout_seconds = await rate_limiter.check_lockout(form_data.username)
        if is_locked:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account is locked. Try again in {lockout_seconds} seconds",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check IP lockout
        is_ip_locked, ip_lockout_seconds = await rate_limiter.check_lockout(ip_address)
        if is_ip_locked:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Too many failed attempts from this IP. Try again in {ip_lockout_seconds} seconds",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Authenticate user using CRUD operation
        user = authenticate_user(db, form_data.username, form_data.password)
        
        if not user:
            # Record failed attempt
            attempts, locked = await rate_limiter.record_failed_attempt(form_data.username, ip_address)
            
            if locked:
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=f"Account locked after {attempts} failed attempts. Try again later",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Incorrect email or password. {5 - attempts} attempts remaining",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if 2FA is enabled
        if user.two_factor_secret:
            # Create a partial token that requires 2FA verification
            partial_token = create_access_token(
                subject=user.id,
                additional_claims={"partial": True, "requires_2fa": True}
            )
            
            logger.info(f"User {user.email} requires 2FA verification")
            
            return {
                "access_token": "",  # Empty access token
                "token_type": "bearer",
                "requires_2fa": True,
                "partial_token": partial_token
            }
        
        # Clear failed login attempts after successful authentication
        await rate_limiter.clear_failed_attempts(form_data.username)
        
        # Create session
        device_info = DeviceInfo(
            user_agent=request.headers.get("user-agent", "") if request else "",
            ip_address=request.client.host if request and request.client else "unknown",
            platform=request.headers.get("sec-ch-ua-platform", "").strip('"') if request else None
        )
        
        session = await session_manager.create_session(
            user_id=str(user.id),
            device_info=device_info,
            is_persistent="remember_me" in form_data.scopes,  # Check if remember me
            metadata={"login_method": "password"}
        )
        
        # Create tokens for non-2FA users
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)
        
        # Calculate token expiration in seconds
        token_expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        # Update last login timestamp
        try:
            update_user_last_login(db, str(user.id))
        except Exception as e:
            logger.warning(f"Failed to update last login for user {user.id}: {e}")
        
        # If using HTTP-only cookies for refresh tokens (more secure)
        if response:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=settings.SECURE_COOKIES or settings.ENVIRONMENT == "production",
                samesite="lax",
                max_age=60 * 60 * 24 * 30  # 30 days
            )
            
            # Set session cookie
            response.set_cookie(
                key="session_id",
                value=session.session_id,
                httponly=True,
                secure=settings.SECURE_COOKIES or settings.ENVIRONMENT == "production",
                samesite="lax",
                max_age=60 * 60 * 24 * 30 if session.is_persistent else None
            )
        
        logger.info(f"User logged in: {user.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
            "expires_in": token_expires_in
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    token_data: TokenRefresh = None,
    refresh_token: str = Cookie(None),
    db: Session = Depends(get_db),
    response: Response = None
):
    """Refresh access token using refresh token."""
    try:
        # Get refresh token from request body or cookie
        token = token_data.refresh_token if token_data else refresh_token
        
        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required"
            )
        
        # Validate refresh token
        payload = validate_token(token, REFRESH_TOKEN_TYPE)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify user exists and is active using CRUD operation
        from app.crud.crud_user import get_user
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Revoke old refresh token (optional but recommended)
        revoke_token(token)
        
        # Create new tokens
        new_access_token = create_access_token(subject=user.id)
        new_refresh_token = create_refresh_token(subject=user.id)
        
        # Calculate token expiration in seconds
        token_expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        # Update cookie if using HTTP-only cookies
        if response:
            response.set_cookie(
                key="refresh_token",
                value=new_refresh_token,
                httponly=True,
                secure=settings.SECURE_COOKIES or settings.ENVIRONMENT == "production",
                samesite="lax",
                max_age=60 * 60 * 24 * 30  # 30 days
            )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "refresh_token": new_refresh_token,
            "expires_in": token_expires_in
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/revoke")
async def logout(
    token_data: TokenRevoke,
    response: Response = None
):
    """Revoke a token (logout)."""
    try:
        success = revoke_token(token_data.token)
        
        # Clear refresh token cookie if using HTTP-only cookies
        if response:
            response.delete_cookie(
                key="refresh_token",
                httponly=True,
                secure=settings.SECURE_COOKIES or settings.ENVIRONMENT == "production",
                samesite="lax"
            )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token"
            )
        
        return {"detail": "Token successfully revoked"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user profile."""
    return current_user


@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change user password with full policy validation."""
    try:
        # Verify current password
        from app.core.security import verify_password
        if not verify_password(current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password using CRUD operation (includes validation)
        from app.schemas.user import UserUpdate
        from app.crud.crud_user import update_user
        
        user_update = UserUpdate(password=new_password)
        updated_user = await update_user(db, str(current_user.id), user_update)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        logger.info(f"Password changed for user: {current_user.email}")
        
        return {"detail": "Password successfully changed"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.delete("/account")
async def delete_account(
    password: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete user account."""
    try:
        # Verify password before deletion
        from app.core.security import verify_password
        if not verify_password(password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is incorrect"
            )
        
        # Delete user using CRUD operation
        from app.crud.crud_user import delete_user
        success = delete_user(db, str(current_user.id))
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete account"
            )
        
        logger.info(f"Account deleted for user: {current_user.email}")
        
        return {"detail": "Account successfully deleted"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Account deletion error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account deletion failed"
        )


@router.post("/2fa/login", response_model=Token)
async def login_2fa(
    login_data: TwoFactorLogin,
    db: Session = Depends(get_db),
    request: Request = None,
    response: Response = None
):
    """Complete login with 2FA verification."""
    try:
        # Validate the partial token
        from app.core.security import validate_token, ACCESS_TOKEN_TYPE
        payload = validate_token(login_data.partial_token, ACCESS_TOKEN_TYPE)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired partial token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if this is a partial token requiring 2FA
        if not payload.get("partial") or not payload.get("requires_2fa"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token does not require 2FA verification"
            )
        
        # Get user from token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid partial token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Get user from database
        user = get_user(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verify 2FA code
        is_valid, is_backup, remaining = await two_factor_service.verify_2fa_code(
            db=db,
            user=user,
            code=login_data.code
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create session after successful 2FA
        device_info = DeviceInfo(
            user_agent=request.headers.get("user-agent", "") if request else "",
            ip_address=request.client.host if request and request.client else "unknown",
            platform=request.headers.get("sec-ch-ua-platform", "").strip('"') if request else None
        )
        
        session = await session_manager.create_session(
            user_id=str(user.id),
            device_info=device_info,
            is_persistent=False,  # Can be updated based on login data
            metadata={"login_method": "2fa"}
        )
        
        # Create full access tokens
        from app.core.security import create_access_token, create_refresh_token
        access_token = create_access_token(subject=user.id)
        refresh_token = create_refresh_token(subject=user.id)
        
        # Calculate token expiration in seconds
        token_expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        
        # Update last login timestamp
        try:
            update_user_last_login(db, str(user.id))
        except Exception as e:
            logger.warning(f"Failed to update last login for user {user.id}: {e}")
        
        # If using HTTP-only cookies for refresh tokens
        if response:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=settings.SECURE_COOKIES or settings.ENVIRONMENT == "production",
                samesite="lax",
                max_age=60 * 60 * 24 * 30  # 30 days
            )
            
            # Set session cookie
            response.set_cookie(
                key="session_id",
                value=session.session_id,
                httponly=True,
                secure=settings.SECURE_COOKIES or settings.ENVIRONMENT == "production",
                samesite="lax",
                max_age=60 * 60 * 24 * 30 if session.is_persistent else None
            )
        
        logger.info(f"User logged in with 2FA: {user.email}")
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "refresh_token": refresh_token,
            "expires_in": token_expires_in
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        # Rate limiting error from 2FA service
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"2FA login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="2FA login failed"
        )