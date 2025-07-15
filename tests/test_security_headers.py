import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_security_headers_on_endpoints():
    """Test that security headers are present on API responses."""
    # Test on a basic endpoint
    response = client.get("/health")
    
    # Test Content-Security-Policy header
    assert "Content-Security-Policy" in response.headers
    csp = response.headers["Content-Security-Policy"]
    
    # Check for critical CSP directives
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    
    # Test other security headers
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    
    assert "Strict-Transport-Security" in response.headers
    assert "max-age=31536000" in response.headers["Strict-Transport-Security"]
    
    assert "Referrer-Policy" in response.headers
    
    assert "X-XSS-Protection" in response.headers
    assert response.headers["X-XSS-Protection"] == "1; mode=block"
    
    assert "Permissions-Policy" in response.headers


def test_security_headers_on_api_endpoints():
    """Test that security headers are present on deeper API routes."""
    # Test an API endpoint (using OPTIONS to avoid auth requirements)
    response = client.options("/api/auth/login")
    
    # Check core security headers
    assert "Content-Security-Policy" in response.headers
    assert "X-Frame-Options" in response.headers
    assert "X-Content-Type-Options" in response.headers
    assert "Referrer-Policy" in response.headers


def test_csp_headers_content():
    """Test that the CSP header contains the expected directives."""
    response = client.get("/health")
    
    csp = response.headers["Content-Security-Policy"]
    
    # Split the directives for easier assertions
    directives = csp.split("; ")
    directives_dict = {}
    
    for directive in directives:
        if " " in directive:
            key, value = directive.split(" ", 1)
            directives_dict[key] = value
        else:
            directives_dict[directive] = None
    
    # Test core directives are present
    assert "default-src" in directives_dict
    assert "img-src" in directives_dict
    assert "script-src" in directives_dict
    assert "style-src" in directives_dict
    assert "connect-src" in directives_dict
    assert "frame-ancestors" in directives_dict
    
    # Test expected values
    assert "'self'" in directives_dict["default-src"]
    assert "'self'" in directives_dict["img-src"]
    assert "data:" in directives_dict["img-src"]
    assert "'self'" in directives_dict["script-src"]
    assert "'none'" in directives_dict["frame-ancestors"]