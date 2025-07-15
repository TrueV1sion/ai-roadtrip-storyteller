#!/usr/bin/env python3
"""
Smoke Tests for Production Deployment
Validates critical functionality after deployment
"""

import argparse
import sys
import time
import requests
from typing import Dict, List, Tuple
import json


class SmokeTestRunner:
    """Run smoke tests against deployed service"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.results: List[Tuple[str, bool, str]] = []
        
    def run_all_tests(self) -> bool:
        """Run all smoke tests"""
        print(f"Running smoke tests against: {self.base_url}")
        print("=" * 60)
        
        # Health checks
        self.test_health_endpoint()
        self.test_readiness_endpoint()
        
        # API functionality
        self.test_api_docs()
        self.test_cors_headers()
        
        # Core endpoints
        self.test_story_generation_endpoint()
        self.test_navigation_endpoint()
        self.test_booking_search_endpoint()
        
        # Performance
        self.test_response_times()
        
        # Security
        self.test_security_headers()
        self.test_unauthorized_access()
        
        # Print results
        self.print_results()
        
        # Return success if all tests passed
        return all(result[1] for result in self.results)
    
    def test_health_endpoint(self):
        """Test /health endpoint"""
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.results.append(("Health Check", True, "Service is healthy"))
                else:
                    self.results.append(("Health Check", False, f"Unhealthy status: {data}"))
            else:
                self.results.append(("Health Check", False, f"HTTP {response.status_code}"))
                
        except Exception as e:
            self.results.append(("Health Check", False, str(e)))
    
    def test_readiness_endpoint(self):
        """Test /ready endpoint"""
        try:
            response = requests.get(
                f"{self.base_url}/ready",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ready") is True:
                    # Check individual services
                    services = data.get("services", {})
                    if services.get("database") == "connected" and services.get("redis") == "connected":
                        self.results.append(("Readiness Check", True, "All services ready"))
                    else:
                        self.results.append(("Readiness Check", False, f"Services not ready: {services}"))
                else:
                    self.results.append(("Readiness Check", False, "Service not ready"))
            else:
                self.results.append(("Readiness Check", False, f"HTTP {response.status_code}"))
                
        except Exception as e:
            self.results.append(("Readiness Check", False, str(e)))
    
    def test_api_docs(self):
        """Test API documentation endpoint"""
        try:
            response = requests.get(
                f"{self.base_url}/docs",
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.results.append(("API Docs", True, "Documentation accessible"))
            else:
                self.results.append(("API Docs", False, f"HTTP {response.status_code}"))
                
        except Exception as e:
            self.results.append(("API Docs", False, str(e)))
    
    def test_cors_headers(self):
        """Test CORS configuration"""
        try:
            response = requests.options(
                f"{self.base_url}/api/v1/stories/generate",
                headers={
                    "Origin": "https://app.roadtripai.com",
                    "Access-Control-Request-Method": "POST"
                },
                timeout=self.timeout
            )
            
            cors_headers = {
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Methods",
                "Access-Control-Allow-Headers"
            }
            
            missing_headers = []
            for header in cors_headers:
                if header not in response.headers:
                    missing_headers.append(header)
            
            if not missing_headers:
                self.results.append(("CORS Headers", True, "All CORS headers present"))
            else:
                self.results.append(("CORS Headers", False, f"Missing: {missing_headers}"))
                
        except Exception as e:
            self.results.append(("CORS Headers", False, str(e)))
    
    def test_story_generation_endpoint(self):
        """Test story generation API (without auth for smoke test)"""
        try:
            # First check if endpoint exists
            response = requests.get(
                f"{self.base_url}/api/v1/stories/generate",
                timeout=self.timeout
            )
            
            # Should return 405 (Method Not Allowed) or 401 (Unauthorized)
            if response.status_code in [405, 401]:
                self.results.append(("Story API Exists", True, f"Endpoint exists (HTTP {response.status_code})"))
            else:
                self.results.append(("Story API Exists", False, f"Unexpected response: HTTP {response.status_code}"))
                
        except Exception as e:
            self.results.append(("Story API Exists", False, str(e)))
    
    def test_navigation_endpoint(self):
        """Test navigation API endpoint"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/navigation/route",
                timeout=self.timeout
            )
            
            if response.status_code in [405, 401]:
                self.results.append(("Navigation API Exists", True, f"Endpoint exists (HTTP {response.status_code})"))
            else:
                self.results.append(("Navigation API Exists", False, f"Unexpected response: HTTP {response.status_code}"))
                
        except Exception as e:
            self.results.append(("Navigation API Exists", False, str(e)))
    
    def test_booking_search_endpoint(self):
        """Test booking search API endpoint"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/bookings/restaurants/search",
                timeout=self.timeout
            )
            
            if response.status_code in [401, 422]:  # Unauthorized or missing params
                self.results.append(("Booking API Exists", True, f"Endpoint exists (HTTP {response.status_code})"))
            else:
                self.results.append(("Booking API Exists", False, f"Unexpected response: HTTP {response.status_code}"))
                
        except Exception as e:
            self.results.append(("Booking API Exists", False, str(e)))
    
    def test_response_times(self):
        """Test response times for critical endpoints"""
        endpoints = [
            ("/health", 1.0),
            ("/ready", 2.0),
            ("/api/v1/auth/login", 3.0)
        ]
        
        for endpoint, max_time in endpoints:
            try:
                start_time = time.time()
                response = requests.get(
                    f"{self.base_url}{endpoint}",
                    timeout=self.timeout
                )
                elapsed = time.time() - start_time
                
                if elapsed < max_time:
                    self.results.append((f"Response Time {endpoint}", True, f"{elapsed:.2f}s < {max_time}s"))
                else:
                    self.results.append((f"Response Time {endpoint}", False, f"{elapsed:.2f}s > {max_time}s"))
                    
            except Exception as e:
                self.results.append((f"Response Time {endpoint}", False, str(e)))
    
    def test_security_headers(self):
        """Test security headers"""
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            
            security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": ["DENY", "SAMEORIGIN"],
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": None  # Check exists
            }
            
            missing_headers = []
            for header, expected_values in security_headers.items():
                if header not in response.headers:
                    missing_headers.append(header)
                elif expected_values:
                    actual_value = response.headers[header]
                    if isinstance(expected_values, list):
                        if actual_value not in expected_values:
                            missing_headers.append(f"{header}={actual_value}")
                    elif actual_value != expected_values:
                        missing_headers.append(f"{header}={actual_value}")
            
            if not missing_headers:
                self.results.append(("Security Headers", True, "All security headers present"))
            else:
                self.results.append(("Security Headers", False, f"Issues: {missing_headers}"))
                
        except Exception as e:
            self.results.append(("Security Headers", False, str(e)))
    
    def test_unauthorized_access(self):
        """Test that protected endpoints require authentication"""
        protected_endpoints = [
            "/api/v1/stories/generate",
            "/api/v1/bookings/create",
            "/api/v1/user/profile"
        ]
        
        for endpoint in protected_endpoints:
            try:
                response = requests.post(
                    f"{self.base_url}{endpoint}",
                    json={},
                    timeout=self.timeout
                )
                
                if response.status_code == 401:
                    self.results.append((f"Auth Required {endpoint}", True, "Properly secured"))
                else:
                    self.results.append((f"Auth Required {endpoint}", False, f"HTTP {response.status_code} - Not secured!"))
                    
            except Exception as e:
                self.results.append((f"Auth Required {endpoint}", False, str(e)))
    
    def print_results(self):
        """Print test results summary"""
        print("\nTest Results:")
        print("=" * 60)
        
        passed = 0
        failed = 0
        
        for test_name, success, message in self.results:
            status = "✓ PASS" if success else "✗ FAIL"
            print(f"{status} | {test_name:<30} | {message}")
            
            if success:
                passed += 1
            else:
                failed += 1
        
        print("=" * 60)
        print(f"Total: {len(self.results)} | Passed: {passed} | Failed: {failed}")
        
        if failed > 0:
            print("\n❌ SMOKE TESTS FAILED")
        else:
            print("\n✅ ALL SMOKE TESTS PASSED")


def main():
    parser = argparse.ArgumentParser(description="Run smoke tests against deployed service")
    parser.add_argument("--url", required=True, help="Base URL of the service")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")
    
    args = parser.parse_args()
    
    runner = SmokeTestRunner(args.url, args.timeout)
    success = runner.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()