#!/usr/bin/env python3
"""
API Configuration Validation Script

This script validates all API configurations and tests basic connectivity
to ensure all integrations are properly set up.
"""

import os
import sys
import json
import requests
from typing import Dict, List, Tuple, Optional
from urllib.parse import urljoin
import time
from datetime import datetime
import google.auth
from google.auth.transport.requests import Request
from google.oauth2 import service_account

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class APIValidator:
    """Validates API configurations and connectivity"""
    
    def __init__(self):
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }
        self.required_env_vars = self._get_required_env_vars()
    
    def _get_required_env_vars(self) -> Dict[str, List[str]]:
        """Define required environment variables by category"""
        return {
            "Google Cloud": [
                "GOOGLE_MAPS_API_KEY",
                "GOOGLE_APPLICATION_CREDENTIALS",
                "VERTEX_AI_PROJECT_ID",
                "VERTEX_AI_LOCATION"
            ],
            "Booking APIs": [
                "OPENTABLE_CLIENT_ID",
                "OPENTABLE_CLIENT_SECRET",
                "YELP_API_KEY",
                "TICKETMASTER_API_KEY",
                "VIATOR_API_KEY"
            ],
            "Entertainment": [
                "SPOTIFY_CLIENT_ID",
                "SPOTIFY_CLIENT_SECRET"
            ],
            "Weather & Traffic": [
                "OPENWEATHER_API_KEY",
                "HERE_API_KEY"
            ]
        }
    
    def validate_env_vars(self) -> None:
        """Check if all required environment variables are set"""
        print("\n🔍 Checking Environment Variables...")
        
        for category, vars in self.required_env_vars.items():
            print(f"\n{category}:")
            for var in vars:
                value = os.getenv(var)
                if value:
                    if value.startswith("your_") or value == "":
                        self._add_warning(f"{var} appears to be a placeholder value")
                        print(f"  ⚠️  {var}: Placeholder value detected")
                    else:
                        self._add_success(f"{var} is set")
                        print(f"  ✅ {var}: Set")
                else:
                    self._add_failure(f"{var} is not set")
                    print(f"  ❌ {var}: Not set")
    
    def validate_google_maps(self) -> None:
        """Test Google Maps API connectivity"""
        print("\n🗺️  Testing Google Maps API...")
        
        api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        if not api_key or api_key.startswith("your_"):
            self._add_failure("Google Maps API key not configured")
            return
        
        # Test Geocoding API
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": "1600 Amphitheatre Parkway, Mountain View, CA",
            "key": api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if data.get("status") == "OK":
                self._add_success("Google Maps Geocoding API is working")
                print("  ✅ Geocoding API: Connected")
            elif data.get("status") == "REQUEST_DENIED":
                self._add_failure(f"Google Maps API access denied: {data.get('error_message', 'Unknown error')}")
                print(f"  ❌ API Error: {data.get('error_message', 'Unknown error')}")
            else:
                self._add_failure(f"Google Maps API error: {data.get('status')}")
                print(f"  ❌ API Status: {data.get('status')}")
        except Exception as e:
            self._add_failure(f"Google Maps API connection failed: {str(e)}")
            print(f"  ❌ Connection Error: {str(e)}")
    
    def validate_google_cloud_auth(self) -> None:
        """Test Google Cloud authentication"""
        print("\n☁️  Testing Google Cloud Authentication...")
        
        creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if not creds_path:
            self._add_failure("GOOGLE_APPLICATION_CREDENTIALS not set")
            return
        
        if not os.path.exists(creds_path):
            self._add_failure(f"Service account key file not found: {creds_path}")
            print(f"  ❌ Key file not found: {creds_path}")
            return
        
        try:
            credentials = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            
            # Test authentication
            auth_req = Request()
            credentials.refresh(auth_req)
            
            self._add_success("Google Cloud authentication successful")
            print("  ✅ Authentication: Success")
            
            # Check project ID
            project_id = os.getenv("VERTEX_AI_PROJECT_ID")
            if project_id:
                print(f"  ✅ Project ID: {project_id}")
            else:
                self._add_warning("VERTEX_AI_PROJECT_ID not set")
                print("  ⚠️  Project ID: Not set")
                
        except Exception as e:
            self._add_failure(f"Google Cloud authentication failed: {str(e)}")
            print(f"  ❌ Authentication Error: {str(e)}")
    
    def validate_opentable(self) -> None:
        """Test OpenTable API connectivity"""
        print("\n🍽️  Testing OpenTable API...")
        
        client_id = os.getenv("OPENTABLE_CLIENT_ID")
        client_secret = os.getenv("OPENTABLE_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            self._add_warning("OpenTable credentials not configured (optional)")
            print("  ⚠️  Credentials not set (optional API)")
            return
        
        if client_id.startswith("your_"):
            self._add_warning("OpenTable credentials appear to be placeholders")
            print("  ⚠️  Placeholder credentials detected")
            return
        
        # Note: Actual OpenTable API testing would require valid credentials
        # This is a placeholder for the actual implementation
        self._add_success("OpenTable credentials configured")
        print("  ✅ Credentials: Configured")
    
    def validate_spotify(self) -> None:
        """Test Spotify API connectivity"""
        print("\n🎵 Testing Spotify API...")
        
        client_id = os.getenv("SPOTIFY_CLIENT_ID")
        client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        
        if not client_id or not client_secret:
            self._add_warning("Spotify credentials not configured (optional)")
            print("  ⚠️  Credentials not set (optional API)")
            return
        
        # Test client credentials flow
        auth_url = "https://accounts.spotify.com/api/token"
        auth_data = {
            "grant_type": "client_credentials"
        }
        
        try:
            response = requests.post(
                auth_url,
                auth=(client_id, client_secret),
                data=auth_data,
                timeout=10
            )
            
            if response.status_code == 200:
                self._add_success("Spotify authentication successful")
                print("  ✅ Authentication: Success")
            else:
                self._add_failure(f"Spotify authentication failed: {response.status_code}")
                print(f"  ❌ Authentication failed: {response.status_code}")
        except Exception as e:
            self._add_failure(f"Spotify API connection failed: {str(e)}")
            print(f"  ❌ Connection Error: {str(e)}")
    
    def validate_openweather(self) -> None:
        """Test OpenWeatherMap API connectivity"""
        print("\n🌤️  Testing OpenWeatherMap API...")
        
        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key or api_key.startswith("your_"):
            self._add_warning("OpenWeatherMap API key not configured (optional)")
            print("  ⚠️  API key not set (optional API)")
            return
        
        # Test weather endpoint
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": "San Francisco",
            "appid": api_key,
            "units": "imperial"
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if response.status_code == 200:
                self._add_success("OpenWeatherMap API is working")
                print("  ✅ Weather API: Connected")
                print(f"     Current temp in SF: {data['main']['temp']}°F")
            elif response.status_code == 401:
                self._add_failure("OpenWeatherMap API key is invalid")
                print("  ❌ Invalid API key")
            else:
                self._add_failure(f"OpenWeatherMap API error: {data.get('message', 'Unknown error')}")
                print(f"  ❌ API Error: {data.get('message', 'Unknown error')}")
        except Exception as e:
            self._add_failure(f"OpenWeatherMap API connection failed: {str(e)}")
            print(f"  ❌ Connection Error: {str(e)}")
    
    def check_network_connectivity(self) -> None:
        """Basic network connectivity check"""
        print("\n🌐 Checking Network Connectivity...")
        
        test_urls = [
            ("Google", "https://www.google.com"),
            ("Google Cloud", "https://cloud.google.com"),
            ("OpenTable", "https://www.opentable.com"),
            ("Spotify", "https://api.spotify.com")
        ]
        
        for name, url in test_urls:
            try:
                response = requests.head(url, timeout=5)
                if response.status_code < 400:
                    print(f"  ✅ {name}: Reachable")
                else:
                    print(f"  ⚠️  {name}: HTTP {response.status_code}")
            except Exception as e:
                print(f"  ❌ {name}: Unreachable - {type(e).__name__}")
    
    def _add_success(self, message: str) -> None:
        """Add a success result"""
        self.results["passed"].append(message)
    
    def _add_failure(self, message: str) -> None:
        """Add a failure result"""
        self.results["failed"].append(message)
    
    def _add_warning(self, message: str) -> None:
        """Add a warning result"""
        self.results["warnings"].append(message)
    
    def generate_report(self) -> None:
        """Generate and display the validation report"""
        print("\n" + "="*60)
        print("📊 VALIDATION REPORT")
        print("="*60)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n✅ Passed: {len(self.results['passed'])}")
        print(f"❌ Failed: {len(self.results['failed'])}")
        print(f"⚠️  Warnings: {len(self.results['warnings'])}")
        
        if self.results['failed']:
            print("\n❌ FAILURES:")
            for failure in self.results['failed']:
                print(f"  • {failure}")
        
        if self.results['warnings']:
            print("\n⚠️  WARNINGS:")
            for warning in self.results['warnings']:
                print(f"  • {warning}")
        
        if not self.results['failed']:
            print("\n🎉 All critical validations passed!")
        else:
            print("\n⚠️  Please fix the failures before proceeding.")
        
        # Save report to file
        report_path = "api_validation_report.json"
        with open(report_path, "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": self.results
            }, f, indent=2)
        print(f"\n📄 Detailed report saved to: {report_path}")


def main():
    """Main validation routine"""
    print("🚀 AI Road Trip Storyteller - API Configuration Validator")
    print("="*60)
    
    # Load .env file if it exists
    env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_file):
        print(f"📄 Loading environment from: {env_file}")
        from dotenv import load_dotenv
        load_dotenv(env_file)
    else:
        print("⚠️  No .env file found, using system environment variables")
    
    validator = APIValidator()
    
    # Run validations
    validator.check_network_connectivity()
    validator.validate_env_vars()
    validator.validate_google_maps()
    validator.validate_google_cloud_auth()
    validator.validate_opentable()
    validator.validate_spotify()
    validator.validate_openweather()
    
    # Generate report
    validator.generate_report()
    
    # Exit with appropriate code
    sys.exit(1 if validator.results['failed'] else 0)


if __name__ == "__main__":
    main()