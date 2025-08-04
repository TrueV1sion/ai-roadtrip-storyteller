"""
Fact Verification Service
Verifies facts and information for game content and storytelling
"""

from typing import Dict, List, Optional, Any
import asyncio
from datetime import datetime, timedelta

from app.core.logger import logger
from app.core.cache import cache_manager
from app.core.unified_ai_client import UnifiedAIClient


class FactVerificationService:
    """Service for verifying facts and information accuracy"""
    
    def __init__(self):
        self.ai_client = UnifiedAIClient()
        self.verification_cache: Dict[str, Dict] = {}
        self.trusted_sources = [
            "wikipedia",
            "britannica",
            "national geographic",
            "smithsonian",
            "library of congress",
            "unesco",
            "national park service"
        ]
    
    async def verify_fact(
        self,
        fact: str,
        context: Optional[str] = None,
        category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify a single fact"""
        cache_key = f"fact_verify:{fact[:50]}:{category}"
        
        # Check cache
        cached = await cache_manager.get(cache_key)
        if cached:
            return cached
        
        prompt = f"""Verify the following fact:
        Fact: {fact}
        {"Context: " + context if context else ""}
        {"Category: " + category if category else ""}
        
        Please determine:
        1. Is this fact accurate? (true/false)
        2. Confidence level (0-100%)
        3. Any corrections needed
        4. Reliable sources that confirm or refute this
        5. Additional context that's important
        
        Be strict about accuracy - if you're not certain, mark as unverified.
        """
        
        try:
            response = await self.ai_client.generate_content(prompt)
            result = self._parse_verification_response(response, fact)
            
            # Cache for 1 hour
            await cache_manager.set(cache_key, result, ttl=3600)
            
            return result
        except Exception as e:
            logger.error(f"Error verifying fact: {e}")
            return {
                "is_verified": False,
                "confidence": 0,
                "reason": "Verification failed",
                "original_fact": fact
            }
    
    def _parse_verification_response(self, response: str, original_fact: str) -> Dict:
        """Parse AI verification response"""
        # Simple parsing - in production, use structured output
        is_verified = "accurate" in response.lower() or "true" in response.lower()
        
        # Extract confidence (look for percentage)
        confidence = 50  # default
        import re
        confidence_match = re.search(r'(\d+)%', response)
        if confidence_match:
            confidence = int(confidence_match.group(1))
        
        return {
            "is_verified": is_verified and confidence > 70,
            "confidence": confidence,
            "original_fact": original_fact,
            "verification_response": response,
            "timestamp": datetime.now().isoformat()
        }
    
    async def verify_historical_date(
        self,
        event: str,
        date: str,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """Verify a historical date"""
        fact = f"{event} occurred on {date}"
        if location:
            fact += f" at/in {location}"
        
        return await self.verify_fact(fact, category="history")
    
    async def verify_location_fact(
        self,
        location: str,
        fact: str
    ) -> Dict[str, Any]:
        """Verify a fact about a specific location"""
        full_fact = f"At/In {location}: {fact}"
        return await self.verify_fact(full_fact, category="geography")
    
    async def batch_verify_facts(
        self,
        facts: List[str],
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Verify multiple facts in parallel"""
        tasks = [
            self.verify_fact(fact, category=category)
            for fact in facts
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        verified_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error verifying fact {i}: {result}")
                verified_results.append({
                    "is_verified": False,
                    "confidence": 0,
                    "reason": "Verification error",
                    "original_fact": facts[i] if i < len(facts) else ""
                })
            else:
                verified_results.append(result)
        
        return verified_results
    
    async def verify_trivia_question(
        self,
        question: str,
        correct_answer: str,
        category: str
    ) -> Dict[str, Any]:
        """Verify a trivia question and answer"""
        fact = f"Question: {question} Answer: {correct_answer}"
        result = await self.verify_fact(fact, category=category)
        
        # Additional validation for trivia
        if result["is_verified"]:
            # Check if the answer is unambiguous
            prompt = f"""Is this trivia question clear and unambiguous?
            Question: {question}
            Answer: {correct_answer}
            
            Are there any other valid answers that could be considered correct?
            """
            
            clarity_check = await self.ai_client.generate_content(prompt)
            
            if "ambiguous" in clarity_check.lower() or "multiple correct" in clarity_check.lower():
                result["is_verified"] = False
                result["reason"] = "Question may have multiple valid answers"
        
        return result


# Singleton instance
fact_verifier = FactVerificationService()