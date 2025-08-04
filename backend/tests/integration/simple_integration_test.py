#!/usr/bin/env python3
"""
Simple integration test runner without pytest dependency
"""

import asyncio
import sys
import os
import json
import requests
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class SimpleIntegrationTester:
    """Simple integration tester that uses requests library"""
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.prod_url = "https://roadtrip-mvp-792001900150.us-central1.run.app"
        self.results = []
        self.errors = []
    
    def test_endpoint(self, name: str, method: str, path: str, **kwargs):
        """Test a single endpoint"""
        try:
            # Try local first, then production
            for url in [self.base_url, self.prod_url]:
                try:
                    full_url = f"{url}{path}"
                    response = getattr(requests, method.lower())(full_url, timeout=5, **kwargs)
                    
                    self.results.append({
                        "name": name,
                        "url": full_url,
                        "status": response.status_code,
                        "success": response.status_code < 500,
                        "response_time": response.elapsed.total_seconds()
                    })
                    
                    print(f"[OK] {name}: {response.status_code} ({response.elapsed.total_seconds():.2f}s)")
                    return response
                    
                except requests.ConnectionError:
                    continue
                except Exception as e:
                    self.errors.append(f"{name}: {str(e)}")
                    
            print(f"[FAIL] {name}: Failed to connect to any server")
            self.results.append({
                "name": name,
                "url": path,
                "status": 0,
                "success": False,
                "error": "Connection failed"
            })
            
        except Exception as e:
            print(f"[ERROR] {name}: {str(e)}")
            self.errors.append(f"{name}: {str(e)}")
    
    def run_tests(self):
        """Run all integration tests"""
        print("RoadTrip Integration Test Report")
        print("=" * 60)
        print(f"Testing at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. Test Backend API Health
        print("## 1. Backend API Endpoints")
        self.test_endpoint("Health Check", "GET", "/health")
        self.test_endpoint("API Documentation", "GET", "/docs")
        self.test_endpoint("OpenAPI Schema", "GET", "/openapi.json")
        
        # 2. Test Authentication Endpoints
        print("\n## 2. Authentication Flow")
        self.test_endpoint("Registration Endpoint", "POST", "/api/v1/auth/register", 
                          json={"email": "test@example.com", "password": "Test123!", "name": "Test"})
        self.test_endpoint("Login Endpoint", "POST", "/api/v1/auth/token",
                          data={"username": "test@example.com", "password": "Test123!"})
        self.test_endpoint("User Profile", "GET", "/api/v1/auth/me")
        self.test_endpoint("2FA Enable", "POST", "/api/v1/auth/2fa/enable")
        
        # 3. Test Story Generation
        print("\n## 3. AI Story Generation")
        self.test_endpoint("Generate Story", "POST", "/api/v1/ai-stories/generate",
                          json={
                              "location": {"lat": 37.7749, "lng": -122.4194},
                              "theme": "historical"
                          })
        self.test_endpoint("Featured Stories", "GET", "/api/v1/stories/featured")
        
        # 4. Test Voice Services
        print("\n## 4. Voice Services")
        self.test_endpoint("TTS Synthesis", "POST", "/api/v1/tts/synthesize",
                          json={
                              "text": "Hello world",
                              "voice_name": "en-US-Wavenet-D"
                          })
        self.test_endpoint("Voice Personalities", "GET", "/api/v1/voice-personality/personalities")
        
        # 5. Test Booking Integrations
        print("\n## 5. Booking API Integrations")
        self.test_endpoint("Search Events", "POST", "/api/v1/booking/search",
                          json={
                              "type": "events",
                              "location": {"lat": 37.7749, "lng": -122.4194}
                          })
        self.test_endpoint("Search Restaurants", "POST", "/api/v1/booking/search",
                          json={
                              "type": "restaurants",
                              "location": {"lat": 37.7749, "lng": -122.4194}
                          })
        
        # 6. Test Navigation
        print("\n## 6. Navigation Services")
        self.test_endpoint("Get Route", "POST", "/api/navigation/route",
                          json={
                              "origin": {"lat": 37.7749, "lng": -122.4194},
                              "destination": "Los Angeles, CA"
                          })
        
        # 7. Test Real-time Features
        print("\n## 7. Real-time Features")
        self.test_endpoint("Location Update", "POST", "/api/v1/location/update",
                          json={
                              "latitude": 37.7749,
                              "longitude": -122.4194,
                              "timestamp": datetime.utcnow().isoformat()
                          })
        
        # 8. Test Security Features
        print("\n## 8. Security Features")
        self.test_endpoint("CSRF Token", "GET", "/api/csrf/token")
        self.test_endpoint("Security Headers", "OPTIONS", "/api/v1/stories/generate",
                          headers={"Origin": "http://localhost:19006"})
        
        # Generate Report
        self.generate_report()
    
    def generate_report(self):
        """Generate test report"""
        print("\n" + "=" * 60)
        print("## Summary")
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r.get("success", False))
        
        print(f"Total Tests: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")
        print(f"Success Rate: {(successful/total*100):.1f}%" if total > 0 else "N/A")
        
        # Save detailed report
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "summary": {
                "total": total,
                "successful": successful,
                "failed": total - successful,
                "success_rate": (successful/total*100) if total > 0 else 0
            },
            "results": self.results,
            "errors": self.errors
        }
        
        report_path = Path(__file__).parent / "simple_integration_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_path}")
        
        # Print recommendations
        print("\n## Recommendations")
        
        if self.errors:
            print("\n### Critical Issues:")
            for error in self.errors[:5]:  # Show first 5 errors
                print(f"- {error}")
        
        # Check specific integrations
        print("\n### Integration Status:")
        
        # Backend API
        health_ok = any(r["name"] == "Health Check" and r["success"] for r in self.results)
        print(f"- Backend API: {'[OK] Running' if health_ok else '[FAIL] Not accessible'}")
        
        # AI Integration
        story_ok = any(r["name"] == "Generate Story" and r.get("status") in [200, 401] for r in self.results)
        print(f"- Google Vertex AI: {'[OK] Endpoint available' if story_ok else '[FAIL] Check configuration'}")
        
        # Voice Services
        tts_ok = any(r["name"] == "TTS Synthesis" and r.get("status") in [200, 401] for r in self.results)
        print(f"- Google Cloud TTS: {'[OK] Endpoint available' if tts_ok else '[FAIL] Check configuration'}")
        
        # Booking APIs
        booking_ok = any("Search" in r["name"] and r.get("status") in [200, 401] for r in self.results)
        print(f"- Booking APIs: {'[OK] Endpoints available' if booking_ok else '[FAIL] Check configuration'}")
        
        # Database (inferred from auth endpoints)
        db_ok = any(r["name"] == "Registration Endpoint" and r.get("status") in [200, 400, 422] for r in self.results)
        print(f"- PostgreSQL Database: {'[OK] Likely working' if db_ok else '[FAIL] Check connection'}")
        
        # Security
        csrf_ok = any(r["name"] == "CSRF Token" and r["success"] for r in self.results)
        print(f"- Security Middleware: {'[OK] Active' if csrf_ok else '[FAIL] Check configuration'}")
        
        print("\n### Missing Error Handling:")
        print("- Implement retry logic for external API calls")
        print("- Add circuit breakers for booking APIs")
        print("- Implement fallback responses for AI service failures")
        print("- Add connection pooling for database operations")
        print("- Implement request caching for expensive operations")


if __name__ == "__main__":
    tester = SimpleIntegrationTester()
    tester.run_tests()