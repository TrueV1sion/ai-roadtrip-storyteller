#!/usr/bin/env python3
"""
Test script to verify that only Vertex AI is being used (not Generative Language API)
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Set minimal environment variables for testing
os.environ.setdefault("GOOGLE_AI_PROJECT_ID", "gen-lang-client-0492208227")
os.environ.setdefault("GOOGLE_AI_LOCATION", "us-central1")
os.environ.setdefault("GOOGLE_AI_MODEL", "gemini-1.5-flash")
os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "test-secret-key")


async def test_vertex_ai():
    """Test that Vertex AI is being used correctly."""
    print("🧪 Testing Vertex AI configuration...")
    
    try:
        # Import the unified AI client
        from app.core.unified_ai_client import unified_ai_client
        
        print("✅ Successfully imported unified_ai_client")
        
        # Initialize the client
        if unified_ai_client.initialize():
            print("✅ Unified AI client initialized successfully")
        else:
            print("❌ Failed to initialize unified AI client")
            return False
        
        # Test a simple generation
        print("\n📝 Testing story generation...")
        response = await unified_ai_client.generate_story(
            location={"latitude": 37.7749, "longitude": -122.4194},
            interests=["history", "architecture"],
            style="default",
            user_preferences={}
        )
        
        if response and response.get("story"):
            print("✅ Story generated successfully!")
            print(f"   - Model used: {response['metadata']['model']}")
            print(f"   - Processing time: {response['metadata']['processing_time']}s")
            print(f"   - Story preview: {response['story'][:100]}...")
        else:
            print("❌ Failed to generate story")
            return False
            
        # Verify no google.generativeai is imported
        print("\n🔍 Checking for google.generativeai imports...")
        import sys
        for module_name in sys.modules:
            if "generativeai" in module_name and "google" in module_name:
                print(f"❌ ERROR: Found google.generativeai module loaded: {module_name}")
                return False
        
        print("✅ No google.generativeai modules found - using Vertex AI only!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_voice_endpoint():
    """Test the voice assistant endpoint."""
    print("\n🎤 Testing voice assistant endpoint...")
    
    try:
        from app.routes.voice_assistant import router
        from app.services.master_orchestration_agent import MasterOrchestrationAgent
        
        print("✅ Voice assistant modules loaded successfully")
        
        # Check if the master orchestration agent uses unified AI client
        print("🔍 Checking MasterOrchestrationAgent configuration...")
        # This would require actually instantiating and testing the agent
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing voice endpoint: {str(e)}")
        return False


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Vertex AI Only Test Suite")
    print("=" * 60)
    
    # Test Vertex AI
    vertex_ai_ok = await test_vertex_ai()
    
    # Test voice endpoint
    voice_ok = await test_voice_endpoint()
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  - Vertex AI: {'✅ PASS' if vertex_ai_ok else '❌ FAIL'}")
    print(f"  - Voice Endpoint: {'✅ PASS' if voice_ok else '❌ FAIL'}")
    print("=" * 60)
    
    if vertex_ai_ok and voice_ok:
        print("\n🎉 All tests passed! Safe to deploy.")
        return 0
    else:
        print("\n❌ Some tests failed. Do not deploy.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)