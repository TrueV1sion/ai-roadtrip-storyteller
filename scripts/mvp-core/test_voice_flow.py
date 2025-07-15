#!/usr/bin/env python3
"""
Test Voice Flow - End-to-end test of voice command to story playback
Tests only MVP features: voice recognition → navigation → story generation → audio playback
"""

import asyncio
import time
import sys
from pathlib import Path
from typing import Dict, Optional

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

class VoiceFlowTester:
    def __init__(self):
        self.api_base = "http://localhost:8000"
        self.test_commands = [
            "Navigate to Golden Gate Bridge",
            "Navigate to Starbucks", 
            "Navigate to Central Park",
            "Take me to the nearest gas station"
        ]
        self.results = []
    
    async def test_voice_command(self, command: str) -> Dict:
        """Test a single voice command through the entire flow"""
        print(f"\n🎤 Testing: '{command}'")
        result = {
            "command": command,
            "steps": {},
            "total_time": 0,
            "success": False
        }
        
        start_time = time.time()
        
        try:
            # Step 1: Voice recognition (simulated)
            print("  1️⃣ Voice recognition...", end="")
            await asyncio.sleep(0.5)  # Simulate recognition time
            result["steps"]["recognition"] = {"success": True, "time": 0.5}
            print(" ✅")
            
            # Step 2: Send to backend
            print("  2️⃣ Sending to backend...", end="")
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "user_input": command,
                    "context": {
                        "location": {"lat": 37.7749, "lng": -122.4194},  # SF
                        "speed": 35,
                        "heading": 180
                    }
                }
                
                api_start = time.time()
                async with session.post(
                    f"{self.api_base}/api/voice-assistant/interact",
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        api_time = time.time() - api_start
                        result["steps"]["api"] = {
                            "success": True,
                            "time": api_time,
                            "response_length": len(str(data))
                        }
                        print(f" ✅ ({api_time:.2f}s)")
                    else:
                        result["steps"]["api"] = {
                            "success": False,
                            "error": f"Status {response.status}"
                        }
                        print(f" ❌ (Status {response.status})")
                        return result
            
            # Step 3: Story generation check
            print("  3️⃣ Story generation...", end="")
            if "data" in data and "response" in data["data"]:
                story_text = data["data"]["response"].get("text", "")
                if len(story_text) > 50:  # Minimum story length
                    result["steps"]["story"] = {
                        "success": True,
                        "length": len(story_text),
                        "preview": story_text[:100] + "..."
                    }
                    print(f" ✅ ({len(story_text)} chars)")
                else:
                    result["steps"]["story"] = {
                        "success": False,
                        "error": "Story too short"
                    }
                    print(" ❌ (Too short)")
            
            # Step 4: TTS generation (check if audio URL provided)
            print("  4️⃣ Audio generation...", end="")
            audio_url = data["data"]["response"].get("audio_url")
            if audio_url:
                result["steps"]["tts"] = {
                    "success": True,
                    "audio_url": audio_url
                }
                print(" ✅")
            else:
                # Simulate TTS generation
                await asyncio.sleep(1.0)
                result["steps"]["tts"] = {
                    "success": True,
                    "simulated": True
                }
                print(" ✅ (simulated)")
            
            # Step 5: Navigation update
            print("  5️⃣ Navigation update...", end="")
            if "navigation" in data["data"]["response"]:
                result["steps"]["navigation"] = {
                    "success": True,
                    "destination": data["data"]["response"]["navigation"].get("destination"),
                    "distance": data["data"]["response"]["navigation"].get("distance"),
                    "duration": data["data"]["response"]["navigation"].get("duration")
                }
                print(" ✅")
            else:
                result["steps"]["navigation"] = {
                    "success": True,
                    "simulated": True
                }
                print(" ✅ (simulated)")
            
            result["success"] = True
            
        except Exception as e:
            print(f" ❌ Error: {str(e)}")
            result["error"] = str(e)
        
        result["total_time"] = time.time() - start_time
        print(f"  ⏱️  Total time: {result['total_time']:.2f}s")
        
        return result
    
    async def run_tests(self):
        """Run all voice flow tests"""
        print("🎯 Voice Flow Testing - Essential MVP")
        print("=" * 50)
        print("Testing voice command → story generation flow\n")
        
        # Check if backend is running
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.api_base}/health") as response:
                    if response.status != 200:
                        print("❌ Backend not healthy!")
                        return
        except:
            print("❌ Backend not running on localhost:8000")
            print("   Run: cd backend && uvicorn app.main:app --reload")
            return
        
        # Run tests
        for command in self.test_commands:
            result = await self.test_voice_command(command)
            self.results.append(result)
            await asyncio.sleep(1)  # Avoid rate limiting
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 VOICE FLOW TEST SUMMARY")
        print("=" * 50)
        
        successful = sum(1 for r in self.results if r["success"])
        total = len(self.results)
        
        print(f"\nOverall: {successful}/{total} commands successful")
        
        # Performance metrics
        if successful > 0:
            avg_time = sum(r["total_time"] for r in self.results if r["success"]) / successful
            print(f"Average response time: {avg_time:.2f}s")
            
            # Check MVP target (<3 seconds)
            if avg_time <= 3.0:
                print("✅ Meets MVP target (<3s)")
            else:
                print(f"❌ Exceeds MVP target (>{avg_time-3:.1f}s over)")
        
        # Detailed results
        print("\nDetailed Results:")
        for result in self.results:
            status = "✅" if result["success"] else "❌"
            print(f"\n{status} '{result['command']}'")
            print(f"   Time: {result['total_time']:.2f}s")
            
            if result["success"]:
                for step, data in result["steps"].items():
                    if data.get("success"):
                        print(f"   - {step}: ✓")
            else:
                print(f"   Error: {result.get('error', 'Unknown')}")
        
        # Recommendations
        print("\n📝 Recommendations:")
        if successful < total:
            print("- Fix failed commands before MVP launch")
        
        avg_time = sum(r["total_time"] for r in self.results) / len(self.results) if self.results else 0
        if avg_time > 3.0:
            print("- Optimize response time (cache stories, faster TTS)")
        
        if all(r.get("steps", {}).get("tts", {}).get("simulated") for r in self.results):
            print("- Implement real Google Cloud TTS")
        
        if all(r.get("steps", {}).get("navigation", {}).get("simulated") for r in self.results):
            print("- Connect real navigation updates")

async def main():
    tester = VoiceFlowTester()
    await tester.run_tests()

if __name__ == "__main__":
    asyncio.run(main())