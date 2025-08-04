#!/usr/bin/env python3
"""
MVP Validation Script - Checks if Essential MVP requirements are met
Only tests core voice navigation + AI storytelling features
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class MVPValidator:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent.parent
        self.results = {
            "mobile": {"passed": 0, "failed": 0, "issues": []},
            "backend": {"passed": 0, "failed": 0, "issues": []},
            "integration": {"passed": 0, "failed": 0, "issues": []},
            "deployment": {"passed": 0, "failed": 0, "issues": []}
        }
    
    def check_mobile_location_service(self) -> bool:
        """Check if real GPS location service is implemented"""
        location_service = self.project_root / "mobile/src/services/locationService.ts"
        
        if not location_service.exists():
            self.results["mobile"]["failed"] += 1
            self.results["mobile"]["issues"].append(
                "❌ locationService.ts missing - GPS is hardcoded to NYC"
            )
            return False
        
        # Check for hardcoded coordinates
        with open(location_service, 'r') as f:
            content = f.read()
            if "40.7128" in content or "-74.0060" in content:
                self.results["mobile"]["failed"] += 1
                self.results["mobile"]["issues"].append(
                    "❌ Hardcoded NYC coordinates found in location service"
                )
                return False
        
        self.results["mobile"]["passed"] += 1
        print("✅ Location service exists without hardcoded coordinates")
        return True
    
    def check_voice_recognition(self) -> bool:
        """Check if native voice recognition is properly configured"""
        voice_recognition_service = self.project_root / "mobile/src/services/voiceRecognitionService.ts"
        
        if not voice_recognition_service.exists():
            self.results["mobile"]["failed"] += 1
            self.results["mobile"]["issues"].append(
                "❌ Voice recognition service not properly implemented"
            )
            return False
        
        # Check for @react-native-voice/voice import
        with open(voice_recognition_service, 'r') as f:
            content = f.read()
            if "@react-native-voice/voice" not in content:
                self.results["mobile"]["failed"] += 1
                self.results["mobile"]["issues"].append(
                    "❌ Not using native voice recognition library"
                )
                return False
        
        self.results["mobile"]["passed"] += 1
        print("✅ Native voice recognition configured")
        return True
    
    def check_backend_ai_integration(self) -> bool:
        """Check if Vertex AI is properly configured"""
        env_file = self.project_root / ".env"
        
        if not env_file.exists():
            self.results["backend"]["failed"] += 1
            self.results["backend"]["issues"].append(
                "❌ No .env file found"
            )
            return False
        
        required_vars = [
            "GOOGLE_AI_PROJECT_ID",
            "GOOGLE_AI_LOCATION",
            "GOOGLE_AI_MODEL",
            "GOOGLE_APPLICATION_CREDENTIALS"
        ]
        
        with open(env_file, 'r') as f:
            content = f.read()
            missing = [var for var in required_vars if var not in content]
        
        if missing:
            self.results["backend"]["failed"] += 1
            self.results["backend"]["issues"].append(
                f"❌ Missing AI config: {', '.join(missing)}"
            )
            return False
        
        self.results["backend"]["passed"] += 1
        print("✅ Vertex AI configuration found")
        return True
    
    def check_tts_configuration(self) -> bool:
        """Check if Google Cloud TTS is configured"""
        tts_service = self.project_root / "backend/app/services/tts_service.py"
        
        if not tts_service.exists():
            self.results["backend"]["failed"] += 1
            self.results["backend"]["issues"].append(
                "❌ TTS service not found"
            )
            return False
        
        self.results["backend"]["passed"] += 1
        print("✅ TTS service exists")
        return True
    
    def check_core_endpoints(self) -> bool:
        """Check if core API endpoints exist"""
        try:
            # Check if backend is running
            import requests
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code != 200:
                self.results["integration"]["failed"] += 1
                self.results["integration"]["issues"].append(
                    "❌ Backend health check failed"
                )
                return False
        except Exception as e:
            self.results["integration"]["failed"] += 1
            self.results["integration"]["issues"].append(
                "❌ Backend not running on localhost:8000"
            )
            return False
        
        self.results["integration"]["passed"] += 1
        print("✅ Backend is running")
        return True
    
    def check_deployment_readiness(self) -> bool:
        """Check if deployment files exist"""
        dockerfile = self.project_root / "Dockerfile"
        
        if not dockerfile.exists():
            self.results["deployment"]["failed"] += 1
            self.results["deployment"]["issues"].append(
                "❌ Dockerfile missing"
            )
            return False
        
        self.results["deployment"]["passed"] += 1
        print("✅ Deployment files exist")
        return True
    
    def run_validation(self):
        """Run all MVP validation checks"""
        print("\n🔍 AI Road Trip Storyteller - MVP Validation")
        print("=" * 50)
        print("Checking Essential MVP Requirements...\n")
        
        # Mobile checks
        print("📱 Mobile App Checks:")
        self.check_mobile_location_service()
        self.check_voice_recognition()
        
        # Backend checks
        print("\n🖥️  Backend Checks:")
        self.check_backend_ai_integration()
        self.check_tts_configuration()
        
        # Integration checks
        print("\n🔗 Integration Checks:")
        self.check_core_endpoints()
        
        # Deployment checks
        print("\n🚀 Deployment Checks:")
        self.check_deployment_readiness()
        
        # Summary
        self.print_summary()
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "=" * 50)
        print("📊 MVP VALIDATION SUMMARY")
        print("=" * 50)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.results.items():
            passed = results["passed"]
            failed = results["failed"]
            total_passed += passed
            total_failed += failed
            
            print(f"\n{category.upper()}:")
            print(f"  ✅ Passed: {passed}")
            print(f"  ❌ Failed: {failed}")
            
            if results["issues"]:
                print("  Issues:")
                for issue in results["issues"]:
                    print(f"    {issue}")
        
        print("\n" + "=" * 50)
        print(f"TOTAL: {total_passed} passed, {total_failed} failed")
        
        if total_failed == 0:
            print("\n🎉 MVP READY! All essential features validated.")
        else:
            print(f"\n⚠️  MVP NOT READY: Fix {total_failed} issues before proceeding.")
            print("\nPriority fixes:")
            print("1. Create mobile/src/services/locationService.ts with real GPS")
            print("2. Fix voice recognition to use native library")
            print("3. Configure Vertex AI credentials in .env")
            print("4. Ensure backend is running for integration tests")
        
        return total_failed == 0

if __name__ == "__main__":
    validator = MVPValidator()
    success = validator.run_validation()
    sys.exit(0 if success else 1)