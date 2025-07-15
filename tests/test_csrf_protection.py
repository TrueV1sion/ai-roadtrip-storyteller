import pytest
from fastapi.testclient import TestClient
import json

from app.main import app
from app.core.csrf import CSRF_HEADER_NAME, get_csrf_token_from_cookie

client = TestClient(app)

def test_csrf_token_endpoint():
    """Test the CSRF token generation endpoint."""
    response = client.get("/api/csrf-token")
    
    # Check response status
    assert response.status_code == 200
    
    # Check response body contains token
    data = response.json()
    assert data["success"] is True
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 0
    
    # Check cookie is set
    assert "csrf_token" in response.cookies
    
    # Check header is set
    assert CSRF_HEADER_NAME in response.headers


def test_protected_endpoint_with_csrf():
    """Test a POST request to a protected endpoint with CSRF token."""
    # First get a CSRF token
    token_response = client.get("/api/csrf-token")
    csrf_token = token_response.json()["csrf_token"]
    csrf_cookie = token_response.cookies["csrf_token"]
    
    # Make a request with the token
    headers = {CSRF_HEADER_NAME: csrf_token}
    cookies = {"csrf_token": csrf_cookie}
    
    # Using the directions endpoint as an example
    data = {
        "origin": "San Francisco, CA",
        "destination": "Los Angeles, CA",
        "mode": "driving"
    }
    
    response = client.post(
        "/api/directions",
        json=data,
        headers=headers,
        cookies=cookies
    )
    
    # We might get a 404 or other error if the service is not available,
    # but we shouldn't get a 403 CSRF error
    assert response.status_code != 403


def test_protected_endpoint_without_csrf():
    """Test a POST request to a protected endpoint without CSRF token."""
    # Make a request without CSRF token
    data = {
        "origin": "San Francisco, CA",
        "destination": "Los Angeles, CA",
        "mode": "driving"
    }
    
    response = client.post("/api/directions", json=data)
    
    # Should get a 403 CSRF error
    assert response.status_code == 403
    assert "CSRF" in response.text


def test_safe_methods_bypass_csrf():
    """Test that safe methods (GET, HEAD, OPTIONS) bypass CSRF protection."""
    # GET request should not require CSRF token
    response = client.get("/health")
    assert response.status_code == 200
    
    # HEAD request should not require CSRF token
    response = client.head("/health")
    assert response.status_code == 200
    
    # OPTIONS request should not require CSRF token
    response = client.options("/health")
    assert response.status_code == 200


def test_csrf_token_verification_failure():
    """Test that a request with an invalid CSRF token is rejected."""
    # First get a CSRF token (for the cookie)
    token_response = client.get("/api/csrf-token")
    csrf_cookie = token_response.cookies["csrf_token"]
    
    # Make a request with an invalid token in the header
    headers = {CSRF_HEADER_NAME: "invalid-token"}
    cookies = {"csrf_token": csrf_cookie}
    
    data = {
        "origin": "San Francisco, CA",
        "destination": "Los Angeles, CA",
        "mode": "driving"
    }
    
    response = client.post(
        "/api/directions",
        json=data,
        headers=headers,
        cookies=cookies
    )
    
    # Should get a 403 CSRF error
    assert response.status_code == 403
    assert "CSRF" in response.text