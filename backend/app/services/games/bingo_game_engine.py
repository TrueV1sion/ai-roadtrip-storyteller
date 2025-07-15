"""
Travel Bingo Game Engine for Voice-Driven Gameplay
Players spot items during their journey and call them out
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import random
import asyncio
import logging
from enum import Enum

from .game_engine_base import (
    BaseGameEngine,
    GameSession,
    GameAction,
    GameEvent,
    Player,
    GameState,
    DifficultyLevel
)
from ...core.enhanced_ai_client import EnhancedAIClient
from ...services.location_service import get_nearby_places
from ...services.voice_character_system import VoiceCharacterSystem

logger = logging.getLogger(__name__)


class BingoPatternType(Enum):
    """Types of winning patterns in Bingo"""
    LINE_HORIZONTAL = "line_horizontal"
    LINE_VERTICAL = "line_vertical"
    LINE_DIAGONAL = "line_diagonal"
    FOUR_CORNERS = "four_corners"
    FULL_CARD = "full_card"
    LETTER_T = "letter_t"
    LETTER_X = "letter_x"
    CUSTOM = "custom"


@dataclass
class BingoItem:
    """An item on the bingo card"""
    id: str
    name: str
    category: str
    description: str
    difficulty_score: float
    location_specific: bool = False
    weather_dependent: bool = False
    time_dependent: bool = False
    rarity: str = "common"  # common, uncommon, rare
    points: int = 10
    image_hint: Optional[str] = None


@dataclass
class BingoSquare:
    """A square on the bingo card"""
    row: int
    col: int
    item: Optional[BingoItem]
    is_marked: bool = False
    marked_by: Optional[str] = None
    marked_at: Optional[datetime] = None
    verified: bool = False


@dataclass
class BingoCard:
    """A player's bingo card"""
    player_id: str
    card_id: str
    size: int = 5  # 5x5 grid
    squares: List[List[BingoSquare]] = field(default_factory=list)
    completed_patterns: List[BingoPatternType] = field(default_factory=list)
    total_marked: int = 0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SpottedItem:
    """Record of a spotted item"""
    item_id: str
    player_id: str
    timestamp: datetime
    location: Dict[str, float]
    confidence: float
    verified: bool = False
    points_awarded: int = 0


class BingoGameEngine(BaseGameEngine):
    """
    Travel Bingo implementation where players spot items
    during their journey and mark them on their cards
    """
    
    def __init__(self, ai_client: EnhancedAIClient, voice_system: VoiceCharacterSystem):
        super().__init__("travel_bingo")
        self.ai_client = ai_client
        self.voice_system = voice_system
        
        # Game configuration
        self.card_size = 5
        self.free_space_enabled = True
        self.verification_required = False
        self.collaborative_mode = True  # All players work together
        
        # Item categories for travel
        self.categories = [
            "Vehicles", "Animals", "Buildings", "Nature",
            "Signs", "People", "Weather", "Colors",
            "Landmarks", "Activities"
        ]
        
        # Scoring
        self.pattern_scores = {
            BingoPatternType.LINE_HORIZONTAL: 50,
            BingoPatternType.LINE_VERTICAL: 50,
            BingoPatternType.LINE_DIAGONAL: 75,
            BingoPatternType.FOUR_CORNERS: 40,
            BingoPatternType.LETTER_T: 100,
            BingoPatternType.LETTER_X: 100,
            BingoPatternType.FULL_CARD: 200
        }
        
        self.rarity_multipliers = {
            "common": 1.0,
            "uncommon": 1.5,
            "rare": 2.0
        }
    
    def _initialize_game(self):
        """Initialize bingo-specific components"""
        # Register voice command patterns
        self.register_voice_command("i see", self._handle_item_spotted)
        self.register_voice_command("i found", self._handle_item_spotted)
        self.register_voice_command("there's a", self._handle_item_spotted)
        self.register_voice_command("spotted", self._handle_item_spotted)
        self.register_voice_command("bingo", self._handle_bingo_call)
        self.register_voice_command("my card", self._handle_card_status)
        self.register_voice_command("what should i look for", self._handle_suggestion_request)
    
    async def process_game_action(
        self,
        session: GameSession,
        action: GameAction
    ) -> Dict[str, Any]:
        """Process bingo-specific actions"""
        
        if action.action_type == "spot_item":
            return await self._process_spotted_item(session, action)
        
        elif action.action_type == "call_bingo":
            return await self._verify_bingo(session, action)
        
        elif action.action_type == "get_card":
            return await self._get_player_card(session, action)
        
        elif action.action_type == "get_suggestions":
            return await self._get_item_suggestions(session, action)
        
        elif action.action_type == "verify_item":
            return await self._verify_spotted_item(session, action)
        
        return {"error": "Unknown action type"}
    
    async def generate_game_content(
        self,
        session: GameSession,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate bingo cards based on journey context"""
        location = context.get("location", {})
        difficulty = DifficultyLevel(context.get("difficulty", DifficultyLevel.MEDIUM.value))
        num_players = len(session.players)
        
        # Generate pool of items
        item_pool = await self._generate_item_pool(
            location=location,
            difficulty=difficulty,
            count=100  # Generate more than needed for variety
        )
        
        # Create cards for each player
        cards = {}
        for player_id in session.players:
            card = self._create_bingo_card(player_id, item_pool)
            cards[player_id] = card
        
        # Initialize tracking
        return {
            "item_pool": item_pool,
            "player_cards": cards,
            "spotted_items": [],
            "active_patterns": list(BingoPatternType),
            "collaborative_mode": self.collaborative_mode,
            "journey_start_location": location
        }
    
    async def _generate_item_pool(
        self,
        location: Dict[str, Any],
        difficulty: DifficultyLevel,
        count: int
    ) -> List[BingoItem]:
        """Generate pool of bingo items based on journey"""
        
        # Get nearby places for location-specific items
        nearby_places = []
        if location and "lat" in location and "lng" in location:
            nearby_places = await get_nearby_places(
                location["lat"],
                location["lng"],
                radius=50000  # 50km radius for journey
            )
        
        prompt = f"""
        Generate {count} items for a Travel Bingo game.
        
        Journey starting from: {location.get('name', 'Unknown location')}
        Nearby landmarks: {', '.join([p['name'] for p in nearby_places[:10]])}
        Difficulty: {difficulty.value}
        
        Requirements:
        1. Mix of common roadside items and location-specific items
        2. Items should be spottable from a moving vehicle
        3. Include variety across categories: {', '.join(self.categories)}
        4. Some items should be weather or time dependent
        5. Rarity distribution: 60% common, 30% uncommon, 10% rare
        
        For each item provide:
        Name: [What to spot]
        Category: [From the list above]
        Description: [Brief description to help identify]
        Rarity: [common/uncommon/rare]
        Location_Specific: [yes/no]
        Weather_Dependent: [yes/no]
        Time_Dependent: [yes/no]
        Visual_Hint: [What to look for]
        """
        
        response = await self.ai_client.generate_content(prompt)
        return self._parse_bingo_items(response, difficulty)
    
    def _parse_bingo_items(self, response: str, difficulty: DifficultyLevel) -> List[BingoItem]:
        """Parse AI response into BingoItem objects"""
        items = []
        item_blocks = response.strip().split('\n\n')
        
        for i, block in enumerate(item_blocks):
            try:
                lines = block.strip().split('\n')
                if len(lines) < 8:
                    continue
                
                # Parse item attributes
                name = ""
                category = ""
                description = ""
                rarity = "common"
                location_specific = False
                weather_dependent = False
                time_dependent = False
                visual_hint = ""
                
                for line in lines:
                    if line.startswith('Name:'):
                        name = line.replace('Name:', '').strip()
                    elif line.startswith('Category:'):
                        category = line.replace('Category:', '').strip()
                    elif line.startswith('Description:'):
                        description = line.replace('Description:', '').strip()
                    elif line.startswith('Rarity:'):
                        rarity = line.replace('Rarity:', '').strip().lower()
                    elif line.startswith('Location_Specific:'):
                        location_specific = 'yes' in line.lower()
                    elif line.startswith('Weather_Dependent:'):
                        weather_dependent = 'yes' in line.lower()
                    elif line.startswith('Time_Dependent:'):
                        time_dependent = 'yes' in line.lower()
                    elif line.startswith('Visual_Hint:'):
                        visual_hint = line.replace('Visual_Hint:', '').strip()
                
                if name and category:
                    # Calculate difficulty score
                    difficulty_score = 0.5
                    if rarity == "uncommon":
                        difficulty_score = 0.7
                    elif rarity == "rare":
                        difficulty_score = 0.9
                    
                    # Calculate points
                    base_points = 10
                    if rarity == "uncommon":
                        base_points = 20
                    elif rarity == "rare":
                        base_points = 30
                    
                    items.append(BingoItem(
                        id=f"item_{i}_{name.lower().replace(' ', '_')}",
                        name=name,
                        category=category,
                        description=description,
                        difficulty_score=difficulty_score,
                        location_specific=location_specific,
                        weather_dependent=weather_dependent,
                        time_dependent=time_dependent,
                        rarity=rarity,
                        points=base_points,
                        image_hint=visual_hint
                    ))
                
            except Exception as e:
                logger.error(f"Error parsing bingo item: {e}")
                continue
        
        return items
    
    def _create_bingo_card(self, player_id: str, item_pool: List[BingoItem]) -> BingoCard:
        """Create a bingo card for a player"""
        card = BingoCard(
            player_id=player_id,
            card_id=f"card_{player_id}_{datetime.now().timestamp()}",
            size=self.card_size
        )
        
        # Shuffle items for randomness
        shuffled_items = random.sample(item_pool, min(len(item_pool), self.card_size * self.card_size))
        
        # Fill the card
        card.squares = []
        item_index = 0
        
        for row in range(self.card_size):
            card_row = []
            for col in range(self.card_size):
                # Free space in center
                if self.free_space_enabled and row == self.card_size // 2 and col == self.card_size // 2:
                    square = BingoSquare(row=row, col=col, item=None, is_marked=True)
                else:
                    item = shuffled_items[item_index] if item_index < len(shuffled_items) else None
                    square = BingoSquare(row=row, col=col, item=item)
                    item_index += 1
                
                card_row.append(square)
            card.squares.append(card_row)
        
        return card
    
    async def _process_spotted_item(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Process when a player spots an item"""
        content = session.metadata.get("game_content", {})
        cards = content.get("player_cards", {})
        
        player_card = cards.get(action.player_id)
        if not player_card:
            return {"error": "Player card not found"}
        
        # Extract spotted item from voice input
        spotted_text = action.data.get("item", "")
        if action.data.get("raw_command"):
            spotted_text = self._extract_item_from_voice(action.data["raw_command"])
        
        # Find matching item on card
        matched_square = None
        matched_item = None
        
        for row in player_card.squares:
            for square in row:
                if square.item and not square.is_marked:
                    if self._match_item(spotted_text, square.item):
                        matched_square = square
                        matched_item = square.item
                        break
            if matched_square:
                break
        
        if not matched_square:
            # Check if item exists but already marked
            for row in player_card.squares:
                for square in row:
                    if square.item and square.is_marked:
                        if self._match_item(spotted_text, square.item):
                            return {
                                "already_marked": True,
                                "item": square.item.name,
                                "voice_response": f"{square.item.name} has already been marked!"
                            }
            
            return {
                "not_found": True,
                "voice_response": f"I couldn't find '{spotted_text}' on your bingo card. Try looking for something else!"
            }
        
        # Mark the square
        matched_square.is_marked = True
        matched_square.marked_by = action.player_id
        matched_square.marked_at = datetime.now()
        player_card.total_marked += 1
        
        # Award points
        player = session.players.get(action.player_id)
        if player:
            points = int(matched_item.points * self.rarity_multipliers[matched_item.rarity])
            player.score += points
        
        # Record spotted item
        spotted_record = SpottedItem(
            item_id=matched_item.id,
            player_id=action.player_id,
            timestamp=datetime.now(),
            location=action.data.get("location", {}),
            confidence=action.voice_confidence,
            points_awarded=points
        )
        content["spotted_items"].append(spotted_record)
        
        # Check for completed patterns
        completed_patterns = self._check_patterns(player_card)
        new_patterns = [p for p in completed_patterns if p not in player_card.completed_patterns]
        
        # Award pattern bonuses
        pattern_bonus = 0
        for pattern in new_patterns:
            pattern_bonus += self.pattern_scores.get(pattern, 0)
            player_card.completed_patterns.append(pattern)
        
        if pattern_bonus > 0 and player:
            player.score += pattern_bonus
        
        # Generate response narrative
        narrative = await self._generate_spot_narrative(
            matched_item,
            player_card,
            new_patterns,
            points
        )
        
        result = {
            "marked": True,
            "item": matched_item.name,
            "category": matched_item.category,
            "points_earned": points,
            "total_marked": player_card.total_marked,
            "voice_narrative": narrative,
            "audio_cue": "item_marked"
        }
        
        if new_patterns:
            result["new_patterns"] = [p.value for p in new_patterns]
            result["pattern_bonus"] = pattern_bonus
            result["audio_cue"] = "pattern_complete"
        
        if self._check_full_card(player_card):
            result["bingo"] = True
            result["audio_cue"] = "bingo_win"
        
        return result
    
    def _extract_item_from_voice(self, voice_input: str) -> str:
        """Extract item name from voice command"""
        voice_lower = voice_input.lower()
        
        # Remove command prefixes
        prefixes = ["i see", "i found", "there's a", "there's an", "spotted", "i spotted"]
        for prefix in prefixes:
            if voice_lower.startswith(prefix):
                return voice_input[len(prefix):].strip()
        
        return voice_input
    
    def _match_item(self, spotted_text: str, item: BingoItem) -> bool:
        """Check if spotted text matches a bingo item"""
        spotted_lower = spotted_text.lower().strip()
        item_lower = item.name.lower()
        
        # Exact match
        if spotted_lower == item_lower:
            return True
        
        # Contains match
        if spotted_lower in item_lower or item_lower in spotted_lower:
            return True
        
        # Key word match
        spotted_words = set(spotted_lower.split())
        item_words = set(item_lower.split())
        
        # If more than half the words match
        common_words = spotted_words.intersection(item_words)
        if len(common_words) >= len(item_words) / 2:
            return True
        
        return False
    
    def _check_patterns(self, card: BingoCard) -> List[BingoPatternType]:
        """Check for completed patterns on the card"""
        completed = []
        size = card.size
        
        # Check horizontal lines
        for row in range(size):
            if all(card.squares[row][col].is_marked for col in range(size)):
                completed.append(BingoPatternType.LINE_HORIZONTAL)
                break
        
        # Check vertical lines
        for col in range(size):
            if all(card.squares[row][col].is_marked for row in range(size)):
                completed.append(BingoPatternType.LINE_VERTICAL)
                break
        
        # Check diagonals
        if all(card.squares[i][i].is_marked for i in range(size)):
            completed.append(BingoPatternType.LINE_DIAGONAL)
        
        if all(card.squares[i][size-1-i].is_marked for i in range(size)):
            completed.append(BingoPatternType.LINE_DIAGONAL)
        
        # Check four corners
        corners = [
            card.squares[0][0],
            card.squares[0][size-1],
            card.squares[size-1][0],
            card.squares[size-1][size-1]
        ]
        if all(corner.is_marked for corner in corners):
            completed.append(BingoPatternType.FOUR_CORNERS)
        
        # Check full card
        if self._check_full_card(card):
            completed.append(BingoPatternType.FULL_CARD)
        
        return completed
    
    def _check_full_card(self, card: BingoCard) -> bool:
        """Check if entire card is marked"""
        for row in card.squares:
            for square in row:
                if square.item and not square.is_marked:
                    return False
        return True
    
    async def _verify_bingo(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Verify a bingo call"""
        content = session.metadata.get("game_content", {})
        cards = content.get("player_cards", {})
        
        player_card = cards.get(action.player_id)
        if not player_card:
            return {"error": "Player card not found"}
        
        # Check if player has bingo
        has_bingo = self._check_full_card(player_card)
        
        if has_bingo:
            # Calculate final score
            player = session.players.get(action.player_id)
            if player:
                # Bonus for calling bingo
                player.score += 100
            
            return {
                "valid_bingo": True,
                "total_score": player.score if player else 0,
                "voice_response": "BINGO! Congratulations! You've completed your entire card!",
                "audio_cue": "bingo_celebration"
            }
        else:
            # Count remaining squares
            remaining = sum(1 for row in player_card.squares for square in row 
                          if square.item and not square.is_marked)
            
            return {
                "valid_bingo": False,
                "remaining_squares": remaining,
                "voice_response": f"Not quite yet! You still have {remaining} squares to mark.",
                "audio_cue": "not_yet"
            }
    
    async def _get_player_card(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Get player's current card status"""
        content = session.metadata.get("game_content", {})
        cards = content.get("player_cards", {})
        
        player_card = cards.get(action.player_id)
        if not player_card:
            return {"error": "Player card not found"}
        
        # Get unmarked items
        unmarked_items = []
        for row in player_card.squares:
            for square in row:
                if square.item and not square.is_marked:
                    unmarked_items.append({
                        "name": square.item.name,
                        "category": square.item.category,
                        "hint": square.item.description,
                        "rarity": square.item.rarity
                    })
        
        # Sort by category for easier reference
        unmarked_items.sort(key=lambda x: x["category"])
        
        return {
            "total_marked": player_card.total_marked,
            "total_squares": self.card_size * self.card_size - (1 if self.free_space_enabled else 0),
            "unmarked_items": unmarked_items[:10],  # Show next 10 items
            "completed_patterns": [p.value for p in player_card.completed_patterns],
            "voice_response": f"You've marked {player_card.total_marked} squares. " +
                            f"Look for: {', '.join([item['name'] for item in unmarked_items[:3]])}"
        }
    
    async def _get_item_suggestions(self, session: GameSession, action: GameAction) -> Dict[str, Any]:
        """Suggest items to look for based on context"""
        content = session.metadata.get("game_content", {})
        cards = content.get("player_cards", {})
        
        player_card = cards.get(action.player_id)
        if not player_card:
            return {"error": "Player card not found"}
        
        # Get location and time context
        location = action.data.get("location", {})
        current_time = datetime.now()
        is_daytime = 6 <= current_time.hour <= 18
        
        # Find contextually relevant unmarked items
        suggestions = []
        for row in player_card.squares:
            for square in row:
                if square.item and not square.is_marked:
                    relevance_score = 1.0
                    
                    # Boost common items
                    if square.item.rarity == "common":
                        relevance_score += 0.5
                    
                    # Boost time-appropriate items
                    if square.item.time_dependent:
                        if is_daytime and "day" in square.item.name.lower():
                            relevance_score += 1.0
                        elif not is_daytime and "night" in square.item.name.lower():
                            relevance_score += 1.0
                    
                    suggestions.append((square.item, relevance_score))
        
        # Sort by relevance
        suggestions.sort(key=lambda x: x[1], reverse=True)
        top_suggestions = [item for item, _ in suggestions[:5]]
        
        # Generate narrative
        narrative_parts = ["Based on where you are, try looking for:"]
        for i, item in enumerate(top_suggestions[:3], 1):
            narrative_parts.append(f"{i}. {item.name} - {item.description}")
        
        return {
            "suggestions": [
                {
                    "name": item.name,
                    "category": item.category,
                    "hint": item.description,
                    "rarity": item.rarity
                }
                for item in top_suggestions
            ],
            "voice_narrative": " ".join(narrative_parts)
        }
    
    async def _generate_spot_narrative(
        self,
        item: BingoItem,
        card: BingoCard,
        new_patterns: List[BingoPatternType],
        points: int
    ) -> str:
        """Generate narrative for spotted item"""
        parts = []
        
        # Confirmation
        exclamations = {
            "common": ["Great spot!", "Nice find!", "Well spotted!"],
            "uncommon": ["Excellent find!", "That's a good one!", "Great eye!"],
            "rare": ["Amazing find!", "Incredible spot!", "What a rare sight!"]
        }
        parts.append(random.choice(exclamations[item.rarity]))
        
        # Item and points
        parts.append(f"You marked {item.name} for {points} points!")
        
        # Pattern completion
        if new_patterns:
            if len(new_patterns) == 1:
                parts.append(f"You completed a {new_patterns[0].value.replace('_', ' ')}!")
            else:
                patterns_text = ", ".join([p.value.replace('_', ' ') for p in new_patterns])
                parts.append(f"Amazing! You completed: {patterns_text}!")
        
        # Progress update
        remaining = sum(1 for row in card.squares for square in row 
                       if square.item and not square.is_marked)
        if remaining > 0:
            if remaining == 1:
                parts.append("Just one more square to go!")
            elif remaining <= 5:
                parts.append(f"Only {remaining} squares left!")
        
        return " ".join(parts)
    
    # Voice command handlers
    
    async def _handle_item_spotted(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle item spotting from voice"""
        return {
            "type": "spot_item",
            "data": {"raw_command": command}
        }
    
    async def _handle_bingo_call(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle bingo call"""
        return {
            "type": "call_bingo",
            "data": {}
        }
    
    async def _handle_card_status(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle card status request"""
        return {
            "type": "get_card",
            "data": {}
        }
    
    async def _handle_suggestion_request(self, command: str, session: GameSession) -> Dict[str, Any]:
        """Handle suggestion request"""
        return {
            "type": "get_suggestions",
            "data": {}
        }
