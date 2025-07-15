# Unified AI Client Documentation

## Overview

The Unified AI Client is a centralized component that provides a consistent interface for all AI operations in the AI Road Trip Storyteller application. It abstracts away the details of specific AI providers and models, making it easy to switch between different AI backends without changing the application code.

## Key Features

- **Multiple AI Provider Support**: Designed to work with Google Vertex AI (Gemini), with easy extensibility for other providers like Anthropic or OpenAI.
- **Consistent Interface**: All AI operations use the same interface, regardless of the underlying provider.
- **Storytelling Styles**: Supports multiple predefined storytelling styles that adjust the AI's parameters and prompts.
- **Personalization**: Built-in support for personalized content generation based on user preferences.
- **Conversation Context**: Maintains session history for multi-turn interactions.
- **Content Safety**: Implements content filtering and cleaning for inappropriate content.
- **Fallbacks**: Provides graceful degradation with fallback content when AI generation fails.
- **Metrics and Logging**: Comprehensive logging and performance metrics for monitoring and debugging.

## Usage

### Basic Story Generation

The most common use case is generating a location-based story:

```python
story_result = await unified_ai_client.generate_story(
    location={"latitude": 37.7749, "longitude": -122.4194},
    interests=["history", "architecture"],
    context={"time_of_day": "evening", "weather": "clear"},
    style=StoryStyle.FAMILY
)

print(story_result["text"])  # The generated story
```

### Personalized Generation

For personalized content based on user preferences:

```python
story_result = await unified_ai_client.generate_personalized_story(
    user_id="user123",
    location={"latitude": 37.7749, "longitude": -122.4194},
    interests=["history", "architecture"],
    user_preferences={
        "storytelling_style": "educational",
        "preferred_voice": "warm",
        "include_facts": True
    }
)
```

### Multi-turn Conversations

For maintaining context across multiple interactions:

```python
# First interaction
story_result = await unified_ai_client.generate_story(
    location={"latitude": 37.7749, "longitude": -122.4194},
    interests=["history"],
    conversation_id="session123"
)

# Later interaction (maintains context)
follow_up = await unified_ai_client.generate_story(
    location={"latitude": 37.7749, "longitude": -122.4194},
    interests=["architecture"],
    context={"special_requests": "Tell me more about the buildings"},
    conversation_id="session123"  # Same session ID keeps context
)
```

## Storytelling Styles

The client supports various predefined storytelling styles:

- **DEFAULT**: Balanced approach suitable for most situations
- **EDUCATIONAL**: Focuses on factual information and learning
- **ENTERTAINING**: Emphasizes fun, humor, and engagement
- **FAMILY**: Designed for all ages, with appropriate content
- **HISTORIC**: Emphasizes historical facts and context
- **ADVENTURE**: Focuses on exploration and discovery
- **MYSTERY**: Creates intrigue with legends and local lore

Each style adjusts the AI's parameters:

```python
# Generate an educational story
story_result = await unified_ai_client.generate_story(
    location={"latitude": 37.7749, "longitude": -122.4194},
    interests=["history"],
    style=StoryStyle.EDUCATIONAL
)
```

## Response Format

The client returns a dictionary with:

```python
{
    "text": "The generated story text...",
    "provider": "google",  # The AI provider used
    "model": "gemini-1.5-flash",  # The specific model used
    "style": "family",  # The storytelling style used
    "generation_time": 1.24,  # Time taken in seconds
    "word_count": 245,  # Number of words in the story
    "sentiment": "positive",  # Overall sentiment of the story
    "is_fallback": False  # Whether this is fallback content
}
```

## Error Handling

The client handles errors gracefully:

1. **Initialization Failures**: If the AI provider cannot be initialized, the client will attempt to use a fallback.
2. **Generation Failures**: If story generation fails, a fallback story is provided.
3. **Content Safety Issues**: If inappropriate content is detected, it's either cleaned or replaced with fallback content.

## Advanced Topics

### Customizing System Prompts

The system prompts that define the AI's behavior can be customized:

```python
# Access the client's system templates
template = unified_ai_client.system_templates[StoryStyle.EDUCATIONAL]

# Modify a template (not generally recommended)
unified_ai_client.system_templates[StoryStyle.EDUCATIONAL] = "New system prompt..."
```

### Location Enhancement

The client automatically enhances prompts with location information:

```python
# This happens automatically, but can be customized
enhanced_prompt = unified_ai_client._enhance_system_prompt_with_location(
    system_prompt="Base prompt...",
    location={"latitude": 37.7749, "longitude": -122.4194}
)
```

## Implementation Details

### Provider-Specific Implementations

The client uses different implementations for different providers:

```python
# Google's Vertex AI
if self.provider == AIModelProvider.GOOGLE:
    return await self._generate_with_vertex(system_prompt, user_prompt, style)
# Could add other providers
else:
    logger.warning(f"Provider {self.provider} not implemented")
    return await self._generate_with_vertex(system_prompt, user_prompt, style)
```

### Generation Parameters

Parameters are tuned for each storytelling style:

```python
# For educational style
if style == StoryStyle.EDUCATIONAL:
    temperature = 0.5  # More factual
    top_p = 0.85
# For entertaining style
elif style == StoryStyle.ENTERTAINING:
    temperature = 0.8  # More creative
    top_p = 0.95
```

## Configuration

Configuration is loaded from app settings:

```python
# In config.py
DEFAULT_AI_PROVIDER: str = "google"  # Options: google, anthropic, openai
GOOGLE_AI_MODEL: str = "gemini-1.5-flash"
GOOGLE_AI_PROJECT_ID: str
GOOGLE_AI_LOCATION: str = "us-central1"
```

## Best Practices

1. **Initialization**: Initialize the client early in the application lifecycle
2. **Error Handling**: Always handle potential errors from AI generation
3. **User Context**: Provide as much relevant context as possible for better results
4. **Rate Limiting**: Implement rate limiting for fair usage
5. **Content Safety**: Always use the client's built-in content safety mechanisms
6. **Performance Monitoring**: Monitor generation times and fallback rates

## When to Use

- **Direct User Interactions**: Stories, explanations, narratives
- **Content Generation**: Creating location-based content
- **Personalized Experiences**: User-specific content
- **Interactive Features**: Features requiring ongoing conversation

## Roadmap

Future enhancements planned for the Unified AI Client:

1. Support for additional AI providers
2. Improved content safety filters
3. Enhanced context handling for longer conversations
4. Fine-tuned domain-specific models
5. Better caching and optimization
6. Support for image inputs and multimodal generation

## Contributing

When extending the Unified AI Client:

1. Maintain the consistent interface
2. Add extensive error handling
3. Include comprehensive logging
4. Write tests for new functionality
5. Update this documentation

## Debugging

For debugging issues:

1. Enable verbose logging
2. Check initialization errors
3. Verify API keys and permissions
4. Inspect the generated prompts
5. Test with simplified inputs
6. Verify model availability