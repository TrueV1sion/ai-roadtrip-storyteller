# Dynamic Personality System Documentation

## Overview

The Dynamic Personality System is a comprehensive framework that automatically selects and manages voice personalities for the AI Road Trip Storyteller based on multiple contextual factors. The system creates immersive, contextually appropriate experiences by matching voice personalities to events, locations, times, and user preferences.

## Key Features

### 1. **Multi-Factor Personality Selection**
The system considers multiple factors when selecting a personality:
- **Event Type**: Concerts, sports, theater, theme parks
- **Venue**: Specific locations trigger special personalities
- **Holiday/Season**: Seasonal personalities activate automatically
- **Location/Region**: Regional accents and local experts
- **Time of Day**: Morning motivators, sunset poets, night owls
- **Weather**: Weather-appropriate personalities
- **User Preferences**: Mood, energy level, formality
- **Special Occasions**: Weddings, birthdays, anniversaries

### 2. **Personality Categories**

#### Event Personalities
- **Mickey Mouse**: Disney trips and family entertainment
- **Rock Star**: Rock concerts and music festivals
- **Broadway Diva**: Theater and musicals
- **Sports Announcer**: Football, basketball, baseball games
- **Jazz Cat**: Jazz clubs and smooth evening events

#### Holiday Personalities
- **Santa Claus**: Christmas season (Dec 1-25)
- **Halloween Witch**: Halloween season (October)
- **Cupid**: Valentine's Day
- **Easter Bunny**: Easter season
- **Thanksgiving Host**: Thanksgiving week

#### Regional Personalities
- **Texas Ranger**: Texas and Southwest
- **Southern Belle**: Southern hospitality
- **Beach Guru**: California, Florida, Hawaii
- **Mountain Sage**: Colorado, Utah, Montana
- **Cajun Guide**: Louisiana and bayou country

#### Time-Based Personalities
- **Morning Motivator**: 5 AM - 9 AM
- **Sunset Romantic**: Golden hour (5 PM - 8 PM)
- **Midnight Mystic**: Late night (10 PM - 4 AM)

#### Special Theme Personalities
- **Time Traveler**: Historical sites and museums
- **Alien Ambassador**: Space centers and sci-fi events
- **Pirate Captain**: Maritime adventures
- **Superhero**: Comic conventions and theme parks

### 3. **Intelligent Selection Algorithm**

The system uses a sophisticated scoring algorithm:

```python
Score = Base Priority + Context Matches + User Preferences - Exclusions
```

**Scoring Weights:**
- Event type match: +30 points
- Venue match: +25 points
- Active holiday: +40 points
- Regional match: +20 points
- Time slot match: +15 points
- Weather match: +10 points
- User mood match: +15 points
- Special occasion: +25 points
- User preference: +20 points

### 4. **Exclusion Rules**

Some personalities have exclusion rules for safety or appropriateness:
- Halloween Narrator excluded when young children present
- Adult-only personalities excluded for family trips
- Weather-dependent personalities (Beach Guru requires warm weather)

## API Usage

### Select Personality for Journey

```python
POST /api/personality/select
{
    "journey_data": {
        "event_metadata": {
            "name": "Disneyland Visit",
            "venue": {"name": "Disneyland Park"},
            "classifications": [{"segment": "theme_park"}]
        },
        "destination_state": "california",
        "destination_city": "anaheim",
        "journey_type": "family_vacation",
        "passengers": [
            {"age": 35},
            {"age": 8}
        ]
    },
    "user_mood": "excited"
}
```

**Response:**
```json
{
    "selected": {
        "id": "mickey_mouse",
        "name": "Mickey Mouse",
        "description": "The one and only Mickey Mouse...",
        "greeting": "Oh boy! Ha-ha! Welcome to the most magical place on Earth!"
    },
    "confidence_score": 0.95,
    "selection_reason": "Perfect for Disneyland Visit | Ideal for family vacation",
    "alternatives": [
        {"id": "friendly_guide", "name": "Alex the Guide", "score": 85.0}
    ],
    "context_analysis": {
        "primary_factors": ["event-driven"],
        "time_analysis": {"period": "morning", "day_type": "weekend"}
    }
}
```

### Get Personality Recommendations

```python
GET /api/personality/recommendations?event_type=concert&mood=excited
```

### Preview Personality

```python
GET /api/personality/preview/rock_star?sample_text=Welcome to the show!
```

### Get Active Personalities

```python
GET /api/personality/active
```

Shows which special personalities are currently active based on time, date, and season.

### Submit Feedback

```python
POST /api/personality/feedback
{
    "personality_id": "mickey_mouse",
    "rating": 5,
    "feedback": "Perfect for our Disney trip!"
}
```

## Integration with Voice System

The Dynamic Personality System integrates seamlessly with the existing voice infrastructure:

1. **Voice Settings**: Each personality has specific voice parameters (pitch, speed, emphasis)
2. **Text Adaptation**: Text is automatically adjusted to match personality style
3. **Catchphrases**: Personalities use signature phrases and greetings
4. **Emotional Range**: Different personalities express different emotions

## Use Cases

### 1. **Disney Family Trip**
- **Selected**: Mickey Mouse
- **Features**: High energy, magical phrases, child-friendly
- **Greeting**: "Oh boy! Ha-ha! Welcome to the most magical place on Earth!"

### 2. **Christmas Eve Journey**
- **Selected**: Santa Claus
- **Features**: Jolly, warm, holiday-themed
- **Greeting**: "Ho ho ho! Merry travelers!"

### 3. **Rock Concert Night**
- **Selected**: Rock DJ
- **Features**: High energy, music slang, excitement
- **Greeting**: "Let's rock and roll! This is gonna be EPIC!"

### 4. **Texas BBQ Festival**
- **Selected**: Texas Ranger
- **Features**: Texas drawl, pride, BBQ knowledge
- **Greeting**: "Howdy, partners! Everything's bigger in Texas!"

### 5. **Valentine's Date Night**
- **Selected**: Cupid
- **Features**: Romantic, sweet, love-themed
- **Greeting**: "Love is in the air! How romantic!"

## Configuration

### Adding New Personalities

1. Add to `personality_registry.py`:
```python
self.personalities["new_personality"] = ExtendedPersonalityMetadata(
    id="new_personality",
    name="Personality Name",
    category="event",  # or holiday, regional, etc.
    priority=80,
    event_types=["event_type"],
    personality_traits=["trait1", "trait2"],
    enthusiasm_level=0.8,
    # ... other metadata
)
```

2. Create VoicePersonality in `dynamic_personality_system.py`:
```python
"new_personality": VoicePersonality(
    id="new_personality",
    name="Personality Name",
    description="Description",
    voice_id="en-US-Neural2-X",
    speaking_style={...},
    catchphrases=[...],
    # ... other properties
)
```

### Adjusting Selection Weights

Modify scoring weights in `_calculate_personality_scores()`:
```python
# Event type matching (highest weight)
if event_type in metadata.event_types:
    score += 30  # Adjust this value
```

## Performance Considerations

1. **Caching**: Personality selections are cached for 1 hour
2. **Preloading**: All personality metadata loaded at startup
3. **Async Operations**: All selection operations are async
4. **Analytics**: Selection history limited to last 1000 entries

## Testing

Run comprehensive tests:
```bash
pytest tests/unit/test_dynamic_personality_system.py -v
```

Run the demo:
```bash
python demo_personality_system.py
```

## Future Enhancements

1. **Machine Learning**: Learn user preferences over time
2. **Custom Personalities**: User-created personalities
3. **Voice Cloning**: Clone specific celebrity voices (with permission)
4. **Multi-Language**: Personalities in different languages
5. **Emotion Detection**: Adapt based on user's emotional state
6. **Group Dynamics**: Different personalities for group trips