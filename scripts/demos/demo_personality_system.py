"""
Demo script for the Dynamic Personality System

Shows how the system automatically selects appropriate voice personalities
based on various contextual factors.
"""

import asyncio
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from backend.app.services.dynamic_personality_system import (
    DynamicPersonalitySystem,
    PersonalityContext
)
from backend.app.services.personality_integration import PersonalityIntegrationService
from backend.app.services.personality_registry import personality_registry

console = Console()


async def demo_personality_selection():
    """Demonstrate personality selection for various scenarios"""
    system = DynamicPersonalitySystem()
    integration = PersonalityIntegrationService()
    
    console.print("\n[bold cyan]🎭 AI Road Trip Dynamic Personality System Demo[/bold cyan]\n")
    
    # Define test scenarios
    scenarios = [
        {
            "name": "Disney Family Trip",
            "context": PersonalityContext(
                event_metadata={
                    "name": "Disneyland Magic",
                    "venue": {"name": "Disneyland Park"},
                    "classifications": [{"segment": "theme_park", "genre": "disney"}]
                },
                location={"state": "california", "city": "anaheim"},
                datetime=datetime(2024, 7, 15, 10, 0),
                passenger_info={"passengers": [{"age": 35}, {"age": 8}], "count": 2},
                journey_type="family_vacation"
            )
        },
        {
            "name": "Christmas Eve Journey",
            "context": PersonalityContext(
                datetime=datetime(2024, 12, 24, 18, 0),
                location={"state": "colorado", "city": "denver"},
                weather={"condition": "snow", "temperature": 25},
                special_occasion="christmas_eve"
            )
        },
        {
            "name": "Rock Concert Night",
            "context": PersonalityContext(
                event_metadata={
                    "name": "Metallica Live",
                    "venue": {"name": "Red Rocks Amphitheatre"},
                    "classifications": [{"segment": "music", "genre": "rock"}]
                },
                datetime=datetime(2024, 8, 15, 20, 0),
                user_mood="excited",
                journey_type="entertainment"
            )
        },
        {
            "name": "Broadway Show Evening",
            "context": PersonalityContext(
                event_metadata={
                    "name": "Hamilton",
                    "venue": {"name": "Richard Rodgers Theatre"},
                    "classifications": [{"segment": "arts & theatre", "genre": "musical"}]
                },
                location={"state": "new york", "city": "new york"},
                datetime=datetime(2024, 9, 20, 19, 30)
            )
        },
        {
            "name": "Texas BBQ Festival",
            "context": PersonalityContext(
                event_metadata={
                    "name": "Austin BBQ Festival",
                    "classifications": [{"segment": "food", "genre": "festival"}]
                },
                location={"state": "texas", "city": "austin"},
                datetime=datetime(2024, 6, 1, 14, 0),
                weather={"condition": "sunny", "temperature": 92}
            )
        },
        {
            "name": "Valentine's Date Night",
            "context": PersonalityContext(
                datetime=datetime(2024, 2, 14, 19, 0),
                special_occasion="date_night",
                user_mood="romantic",
                journey_type="romantic_dinner"
            )
        },
        {
            "name": "Halloween Ghost Tour",
            "context": PersonalityContext(
                event_metadata={
                    "name": "Haunted New Orleans Tour",
                    "classifications": [{"segment": "tour", "genre": "ghost"}]
                },
                datetime=datetime(2024, 10, 31, 21, 0),
                location={"state": "louisiana", "city": "new orleans"},
                weather={"condition": "foggy", "temperature": 68}
            )
        },
        {
            "name": "Morning Workout Drive",
            "context": PersonalityContext(
                datetime=datetime(2024, 5, 15, 6, 0),
                user_mood="motivated",
                journey_type="fitness",
                special_occasion="workout"
            )
        }
    ]
    
    # Process each scenario
    for scenario in scenarios:
        console.print(f"\n[bold yellow]📍 Scenario: {scenario['name']}[/bold yellow]")
        
        # Get personality selection
        result = await integration.select_personality_for_journey(
            user_id="demo_user",
            journey_data=_context_to_journey_data(scenario["context"]),
            user_preferences=None
        )
        
        # Display results
        personality = result.selected_personality
        
        # Create info panel
        info = Panel(
            f"[green]Selected: {personality.name}[/green]\n"
            f"Description: {personality.description}\n"
            f"Confidence: {result.confidence_score:.0%}\n"
            f"Reason: {result.selection_reason}",
            title="🎭 Personality Selection",
            border_style="cyan"
        )
        console.print(info)
        
        # Show greeting
        greeting = integration.personality_engine.get_personality_greeting(personality)
        console.print(f"[italic]Greeting: \"{greeting}\"[/italic]")
        
        # Show alternatives
        if result.alternatives:
            table = Table(title="Alternative Personalities", show_header=True)
            table.add_column("Personality", style="cyan")
            table.add_column("Score", style="yellow")
            
            for alt_personality, score in result.alternatives[:3]:
                table.add_row(alt_personality.name, f"{score:.1f}")
            
            console.print(table)
        
        # Show context analysis
        if result.context_analysis:
            analysis_text = Text()
            analysis_text.append("Context Analysis:\n", style="bold")
            for key, value in result.context_analysis.items():
                if isinstance(value, list):
                    analysis_text.append(f"  {key}: {', '.join(value)}\n")
                elif isinstance(value, dict):
                    analysis_text.append(f"  {key}: {value}\n")
            
            console.print(Panel(analysis_text, border_style="dim"))
        
        await asyncio.sleep(0.5)  # Brief pause between scenarios


def _context_to_journey_data(context: PersonalityContext) -> dict:
    """Convert PersonalityContext to journey data format"""
    data = {}
    
    if context.event_metadata:
        data["event_metadata"] = context.event_metadata
        data["event_name"] = context.event_metadata.get("name", "")
    
    if context.location:
        data["destination_state"] = context.location.get("state")
        data["destination_city"] = context.location.get("city")
    
    if context.journey_type:
        data["journey_type"] = context.journey_type
    
    if context.passenger_info:
        data.update(context.passenger_info)
    
    if context.special_occasion:
        data["special_occasion"] = context.special_occasion
    
    if context.user_mood:
        data["user_mood"] = context.user_mood
    
    return data


async def show_personality_catalog():
    """Display the complete personality catalog"""
    console.print("\n[bold cyan]📚 Personality Catalog[/bold cyan]\n")
    
    categories = ["event", "holiday", "regional", "time_based", "mood_based", "special"]
    
    for category in categories:
        personalities = personality_registry.get_personalities_by_category(category)
        
        if personalities:
            table = Table(title=f"{category.title()} Personalities", show_header=True)
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="yellow")
            table.add_column("Priority", style="green")
            table.add_column("Key Traits", style="white")
            
            for p in sorted(personalities, key=lambda x: x.priority, reverse=True)[:5]:
                traits = ", ".join(p.personality_traits[:3]) if p.personality_traits else "N/A"
                table.add_row(
                    p.id,
                    p.name,
                    str(p.priority),
                    traits
                )
            
            console.print(table)
            console.print()


async def show_active_personalities():
    """Show currently active personalities based on time/date"""
    console.print("\n[bold cyan]🌟 Currently Active Special Personalities[/bold cyan]\n")
    
    current_time = datetime.now()
    active = []
    
    for p_id, metadata in personality_registry.personalities.items():
        reasons = []
        
        # Check time slots
        if metadata.time_slots:
            hour = current_time.hour
            time_slot = ("morning" if 5 <= hour < 12 else
                        "afternoon" if 12 <= hour < 17 else
                        "evening" if 17 <= hour < 21 else "night")
            
            if time_slot in metadata.time_slots:
                reasons.append(f"Active during {time_slot}")
        
        # Check months
        if metadata.active_months and current_time.month in metadata.active_months:
            reasons.append(f"Active in {current_time.strftime('%B')}")
        
        # Check specific dates
        if metadata.active_dates:
            current_date = (current_time.month, current_time.day)
            if current_date in metadata.active_dates:
                reasons.append("Special date activation")
        
        if reasons or (not metadata.time_slots and not metadata.active_months and not metadata.active_dates):
            active.append({
                "id": p_id,
                "name": metadata.name,
                "category": metadata.category,
                "reasons": reasons or ["Always available"],
                "priority": metadata.priority
            })
    
    # Sort by priority and category
    active.sort(key=lambda x: (x["category"] != "holiday", -x["priority"]))
    
    # Display
    table = Table(show_header=True)
    table.add_column("Personality", style="cyan")
    table.add_column("Category", style="yellow")
    table.add_column("Priority", style="green")
    table.add_column("Active Because", style="white")
    
    for item in active[:10]:  # Show top 10
        table.add_row(
            item["name"],
            item["category"],
            str(item["priority"]),
            " | ".join(item["reasons"])
        )
    
    console.print(table)
    console.print(f"\n[dim]Current time: {current_time.strftime('%Y-%m-%d %H:%M')}[/dim]")


async def main():
    """Run the complete demo"""
    console.print("[bold green]Welcome to the Dynamic Personality System Demo![/bold green]")
    
    # Show personality catalog
    await show_personality_catalog()
    
    # Show active personalities
    await show_active_personalities()
    
    # Run personality selection demo
    await demo_personality_selection()
    
    # Show analytics
    system = DynamicPersonalitySystem()
    analytics = system.get_analytics()
    
    if analytics.get("total_selections", 0) > 0:
        console.print("\n[bold cyan]📊 Selection Analytics[/bold cyan]")
        console.print(f"Total selections: {analytics['total_selections']}")
        
        if analytics.get("most_popular"):
            console.print(f"Most popular: {analytics['most_popular']}")


if __name__ == "__main__":
    asyncio.run(main())