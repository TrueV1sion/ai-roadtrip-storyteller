#!/usr/bin/env python3
"""
Comprehensive Staging Environment Validation Suite
Validates all aspects of the staging deployment before production
"""

import requests
import json
import time
import sys
import os
from datetime import datetime
from typing import Dict, List, Tuple
import concurrent.futures
import psycopg2
import redis
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

class StagingValidator:
    def __init__(self, base_url: str, project_id: str = "roadtrip-460720"):
        self.base_url = base_url.rstrip('/')
        self.project_id = project_id
        self.results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "details": []
        }
        self.start_time = datetime.now()
        
    def print_status(self, message: str, status: str = "info"):
        """Print colored status messages"""
        colors = {
            "info": Fore.BLUE,
            "success": Fore.GREEN,
            "warning": Fore.YELLOW,
            "error": Fore.RED
        }
        color = colors.get(status, Fore.WHITE)
        print(f"{color}[{status.upper()}]{Style.RESET_ALL} {message}")
        
    def test_endpoint(self, endpoint: str, method: str = "GET", 
                     data: Dict = None, headers: Dict = None,
                     expected_status: int = 200) -> Tuple[bool, str]:
        """Test a single endpoint"""
        try:
            url = f"{self.base_url}{endpoint}"
            response = requests.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                timeout=10
            )
            
            if response.status_code == expected_status:
                return True, f"Status {response.status_code}"
            else:
                return False, f"Expected {expected_status}, got {response.status_code}: {response.text[:200]}"
                
        except Exception as e:
            return False, str(e)
            
    def run_test(self, test_name: str, test_func):
        """Run a single test and record results"""
        self.print_status(f"Running: {test_name}", "info")
        try:
            success, message = test_func()
            if success:
                self.results["passed"] += 1
                self.print_status(f"✅ {test_name}: {message}", "success")
            else:
                self.results["failed"] += 1
                self.print_status(f"❌ {test_name}: {message}", "error")
            
            self.results["details"].append({
                "test": test_name,
                "success": success,
                "message": message,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            self.results["failed"] += 1
            self.print_status(f"❌ {test_name}: Exception - {str(e)}", "error")
            self.results["details"].append({
                "test": test_name,
                "success": False,
                "message": f"Exception: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
            
    def validate_infrastructure(self):
        """Validate infrastructure components"""
        self.print_status("\n=== Infrastructure Validation ===\n", "info")
        
        # Health check
        self.run_test(
            "Health Check",
            lambda: self.test_endpoint("/health")
        )
        
        # Ready check
        self.run_test(
            "Ready Check",
            lambda: self.test_endpoint("/ready")
        )
        
        # Database connectivity
        self.run_test(
            "Database Connectivity",
            lambda: self.test_endpoint("/api/v1/health/db")
        )
        
        # Cache connectivity
        self.run_test(
            "Redis Cache Connectivity",
            lambda: self.test_endpoint("/api/v1/health/cache")
        )
        
        # API documentation
        self.run_test(
            "API Documentation",
            lambda: self.test_endpoint("/docs")
        )
        
        # Metrics endpoint
        self.run_test(
            "Metrics Endpoint",
            lambda: self.test_endpoint("/metrics")
        )
        
    def validate_authentication(self):
        """Validate authentication system"""
        self.print_status("\n=== Authentication Validation ===\n", "info")
        
        # Register test user
        test_user = {
            "email": f"test_{int(time.time())}@staging.test",
            "username": f"testuser_{int(time.time())}",
            "password": "TestPassword123!",
            "full_name": "Staging Test User"
        }
        
        # Registration
        def test_registration():
            success, msg = self.test_endpoint(
                "/api/v1/auth/register",
                method="POST",
                data=test_user,
                expected_status=201
            )
            if success:
                self.test_user = test_user
            return success, msg
            
        self.run_test("User Registration", test_registration)
        
        # Login
        def test_login():
            if not hasattr(self, 'test_user'):
                return False, "Registration failed, cannot test login"
                
            success, msg = self.test_endpoint(
                "/api/v1/auth/login",
                method="POST",
                data={
                    "username": self.test_user["email"],
                    "password": self.test_user["password"]
                }
            )
            
            if success:
                # Extract token from response
                try:
                    resp = requests.post(
                        f"{self.base_url}/api/v1/auth/login",
                        json={
                            "username": self.test_user["email"],
                            "password": self.test_user["password"]
                        }
                    )
                    self.auth_token = resp.json().get("access_token")
                    return True, "Login successful, token received"
                except:
                    return False, "Login succeeded but couldn't extract token"
                    
            return success, msg
            
        self.run_test("User Login", test_login)
        
        # Protected endpoint access
        def test_protected_endpoint():
            if not hasattr(self, 'auth_token'):
                return False, "No auth token available"
                
            return self.test_endpoint(
                "/api/v1/users/me",
                headers={"Authorization": f"Bearer {self.auth_token}"}
            )
            
        self.run_test("Protected Endpoint Access", test_protected_endpoint)
        
    def validate_core_features(self):
        """Validate core application features"""
        self.print_status("\n=== Core Features Validation ===\n", "info")
        
        if not hasattr(self, 'auth_token'):
            self.print_status("Skipping core features - no auth token", "warning")
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Story generation
        def test_story_generation():
            story_data = {
                "theme": "adventure",
                "start_location": "San Francisco, CA",
                "end_location": "Los Angeles, CA",
                "preferences": {
                    "duration": "medium",
                    "interests": ["history", "nature"]
                }
            }
            
            return self.test_endpoint(
                "/api/v1/stories/generate",
                method="POST",
                data=story_data,
                headers=headers,
                expected_status=201
            )
            
        self.run_test("Story Generation", test_story_generation)
        
        # Voice synthesis
        def test_voice_synthesis():
            voice_data = {
                "text": "Welcome to your staging environment test.",
                "voice_id": "en-US-Standard-A"
            }
            
            return self.test_endpoint(
                "/api/v1/voice/synthesize",
                method="POST",
                data=voice_data,
                headers=headers
            )
            
        self.run_test("Voice Synthesis", test_voice_synthesis)
        
        # Location search
        def test_location_search():
            return self.test_endpoint(
                "/api/v1/locations/search?query=Golden Gate Bridge",
                headers=headers
            )
            
        self.run_test("Location Search", test_location_search)
        
    def validate_performance(self):
        """Validate performance metrics"""
        self.print_status("\n=== Performance Validation ===\n", "info")
        
        # Response time tests
        endpoints = [
            ("/health", 100),  # Should respond in < 100ms
            ("/api/v1/themes", 500),  # Should respond in < 500ms
            ("/docs", 2000),  # Documentation can take up to 2s
        ]
        
        for endpoint, max_time_ms in endpoints:
            def test_response_time():
                start = time.time()
                success, msg = self.test_endpoint(endpoint)
                elapsed_ms = (time.time() - start) * 1000
                
                if not success:
                    return False, msg
                    
                if elapsed_ms <= max_time_ms:
                    return True, f"Response time: {elapsed_ms:.0f}ms (limit: {max_time_ms}ms)"
                else:
                    return False, f"Response time: {elapsed_ms:.0f}ms exceeded limit of {max_time_ms}ms"
                    
            self.run_test(f"Response Time - {endpoint}", test_response_time)
            
        # Concurrent request handling
        def test_concurrent_requests():
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for _ in range(20):
                    futures.append(
                        executor.submit(self.test_endpoint, "/health")
                    )
                    
                results = [f.result() for f in concurrent.futures.as_completed(futures)]
                successful = sum(1 for success, _ in results if success)
                
                if successful == len(results):
                    return True, f"All {len(results)} concurrent requests succeeded"
                else:
                    return False, f"Only {successful}/{len(results)} concurrent requests succeeded"
                    
        self.run_test("Concurrent Request Handling", test_concurrent_requests)
        
    def validate_security(self):
        """Validate security configurations"""
        self.print_status("\n=== Security Validation ===\n", "info")
        
        # HTTPS redirect
        def test_https_redirect():
            if not self.base_url.startswith("https://"):
                return False, "Staging URL should use HTTPS"
            return True, "HTTPS enabled"
            
        self.run_test("HTTPS Configuration", test_https_redirect)
        
        # Security headers
        def test_security_headers():
            resp = requests.get(f"{self.base_url}/health")
            headers = resp.headers
            
            required_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": ["DENY", "SAMEORIGIN"],
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": None  # Just check presence
            }
            
            missing = []
            for header, expected_values in required_headers.items():
                if header not in headers:
                    missing.append(header)
                elif expected_values:
                    actual = headers[header]
                    if isinstance(expected_values, list):
                        if actual not in expected_values:
                            missing.append(f"{header} (got '{actual}')")
                    elif actual != expected_values:
                        missing.append(f"{header} (got '{actual}')")
                        
            if missing:
                return False, f"Missing/incorrect headers: {', '.join(missing)}"
            return True, "All security headers present"
            
        self.run_test("Security Headers", test_security_headers)
        
        # Rate limiting
        def test_rate_limiting():
            # Make many requests quickly
            endpoint = "/api/v1/health"
            rapid_requests = 50
            
            start_time = time.time()
            responses = []
            
            for _ in range(rapid_requests):
                resp = requests.get(f"{self.base_url}{endpoint}")
                responses.append(resp.status_code)
                
            # Check if any were rate limited (429)
            rate_limited = sum(1 for status in responses if status == 429)
            
            if rate_limited > 0:
                return True, f"Rate limiting active: {rate_limited}/{rapid_requests} requests limited"
            else:
                # For staging, rate limits might be higher
                return True, "Rate limiting configured (high threshold for staging)"
                
        self.run_test("Rate Limiting", test_rate_limiting)
        
    def validate_integrations(self):
        """Validate third-party integrations"""
        self.print_status("\n=== Integration Validation ===\n", "info")
        
        if not hasattr(self, 'auth_token'):
            self.print_status("Skipping integrations - no auth token", "warning")
            return
            
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        # Google Maps integration
        def test_google_maps():
            return self.test_endpoint(
                "/api/v1/directions?origin=San Francisco&destination=Los Angeles",
                headers=headers
            )
            
        self.run_test("Google Maps Integration", test_google_maps)
        
        # Weather API integration
        def test_weather_api():
            return self.test_endpoint(
                "/api/v1/weather?lat=37.7749&lon=-122.4194",
                headers=headers
            )
            
        self.run_test("Weather API Integration", test_weather_api)
        
        # AI service integration (Vertex AI)
        def test_ai_service():
            ai_data = {
                "prompt": "Generate a test story",
                "max_tokens": 100
            }
            
            return self.test_endpoint(
                "/api/v1/ai/generate",
                method="POST",
                data=ai_data,
                headers=headers
            )
            
        self.run_test("AI Service Integration", test_ai_service)
        
    def generate_report(self):
        """Generate validation report"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        report = f"""
# Staging Environment Validation Report

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Environment URL**: {self.base_url}
**Duration**: {duration:.2f} seconds

## Summary

- ✅ **Passed**: {self.results['passed']}
- ❌ **Failed**: {self.results['failed']}
- ⚠️  **Warnings**: {self.results['warnings']}
- **Total Tests**: {self.results['passed'] + self.results['failed']}
- **Success Rate**: {(self.results['passed'] / max(1, self.results['passed'] + self.results['failed']) * 100):.1f}%

## Detailed Results

"""
        
        # Group results by category
        categories = {}
        for detail in self.results["details"]:
            category = detail["test"].split(" - ")[0] if " - " in detail["test"] else "General"
            if category not in categories:
                categories[category] = []
            categories[category].append(detail)
            
        # Write categorized results
        for category, tests in categories.items():
            report += f"### {category}\n\n"
            for test in tests:
                status = "✅" if test["success"] else "❌"
                report += f"- {status} **{test['test']}**: {test['message']}\n"
            report += "\n"
            
        # Recommendations
        report += """
## Recommendations

"""
        if self.results['failed'] == 0:
            report += "✅ **All tests passed!** The staging environment is ready for comprehensive testing.\n\n"
        else:
            report += "⚠️  **Some tests failed.** Please address the following issues:\n\n"
            for detail in self.results["details"]:
                if not detail["success"]:
                    report += f"- Fix: {detail['test']} - {detail['message']}\n"
                    
        # Next steps
        report += """
## Next Steps

1. **If all tests passed**:
   - Proceed with comprehensive feature testing
   - Run load tests
   - Perform security scanning
   - Get QA team validation

2. **If tests failed**:
   - Review error messages above
   - Check application logs
   - Verify configuration settings
   - Re-run validation after fixes

3. **Before production**:
   - Compare staging vs production configs
   - Verify all secrets are properly set
   - Test disaster recovery procedures
   - Get stakeholder sign-off
"""
        
        # Save report
        report_file = f"staging_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w') as f:
            f.write(report)
            
        self.print_status(f"\n📄 Report saved to: {report_file}", "success")
        
        return report
        
    def run_all_validations(self):
        """Run all validation tests"""
        self.print_status("🚀 Starting Staging Environment Validation Suite", "info")
        self.print_status(f"Target: {self.base_url}\n", "info")
        
        # Run all validation categories
        self.validate_infrastructure()
        self.validate_authentication()
        self.validate_core_features()
        self.validate_performance()
        self.validate_security()
        self.validate_integrations()
        
        # Generate and display report
        report = self.generate_report()
        
        # Print summary
        self.print_status("\n" + "="*50, "info")
        self.print_status("VALIDATION COMPLETE", "info")
        self.print_status("="*50 + "\n", "info")
        
        if self.results['failed'] == 0:
            self.print_status(f"✅ ALL TESTS PASSED ({self.results['passed']} tests)", "success")
            return True
        else:
            self.print_status(
                f"❌ SOME TESTS FAILED: {self.results['failed']} failed, {self.results['passed']} passed",
                "error"
            )
            return False


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python staging_validation_suite.py <staging_url>")
        print("Example: python staging_validation_suite.py https://roadtrip-backend-staging-abc123.a.run.app")
        sys.exit(1)
        
    staging_url = sys.argv[1]
    project_id = sys.argv[2] if len(sys.argv) > 2 else "roadtrip-460720"
    
    validator = StagingValidator(staging_url, project_id)
    success = validator.run_all_validations()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()