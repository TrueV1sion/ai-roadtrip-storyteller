#!/usr/bin/env python3
"""
Main entry point for running AI Road Trip Storyteller simulations
Provides various simulation scenarios and test configurations
"""

import asyncio
import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

# Add scripts directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulation_engine import SimulationEngine, UserPersona, JourneyType
from user_simulator import UserSimulator
from route_simulator import RouteSimulator
from simulation_dashboard import run_simulation_with_dashboard


class SimulationScenarios:
    """Pre-defined simulation scenarios for different test cases"""
    
    @staticmethod
    def peak_traffic_scenario():
        """Simulate peak traffic conditions"""
        return {
            "name": "Peak Traffic",
            "description": "Heavy load during commute hours",
            "num_users": 500,
            "duration_minutes": 30,
            "concurrent_users": 100,
            "user_distribution": {
                "business_traveler": 0.4,
                "rideshare_driver": 0.3,
                "family": 0.15,
                "young_professional": 0.15
            },
            "time_of_day": "rush_hour"
        }
        
    @staticmethod
    def weekend_leisure_scenario():
        """Simulate weekend leisure travel"""
        return {
            "name": "Weekend Leisure",
            "description": "Family trips and adventure seekers",
            "num_users": 200,
            "duration_minutes": 60,
            "concurrent_users": 50,
            "user_distribution": {
                "family": 0.4,
                "adventure_seeker": 0.2,
                "nature_lover": 0.15,
                "foodie": 0.15,
                "couple_romantic": 0.1
            },
            "time_of_day": "weekend_morning"
        }
        
    @staticmethod
    def voice_interaction_stress_test():
        """Test voice interaction system under load"""
        return {
            "name": "Voice Stress Test",
            "description": "High frequency voice commands",
            "num_users": 100,
            "duration_minutes": 20,
            "concurrent_users": 50,
            "interaction_frequency_multiplier": 2.0,
            "focus_interactions": ["voice_command", "story_request", "trivia_game"]
        }
        
    @staticmethod
    def booking_conversion_test():
        """Test booking and reservation system"""
        return {
            "name": "Booking Conversion",
            "description": "Focus on users likely to make bookings",
            "num_users": 150,
            "duration_minutes": 45,
            "concurrent_users": 30,
            "user_distribution": {
                "foodie": 0.3,
                "business_traveler": 0.25,
                "family": 0.25,
                "couple_romantic": 0.2
            },
            "booking_probability_boost": 0.3
        }
        
    @staticmethod
    def multi_day_journey_scenario():
        """Test long-distance multi-day journeys"""
        return {
            "name": "Multi-Day Journey",
            "description": "Cross-country and long trips",
            "num_users": 50,
            "duration_minutes": 90,
            "concurrent_users": 20,
            "journey_types": [
                JourneyType.CROSS_COUNTRY,
                JourneyType.SCENIC_ROUTE,
                JourneyType.HISTORICAL_TOUR
            ],
            "min_journey_duration": 480  # 8 hours minimum
        }
        
    @staticmethod
    def seasonal_variation_test():
        """Test different seasonal conditions"""
        return {
            "name": "Seasonal Variation",
            "description": "Various weather and seasonal conditions",
            "num_users": 100,
            "duration_minutes": 40,
            "concurrent_users": 25,
            "seasons": ["summer", "winter", "fall", "spring"],
            "weather_conditions": ["clear", "rain", "snow", "fog"]
        }
        

async def run_scenario(scenario: Dict[str, Any]):
    """Run a specific simulation scenario"""
    print(f"\n{'='*80}")
    print(f"Running Scenario: {scenario['name']}")
    print(f"Description: {scenario['description']}")
    print(f"{'='*80}\n")
    
    # Create custom simulation engine with scenario parameters
    async with SimulationEngine() as engine:
        # Generate users based on scenario
        user_sim = UserSimulator()
        
        if "user_distribution" in scenario:
            users = user_sim.generate_batch(
                scenario["num_users"],
                scenario["user_distribution"]
            )
        else:
            users = user_sim.generate_batch(scenario["num_users"])
            
        # Apply scenario-specific modifications
        if "interaction_frequency_multiplier" in scenario:
            for user in users:
                user.interaction_frequency *= scenario["interaction_frequency_multiplier"]
                
        if "booking_probability_boost" in scenario:
            for user in users:
                user.booking_probability = min(
                    1.0, 
                    user.booking_probability + scenario["booking_probability_boost"]
                )
                
        # Add users to engine
        for user in users:
            engine.users[user.id] = user
        engine.metrics["total_users"] = len(users)
        
        # Run simulation
        await engine.run_load_test(
            scenario["num_users"],
            scenario["duration_minutes"],
            scenario["concurrent_users"]
        )
        
        # Generate report
        metrics = engine.get_metrics_summary()
        
        # Save scenario results
        results = {
            "scenario": scenario,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
        filename = f"scenario_{scenario['name'].lower().replace(' ', '_')}_{int(datetime.now().timestamp())}.json"
        with open(filename, 'w') as f:
            json.dump(results, f, indent=2)
            
        print(f"\nScenario '{scenario['name']}' completed.")
        print(f"Results saved to: {filename}")
        
        # Print summary
        print("\nSummary:")
        print(f"  Total Interactions: {metrics['summary']['total_interactions']}")
        print(f"  Error Rate: {metrics['summary']['error_rate']:.1%}")
        print(f"  Avg Response Time: {metrics['response_times'].get('mean', 0):.3f}s")
        print(f"  Booking Conversion: {metrics['bookings']['conversion_rate']:.1%}")
        

async def run_all_scenarios():
    """Run all pre-defined scenarios"""
    scenarios = [
        SimulationScenarios.peak_traffic_scenario(),
        SimulationScenarios.weekend_leisure_scenario(),
        SimulationScenarios.voice_interaction_stress_test(),
        SimulationScenarios.booking_conversion_test(),
        SimulationScenarios.multi_day_journey_scenario(),
        SimulationScenarios.seasonal_variation_test()
    ]
    
    print(f"Running {len(scenarios)} simulation scenarios...")
    
    for scenario in scenarios:
        await run_scenario(scenario)
        
    print("\nAll scenarios completed!")
    

async def run_custom_simulation(config_file: str):
    """Run simulation from custom configuration file"""
    with open(config_file, 'r') as f:
        config = json.load(f)
        
    await run_scenario(config)
    

def create_sample_config():
    """Create a sample configuration file"""
    sample_config = {
        "name": "Custom Simulation",
        "description": "Custom simulation configuration",
        "num_users": 100,
        "duration_minutes": 30,
        "concurrent_users": 25,
        "user_distribution": {
            "family": 0.3,
            "business_traveler": 0.2,
            "adventure_seeker": 0.2,
            "foodie": 0.15,
            "history_buff": 0.15
        },
        "interaction_frequency_multiplier": 1.0,
        "booking_probability_boost": 0.0,
        "api_base_url": "http://localhost:8000"
    }
    
    with open("simulation_config_sample.json", 'w') as f:
        json.dump(sample_config, f, indent=2)
        
    print("Sample configuration created: simulation_config_sample.json")
    

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="AI Road Trip Storyteller Simulation Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with interactive dashboard
  python run_simulation.py --mode dashboard
  
  # Run specific scenario
  python run_simulation.py --scenario peak_traffic
  
  # Run all scenarios
  python run_simulation.py --mode all_scenarios
  
  # Run custom configuration
  python run_simulation.py --config my_config.json
  
  # Create sample configuration
  python run_simulation.py --create-sample
        """
    )
    
    parser.add_argument(
        "--mode",
        choices=["dashboard", "scenario", "all_scenarios", "custom"],
        default="dashboard",
        help="Simulation mode"
    )
    
    parser.add_argument(
        "--scenario",
        choices=[
            "peak_traffic",
            "weekend_leisure", 
            "voice_stress",
            "booking_conversion",
            "multi_day",
            "seasonal"
        ],
        help="Pre-defined scenario to run"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        help="Path to custom configuration file"
    )
    
    parser.add_argument(
        "--users",
        type=int,
        default=100,
        help="Number of users (for dashboard mode)"
    )
    
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration in minutes (for dashboard mode)"
    )
    
    parser.add_argument(
        "--concurrent",
        type=int,
        default=25,
        help="Concurrent users (for dashboard mode)"
    )
    
    parser.add_argument(
        "--create-sample",
        action="store_true",
        help="Create sample configuration file"
    )
    
    args = parser.parse_args()
    
    if args.create_sample:
        create_sample_config()
        return
        
    if args.mode == "dashboard":
        # Run with interactive dashboard
        asyncio.run(run_simulation_with_dashboard(
            args.users,
            args.duration,
            args.concurrent
        ))
        
    elif args.mode == "scenario":
        if not args.scenario:
            print("Error: --scenario required for scenario mode")
            parser.print_help()
            return
            
        # Map scenario names to functions
        scenario_map = {
            "peak_traffic": SimulationScenarios.peak_traffic_scenario,
            "weekend_leisure": SimulationScenarios.weekend_leisure_scenario,
            "voice_stress": SimulationScenarios.voice_interaction_stress_test,
            "booking_conversion": SimulationScenarios.booking_conversion_test,
            "multi_day": SimulationScenarios.multi_day_journey_scenario,
            "seasonal": SimulationScenarios.seasonal_variation_test
        }
        
        scenario = scenario_map[args.scenario]()
        asyncio.run(run_scenario(scenario))
        
    elif args.mode == "all_scenarios":
        asyncio.run(run_all_scenarios())
        
    elif args.mode == "custom":
        if not args.config:
            print("Error: --config required for custom mode")
            parser.print_help()
            return
            
        asyncio.run(run_custom_simulation(args.config))
        

if __name__ == "__main__":
    main()