"""
Gemini AI Client - Alternative to Vertex AI using Google AI Studio API
"""
import os
import httpx
from typing import Dict, List, Any, Optional
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class GeminiAIClient:
    """Client for Google AI Studio Gemini API"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not found, using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        self.model = "models/gemini-pro"
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def generate_response(self, prompt: str) -> str:
        """Generate a response using Gemini API"""
        
        if self.mock_mode:
            return self._mock_response(prompt)
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/{self.model}:generateContent",
                    params={"key": self.api_key},
                    json={
                        "contents": [{
                            "parts": [{
                                "text": prompt
                            }]
                        }]
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
                
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                return self._mock_response(prompt)
    
    async def generate_structured_response(self, prompt: str, expected_format: str) -> Dict[str, Any]:
        """Generate a structured response"""
        
        structured_prompt = f"{prompt}\n\nRespond in valid JSON format matching: {expected_format}"
        response = await self.generate_response(structured_prompt)
        
        try:
            import json
            return json.loads(response)
        except:
            # Return mock structured data if parsing fails
            return self._mock_structured_response(expected_format)
    
    def _mock_response(self, prompt: str) -> str:
        """Generate mock responses for testing"""
        
        if "story" in prompt.lower():
            return "As you drive along this historic route, imagine the countless travelers who have journeyed here before you..."
        elif "booking" in prompt.lower():
            return "I found several great restaurants nearby that match your preferences. Would you like me to check availability?"
        elif "personality" in prompt.lower():
            return "Welcome aboard! I'm your friendly travel guide, ready to make this journey unforgettable!"
        else:
            return "I'm here to help make your journey amazing. What would you like to know?"
    
    def _mock_structured_response(self, expected_format: str) -> Dict[str, Any]:
        """Generate mock structured responses"""
        
        if "intent_analysis" in expected_format:
            return {
                "primary_intent": "story_request",
                "secondary_intents": [],
                "required_agents": {"story": {"task": "generate"}},
                "urgency": "can_wait",
                "context_requirements": [],
                "expected_response_type": "story"
            }
        else:
            return {"status": "success", "data": {}}