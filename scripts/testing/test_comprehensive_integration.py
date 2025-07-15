#!/usr/bin/env python3
"""
Comprehensive Integration Test Suite for AI Road Trip Storyteller
Tests all critical components and user flows
"""

import asyncio
import sys
import os
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import httpx
from pathlib import Path

# Add the backend directory to the Python path
sys.path.append(str(Path(__file__).parent / "backend"))

# Test configuration
TEST_CONFIG = {
    "base_url": "http://localhost:8000",
    "timeout": 30.0,
    "test_user": {
        "email": "test@roadtrip.example",
        "password": "test_password_123",
        "name": "Test User"
    },
    "test_location": {
        "latitude": 37.7749,
        "longitude": -122.4194,
        "name": "San Francisco, CA"
    }
}


class IntegrationTestSuite:
    """Comprehensive integration test suite."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=TEST_CONFIG["base_url"],
            timeout=TEST_CONFIG["timeout"]
        )
        self.test_results = []
        self.auth_token = None
        self.test_user_id = None
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all integration tests."""
        print("🧪 Starting Comprehensive Integration Test Suite")
        print("=" * 60)
        
        start_time = time.time()
        
        # Test categories
        test_categories = [
            ("Infrastructure Tests", self._run_infrastructure_tests),
            ("Authentication Tests", self._run_auth_tests),
            ("Core API Tests", self._run_core_api_tests),
            ("AI Integration Tests", self._run_ai_integration_tests),
            ("Database Tests", self._run_database_tests),
            ("Third-party API Tests", self._run_third_party_api_tests),
            ("End-to-End User Journey Tests", self._run_e2e_tests),
        ]
        
        category_results = {}
        
        for category_name, test_function in test_categories:
            print(f"\n📋 Running {category_name}")
            print("-" * 40)
            
            try:
                results = await test_function()
                category_results[category_name] = results
                
                passed = sum(1 for r in results if r.get("status") == "passed")
                total = len(results)
                print(f"✅ {category_name}: {passed}/{total} tests passed")
                
            except Exception as e:
                print(f"❌ {category_name} failed: {e}")
                category_results[category_name] = [{"name": "Category Error", "status": "failed", "error": str(e)}]
        
        # Generate summary report
        total_time = time.time() - start_time
        summary = await self._generate_summary_report(category_results, total_time)
        
        await self.client.aclose()
        return summary
    
    async def _run_infrastructure_tests(self) -> List[Dict[str, Any]]:
        """Test basic infrastructure components."""
        tests = []
        
        # Health check
        try:
            response = await self.client.get("/health")
            tests.append({
                "name": "Health Check",
                "status": "passed" if response.status_code == 200 else "failed",
                "response_time": getattr(response, '_elapsed', 0),
                "details": response.json() if response.status_code == 200 else response.text
            })
        except Exception as e:
            tests.append({"name": "Health Check", "status": "failed", "error": str(e)})
        
        # Detailed health check
        try:
            response = await self.client.get("/health/detailed")
            tests.append({
                "name": "Detailed Health Check",
                "status": "passed" if response.status_code == 200 else "failed",
                "details": response.json() if response.status_code == 200 else response.text
            })
        except Exception as e:
            tests.append({"name": "Detailed Health Check", "status": "failed", "error": str(e)})
        
        # Database health
        try:
            response = await self.client.get("/api/health/database")
            tests.append({
                "name": "Database Health",
                "status": "passed" if response.status_code == 200 else "failed",
                "details": response.json() if response.status_code == 200 else response.text
            })
        except Exception as e:
            tests.append({"name": "Database Health", "status": "failed", "error": str(e)})
        
        # API documentation
        try:
            response = await self.client.get("/docs")
            tests.append({
                "name": "API Documentation",
                "status": "passed" if response.status_code == 200 else "failed"
            })
        except Exception as e:
            tests.append({"name": "API Documentation", "status": "failed", "error": str(e)})
        
        return tests
    
    async def _run_auth_tests(self) -> List[Dict[str, Any]]:
        """Test authentication and authorization."""
        tests = []
        
        # User registration
        try:
            user_data = {
                "email": TEST_CONFIG["test_user"]["email"],
                "password": TEST_CONFIG["test_user"]["password"],
                "full_name": TEST_CONFIG["test_user"]["name"]
            }
            
            response = await self.client.post("/api/auth/register", json=user_data)
            
            if response.status_code in [200, 201, 409]:  # 409 if user already exists
                tests.append({"name": "User Registration", "status": "passed"})
                if response.status_code in [200, 201]:
                    self.test_user_id = response.json().get("id")
            else:
                tests.append({"name": "User Registration", "status": "failed", "details": response.text})
        except Exception as e:
            tests.append({"name": "User Registration", "status": "failed", "error": str(e)})
        
        # User login
        try:
            login_data = {
                "username": TEST_CONFIG["test_user"]["email"],
                "password": TEST_CONFIG["test_user"]["password"]
            }
            
            response = await self.client.post("/api/auth/login", data=login_data)
            
            if response.status_code == 200:
                token_data = response.json()
                self.auth_token = token_data.get("access_token")
                self.client.headers["Authorization"] = f"Bearer {self.auth_token}"
                tests.append({"name": "User Login", "status": "passed"})
            else:
                tests.append({"name": "User Login", "status": "failed", "details": response.text})
        except Exception as e:
            tests.append({"name": "User Login", "status": "failed", "error": str(e)})
        
        # Protected endpoint access
        try:
            response = await self.client.get("/api/users/me")
            tests.append({
                "name": "Protected Endpoint Access",
                "status": "passed" if response.status_code == 200 else "failed",
                "details": response.json() if response.status_code == 200 else response.text
            })
        except Exception as e:
            tests.append({"name": "Protected Endpoint Access", "status": "failed", "error": str(e)})
        
        return tests
    
    async def _run_core_api_tests(self) -> List[Dict[str, Any]]:
        """Test core API functionality."""
        tests = []
        
        # Story generation
        try:
            story_request = {
                "location": TEST_CONFIG["test_location"],
                "interests": ["history", "culture"],
                "conversation_id": "test_conversation_001"
            }
            
            response = await self.client.post("/api/story/generate", json=story_request)
            tests.append({
                "name": "Story Generation",
                "status": "passed" if response.status_code == 200 else "failed",
                "details": response.json() if response.status_code == 200 else response.text
            })
        except Exception as e:
            tests.append({"name": "Story Generation", "status": "failed", "error": str(e)})
        
        # Personalized story
        try:
            personalized_request = {
                "location": TEST_CONFIG["test_location"],
                "interests": ["adventure", "nature"],
                "user_preferences": {
                    "storytelling_style": "adventure",
                    "content_length": "medium"
                }
            }
            
            response = await self.client.post("/api/personalized-story", json=personalized_request)
            tests.append({
                "name": "Personalized Story Generation",
                "status": "passed" if response.status_code == 200 else "failed",
                "details": response.json() if response.status_code == 200 else response.text
            })
        except Exception as e:
            tests.append({"name": "Personalized Story Generation", "status": "failed", "error": str(e)})
        
        # Voice personality selection
        try:
            response = await self.client.get("/api/voice-personalities")
            tests.append({
                "name": "Voice Personality List",
                "status": "passed" if response.status_code == 200 else "failed",
                "details": len(response.json()) if response.status_code == 200 else response.text
            })
        except Exception as e:
            tests.append({"name": "Voice Personality List", "status": "failed", "error": str(e)})
        
        # TTS generation
        try:
            tts_request = {
                "text": "This is a test of the text-to-speech system.",
                "voice_name": "en-US-Studio-O"
            }
            
            response = await self.client.post("/api/tts/synthesize", json=tts_request)
            tests.append({
                "name": "Text-to-Speech Generation",
                "status": "passed" if response.status_code in [200, 202] else "failed",
                "details": response.json() if response.status_code in [200, 202] else response.text
            })
        except Exception as e:
            tests.append({"name": "Text-to-Speech Generation", "status": "failed", "error": str(e)})
        
        return tests
    
    async def _run_ai_integration_tests(self) -> List[Dict[str, Any]]:
        """Test AI service integrations."""
        tests = []
        
        # Voice assistant interaction
        try:
            voice_request = {
                "user_input": "Tell me something interesting about this area",
                "context": {
                    "location": TEST_CONFIG["test_location"],
                    "time_of_day": "afternoon"
                }
            }
            
            response = await self.client.post("/api/voice-assistant/interact", json=voice_request)
            tests.append({
                "name": "Voice Assistant Interaction",
                "status": "passed" if response.status_code == 200 else "failed",
                "details": response.json() if response.status_code == 200 else response.text
            })
        except Exception as e:
            tests.append({"name": "Voice Assistant Interaction", "status": "failed", "error": str(e)})
        
        # Event journey detection
        try:
            event_request = {
                "destination": "Disneyland, Anaheim, CA",
                "travel_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "party_size": 4
            }
            
            response = await self.client.post("/api/event-journeys/detect", json=event_request)
            tests.append({
                "name": "Event Journey Detection",
                "status": "passed" if response.status_code == 200 else "failed",
                "details": response.json() if response.status_code == 200 else response.text
            })
        except Exception as e:
            tests.append({"name": "Event Journey Detection", "status": "failed", "error": str(e)})
        
        return tests
    
    async def _run_database_tests(self) -> List[Dict[str, Any]]:
        """Test database operations."""
        tests = []
        
        # Database query test
        try:
            response = await self.client.get("/api/health/database/test-query")
            tests.append({
                "name": "Database Query Test",
                "status": "passed" if response.status_code == 200 else "failed",
                "details": response.json() if response.status_code == 200 else response.text
            })
        except Exception as e:
            tests.append({"name": "Database Query Test", "status": "failed", "error": str(e)})
        
        # Migration status
        try:
            response = await self.client.get("/api/health/database/migrations")
            tests.append({
                "name": "Database Migration Status",
                "status": "passed" if response.status_code == 200 else "failed",
                "details": response.json() if response.status_code == 200 else response.text
            })
        except Exception as e:
            tests.append({"name": "Database Migration Status", "status": "failed", "error": str(e)})
        
        return tests
    
    async def _run_third_party_api_tests(self) -> List[Dict[str, Any]]:
        """Test third-party API integrations."""
        tests = []
        
        # Directions API
        try:
            directions_request = {
                "origin": "San Francisco, CA",
                "destination": "Los Angeles, CA",
                "travel_mode": "driving"
            }
            
            response = await self.client.post("/api/directions", json=directions_request)
            tests.append({
                "name": "Google Directions API",
                "status": "passed" if response.status_code == 200 else "failed",
                "details": response.json() if response.status_code == 200 else response.text
            })
        except Exception as e:
            tests.append({"name": "Google Directions API", "status": "failed", "error": str(e)})
        
        # Booking search (mock mode)
        try:
            booking_request = {
                "location": TEST_CONFIG["test_location"],
                "booking_type": "restaurant",
                "party_size": 2,
                "date": (datetime.now() + timedelta(days=1)).isoformat()
            }
            
            response = await self.client.post("/api/bookings/search", json=booking_request)
            tests.append({
                "name": "Booking Search API",
                "status": "passed" if response.status_code in [200, 202] else "failed",
                "details": response.json() if response.status_code in [200, 202] else response.text
            })
        except Exception as e:
            tests.append({"name": "Booking Search API", "status": "failed", "error": str(e)})
        
        return tests
    
    async def _run_e2e_tests(self) -> List[Dict[str, Any]]:
        """Test complete end-to-end user journeys."""
        tests = []
        
        # Complete journey simulation
        try:
            # Step 1: Plan a journey
            journey_request = {
                "origin": "San Francisco, CA",
                "destination": "Monterey, CA",
                "interests": ["nature", "scenic_drives"],
                "travel_date": (datetime.now() + timedelta(days=3)).isoformat()
            }
            
            # Step 2: Get personalized stories for the route
            story_request = {
                "location": {"latitude": 36.6002, "longitude": -121.8947},  # Monterey
                "interests": journey_request["interests"],
                "user_preferences": {"storytelling_style": "entertaining"}
            }
            
            story_response = await self.client.post("/api/personalized-story", json=story_request)
            
            # Step 3: Generate TTS for the story
            if story_response.status_code == 200:
                story_data = story_response.json()
                tts_request = {
                    "text": story_data.get("story", "Welcome to your journey!"),
                    "voice_name": "en-US-Studio-O"
                }
                
                tts_response = await self.client.post("/api/tts/synthesize", json=tts_request)
                
                if tts_response.status_code in [200, 202]:
                    tests.append({"name": "Complete Journey E2E", "status": "passed", "details": "Full journey flow completed successfully"})
                else:
                    tests.append({"name": "Complete Journey E2E", "status": "failed", "details": "TTS generation failed"})
            else:
                tests.append({"name": "Complete Journey E2E", "status": "failed", "details": "Story generation failed"})
                
        except Exception as e:
            tests.append({"name": "Complete Journey E2E", "status": "failed", "error": str(e)})
        
        return tests
    
    async def _generate_summary_report(self, category_results: Dict[str, List], total_time: float) -> Dict[str, Any]:
        """Generate a comprehensive test summary report."""
        all_tests = []
        for category, tests in category_results.items():
            for test in tests:
                test["category"] = category
                all_tests.append(test)
        
        passed_tests = [t for t in all_tests if t.get("status") == "passed"]
        failed_tests = [t for t in all_tests if t.get("status") == "failed"]
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_time_seconds": round(total_time, 2),
            "summary": {
                "total_tests": len(all_tests),
                "passed": len(passed_tests),
                "failed": len(failed_tests),
                "success_rate": round(len(passed_tests) / len(all_tests) * 100, 1) if all_tests else 0
            },
            "categories": {
                category: {
                    "total": len(tests),
                    "passed": len([t for t in tests if t.get("status") == "passed"]),
                    "failed": len([t for t in tests if t.get("status") == "failed"])
                }
                for category, tests in category_results.items()
            },
            "failed_tests": [
                {
                    "name": test["name"],
                    "category": test["category"],
                    "error": test.get("error", test.get("details", "Unknown error"))
                }
                for test in failed_tests
            ],
            "all_results": category_results
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY REPORT")
        print("=" * 60)
        print(f"Total Tests: {summary['summary']['total_tests']}")
        print(f"Passed: {summary['summary']['passed']}")
        print(f"Failed: {summary['summary']['failed']}")
        print(f"Success Rate: {summary['summary']['success_rate']}%")
        print(f"Total Time: {summary['total_time_seconds']} seconds")
        
        if failed_tests:
            print("\n❌ FAILED TESTS:")
            for test in summary["failed_tests"]:
                print(f"  - {test['category']}: {test['name']}")
                print(f"    Error: {test['error']}")
        
        return summary


async def main():
    """Run the comprehensive integration test suite."""
    suite = IntegrationTestSuite()
    
    try:
        results = await suite.run_all_tests()
        
        # Save results to file
        results_file = Path("test_results_comprehensive.json")
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Detailed results saved to: {results_file}")
        
        # Exit with appropriate code
        success_rate = results["summary"]["success_rate"]
        if success_rate >= 80:
            print("\n🎉 Integration tests PASSED!")
            return 0
        else:
            print(f"\n❌ Integration tests FAILED (only {success_rate}% passed)")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)