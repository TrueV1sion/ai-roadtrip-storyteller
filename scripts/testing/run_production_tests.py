#!/usr/bin/env python3
"""
Run Production Tests
Execute comprehensive tests against production or staging environment
"""
import asyncio
import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.core.config import settings


class ProductionTestRunner:
    """Runs comprehensive tests against production environment"""
    
    def __init__(self, base_url: str, environment: str = "production"):
        self.base_url = base_url.rstrip('/')
        self.environment = environment
        self.test_results = {
            "environment": environment,
            "base_url": base_url,
            "start_time": datetime.now().isoformat(),
            "tests": {},
            "summary": {}
        }
        
    async def run_all_tests(self):
        """Run all test suites"""
        print(f"\n🧪 PRODUCTION TEST SUITE")
        print("=" * 60)
        print(f"Environment: {self.environment}")
        print(f"Target URL:  {self.base_url}")
        print(f"Started at:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        test_suites = [
            ("Health Checks", self.test_health_checks),
            ("API Endpoints", self.test_api_endpoints),
            ("Authentication", self.test_authentication),
            ("Voice Assistant", self.test_voice_assistant),
            ("Booking Flow", self.test_booking_flow),
            ("Performance", self.test_performance),
            ("Error Handling", self.test_error_handling),
            ("Security Headers", self.test_security_headers)
        ]
        
        total_passed = 0
        total_failed = 0
        
        for suite_name, test_func in test_suites:
            print(f"\n📋 {suite_name}")
            print("-" * 40)
            
            suite_start = time.time()
            passed, failed = await test_func()
            suite_duration = time.time() - suite_start
            
            self.test_results["tests"][suite_name] = {
                "passed": passed,
                "failed": failed,
                "duration": f"{suite_duration:.2f}s"
            }
            
            total_passed += passed
            total_failed += failed
            
            print(f"✅ Passed: {passed} | ❌ Failed: {failed} | ⏱️  {suite_duration:.2f}s")
        
        # Generate summary
        self.test_results["summary"] = {
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_tests": total_passed + total_failed,
            "success_rate": f"{(total_passed / (total_passed + total_failed) * 100):.1f}%",
            "duration": f"{time.time() - time.mktime(datetime.now().timetuple()):.2f}s"
        }
        
        self.save_results()
        self.print_summary()
    
    async def test_health_checks(self) -> tuple[int, int]:
        """Test health check endpoints"""
        passed = 0
        failed = 0
        
        endpoints = [
            ("/health", "API Health"),
            ("/health/db", "Database Health"),
            ("/health/redis", "Redis Health"),
            ("/health/ready", "Readiness Check")
        ]
        
        for endpoint, name in endpoints:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        if response.status == 200:
                            print(f"  ✅ {name}: OK")
                            passed += 1
                        else:
                            print(f"  ❌ {name}: HTTP {response.status}")
                            failed += 1
            except Exception as e:
                print(f"  ❌ {name}: {str(e)}")
                failed += 1
        
        return passed, failed
    
    async def test_api_endpoints(self) -> tuple[int, int]:
        """Test core API endpoints"""
        passed = 0
        failed = 0
        
        # Test cases
        test_cases = [
            {
                "name": "Get Directions",
                "method": "POST",
                "endpoint": "/api/directions",
                "data": {
                    "origin": "San Francisco, CA",
                    "destination": "Los Angeles, CA"
                }
            },
            {
                "name": "Voice Assistant",
                "method": "POST",
                "endpoint": "/api/voice-assistant/interact",
                "data": {
                    "user_input": "I want to go to Disneyland",
                    "context": {
                        "origin": "San Francisco, CA"
                    }
                }
            },
            {
                "name": "Get Stories",
                "method": "GET",
                "endpoint": "/api/stories",
                "params": {
                    "location": "San Francisco, CA",
                    "interests": "history,culture"
                }
            }
        ]
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            for test in test_cases:
                try:
                    if test["method"] == "GET":
                        url = f"{self.base_url}{test['endpoint']}"
                        async with session.get(url, params=test.get("params")) as response:
                            if response.status == 200:
                                print(f"  ✅ {test['name']}: OK")
                                passed += 1
                            else:
                                print(f"  ❌ {test['name']}: HTTP {response.status}")
                                failed += 1
                    else:  # POST
                        url = f"{self.base_url}{test['endpoint']}"
                        async with session.post(url, json=test.get("data")) as response:
                            if response.status in [200, 201]:
                                print(f"  ✅ {test['name']}: OK")
                                passed += 1
                            else:
                                print(f"  ❌ {test['name']}: HTTP {response.status}")
                                failed += 1
                except Exception as e:
                    print(f"  ❌ {test['name']}: {str(e)}")
                    failed += 1
        
        return passed, failed
    
    async def test_authentication(self) -> tuple[int, int]:
        """Test authentication flow"""
        passed = 0
        failed = 0
        
        # Test registration
        test_user = {
            "email": f"test_{int(time.time())}@roadtrip-test.com",
            "password": "TestPassword123!",
            "username": f"testuser_{int(time.time())}"
        }
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            # Register
            try:
                async with session.post(
                    f"{self.base_url}/api/auth/register",
                    json=test_user
                ) as response:
                    if response.status in [200, 201]:
                        print(f"  ✅ User Registration: OK")
                        passed += 1
                        
                        # Try login
                        login_data = {
                            "username": test_user["email"],
                            "password": test_user["password"]
                        }
                        async with session.post(
                            f"{self.base_url}/api/auth/login",
                            json=login_data
                        ) as login_response:
                            if login_response.status == 200:
                                print(f"  ✅ User Login: OK")
                                passed += 1
                            else:
                                print(f"  ❌ User Login: HTTP {login_response.status}")
                                failed += 1
                    else:
                        print(f"  ❌ User Registration: HTTP {response.status}")
                        failed += 1
            except Exception as e:
                print(f"  ❌ Authentication Test: {str(e)}")
                failed += 2
        
        return passed, failed
    
    async def test_voice_assistant(self) -> tuple[int, int]:
        """Test voice assistant functionality"""
        passed = 0
        failed = 0
        
        test_scenarios = [
            {
                "name": "Navigation Request",
                "input": "Take me to the Golden Gate Bridge",
                "expected_in_response": ["Golden Gate", "route", "navigate"]
            },
            {
                "name": "Booking Request", 
                "input": "Find me a hotel in San Francisco",
                "expected_in_response": ["hotel", "San Francisco", "book"]
            },
            {
                "name": "Story Request",
                "input": "Tell me about the history of this area",
                "expected_in_response": ["history", "story", "area"]
            }
        ]
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            for scenario in test_scenarios:
                try:
                    data = {
                        "user_input": scenario["input"],
                        "context": {
                            "location": "San Francisco, CA",
                            "speed": 35,
                            "is_highway": False
                        }
                    }
                    
                    async with session.post(
                        f"{self.base_url}/api/voice-assistant/interact",
                        json=data
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            response_text = result.get("response", "").lower()
                            
                            # Check if expected keywords are in response
                            found_keywords = any(
                                keyword.lower() in response_text 
                                for keyword in scenario["expected_in_response"]
                            )
                            
                            if found_keywords:
                                print(f"  ✅ {scenario['name']}: OK")
                                passed += 1
                            else:
                                print(f"  ⚠️  {scenario['name']}: Response doesn't match expected")
                                failed += 1
                        else:
                            print(f"  ❌ {scenario['name']}: HTTP {response.status}")
                            failed += 1
                except Exception as e:
                    print(f"  ❌ {scenario['name']}: {str(e)}")
                    failed += 1
        
        return passed, failed
    
    async def test_booking_flow(self) -> tuple[int, int]:
        """Test booking flow"""
        passed = 0
        failed = 0
        
        # Search for hotels
        search_data = {
            "location": "San Francisco, CA",
            "check_in": "2025-07-01",
            "check_out": "2025-07-03",
            "guests": 2
        }
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            try:
                # Search
                async with session.post(
                    f"{self.base_url}/api/bookings/search/hotels",
                    json=search_data
                ) as response:
                    if response.status == 200:
                        print(f"  ✅ Hotel Search: OK")
                        passed += 1
                        
                        results = await response.json()
                        if results.get("results"):
                            # Simulate booking attempt
                            print(f"  ✅ Found {len(results['results'])} hotels")
                            passed += 1
                        else:
                            print(f"  ⚠️  No hotels found in search")
                    else:
                        print(f"  ❌ Hotel Search: HTTP {response.status}")
                        failed += 1
            except Exception as e:
                print(f"  ❌ Booking Flow Test: {str(e)}")
                failed += 1
        
        return passed, failed
    
    async def test_performance(self) -> tuple[int, int]:
        """Test performance metrics"""
        passed = 0
        failed = 0
        
        endpoints = [
            ("/api/health", 100),  # Should respond in <100ms
            ("/api/voice-assistant/interact", 500),  # Should respond in <500ms
            ("/api/directions", 300)  # Should respond in <300ms
        ]
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            for endpoint, max_time_ms in endpoints:
                try:
                    data = {}
                    if "voice" in endpoint:
                        data = {"user_input": "test", "context": {}}
                    elif "directions" in endpoint:
                        data = {"origin": "A", "destination": "B"}
                    
                    start_time = time.time()
                    
                    if data:
                        async with session.post(f"{self.base_url}{endpoint}", json=data) as response:
                            response_time_ms = (time.time() - start_time) * 1000
                    else:
                        async with session.get(f"{self.base_url}{endpoint}") as response:
                            response_time_ms = (time.time() - start_time) * 1000
                    
                    if response.status in [200, 201] and response_time_ms < max_time_ms:
                        print(f"  ✅ {endpoint}: {response_time_ms:.0f}ms (target: <{max_time_ms}ms)")
                        passed += 1
                    else:
                        print(f"  ❌ {endpoint}: {response_time_ms:.0f}ms (target: <{max_time_ms}ms)")
                        failed += 1
                        
                except Exception as e:
                    print(f"  ❌ {endpoint}: {str(e)}")
                    failed += 1
        
        return passed, failed
    
    async def test_error_handling(self) -> tuple[int, int]:
        """Test error handling"""
        passed = 0
        failed = 0
        
        error_cases = [
            {
                "name": "Invalid Route",
                "endpoint": "/api/invalid-endpoint",
                "expected_status": 404
            },
            {
                "name": "Missing Required Fields",
                "endpoint": "/api/directions",
                "method": "POST",
                "data": {},  # Missing origin and destination
                "expected_status": 422
            },
            {
                "name": "Invalid JSON",
                "endpoint": "/api/voice-assistant/interact",
                "method": "POST",
                "raw_data": "invalid json",
                "expected_status": 422
            }
        ]
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            for case in error_cases:
                try:
                    if case.get("method") == "POST":
                        if "raw_data" in case:
                            async with session.post(
                                f"{self.base_url}{case['endpoint']}",
                                data=case["raw_data"],
                                headers={"Content-Type": "application/json"}
                            ) as response:
                                if response.status == case["expected_status"]:
                                    print(f"  ✅ {case['name']}: Correctly returned {response.status}")
                                    passed += 1
                                else:
                                    print(f"  ❌ {case['name']}: Expected {case['expected_status']}, got {response.status}")
                                    failed += 1
                        else:
                            async with session.post(
                                f"{self.base_url}{case['endpoint']}",
                                json=case.get("data", {})
                            ) as response:
                                if response.status == case["expected_status"]:
                                    print(f"  ✅ {case['name']}: Correctly returned {response.status}")
                                    passed += 1
                                else:
                                    print(f"  ❌ {case['name']}: Expected {case['expected_status']}, got {response.status}")
                                    failed += 1
                    else:
                        async with session.get(f"{self.base_url}{case['endpoint']}") as response:
                            if response.status == case["expected_status"]:
                                print(f"  ✅ {case['name']}: Correctly returned {response.status}")
                                passed += 1
                            else:
                                print(f"  ❌ {case['name']}: Expected {case['expected_status']}, got {response.status}")
                                failed += 1
                except Exception as e:
                    print(f"  ❌ {case['name']}: {str(e)}")
                    failed += 1
        
        return passed, failed
    
    async def test_security_headers(self) -> tuple[int, int]:
        """Test security headers"""
        passed = 0
        failed = 0
        
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": ["DENY", "SAMEORIGIN"],
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age="
        }
        
        import aiohttp
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.base_url}/health") as response:
                    headers = response.headers
                    
                    for header, expected_value in required_headers.items():
                        if header in headers:
                            actual_value = headers[header]
                            
                            if isinstance(expected_value, list):
                                if any(val in actual_value for val in expected_value):
                                    print(f"  ✅ {header}: {actual_value}")
                                    passed += 1
                                else:
                                    print(f"  ❌ {header}: Expected one of {expected_value}, got {actual_value}")
                                    failed += 1
                            elif expected_value in actual_value:
                                print(f"  ✅ {header}: {actual_value}")
                                passed += 1
                            else:
                                print(f"  ❌ {header}: Expected {expected_value}, got {actual_value}")
                                failed += 1
                        else:
                            print(f"  ❌ {header}: Missing")
                            failed += 1
                            
            except Exception as e:
                print(f"  ❌ Security Headers Test: {str(e)}")
                failed += len(required_headers)
        
        return passed, failed
    
    def save_results(self):
        """Save test results to file"""
        filename = f"production_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\n📄 Results saved to: {filename}")
    
    def print_summary(self):
        """Print test summary"""
        summary = self.test_results["summary"]
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests:  {summary['total_tests']}")
        print(f"Passed:       {summary['total_passed']}")
        print(f"Failed:       {summary['total_failed']}")
        print(f"Success Rate: {summary['success_rate']}")
        print()
        
        if summary["total_failed"] == 0:
            print("✅ ALL TESTS PASSED! System is ready for production.")
        else:
            print("❌ Some tests failed. Please review and fix before deploying.")
            print("\nFailed test suites:")
            for suite_name, results in self.test_results["tests"].items():
                if results["failed"] > 0:
                    print(f"  • {suite_name}: {results['failed']} failures")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Run production tests")
    parser.add_argument("--url", type=str, help="Base URL to test", 
                       default="http://localhost:8000")
    parser.add_argument("--env", type=str, help="Environment name",
                       default="production")
    args = parser.parse_args()
    
    print(f"🧪 Running tests against: {args.url}")
    
    runner = ProductionTestRunner(args.url, args.env)
    
    try:
        await runner.run_all_tests()
    except Exception as e:
        print(f"\n❌ Test suite failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())