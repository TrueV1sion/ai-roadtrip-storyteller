from typing import List, Dict, Any, Optional, Union
import logging
import json
from uuid import uuid4
from datetime import datetime
from pydantic import BaseModel, Field

from ..core.config import settings
from ..core.enhanced_ai_client import EnhancedAIClient
from ..models.user import User

logger = logging.getLogger(__name__)

class NarrativeChoice(BaseModel):
    """Model for a narrative choice"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    text: str
    description: str
    consequences: Dict[str, Any] = Field(default_factory=dict)
    
class NarrativeNode(BaseModel):
    """Model for a narrative node"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    content: str
    image_prompt: Optional[str] = None
    audio_prompt: Optional[str] = None
    choices: List[NarrativeChoice] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class NarrativeState(BaseModel):
    """Model for tracking narrative state"""
    current_node_id: str
    visited_nodes: List[str] = Field(default_factory=list)
    inventory: Dict[str, Any] = Field(default_factory=dict)
    character_traits: Dict[str, float] = Field(default_factory=dict)
    story_variables: Dict[str, Any] = Field(default_factory=dict)
    
class StoryMetadata(BaseModel):
    """Metadata about a narrative story"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    theme: str
    location_type: str
    duration: str
    created_at: datetime = Field(default_factory=datetime.now)
    tags: List[str] = Field(default_factory=list)

class NarrativeGraph(BaseModel):
    """A complete interactive narrative graph"""
    id: str = Field(default_factory=lambda: str(uuid4()))
    metadata: StoryMetadata
    nodes: Dict[str, NarrativeNode] = Field(default_factory=dict)
    initial_node_id: str

class InteractiveNarrative:
    """Service for managing interactive narratives"""
    
    def __init__(self, ai_client: EnhancedAIClient):
        self.ai_client = ai_client
        logger.info("Interactive Narrative service initialized")
    
    async def create_narrative(
        self, 
        user: User,
        location: Dict[str, Any],
        theme: str,
        duration: str,
        complexity: int = 2
    ) -> NarrativeGraph:
        """Create a new interactive narrative based on location and preferences"""
        
        # Generate story parameters based on input and user preferences
        story_parameters = self._generate_story_parameters(user, location, theme, complexity)
        
        # Use AI to create the overall narrative structure
        narrative_structure = await self._generate_narrative_structure(
            story_parameters, duration, complexity
        )
        
        # Generate individual nodes
        nodes = {}
        for node_outline in narrative_structure["nodes"]:
            node = await self._generate_narrative_node(
                node_outline, story_parameters, complexity
            )
            nodes[node.id] = node
        
        # Create the full narrative graph
        metadata = StoryMetadata(
            title=narrative_structure["title"],
            description=narrative_structure["description"],
            theme=theme,
            location_type=location["type"],
            duration=duration,
            tags=narrative_structure.get("tags", [])
        )
        
        narrative = NarrativeGraph(
            metadata=metadata,
            nodes=nodes,
            initial_node_id=narrative_structure["initial_node_id"]
        )
        
        return narrative
    
    def _generate_story_parameters(
        self, user: User, location: Dict[str, Any], theme: str, complexity: int
    ) -> Dict[str, Any]:
        """Generate parameters for the story based on user and location"""
        
        # Extract location information
        location_type = location.get("type", "unknown")
        location_name = location.get("name", "a mysterious place")
        location_description = location.get("description", "")
        location_attractions = location.get("attractions", [])
        
        # Generate parameters based on complexity
        if complexity == 1:  # Simple
            character_count = 3
            choice_count = 2
            nodes_count = 5
        elif complexity == 2:  # Medium
            character_count = 5
            choice_count = 3 
            nodes_count = 10
        else:  # Complex
            character_count = 8
            choice_count = 4
            nodes_count = 15
        
        return {
            "user_preferences": {
                "interests": user.interests if hasattr(user, "interests") else [],
                "travel_style": user.travel_style if hasattr(user, "travel_style") else "explorer",
                "age_group": user.age_group if hasattr(user, "age_group") else "adult"
            },
            "location": {
                "type": location_type,
                "name": location_name,
                "description": location_description,
                "attractions": location_attractions
            },
            "theme": theme,
            "complexity": {
                "character_count": character_count,
                "choice_count": choice_count,
                "nodes_count": nodes_count
            }
        }
    
    async def _generate_narrative_structure(
        self, parameters: Dict[str, Any], duration: str, complexity: int
    ) -> Dict[str, Any]:
        """Generate the overall narrative structure using AI"""
        
        prompt = f"""
        Create an interactive narrative structure for a location-based story with the following parameters:
        
        LOCATION: {parameters['location']['name']} ({parameters['location']['type']})
        LOCATION DESCRIPTION: {parameters['location']['description']}
        THEME: {parameters['theme']}
        USER INTERESTS: {', '.join(parameters['user_preferences']['interests'])}
        TRAVEL STYLE: {parameters['user_preferences']['travel_style']}
        DURATION: {duration}
        COMPLEXITY: {'Simple' if complexity == 1 else 'Medium' if complexity == 2 else 'Complex'}
        
        Create an interactive story structure with branching narrative paths. The story should be engaging, 
        location-specific, and thematically appropriate. Include the following in your response as a JSON object:
        
        1. A captivating title for the story
        2. A brief description of the overall narrative
        3. A list of node outlines (not full nodes) that will form the story graph
        4. The ID of the initial node where the story begins
        5. A list of tags or keywords relevant to the story
        
        For each node outline, include:
        - A unique node ID
        - A brief title for the node
        - A short description of what happens at this node
        - A list of possible choices with their IDs and brief descriptions
        - Any critical story variables or consequences that should be tracked
        
        The nodes should form a coherent graph with multiple pathways and meaningful choices.
        """
        
        response = await self.ai_client.generate_content(prompt)
        try:
            # Parse the JSON response
            narrative_structure = json.loads(response["text"])
            return narrative_structure
        except Exception as e:
            logger.error(f"Error parsing narrative structure: {e}")
            # Return a simple default structure if parsing fails
            return {
                "title": f"Adventure in {parameters['location']['name']}",
                "description": "An interactive adventure with multiple paths.",
                "nodes": [],
                "initial_node_id": "node_1",
                "tags": [parameters['theme'], parameters['location']['type']]
            }
    
    async def _generate_narrative_node(
        self, node_outline: Dict[str, Any], parameters: Dict[str, Any], complexity: int
    ) -> NarrativeNode:
        """Generate a full narrative node from an outline"""
        
        prompt = f"""
        Create a detailed interactive narrative node based on this outline:
        
        NODE TITLE: {node_outline['title']}
        NODE DESCRIPTION: {node_outline['description']}
        
        LOCATION CONTEXT: {parameters['location']['name']} - {parameters['location']['description']}
        THEME: {parameters['theme']}
        
        Develop this node into a rich, detailed scene with:
        
        1. Vivid, descriptive content that immerses the user in the location
        2. Dialogue if appropriate
        3. Sensory details about the location
        4. Emotional elements that connect to the theme
        5. Clear presentation of the choices available
        
        For each choice in the outline, develop a more detailed description of the choice and its immediate consequences.
        
        Also include:
        - A prompt for a relevant image that could illustrate this scene
        - A prompt for mood-appropriate background audio
        
        Respond with a JSON object containing all these elements.
        """
        
        response = await self.ai_client.generate_content(prompt)
        try:
            # Parse the JSON response
            node_data = json.loads(response["text"])
            
            # Create choices
            choices = []
            for choice_data in node_data.get("choices", []):
                choice = NarrativeChoice(
                    id=choice_data.get("id", str(uuid4())),
                    text=choice_data.get("text", "Continue"),
                    description=choice_data.get("description", ""),
                    consequences=choice_data.get("consequences", {})
                )
                choices.append(choice)
            
            # Create the node
            node = NarrativeNode(
                id=node_outline.get("id", str(uuid4())),
                title=node_data.get("title", node_outline.get("title", "Untitled Node")),
                content=node_data.get("content", ""),
                image_prompt=node_data.get("image_prompt"),
                audio_prompt=node_data.get("audio_prompt"),
                choices=choices,
                metadata=node_data.get("metadata", {})
            )
            
            return node
        except Exception as e:
            logger.error(f"Error parsing narrative node: {e}")
            # Return a simple default node if parsing fails
            return NarrativeNode(
                id=node_outline.get("id", str(uuid4())),
                title=node_outline.get("title", "Untitled Node"),
                content=f"You find yourself in {parameters['location']['name']}. What would you like to do?",
                choices=[
                    NarrativeChoice(
                        id="default_choice",
                        text="Continue",
                        description="Continue your journey",
                        consequences={}
                    )
                ]
            )
    
    async def make_choice(
        self, narrative: NarrativeGraph, state: NarrativeState, choice_id: str
    ) -> NarrativeState:
        """Process a user choice and update the narrative state"""
        
        # Get current node
        current_node = narrative.nodes.get(state.current_node_id)
        if not current_node:
            logger.error(f"Invalid node ID: {state.current_node_id}")
            return state
        
        # Find the selected choice
        selected_choice = None
        for choice in current_node.choices:
            if choice.id == choice_id:
                selected_choice = choice
                break
        
        if not selected_choice:
            logger.error(f"Invalid choice ID: {choice_id}")
            return state
        
        # Process choice consequences
        consequences = selected_choice.consequences
        
        # Update state based on consequences
        next_node_id = consequences.get("next_node_id")
        if not next_node_id or next_node_id not in narrative.nodes:
            logger.error(f"Invalid next node ID: {next_node_id}")
            return state
        
        # Update inventory
        for item, action in consequences.get("inventory", {}).items():
            if action == "add":
                state.inventory[item] = state.inventory.get(item, 0) + 1
            elif action == "remove" and item in state.inventory:
                state.inventory[item] = max(0, state.inventory.get(item, 0) - 1)
        
        # Update character traits
        for trait, change in consequences.get("character_traits", {}).items():
            state.character_traits[trait] = state.character_traits.get(trait, 0) + change
        
        # Update story variables
        for var, value in consequences.get("story_variables", {}).items():
            state.story_variables[var] = value
        
        # Add current node to visited nodes
        if state.current_node_id not in state.visited_nodes:
            state.visited_nodes.append(state.current_node_id)
        
        # Update current node
        state.current_node_id = next_node_id
        
        return state
    
    def initialize_state(self, narrative: NarrativeGraph) -> NarrativeState:
        """Initialize a new narrative state for a story"""
        return NarrativeState(
            current_node_id=narrative.initial_node_id,
            visited_nodes=[],
            inventory={},
            character_traits={},
            story_variables={}
        )
    
    async def generate_dynamic_content(
        self, narrative: NarrativeGraph, state: NarrativeState, node_id: str
    ) -> Dict[str, Any]:
        """Generate dynamic content for a node based on current state"""
        
        node = narrative.nodes.get(node_id)
        if not node:
            logger.error(f"Invalid node ID for dynamic content: {node_id}")
            return {
                "error": "Invalid node ID",
                "content": "Error loading content"
            }
        
        # Prepare the context for personalization
        context = {
            "node": node.dict(),
            "state": state.dict(),
            "visited_nodes": [narrative.nodes.get(nid).dict() for nid in state.visited_nodes if narrative.nodes.get(nid)],
            "theme": narrative.metadata.theme
        }
        
        prompt = f"""
        Personalize the following narrative node based on the user's current state and history:
        
        NODE TITLE: {node.title}
        NODE CONTENT: {node.content}
        
        USER STATE:
        - Visited Nodes: {len(state.visited_nodes)}
        - Inventory: {state.inventory}
        - Character Traits: {state.character_traits}
        - Story Variables: {state.story_variables}
        
        Adapt the narrative content to acknowledge:
        1. Previous choices the user has made
        2. Items they have collected
        3. Character traits they have developed
        4. Story variables that are currently set
        
        Keep the same overall meaning and choices, but personalize the presentation.
        Respond with a JSON object containing the personalized content.
        """
        
        response = await self.ai_client.generate_content(prompt)
        try:
            # Parse the JSON response
            personalized_content = json.loads(response["text"])
            return personalized_content
        except Exception as e:
            logger.error(f"Error parsing personalized content: {e}")
            # Return the original content if parsing fails
            return {
                "content": node.content,
                "note": "Original content shown due to personalization error"
            }
    
    def get_node(self, narrative: NarrativeGraph, node_id: str) -> Optional[NarrativeNode]:
        """Get a specific node from the narrative"""
        return narrative.nodes.get(node_id)
    
    def get_current_node(self, narrative: NarrativeGraph, state: NarrativeState) -> Optional[NarrativeNode]:
        """Get the current node based on state"""
        return self.get_node(narrative, state.current_node_id)