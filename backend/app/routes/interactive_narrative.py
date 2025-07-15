from fastapi import APIRouter, Depends, HTTPException, Query, Path
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from ..core.security import get_current_user
from ..core.enhanced_ai_client import get_enhanced_ai_client
from ..database import get_db
from ..models.user import User
from ..services.interactive_narrative import InteractiveNarrative
from ..schemas.interactive_narrative import (
    NarrativeGraph,
    NarrativeState, 
    CreateNarrativeRequest,
    MakeChoiceRequest,
    NodeContentRequest,
    NodeResponse,
    NarrativeProgressResponse
)

router = APIRouter(prefix="/interactive-narrative", tags=["Interactive Narrative"])

# Helper function to get the interactive narrative service
def get_interactive_narrative_service(
    ai_client = Depends(get_enhanced_ai_client)
) -> InteractiveNarrative:
    return InteractiveNarrative(ai_client)

# In-memory storage for narratives and states - would be replaced with database in production
narratives = {}
states = {}

@router.post("/create", response_model=NarrativeGraph)
async def create_narrative(
    request: CreateNarrativeRequest,
    current_user: User = Depends(get_current_user),
    service: InteractiveNarrative = Depends(get_interactive_narrative_service)
):
    """Create a new interactive narrative"""
    try:
        narrative = await service.create_narrative(
            user=current_user,
            location=request.location,
            theme=request.theme,
            duration=request.duration,
            complexity=request.complexity
        )
        
        # Store the narrative in memory (would be DB in production)
        narratives[narrative.id] = narrative
        
        return narrative
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating narrative: {str(e)}")

@router.post("/initialize-state", response_model=NarrativeState)
async def initialize_state(
    narrative_id: str,
    current_user: User = Depends(get_current_user),
    service: InteractiveNarrative = Depends(get_interactive_narrative_service)
):
    """Initialize a new state for a narrative"""
    if narrative_id not in narratives:
        raise HTTPException(status_code=404, detail="Narrative not found")
    
    narrative = narratives[narrative_id]
    state = service.initialize_state(narrative)
    
    # Add user ID to track ownership
    state.story_variables["user_id"] = str(current_user.id)
    
    # Store the state in memory (would be DB in production)
    states[state.id] = state
    
    return state

@router.post("/make-choice", response_model=NarrativeState)
async def make_choice(
    request: MakeChoiceRequest,
    current_user: User = Depends(get_current_user),
    service: InteractiveNarrative = Depends(get_interactive_narrative_service)
):
    """Make a choice in the narrative"""
    if request.narrative_id not in narratives:
        raise HTTPException(status_code=404, detail="Narrative not found")
    
    if request.state_id not in states:
        raise HTTPException(status_code=404, detail="State not found")
    
    # Check user ownership of the state
    state = states[request.state_id]
    if state.story_variables.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to modify this state")
    
    narrative = narratives[request.narrative_id]
    
    # Process the choice
    updated_state = await service.make_choice(
        narrative=narrative,
        state=state,
        choice_id=request.choice_id
    )
    
    # Update the state in memory
    states[updated_state.id] = updated_state
    
    return updated_state

@router.post("/node-content", response_model=NodeResponse)
async def get_node_content(
    request: NodeContentRequest,
    current_user: User = Depends(get_current_user),
    service: InteractiveNarrative = Depends(get_interactive_narrative_service)
):
    """Get personalized content for a node"""
    if request.narrative_id not in narratives:
        raise HTTPException(status_code=404, detail="Narrative not found")
    
    if request.state_id not in states:
        raise HTTPException(status_code=404, detail="State not found")
    
    # Check user ownership of the state
    state = states[request.state_id]
    if state.story_variables.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this state")
    
    narrative = narratives[request.narrative_id]
    
    # Get the node
    node = service.get_node(narrative, request.node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    
    # Generate personalized content
    personalized_content = await service.generate_dynamic_content(
        narrative=narrative,
        state=state,
        node_id=request.node_id
    )
    
    return NodeResponse(
        node=node,
        personalized_content=personalized_content,
        available_choices=node.choices
    )

@router.get("/current-node/{state_id}", response_model=NodeResponse)
async def get_current_node(
    state_id: str,
    narrative_id: str = Query(..., description="ID of the narrative"),
    current_user: User = Depends(get_current_user),
    service: InteractiveNarrative = Depends(get_interactive_narrative_service)
):
    """Get the current node for a narrative state"""
    if narrative_id not in narratives:
        raise HTTPException(status_code=404, detail="Narrative not found")
    
    if state_id not in states:
        raise HTTPException(status_code=404, detail="State not found")
    
    # Check user ownership of the state
    state = states[state_id]
    if state.story_variables.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this state")
    
    narrative = narratives[narrative_id]
    
    # Get the current node
    current_node = service.get_current_node(narrative, state)
    if not current_node:
        raise HTTPException(status_code=404, detail="Current node not found")
    
    # Generate personalized content
    personalized_content = await service.generate_dynamic_content(
        narrative=narrative,
        state=state,
        node_id=current_node.id
    )
    
    return NodeResponse(
        node=current_node,
        personalized_content=personalized_content,
        available_choices=current_node.choices
    )

@router.get("/progress/{state_id}", response_model=NarrativeProgressResponse)
async def get_narrative_progress(
    state_id: str,
    narrative_id: str = Query(..., description="ID of the narrative"),
    current_user: User = Depends(get_current_user),
    service: InteractiveNarrative = Depends(get_interactive_narrative_service)
):
    """Get progress information for a narrative state"""
    if narrative_id not in narratives:
        raise HTTPException(status_code=404, detail="Narrative not found")
    
    if state_id not in states:
        raise HTTPException(status_code=404, detail="State not found")
    
    # Check user ownership of the state
    state = states[state_id]
    if state.story_variables.get("user_id") != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to access this state")
    
    narrative = narratives[narrative_id]
    
    # Get the current node
    current_node = service.get_current_node(narrative, state)
    
    # Calculate completion percentage based on visited nodes
    total_nodes = len(narrative.nodes)
    visited_nodes = len(state.visited_nodes)
    completion_percentage = (visited_nodes / total_nodes) * 100 if total_nodes > 0 else 0
    
    # Get personalized content for current node if available
    node_response = None
    if current_node:
        personalized_content = await service.generate_dynamic_content(
            narrative=narrative,
            state=state,
            node_id=current_node.id
        )
        
        node_response = NodeResponse(
            node=current_node,
            personalized_content=personalized_content,
            available_choices=current_node.choices
        )
    
    return NarrativeProgressResponse(
        narrative_id=narrative_id,
        state=state,
        current_node=node_response,
        completion_percentage=completion_percentage,
        choices_made=len(state.visited_nodes)
    )

@router.get("/narratives", response_model=List[NarrativeGraph])
async def get_narratives(
    current_user: User = Depends(get_current_user)
):
    """Get all available narratives"""
    # In a real implementation, this would filter by user or permissions
    return list(narratives.values())

@router.get("/states", response_model=List[NarrativeState])
async def get_states(
    current_user: User = Depends(get_current_user)
):
    """Get all states owned by the current user"""
    user_states = [
        state for state in states.values() 
        if state.story_variables.get("user_id") == str(current_user.id)
    ]
    return user_states