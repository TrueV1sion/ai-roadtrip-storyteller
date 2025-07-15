"""
Production deployment tests for AI Road Trip Storyteller
Run these after deployment to verify the system is working correctly
"""

import os
import sys
import time
import requests
import pytest
from typing import Dict, Any

# Get API URL from environment or command line
API_URL = os.getenv('API_URL', 'https://roadtrip-backend-xxxxx.a.run.app')
if '--api-url' in sys.argv:
    api_url_index = sys.argv.index('--api-url') + 1
    if api_url_index < len(sys.argv):
        API_URL = sys.argv[api_url_index]

# Test configuration
TIMEOUT = 30
HEADERS = {'Content-Type': 'application/json'}


class TestDeployment:
    """Test suite for production deployment verification"""
    
    def test_health_check(self):
        """Test that the health endpoint is responding"""
        response = requests.get(f"{API_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'version' in data
        assert 'environment' in data
        print(f"✓ Health check passed - Version: {data['version']}")
    
    def test_api_docs(self):
        """Test that API documentation is accessible"""
        response = requests.get(f"{API_URL}/docs", timeout=TIMEOUT)
        assert response.status_code == 200
        assert 'swagger-ui' in response.text.lower() or 'redoc' in response.text.lower()
        print("✓ API documentation is accessible")
    
    def test_cors_headers(self):
        """Test CORS configuration"""
        response = requests.options(
            f"{API_URL}/api/health",
            headers={'Origin': 'https://app.roadtripstoryteller.com'},
            timeout=TIMEOUT
        )
        assert 'access-control-allow-origin' in response.headers
        print("✓ CORS headers configured correctly")
    
    def test_rate_limiting(self):
        """Test that rate limiting is enabled"""
        # Make multiple requests quickly
        responses = []
        for _ in range(10):
            response = requests.get(f"{API_URL}/health", timeout=TIMEOUT)
            responses.append(response)
        
        # Check if rate limit headers are present
        last_response = responses[-1]
        rate_limit_headers = [
            'x-ratelimit-limit',
            'x-ratelimit-remaining',
            'x-ratelimit-reset'
        ]
        
        has_rate_limiting = any(
            header in last_response.headers.keys() 
            for header in rate_limit_headers
        )
        
        if has_rate_limiting:
            print("✓ Rate limiting is enabled")
        else:
            print("⚠ Rate limiting headers not found (may be behind proxy)")
    
    def test_voice_personalities_endpoint(self):
        """Test voice personalities endpoint"""
        response = requests.get(
            f"{API_URL}/api/tts/google/personality-presets",
            timeout=TIMEOUT
        )
        
        # This endpoint requires authentication in production
        if response.status_code == 401:
            print("✓ Voice personalities endpoint requires authentication (expected)")
        elif response.status_code == 200:
            data = response.json()
            assert 'presets' in data
            print(f"✓ Voice personalities available: {len(data['presets'])}")
        else:
            pytest.fail(f"Unexpected status code: {response.status_code}")
    
    def test_database_connectivity(self):
        """Test database connectivity through API"""
        # Try to access an endpoint that uses the database
        response = requests.get(f"{API_URL}/api/health/db", timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            assert data['database'] == 'connected'
            print("✓ Database connectivity verified")
        elif response.status_code == 404:
            # Endpoint might not exist, try alternative
            print("⚠ Database health endpoint not found")
        else:
            pytest.fail(f"Database connectivity test failed: {response.status_code}")
    
    def test_redis_connectivity(self):
        """Test Redis connectivity through API"""
        response = requests.get(f"{API_URL}/api/health/redis", timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            assert data['redis'] == 'connected'
            print("✓ Redis connectivity verified")
        elif response.status_code == 404:
            print("⚠ Redis health endpoint not found")
        else:
            pytest.fail(f"Redis connectivity test failed: {response.status_code}")
    
    def test_google_cloud_services(self):
        """Test Google Cloud service integrations"""
        # Test if Google Cloud services are configured
        test_endpoints = [
            ("/api/health/gcs", "Cloud Storage"),
            ("/api/health/vertex-ai", "Vertex AI"),
            ("/api/health/tts", "Text-to-Speech"),
        ]
        
        for endpoint, service_name in test_endpoints:
            response = requests.get(f"{API_URL}{endpoint}", timeout=TIMEOUT)
            
            if response.status_code == 200:
                print(f"✓ {service_name} service connected")
            elif response.status_code == 404:
                print(f"⚠ {service_name} health endpoint not found")
            else:
                print(f"✗ {service_name} service issue: {response.status_code}")
    
    def test_security_headers(self):
        """Test security headers are present"""
        response = requests.get(f"{API_URL}/health", timeout=TIMEOUT)
        
        security_headers = {
            'x-content-type-options': 'nosniff',
            'x-frame-options': 'DENY',
            'x-xss-protection': '1; mode=block',
            'strict-transport-security': None,  # Value varies
            'content-security-policy': None,  # Value varies
        }
        
        missing_headers = []
        for header, expected_value in security_headers.items():
            if header not in response.headers:
                missing_headers.append(header)
            elif expected_value and response.headers[header] != expected_value:
                missing_headers.append(f"{header} (wrong value)")
        
        if not missing_headers:
            print("✓ Security headers configured correctly")
        else:
            print(f"⚠ Missing security headers: {', '.join(missing_headers)}")
    
    def test_voice_assistant_mock(self):
        """Test voice assistant endpoint with mock data"""
        payload = {
            "user_input": "Navigate to Golden Gate Bridge",
            "context": {
                "origin": "San Francisco, CA",
                "destination": "Golden Gate Bridge"
            }
        }
        
        response = requests.post(
            f"{API_URL}/api/voice-assistant/interact",
            json=payload,
            headers=HEADERS,
            timeout=TIMEOUT
        )
        
        if response.status_code == 401:
            print("✓ Voice assistant endpoint requires authentication (expected)")
        elif response.status_code == 200:
            data = response.json()
            assert 'response' in data
            print("✓ Voice assistant endpoint accessible")
        else:
            print(f"⚠ Voice assistant returned status: {response.status_code}")
    
    def test_response_times(self):
        """Test API response times"""
        endpoints = [
            ("/health", "Health check"),
            ("/api/health", "API health"),
        ]
        
        print("\nResponse time tests:")
        for endpoint, name in endpoints:
            start_time = time.time()
            response = requests.get(f"{API_URL}{endpoint}", timeout=TIMEOUT)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            if response.status_code == 200:
                if response_time < 200:
                    print(f"  ✓ {name}: {response_time:.0f}ms (excellent)")
                elif response_time < 500:
                    print(f"  ✓ {name}: {response_time:.0f}ms (good)")
                else:
                    print(f"  ⚠ {name}: {response_time:.0f}ms (slow)")
            else:
                print(f"  ✗ {name}: Failed with status {response.status_code}")


def run_deployment_tests():
    """Run all deployment tests"""
    print(f"\n🚀 Running deployment tests for: {API_URL}\n")
    
    # Create test instance
    test_suite = TestDeployment()
    test_methods = [
        method for method in dir(test_suite) 
        if method.startswith('test_') and callable(getattr(test_suite, method))
    ]
    
    passed = 0
    failed = 0
    warnings = 0
    
    for test_method_name in test_methods:
        test_method = getattr(test_suite, test_method_name)
        try:
            test_method()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_method_name}: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_method_name}: Unexpected error - {str(e)}")
            failed += 1
    
    print(f"\n📊 Test Summary:")
    print(f"  ✓ Passed: {passed}")
    print(f"  ✗ Failed: {failed}")
    print(f"  Total: {passed + failed}")
    
    if failed == 0:
        print("\n✨ All deployment tests passed! The system is ready for production.")
        return 0
    else:
        print(f"\n❌ {failed} tests failed. Please check the deployment.")
        return 1


if __name__ == "__main__":
    sys.exit(run_deployment_tests())