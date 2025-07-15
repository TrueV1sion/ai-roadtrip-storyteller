#!/usr/bin/env python3
"""
MVP Integration Test Suite
Automated tests for backend API endpoints
"""

import asyncio
import time
import json
import os
from typing import Dict, Any, List
import aiohttp
from datetime import datetime

# Configuration
API_BASE_URL = os.getenv("API_URL", "http://localhost:8000")
TEST_TIMEOUT = 30  # seconds

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "tests": []
}

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

class MVPIntegrationTester:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_health_check(self) -> Dict[str, Any]:
        """Test: Health check endpoint"""
        test_name = "Health Check"
        print(f"\n🧪 Testing: {test_name}")
        
        try:
            start_time = time.time()
            async with self.session.get(
                f"{self.base_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                elapsed = time.time() - start_time
                
                assert response.status == 200, f"Expected 200, got {response.status}"
                data = await response.json()
                assert data.get("status") == "healthy", "Service not healthy"
                
                print(f"{GREEN}✓ Passed{RESET} - {elapsed:.2f}s")
                return {
                    "name": test_name,
                    "passed": True,
                    "duration": elapsed,
                    "details": data
                }
                
        except Exception as e:
            print(f"{RED}✗ Failed{RESET} - {str(e)}")
            return {
                "name": test_name,
                "passed": False,
                "error": str(e)
            }
    
    async def test_voice_navigation(self) -> Dict[str, Any]:
        """Test: Voice navigation request"""
        test_name = "Voice Navigation"
        print(f"\n🧪 Testing: {test_name}")
        
        try:
            payload = {
                "user_input": "Navigate to Golden Gate Bridge",
                "context": {
                    "origin": "37.7749,-122.4194",  # San Francisco
                    "current_location": {
                        "lat": 37.7749,
                        "lng": -122.4194
                    }
                }
            }
            
            start_time = time.time()
            async with self.session.post(
                f"{self.base_url}/api/voice-assistant/interact",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT)
            ) as response:
                elapsed = time.time() - start_time
                
                assert response.status == 200, f"Expected 200, got {response.status}"
                data = await response.json()
                
                # Validate response
                assert "text" in data or "message" in data, "No text in response"
                assert elapsed < 3.0, f"Response too slow: {elapsed:.2f}s (target <3s)"
                
                # Check for story content
                text = data.get("text", data.get("message", ""))
                assert len(text) > 50, "Response too short"
                assert "golden gate" in text.lower() or "bridge" in text.lower(), \
                    "Response not relevant to query"
                
                print(f"{GREEN}✓ Passed{RESET} - {elapsed:.2f}s")
                print(f"  Response preview: {text[:100]}...")
                
                return {
                    "name": test_name,
                    "passed": True,
                    "duration": elapsed,
                    "response_length": len(text),
                    "has_audio": "audio_url" in data
                }
                
        except Exception as e:
            print(f"{RED}✗ Failed{RESET} - {str(e)}")
            return {
                "name": test_name,
                "passed": False,
                "error": str(e)
            }
    
    async def test_story_request(self) -> Dict[str, Any]:
        """Test: Story generation request"""
        test_name = "Story Generation"
        print(f"\n🧪 Testing: {test_name}")
        
        try:
            payload = {
                "user_input": "Tell me about the history of this area",
                "context": {
                    "current_location": {
                        "lat": 40.7128,
                        "lng": -74.0060,
                        "name": "New York City"
                    }
                }
            }
            
            start_time = time.time()
            async with self.session.post(
                f"{self.base_url}/api/voice-assistant/interact",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT)
            ) as response:
                elapsed = time.time() - start_time
                
                assert response.status == 200, f"Expected 200, got {response.status}"
                data = await response.json()
                
                # Validate story response
                text = data.get("text", data.get("message", ""))
                assert len(text) > 100, "Story too short"
                assert elapsed < 3.0, f"Response too slow: {elapsed:.2f}s"
                
                # Check for historical content
                history_keywords = ["history", "founded", "built", "year", "century"]
                has_history = any(keyword in text.lower() for keyword in history_keywords)
                assert has_history, "No historical content in response"
                
                print(f"{GREEN}✓ Passed{RESET} - {elapsed:.2f}s")
                print(f"  Story length: {len(text)} characters")
                
                return {
                    "name": test_name,
                    "passed": True,
                    "duration": elapsed,
                    "story_length": len(text),
                    "has_audio": "audio_url" in data
                }
                
        except Exception as e:
            print(f"{RED}✗ Failed{RESET} - {str(e)}")
            return {
                "name": test_name,
                "passed": False,
                "error": str(e)
            }
    
    async def test_error_handling(self) -> Dict[str, Any]:
        """Test: Error handling with invalid input"""
        test_name = "Error Handling"
        print(f"\n🧪 Testing: {test_name}")
        
        try:
            # Test with empty input
            payload = {
                "user_input": "",
                "context": {}
            }
            
            async with self.session.post(
                f"{self.base_url}/api/voice-assistant/interact",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT)
            ) as response:
                # Should handle gracefully (200 or 400)
                assert response.status in [200, 400], \
                    f"Unexpected status: {response.status}"
                
                if response.status == 200:
                    data = await response.json()
                    text = data.get("text", data.get("message", ""))
                    assert len(text) > 0, "Empty response"
                
                print(f"{GREEN}✓ Passed{RESET} - Handled empty input gracefully")
                
                return {
                    "name": test_name,
                    "passed": True,
                    "status_code": response.status
                }
                
        except Exception as e:
            print(f"{RED}✗ Failed{RESET} - {str(e)}")
            return {
                "name": test_name,
                "passed": False,
                "error": str(e)
            }
    
    async def test_concurrent_requests(self) -> Dict[str, Any]:
        """Test: Concurrent request handling"""
        test_name = "Concurrent Requests"
        print(f"\n🧪 Testing: {test_name}")
        
        try:
            # Create 5 concurrent requests
            requests = [
                {
                    "user_input": f"Tell me about location {i}",
                    "context": {
                        "current_location": {
                            "lat": 37.7749 + i * 0.01,
                            "lng": -122.4194
                        }
                    }
                }
                for i in range(5)
            ]
            
            start_time = time.time()
            
            # Send all requests concurrently
            tasks = []
            for req in requests:
                task = self.session.post(
                    f"{self.base_url}/api/voice-assistant/interact",
                    json=req,
                    timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT)
                )
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            elapsed = time.time() - start_time
            
            # Check results
            successful = 0
            for resp in responses:
                if not isinstance(resp, Exception) and resp.status == 200:
                    successful += 1
            
            success_rate = successful / len(requests) * 100
            assert success_rate >= 80, f"Low success rate: {success_rate}%"
            assert elapsed < 5.0, f"Too slow for concurrent requests: {elapsed:.2f}s"
            
            print(f"{GREEN}✓ Passed{RESET} - {successful}/{len(requests)} succeeded in {elapsed:.2f}s")
            
            return {
                "name": test_name,
                "passed": True,
                "duration": elapsed,
                "success_rate": success_rate,
                "total_requests": len(requests)
            }
            
        except Exception as e:
            print(f"{RED}✗ Failed{RESET} - {str(e)}")
            return {
                "name": test_name,
                "passed": False,
                "error": str(e)
            }
    
    async def test_response_times(self) -> Dict[str, Any]:
        """Test: Response time consistency"""
        test_name = "Response Time Consistency"
        print(f"\n🧪 Testing: {test_name}")
        
        try:
            response_times = []
            
            # Make 10 requests and measure times
            for i in range(10):
                payload = {
                    "user_input": "What's nearby?",
                    "context": {
                        "current_location": {
                            "lat": 37.7749,
                            "lng": -122.4194
                        }
                    }
                }
                
                start_time = time.time()
                async with self.session.post(
                    f"{self.base_url}/api/voice-assistant/interact",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=TEST_TIMEOUT)
                ) as response:
                    elapsed = time.time() - start_time
                    
                    if response.status == 200:
                        response_times.append(elapsed)
                        print(f"  Request {i+1}: {elapsed:.2f}s")
            
            # Calculate statistics
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            min_time = min(response_times)
            
            # All should be under 3 seconds
            assert max_time < 3.0, f"Max time too high: {max_time:.2f}s"
            assert avg_time < 2.0, f"Average time too high: {avg_time:.2f}s"
            
            print(f"{GREEN}✓ Passed{RESET}")
            print(f"  Average: {avg_time:.2f}s, Min: {min_time:.2f}s, Max: {max_time:.2f}s")
            
            return {
                "name": test_name,
                "passed": True,
                "avg_time": avg_time,
                "min_time": min_time,
                "max_time": max_time,
                "samples": len(response_times)
            }
            
        except Exception as e:
            print(f"{RED}✗ Failed{RESET} - {str(e)}")
            return {
                "name": test_name,
                "passed": False,
                "error": str(e)
            }

async def run_integration_tests(api_url: str):
    """Run all integration tests"""
    print(f"🚗 AI Road Trip MVP Integration Tests")
    print(f"=====================================")
    print(f"API URL: {api_url}")
    print(f"Timeout: {TEST_TIMEOUT}s")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    async with MVPIntegrationTester(api_url) as tester:
        # Run all tests
        tests = [
            tester.test_health_check(),
            tester.test_voice_navigation(),
            tester.test_story_request(),
            tester.test_error_handling(),
            tester.test_concurrent_requests(),
            tester.test_response_times(),
        ]
        
        results = []
        for test in tests:
            result = await test
            results.append(result)
            
            # Update counters
            if result.get("passed"):
                test_results["passed"] += 1
            else:
                test_results["failed"] += 1
            
            test_results["tests"].append(result)
            
            # Small delay between tests
            await asyncio.sleep(0.5)
    
    # Print summary
    print(f"\n📊 Test Summary")
    print(f"===============")
    print(f"Total Tests: {test_results['passed'] + test_results['failed']}")
    print(f"{GREEN}Passed: {test_results['passed']}{RESET}")
    print(f"{RED}Failed: {test_results['failed']}{RESET}")
    
    # Calculate success rate
    total = test_results['passed'] + test_results['failed']
    if total > 0:
        success_rate = test_results['passed'] / total * 100
        print(f"Success Rate: {success_rate:.1f}%")
        
        if success_rate == 100:
            print(f"\n{GREEN}✅ All tests passed! Ready for beta deployment.{RESET}")
        elif success_rate >= 80:
            print(f"\n{YELLOW}⚠️  Most tests passed. Review failures before deployment.{RESET}")
        else:
            print(f"\n{RED}❌ Too many failures. Fix issues before deployment.{RESET}")
    
    # Save results
    with open("integration_test_results.json", "w") as f:
        json.dump(test_results, f, indent=2)
        print(f"\nResults saved to: integration_test_results.json")
    
    return test_results['failed'] == 0

def main():
    """Main entry point"""
    import sys
    
    # Get API URL from command line or environment
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
    else:
        api_url = os.getenv("API_URL", "http://localhost:8000")
    
    # Run tests
    success = asyncio.run(run_integration_tests(api_url))
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()