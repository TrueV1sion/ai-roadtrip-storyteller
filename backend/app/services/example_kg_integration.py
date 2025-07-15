"""
Example: How to integrate Knowledge Graph into existing services
This shows the patterns for adding KG support to any service
"""

from typing import Dict, Any, List
import logging

# Import KG decorators and utilities
from ..core.knowledge_graph import (
    kg_analyze_impact,
    kg_pattern_check,
    kg_track_usage,
    kg_suggest_improvements,
    KGTransaction,
    find_similar_implementations,
    check_breaking_changes
)

logger = logging.getLogger(__name__)


class ExampleService:
    """Example service showing KG integration patterns"""
    
    @kg_track_usage("example_service")
    @kg_pattern_check("data_processing")
    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data with KG pattern checking
        The decorators will:
        1. Track that this method was called
        2. Check if it follows established data processing patterns
        """
        # Your existing logic here
        result = {"processed": True, "data": data}
        return result
    
    @kg_analyze_impact
    async def update_critical_config(self, config: Dict[str, Any]) -> bool:
        """
        Update critical configuration with impact analysis
        The decorator will:
        1. Analyze what other code depends on this
        2. Log high-impact changes
        3. Record the update in KG
        """
        # Your existing logic here
        logger.info(f"Updating config: {config}")
        return True
    
    @kg_suggest_improvements
    async def complex_calculation(self, values: List[float]) -> float:
        """
        Complex calculation that might have better implementations
        The decorator will:
        1. Search for similar calculations in the codebase
        2. Log suggestions for optimization
        """
        # Your existing logic here
        return sum(values) / len(values) if values else 0.0
    
    async def multi_step_process(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Multi-step process tracked as a transaction
        Uses context manager for comprehensive tracking
        """
        async with KGTransaction("user_registration", {"user_type": request_data.get("type")}):
            # Step 1: Validate data
            await self._validate_data(request_data)
            
            # Step 2: Check for similar implementations
            similar = await find_similar_implementations("user registration validation")
            if similar:
                logger.debug(f"Found {len(similar)} similar registration flows")
            
            # Step 3: Process registration
            result = await self._process_registration(request_data)
            
            # Step 4: Check if our changes might break anything
            if await check_breaking_changes("services/user_service.py"):
                logger.warning("This change may affect other services")
            
            return result
    
    async def _validate_data(self, data: Dict[str, Any]) -> bool:
        """Internal validation method"""
        return True
    
    async def _process_registration(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Internal processing method"""
        return {"success": True, "user_id": "12345"}


# Example: Adding KG to existing route handler

from fastapi import APIRouter, HTTPException
from ..schemas.example import ExampleRequest, ExampleResponse

router = APIRouter()


@router.post("/example", response_model=ExampleResponse)
@kg_pattern_check("api_endpoint")
async def example_endpoint(request: ExampleRequest) -> ExampleResponse:
    """
    Example API endpoint with KG pattern checking
    The decorator ensures this endpoint follows established patterns
    """
    try:
        # Process request
        service = ExampleService()
        result = await service.process_data(request.dict())
        
        return ExampleResponse(**result)
        
    except Exception as e:
        logger.error(f"Error in example endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Example: Batch operation with KG tracking

@kg_analyze_impact
async def batch_update_users(user_ids: List[str], update_data: Dict[str, Any]) -> int:
    """
    Batch update with impact analysis
    KG will analyze what depends on user data before proceeding
    """
    updated_count = 0
    
    async with KGTransaction("batch_user_update", {"count": len(user_ids)}):
        for user_id in user_ids:
            try:
                # Update each user
                await update_user(user_id, update_data)
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update user {user_id}: {e}")
    
    return updated_count


async def update_user(user_id: str, data: Dict[str, Any]) -> bool:
    """Dummy user update function"""
    return True


# Example: Using KG for code discovery

async def find_similar_endpoints():
    """
    Example of using KG to find similar code
    Useful when implementing new features
    """
    # Find similar authentication endpoints
    auth_endpoints = await find_similar_implementations("authentication endpoint")
    
    # Find similar validation patterns
    validation_patterns = await find_similar_implementations("request validation")
    
    # Find similar error handling
    error_patterns = await find_similar_implementations("error handling")
    
    return {
        "auth_examples": auth_endpoints,
        "validation_examples": validation_patterns,
        "error_examples": error_patterns
    }


# Integration checklist:
# 1. Import KG decorators and utilities
# 2. Add @kg_track_usage to service methods you want to monitor
# 3. Add @kg_pattern_check to ensure consistency
# 4. Add @kg_analyze_impact to critical operations
# 5. Use KGTransaction for multi-step processes
# 6. Use find_similar_implementations when writing new code
# 7. Check breaking_changes before major updates