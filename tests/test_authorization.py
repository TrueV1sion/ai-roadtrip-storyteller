import pytest
from fastapi.testclient import TestClient
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import uuid
from unittest.mock import patch

from app.main import app
from app.database import get_db
from app.models import User
from app.core.security import get_password_hash, create_access_token
from app.core.authorization import (
    get_current_user, get_current_active_user, 
    has_role, ResourcePermission, UserRole,
    ResourceType, Action
)


# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Test client
client = TestClient(app)


# Test user data
test_users = {
    "admin": {
        "id": str(uuid.uuid4()),
        "email": "admin@example.com",
        "name": "Admin User",
        "password": "adminpassword",
        "role": UserRole.ADMIN,
        "is_active": True,
        "is_premium": True
    },
    "premium": {
        "id": str(uuid.uuid4()),
        "email": "premium@example.com",
        "name": "Premium User",
        "password": "premiumpassword",
        "role": UserRole.PREMIUM,
        "is_active": True,
        "is_premium": True
    },
    "standard": {
        "id": str(uuid.uuid4()),
        "email": "standard@example.com",
        "name": "Standard User",
        "password": "standardpassword",
        "role": UserRole.STANDARD,
        "is_active": True,
        "is_premium": False
    },
    "inactive": {
        "id": str(uuid.uuid4()),
        "email": "inactive@example.com",
        "name": "Inactive User",
        "password": "inactivepassword",
        "role": UserRole.STANDARD,
        "is_active": False,
        "is_premium": False
    }
}


def create_test_users(db: Session):
    """Create test users in the database."""
    for user_data in test_users.values():
        user = User(
            id=user_data["id"],
            email=user_data["email"],
            name=user_data["name"],
            hashed_password=get_password_hash(user_data["password"]),
            role=user_data["role"],
            is_active=user_data["is_active"],
            is_premium=user_data["is_premium"]
        )
        db.add(user)
    db.commit()


def get_token_headers(user_key):
    """Get authorization headers for a test user."""
    user = test_users[user_key]
    token = create_access_token(subject=user["id"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def test_db():
    """Create test database tables and users."""
    from app.db.base import Base
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    create_test_users(db)
    yield db
    db.close()
    
    # Clean up after tests
    Base.metadata.drop_all(bind=engine)


# Override the get_db dependency for tests
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def test_get_current_user_valid_token(test_db):
    """Test that get_current_user returns the correct user with a valid token."""
    token = create_access_token(subject=test_users["admin"]["id"])
    
    # Mock the dependency
    with patch("app.core.authorization.validate_token") as mock_validate:
        mock_validate.return_value = {"sub": test_users["admin"]["id"]}
        
        user = get_current_user(token, test_db)
        assert user is not None
        assert user.email == test_users["admin"]["email"]
        assert user.role == UserRole.ADMIN


def test_get_current_user_invalid_token(test_db):
    """Test that get_current_user raises an exception with an invalid token."""
    invalid_token = "invalid.token"
    
    # Mock the dependency
    with patch("app.core.authorization.validate_token") as mock_validate:
        mock_validate.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(invalid_token, test_db)
            
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_active_user_active(test_db):
    """Test that get_current_active_user returns the user if active."""
    active_user = test_db.query(User).filter(User.email == test_users["admin"]["email"]).first()
    
    # Call the function
    result = get_current_active_user(active_user)
    
    assert result == active_user


def test_get_current_active_user_inactive(test_db):
    """Test that get_current_active_user raises an exception if user is inactive."""
    inactive_user = test_db.query(User).filter(User.email == test_users["inactive"]["email"]).first()
    
    with pytest.raises(HTTPException) as exc_info:
        get_current_active_user(inactive_user)
        
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_has_role_sufficient_role(test_db):
    """Test that has_role allows access with sufficient role."""
    admin_user = test_db.query(User).filter(User.email == test_users["admin"]["email"]).first()
    standard_user = test_db.query(User).filter(User.email == test_users["standard"]["email"]).first()
    
    # Test admin accessing admin endpoint
    has_admin_role = has_role(UserRole.ADMIN)
    result = has_admin_role(admin_user)
    # The dependency should complete without raising an exception
    
    # Test admin accessing standard endpoint
    has_standard_role = has_role(UserRole.STANDARD)
    result = has_standard_role(admin_user)
    # Should also complete without exception
    
    # Test standard user accessing standard endpoint
    result = has_standard_role(standard_user)
    # Should complete without exception


def test_has_role_insufficient_role(test_db):
    """Test that has_role denies access with insufficient role."""
    standard_user = test_db.query(User).filter(User.email == test_users["standard"]["email"]).first()
    
    # Test standard user accessing admin endpoint
    has_admin_role = has_role(UserRole.ADMIN)
    
    with pytest.raises(HTTPException) as exc_info:
        has_admin_role(standard_user)
        
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_resource_permission_check(test_db):
    """Test that ResourcePermission.check enforces permissions correctly."""
    admin_user = test_db.query(User).filter(User.email == test_users["admin"]["email"]).first()
    standard_user = test_db.query(User).filter(User.email == test_users["standard"]["email"]).first()
    
    # Create permission checkers
    admin_permission = ResourcePermission(ResourceType.USER, Action.ANY)
    read_permission = ResourcePermission(ResourceType.USER, Action.READ)
    
    # Admin can do anything
    assert await admin_permission.check(None, admin_user, test_db)
    
    # Standard user can read
    assert await read_permission.check(None, standard_user, test_db)
    
    # Standard user can't update other users
    update_permission = ResourcePermission(ResourceType.USER, Action.UPDATE)
    with pytest.raises(HTTPException) as exc_info:
        await update_permission.check(test_users["admin"]["id"], standard_user, test_db)
        
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN


def test_user_endpoint_authorization():
    """Integration test for user endpoints with authorization."""
    # Test admin accessing user list (admin only)
    response = client.get("/api/users/", headers=get_token_headers("admin"))
    assert response.status_code == status.HTTP_200_OK
    
    # Test standard user accessing user list (should be forbidden)
    response = client.get("/api/users/", headers=get_token_headers("standard"))
    assert response.status_code == status.HTTP_403_FORBIDDEN
    
    # Test unauthorized request to protected endpoint
    response = client.get("/api/users/me/stories")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    # Test authorized request to protected endpoint
    response = client.get("/api/users/me/stories", headers=get_token_headers("standard"))
    assert response.status_code == status.HTTP_200_OK