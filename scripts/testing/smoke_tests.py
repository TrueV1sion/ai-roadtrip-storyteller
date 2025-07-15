#!/usr/bin/env python3
"""
Production Smoke Tests
Run after deployment to verify basic functionality
"""

import argparse
import json
import sys
import time
from typing import Dict, List, Tuple
import requests
from datetime import datetime
import urllib3

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SmokeTests:
    """Run smoke tests against deployed service."""
    
    def __init__(self, base_url: str, environment: str = "production"):
        self.base_url = base_url.rstrip('/')
        self.environment = environment
        self.session = requests.Session()
        self.results: List[Tuple[str, bool, str]] = []
        
    def run_all_tests(self) -> bool:
        """Run all smoke tests and return success status."""
        print(f"\n🔍 Running smoke tests against {self.base_url}")
        print(f"Environment: {self.environment}")
        print("=" * 60)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("API Version", self.test_api_version),
            ("Database Connection", self.test_database_connection),
            ("Redis Connection", self.test_redis_connection),
            ("Authentication", self.test_authentication),
            ("Voice Assistant", self.test_voice_assistant),
            ("Story Generation", self.test_story_generation),
            ("Booking Search", self.test_booking_search),
            ("Metrics Endpoint", self.test_metrics_endpoint),
            ("Error Handling", self.test_error_handling),
        ]
        
        for test_name, test_func in tests:
            try:
                print(f"\n🧪 {test_name}...", end=" ")
                start_time = time.time()
                success, message = test_func()
                duration = time.time() - start_time
                
                if success:
                    print(f"✅ PASSED ({duration:.2f}s)")
                    if message:
                        print(f"   {message}")
                else:
                    print(f"❌ FAILED ({duration:.2f}s)")
                    print(f"   Error: {message}")
                
                self.results.append((test_name, success, message))
                
            except Exception as e:
                print(f"❌ ERROR")
                print(f"   Exception: {str(e)}")
                self.results.append((test_name, False, str(e)))
        
        # Print summary
        self.print_summary()
        
        # Return overall success
        return all(success for _, success, _ in self.results)
    
    def test_health_check(self) -> Tuple[bool, str]:
        """Test health endpoint."""
        resp = self.session.get(f"{self.base_url}/health", timeout=10)
        if resp.status_code != 200:
            return False, f"Status code {resp.status_code}"
        
        data = resp.json()
        if data.get("status") != "healthy":
            return False, f"Unhealthy status: {data}"
        
        return True, "Service is healthy"
    
    def test_api_version(self) -> Tuple[bool, str]:
        """Test API version endpoint."""
        resp = self.session.get(f"{self.base_url}/api/version", timeout=10)
        if resp.status_code != 200:
            return False, f"Status code {resp.status_code}"
        
        data = resp.json()
        version = data.get("version")
        if not version:
            return False, "No version returned"
        
        return True, f"Version: {version}"
    
    def test_database_connection(self) -> Tuple[bool, str]:
        """Test database connectivity."""
        resp = self.session.get(f"{self.base_url}/health/detailed", timeout=10)
        if resp.status_code != 200:
            return False, f"Status code {resp.status_code}"
        
        data = resp.json()
        db_status = data.get("services", {}).get("database")
        if db_status != "healthy":
            return False, f"Database unhealthy: {db_status}"
        
        return True, "Database connection healthy"
    
    def test_redis_connection(self) -> Tuple[bool, str]:
        """Test Redis connectivity."""
        resp = self.session.get(f"{self.base_url}/health/detailed", timeout=10)
        if resp.status_code != 200:
            return False, f"Status code {resp.status_code}"
        
        data = resp.json()
        redis_status = data.get("services", {}).get("redis")
        if redis_status != "healthy":
            return False, f"Redis unhealthy: {redis_status}"
        
        return True, "Redis connection healthy"
    
    def test_authentication(self) -> Tuple[bool, str]:
        """Test authentication endpoints."""
        # Test registration
        test_user = {
            "email": f"smoketest_{int(time.time())}@example.com",
            "password": "TestPassword123!",
            "name": "Smoke Test User"
        }
        
        resp = self.session.post(
            f"{self.base_url}/api/auth/register",
            json=test_user,
            timeout=10
        )
        
        if resp.status_code not in [200, 201]:
            return False, f"Registration failed: {resp.status_code}"
        
        # Test login
        login_resp = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={
                "email": test_user["email"],
                "password": test_user["password"]
            },
            timeout=10
        )
        
        if login_resp.status_code != 200:
            return False, f"Login failed: {login_resp.status_code}"
        
        token = login_resp.json().get("access_token")
        if not token:
            return False, "No access token returned"
        
        return True, "Authentication working"
    
    def test_voice_assistant(self) -> Tuple[bool, str]:
        """Test voice assistant endpoint."""
        payload = {
            "user_input": "What's the weather like?",
            "context": {
                "location": {"lat": 37.7749, "lng": -122.4194},
                "destination": "Los Angeles, CA"
            }
        }
        
        resp = self.session.post(
            f"{self.base_url}/api/voice-assistant/interact",
            json=payload,
            timeout=30
        )
        
        if resp.status_code != 200:
            return False, f"Status code {resp.status_code}"
        
        data = resp.json()
        if not data.get("response"):
            return False, "No response from assistant"
        
        return True, "Voice assistant responding"
    
    def test_story_generation(self) -> Tuple[bool, str]:
        """Test story generation endpoint."""
        payload = {
            "location": {"lat": 37.7749, "lng": -122.4194},
            "interests": ["history", "culture"],
            "duration": 10
        }
        
        resp = self.session.post(
            f"{self.base_url}/api/stories/generate",
            json=payload,
            timeout=30
        )
        
        if resp.status_code != 200:
            return False, f"Status code {resp.status_code}"
        
        data = resp.json()
        if not data.get("story"):
            return False, "No story generated"
        
        return True, "Story generation working"
    
    def test_booking_search(self) -> Tuple[bool, str]:
        """Test booking search endpoint."""
        params = {
            "location": "San Francisco, CA",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "type": "restaurant"
        }
        
        resp = self.session.get(
            f"{self.base_url}/api/bookings/search",
            params=params,
            timeout=10
        )
        
        if resp.status_code != 200:
            return False, f"Status code {resp.status_code}"
        
        data = resp.json()
        if "results" not in data:
            return False, "No results field in response"
        
        return True, f"Found {len(data['results'])} booking options"
    
    def test_metrics_endpoint(self) -> Tuple[bool, str]:
        """Test Prometheus metrics endpoint."""
        resp = self.session.get(f"{self.base_url}/metrics", timeout=10)
        
        if resp.status_code != 200:
            return False, f"Status code {resp.status_code}"
        
        content = resp.text
        if "http_requests_total" not in content:
            return False, "Metrics not properly formatted"
        
        return True, "Metrics endpoint working"
    
    def test_error_handling(self) -> Tuple[bool, str]:
        """Test error handling with invalid request."""
        resp = self.session.get(f"{self.base_url}/api/nonexistent", timeout=10)
        
        if resp.status_code != 404:
            return False, f"Expected 404, got {resp.status_code}"
        
        try:
            data = resp.json()
            if "detail" not in data:
                return False, "Error response not properly formatted"
        except:
            return False, "Error response not JSON"
        
        return True, "Error handling working"
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 60)
        print("SMOKE TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, success, _ in self.results if success)
        failed = len(self.results) - passed
        
        print(f"\nTotal Tests: {len(self.results)}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        
        if failed > 0:
            print("\nFailed Tests:")
            for name, success, message in self.results:
                if not success:
                    print(f"  - {name}: {message}")
        
        print("\n" + "=" * 60)
        
        if failed == 0:
            print("🎉 All smoke tests passed!")
        else:
            print(f"⚠️  {failed} smoke tests failed!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run smoke tests against deployed service")
    parser.add_argument("--url", required=True, help="Base URL of the service")
    parser.add_argument("--environment", default="production", help="Environment name")
    parser.add_argument("--timeout", type=int, default=60, help="Overall timeout in seconds")
    
    args = parser.parse_args()
    
    # Run tests
    tester = SmokeTests(args.url, args.environment)
    success = tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()