#!/usr/bin/env python3
"""
Automated API Setup Script for AI Road Trip Storyteller
"""

import os
import sys
import json
import requests
import subprocess
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@dataclass
class APIConfig:
    name: str
    required: bool
    env_vars: List[str]
    test_endpoint: Optional[str] = None
    setup_url: Optional[str] = None
    description: str = ""

class APISetupWizard:
    def __init__(self):
        self.apis = [
            APIConfig(
                name="Google Maps",
                required=True,
                env_vars=["GOOGLE_MAPS_API_KEY"],
                test_endpoint="https://maps.googleapis.com/maps/api/directions/json",
                setup_url="https://console.cloud.google.com/apis/credentials",
                description="Required for navigation, directions, and location services"
            ),
            APIConfig(
                name="Google Vertex AI",
                required=True,
                env_vars=["GOOGLE_APPLICATION_CREDENTIALS", "VERTEX_AI_PROJECT_ID", "VERTEX_AI_LOCATION"],
                setup_url="https://console.cloud.google.com/vertex-ai",
                description="Powers AI storytelling and content generation"
            ),
            APIConfig(
                name="Google Cloud TTS/STT",
                required=True,
                env_vars=["GOOGLE_APPLICATION_CREDENTIALS"],
                setup_url="https://console.cloud.google.com/apis/library/texttospeech.googleapis.com",
                description="Enables voice interaction and audio narration"
            ),
            APIConfig(
                name="OpenTable",
                required=False,
                env_vars=["OPENTABLE_API_KEY"],
                setup_url="https://platform.opentable.com/",
                description="Restaurant reservations and dining recommendations"
            ),
            APIConfig(
                name="Ticketmaster",
                required=False,
                env_vars=["TICKETMASTER_API_KEY"],
                test_endpoint="https://app.ticketmaster.com/discovery/v2/events",
                setup_url="https://developer.ticketmaster.com/",
                description="Event tickets and attraction bookings"
            ),
            APIConfig(
                name="Weather API",
                required=False,
                env_vars=["OPENWEATHER_API_KEY"],
                test_endpoint="https://api.openweathermap.org/data/2.5/weather",
                setup_url="https://openweathermap.org/api",
                description="Weather data for route planning and suggestions"
            ),
            APIConfig(
                name="Spotify",
                required=False,
                env_vars=["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"],
                setup_url="https://developer.spotify.com/dashboard",
                description="Music integration for immersive audio experiences"
            ),
            APIConfig(
                name="Redis",
                required=True,
                env_vars=["REDIS_URL"],
                description="Caching for performance optimization"
            ),
            APIConfig(
                name="PostgreSQL",
                required=True,
                env_vars=["DATABASE_URL"],
                description="Primary database for application data"
            )
        ]
        self.env_file = Path(".env")
        self.env_example_file = Path(".env.example")
        
    def print_header(self, text: str):
        """Print formatted header"""
        print("\n" + "=" * 60)
        print(f" {text.center(58)} ")
        print("=" * 60 + "\n")
        
    def print_status(self, status: str, success: bool):
        """Print colored status message"""
        color = "\033[92m" if success else "\033[91m"
        reset = "\033[0m"
        symbol = "✓" if success else "✗"
        print(f"{color}[{symbol}] {status}{reset}")
        
    def check_prerequisites(self) -> bool:
        """Check if required tools are installed"""
        self.print_header("Checking Prerequisites")
        
        tools = [
            ("Python 3.9+", sys.version_info >= (3, 9)),
            ("pip", subprocess.run(["pip", "--version"], capture_output=True).returncode == 0),
            ("Docker", subprocess.run(["docker", "--version"], capture_output=True).returncode == 0),
            ("Git", subprocess.run(["git", "--version"], capture_output=True).returncode == 0)
        ]
        
        all_good = True
        for tool, installed in tools:
            self.print_status(tool, installed)
            if not installed:
                all_good = False
                
        return all_good
        
    def load_existing_env(self) -> Dict[str, str]:
        """Load existing environment variables"""
        env_vars = {}
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip().strip('"').strip("'")
        return env_vars
        
    def save_env_vars(self, env_vars: Dict[str, str]):
        """Save environment variables to .env file"""
        # Create backup if .env exists
        if self.env_file.exists():
            backup_file = f".env.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.env_file.rename(backup_file)
            print(f"\nBacked up existing .env to {backup_file}")
            
        with open(self.env_file, 'w') as f:
            f.write("# AI Road Trip Storyteller Environment Variables\n")
            f.write(f"# Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Group by API
            for api in self.apis:
                f.write(f"\n# {api.name}\n")
                for var in api.env_vars:
                    value = env_vars.get(var, "")
                    f.write(f"{var}={value}\n")
                    
            # Add any additional vars
            f.write("\n# Application Settings\n")
            f.write("ENVIRONMENT=development\n")
            f.write("DEBUG=True\n")
            f.write("SECRET_KEY=your-secret-key-here\n")
            
    def setup_api(self, api: APIConfig, env_vars: Dict[str, str]) -> Tuple[bool, Dict[str, str]]:
        """Setup individual API configuration"""
        print(f"\n📋 {api.name}")
        print(f"   {api.description}")
        
        if api.setup_url:
            print(f"   Setup URL: {api.setup_url}")
            
        missing_vars = [var for var in api.env_vars if not env_vars.get(var)]
        
        if not missing_vars:
            print("   ✓ Already configured")
            return True, env_vars
            
        if api.required:
            print("   ⚠️  Required API - must be configured")
        else:
            response = input("   Configure this API? (y/n): ").lower()
            if response != 'y':
                return False, env_vars
                
        # Collect missing variables
        for var in missing_vars:
            if var == "GOOGLE_APPLICATION_CREDENTIALS":
                print(f"\n   {var}: Path to service account JSON file")
                print("   (Download from Google Cloud Console)")
            elif var == "DATABASE_URL":
                print(f"\n   {var}: PostgreSQL connection string")
                print("   Format: postgresql://user:password@host:port/database")
            elif var == "REDIS_URL":
                print(f"\n   {var}: Redis connection string")
                print("   Format: redis://host:port/0")
                
            value = input(f"   Enter {var}: ").strip()
            if value:
                env_vars[var] = value
                
        return True, env_vars
        
    def test_google_maps(self, api_key: str) -> bool:
        """Test Google Maps API"""
        try:
            response = requests.get(
                "https://maps.googleapis.com/maps/api/directions/json",
                params={
                    "origin": "San Francisco, CA",
                    "destination": "Los Angeles, CA",
                    "key": api_key
                },
                timeout=10
            )
            return response.status_code == 200 and response.json().get("status") != "REQUEST_DENIED"
        except Exception as e:
            print(f"   Error: {e}")
            return False
            
    def test_weather_api(self, api_key: str) -> bool:
        """Test Weather API"""
        try:
            response = requests.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": "San Francisco",
                    "appid": api_key
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
            
    def test_ticketmaster(self, api_key: str) -> bool:
        """Test Ticketmaster API"""
        try:
            response = requests.get(
                "https://app.ticketmaster.com/discovery/v2/events",
                params={
                    "apikey": api_key,
                    "size": 1
                },
                timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False
            
    def test_apis(self, env_vars: Dict[str, str]):
        """Test all configured APIs"""
        self.print_header("Testing API Connections")
        
        tests = [
            ("Google Maps", "GOOGLE_MAPS_API_KEY", self.test_google_maps),
            ("Weather API", "OPENWEATHER_API_KEY", self.test_weather_api),
            ("Ticketmaster", "TICKETMASTER_API_KEY", self.test_ticketmaster)
        ]
        
        for name, key_var, test_func in tests:
            if key_var in env_vars and env_vars[key_var]:
                print(f"\nTesting {name}...", end=" ")
                success = test_func(env_vars[key_var])
                self.print_status("Connected" if success else "Failed", success)
                
    def generate_example_env(self):
        """Generate .env.example file"""
        with open(self.env_example_file, 'w') as f:
            f.write("# AI Road Trip Storyteller Environment Variables\n")
            f.write("# Copy this file to .env and fill in your values\n\n")
            
            for api in self.apis:
                f.write(f"# {api.name}\n")
                if api.description:
                    f.write(f"# {api.description}\n")
                for var in api.env_vars:
                    f.write(f"{var}=\n")
                f.write("\n")
                
    def run(self):
        """Run the setup wizard"""
        self.print_header("AI Road Trip Storyteller - API Setup Wizard")
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("\n❌ Please install missing prerequisites before continuing.")
            return
            
        # Load existing configuration
        env_vars = self.load_existing_env()
        if env_vars:
            print("\n✓ Found existing .env file")
            
        # Setup each API
        self.print_header("API Configuration")
        
        for api in self.apis:
            configured, env_vars = self.setup_api(api, env_vars)
            
        # Save configuration
        self.save_env_vars(env_vars)
        self.generate_example_env()
        print("\n✓ Configuration saved to .env")
        print("✓ Example configuration saved to .env.example")
        
        # Test APIs
        self.test_apis(env_vars)
        
        # Next steps
        self.print_header("Next Steps")
        print("1. Install dependencies:")
        print("   pip install -r requirements.txt")
        print("\n2. Run database migrations:")
        print("   alembic upgrade head")
        print("\n3. Start Redis and PostgreSQL:")
        print("   docker-compose up -d redis postgres")
        print("\n4. Start the backend server:")
        print("   uvicorn backend.app.main:app --reload")
        print("\n5. Test the API dashboard:")
        print("   python scripts/test_api_dashboard.py")
        print("\n✨ Setup complete! Happy road tripping! 🚗")

if __name__ == "__main__":
    wizard = APISetupWizard()
    wizard.run()