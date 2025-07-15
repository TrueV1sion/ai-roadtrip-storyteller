"""
Comprehensive Voice Interaction Test Scenarios
50+ test cases covering various voice interactions, accents, and edge cases
"""
import json
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import numpy as np


class VoiceTestCategory(Enum):
    NAVIGATION = "navigation"
    BOOKING = "booking"
    ENTERTAINMENT = "entertainment"
    INFORMATION = "information"
    SAFETY = "safety"
    PREFERENCES = "preferences"
    EMERGENCY = "emergency"
    FAMILY = "family"
    RIDESHARE = "rideshare"
    MULTILINGUAL = "multilingual"


@dataclass
class VoiceTestScenario:
    id: str
    category: VoiceTestCategory
    command: str
    expected_intent: str
    expected_response_pattern: str
    context: Dict[str, any]
    background_noise_level: str  # quiet, moderate, loud
    accent: str  # standard, southern, british, spanish, etc.
    speech_rate: str  # slow, normal, fast
    priority: str  # critical, high, medium, low
    safety_critical: bool = False


class VoiceTestSuite:
    """Comprehensive voice interaction test suite"""
    
    def __init__(self):
        self.test_scenarios = self._create_test_scenarios()
        self.noise_profiles = self._create_noise_profiles()
        self.accent_profiles = self._create_accent_profiles()
    
    def _create_test_scenarios(self) -> List[VoiceTestScenario]:
        """Create 50+ comprehensive voice test scenarios"""
        scenarios = []
        
        # Navigation Commands (10 scenarios)
        navigation_commands = [
            ("Navigate to Disneyland", "navigate_to_destination", "I'll help you get to Disneyland"),
            ("Take me to the nearest gas station", "find_nearby_poi", "Finding the nearest gas station"),
            ("Find a scenic route to San Francisco", "navigate_scenic", "I'll find a beautiful route"),
            ("Avoid highways on this route", "modify_route_preferences", "Updating route to avoid highways"),
            ("How long until we arrive", "get_eta", "You'll arrive in approximately"),
            ("Add a stop at Starbucks", "add_waypoint", "Adding Starbucks to your route"),
            ("Cancel current navigation", "cancel_navigation", "Navigation cancelled"),
            ("Take the next exit", "navigation_instruction", "Taking the next exit"),
            ("Find an alternate route", "find_alternate_route", "Looking for alternate routes"),
            ("What's the traffic like ahead", "check_traffic", "Checking traffic conditions"),
        ]
        
        for i, (command, intent, response) in enumerate(navigation_commands):
            scenarios.append(VoiceTestScenario(
                id=f"NAV-{i+1:03d}",
                category=VoiceTestCategory.NAVIGATION,
                command=command,
                expected_intent=intent,
                expected_response_pattern=response,
                context={"driving": True, "speed": 65},
                background_noise_level="moderate",
                accent="standard",
                speech_rate="normal",
                priority="high",
                safety_critical=True
            ))
        
        # Booking Commands (8 scenarios)
        booking_commands = [
            ("Book a hotel for tonight", "book_hotel", "I'll help you find a hotel"),
            ("Find restaurants near me", "find_restaurants", "Looking for restaurants nearby"),
            ("Reserve a table for four at seven PM", "make_reservation", "Making a reservation for 4"),
            ("Book the cheapest hotel available", "book_hotel_budget", "Finding budget-friendly hotels"),
            ("Cancel my hotel reservation", "cancel_booking", "Cancelling your reservation"),
            ("Find Italian restaurants with outdoor seating", "find_specific_restaurants", "Searching for Italian restaurants"),
            ("Book parking at LAX for tomorrow", "book_parking", "Booking parking at LAX"),
            ("Show me pet friendly hotels", "find_pet_hotels", "Finding pet-friendly accommodations"),
        ]
        
        for i, (command, intent, response) in enumerate(booking_commands):
            scenarios.append(VoiceTestScenario(
                id=f"BOOK-{i+1:03d}",
                category=VoiceTestCategory.BOOKING,
                command=command,
                expected_intent=intent,
                expected_response_pattern=response,
                context={"location": {"lat": 34.0522, "lng": -118.2437}},
                background_noise_level="quiet",
                accent="standard",
                speech_rate="normal",
                priority="high",
                safety_critical=False
            ))
        
        # Entertainment Commands (6 scenarios)
        entertainment_commands = [
            ("Start a trivia game", "start_trivia", "Starting trivia game"),
            ("Play some road trip music", "play_music", "Playing road trip playlist"),
            ("Tell me a story about this area", "play_location_story", "Here's an interesting story"),
            ("Create a scavenger hunt", "start_scavenger_hunt", "Creating scavenger hunt"),
            ("Play twenty questions", "start_twenty_questions", "Let's play twenty questions"),
            ("What games can we play", "list_games", "Available games include"),
        ]
        
        for i, (command, intent, response) in enumerate(entertainment_commands):
            scenarios.append(VoiceTestScenario(
                id=f"ENT-{i+1:03d}",
                category=VoiceTestCategory.ENTERTAINMENT,
                command=command,
                expected_intent=intent,
                expected_response_pattern=response,
                context={"passengers": 2},
                background_noise_level="moderate",
                accent="standard",
                speech_rate="normal",
                priority="medium",
                safety_critical=False
            ))
        
        # Information Queries (6 scenarios)
        information_queries = [
            ("What's the weather like at our destination", "get_weather", "The weather at"),
            ("Tell me about the Golden Gate Bridge", "get_poi_info", "The Golden Gate Bridge"),
            ("What's special about this area", "get_local_info", "This area is known for"),
            ("Are there any events happening tonight", "find_events", "Looking for events"),
            ("What time does the park close", "get_poi_hours", "Checking operating hours"),
            ("How much will gas cost for this trip", "calculate_fuel_cost", "Estimated fuel cost"),
        ]
        
        for i, (command, intent, response) in enumerate(information_queries):
            scenarios.append(VoiceTestScenario(
                id=f"INFO-{i+1:03d}",
                category=VoiceTestCategory.INFORMATION,
                command=command,
                expected_intent=intent,
                expected_response_pattern=response,
                context={"location": {"lat": 37.8199, "lng": -122.4783}},
                background_noise_level="quiet",
                accent="standard",
                speech_rate="normal",
                priority="medium",
                safety_critical=False
            ))
        
        # Safety Commands (5 scenarios)
        safety_commands = [
            ("Call nine one one", "emergency_call", "Calling emergency services"),
            ("Find the nearest hospital", "find_emergency_services", "Locating nearest hospital"),
            ("I need help", "emergency_assist", "How can I help you"),
            ("Report an accident ahead", "report_hazard", "Reporting road hazard"),
            ("Emergency stop navigation", "emergency_stop", "Stopping all functions"),
        ]
        
        for i, (command, intent, response) in enumerate(safety_commands):
            scenarios.append(VoiceTestScenario(
                id=f"SAFE-{i+1:03d}",
                category=VoiceTestCategory.SAFETY,
                command=command,
                expected_intent=intent,
                expected_response_pattern=response,
                context={"driving": True, "speed": 70},
                background_noise_level="loud",
                accent="standard",
                speech_rate="fast",
                priority="critical",
                safety_critical=True
            ))
        
        # Preference Commands (4 scenarios)
        preference_commands = [
            ("Switch to Mickey Mouse voice", "change_voice_personality", "Switching to Mickey Mouse"),
            ("Speak slower please", "adjust_speech_rate", "Adjusting speech rate"),
            ("Turn on family mode", "enable_family_mode", "Family mode activated"),
            ("I prefer shorter stories", "update_preferences", "Updating your preferences"),
        ]
        
        for i, (command, intent, response) in enumerate(preference_commands):
            scenarios.append(VoiceTestScenario(
                id=f"PREF-{i+1:03d}",
                category=VoiceTestCategory.PREFERENCES,
                command=command,
                expected_intent=intent,
                expected_response_pattern=response,
                context={},
                background_noise_level="quiet",
                accent="standard",
                speech_rate="normal",
                priority="low",
                safety_critical=False
            ))
        
        # Family Mode Commands (4 scenarios)
        family_commands = [
            ("Are we there yet", "check_eta_family", "We'll be there in"),
            ("I need a bathroom", "find_restroom", "Finding restrooms nearby"),
            ("Play a game for kids", "start_kids_game", "Starting a fun game"),
            ("Find a playground", "find_kids_poi", "Looking for playgrounds"),
        ]
        
        for i, (command, intent, response) in enumerate(family_commands):
            scenarios.append(VoiceTestScenario(
                id=f"FAM-{i+1:03d}",
                category=VoiceTestCategory.FAMILY,
                command=command,
                expected_intent=intent,
                expected_response_pattern=response,
                context={"family_mode": True},
                background_noise_level="loud",
                accent="child",
                speech_rate="fast",
                priority="medium",
                safety_critical=False
            ))
        
        # Rideshare Commands (3 scenarios)
        rideshare_commands = [
            ("Enable driver mode", "enable_rideshare_mode", "Driver mode activated"),
            ("Quick facts about this area", "get_rideshare_facts", "Here's a quick fact"),
            ("Passenger friendly content", "get_passenger_content", "Here's something interesting"),
        ]
        
        for i, (command, intent, response) in enumerate(rideshare_commands):
            scenarios.append(VoiceTestScenario(
                id=f"RIDE-{i+1:03d}",
                category=VoiceTestCategory.RIDESHARE,
                command=command,
                expected_intent=intent,
                expected_response_pattern=response,
                context={"rideshare_mode": True},
                background_noise_level="moderate",
                accent="standard",
                speech_rate="normal",
                priority="medium",
                safety_critical=False
            ))
        
        # Accent Variations (5 scenarios with different accents)
        accent_tests = [
            ("Navigate home", "navigate_to_saved", "Navigating to home", "southern"),
            ("Book a hotel", "book_hotel", "Finding hotels", "british"),
            ("Play music", "play_music", "Playing music", "spanish"),
            ("Find food", "find_restaurants", "Finding restaurants", "indian"),
            ("Tell me a story", "play_story", "Here's a story", "australian"),
        ]
        
        for i, (command, intent, response, accent) in enumerate(accent_tests):
            scenarios.append(VoiceTestScenario(
                id=f"ACC-{i+1:03d}",
                category=VoiceTestCategory.MULTILINGUAL,
                command=command,
                expected_intent=intent,
                expected_response_pattern=response,
                context={},
                background_noise_level="moderate",
                accent=accent,
                speech_rate="normal",
                priority="high",
                safety_critical=False
            ))
        
        # Edge Cases and Complex Commands (5 scenarios)
        edge_cases = [
            ("Um... uh... navigate to... you know... that place with the mouse",
             "navigate_unclear", "Could you clarify", "standard"),
            ("NAVIGATE TO DISNEYLAND", "navigate_to_destination", "Navigating to Disneyland", "standard"),
            ("nav 2 disney", "navigate_to_destination", "Navigating to Disneyland", "standard"),
            ("I want to go to that restaurant we went to last time near the beach with the good tacos",
             "find_previous_location", "Looking for your previous", "standard"),
            ("Play music no wait actually tell me a story no actually just navigate home",
             "multiple_intents", "I'll navigate home", "standard"),
        ]
        
        for i, (command, intent, response, accent) in enumerate(edge_cases):
            scenarios.append(VoiceTestScenario(
                id=f"EDGE-{i+1:03d}",
                category=VoiceTestCategory.NAVIGATION,
                command=command,
                expected_intent=intent,
                expected_response_pattern=response,
                context={},
                background_noise_level="moderate",
                accent=accent,
                speech_rate="varied",
                priority="high",
                safety_critical=False
            ))
        
        return scenarios
    
    def _create_noise_profiles(self) -> Dict[str, Dict[str, any]]:
        """Create background noise profiles for testing"""
        return {
            "quiet": {
                "db_level": 30,
                "description": "Quiet car, windows closed",
                "audio_file": "quiet_car.wav"
            },
            "moderate": {
                "db_level": 60,
                "description": "Highway driving, some wind noise",
                "audio_file": "highway_moderate.wav"
            },
            "loud": {
                "db_level": 80,
                "description": "Windows down, music playing, multiple passengers",
                "audio_file": "loud_environment.wav"
            },
            "extreme": {
                "db_level": 90,
                "description": "Heavy rain, emergency vehicles nearby",
                "audio_file": "extreme_noise.wav"
            }
        }
    
    def _create_accent_profiles(self) -> Dict[str, Dict[str, any]]:
        """Create accent profiles for testing"""
        return {
            "standard": {
                "description": "Standard American English",
                "pitch_variation": 1.0,
                "speed_variation": 1.0
            },
            "southern": {
                "description": "Southern US accent",
                "pitch_variation": 0.9,
                "speed_variation": 0.85
            },
            "british": {
                "description": "British English",
                "pitch_variation": 1.1,
                "speed_variation": 1.05
            },
            "spanish": {
                "description": "Spanish-accented English",
                "pitch_variation": 1.05,
                "speed_variation": 0.95
            },
            "indian": {
                "description": "Indian-accented English",
                "pitch_variation": 1.15,
                "speed_variation": 1.1
            },
            "child": {
                "description": "Child's voice",
                "pitch_variation": 1.4,
                "speed_variation": 1.2
            },
            "elderly": {
                "description": "Elderly speaker",
                "pitch_variation": 0.85,
                "speed_variation": 0.8
            }
        }
    
    def get_test_by_category(self, category: VoiceTestCategory) -> List[VoiceTestScenario]:
        """Get all tests for a specific category"""
        return [test for test in self.test_scenarios if test.category == category]
    
    def get_safety_critical_tests(self) -> List[VoiceTestScenario]:
        """Get all safety-critical tests"""
        return [test for test in self.test_scenarios if test.safety_critical]
    
    def get_tests_by_noise_level(self, noise_level: str) -> List[VoiceTestScenario]:
        """Get tests for specific noise level"""
        return [test for test in self.test_scenarios if test.background_noise_level == noise_level]
    
    def generate_test_report(self) -> Dict[str, any]:
        """Generate comprehensive test report"""
        report = {
            "total_tests": len(self.test_scenarios),
            "categories": {},
            "noise_levels": {},
            "accents": {},
            "safety_critical": len(self.get_safety_critical_tests()),
            "priorities": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0
            }
        }
        
        # Count by category
        for category in VoiceTestCategory:
            count = len(self.get_test_by_category(category))
            if count > 0:
                report["categories"][category.value] = count
        
        # Count by noise level
        for noise_level in ["quiet", "moderate", "loud"]:
            report["noise_levels"][noise_level] = len(self.get_tests_by_noise_level(noise_level))
        
        # Count by priority
        for test in self.test_scenarios:
            report["priorities"][test.priority] += 1
        
        return report


class VoiceTestRunner:
    """Runs voice tests with simulated conditions"""
    
    def __init__(self, test_suite: VoiceTestSuite):
        self.test_suite = test_suite
        self.results = []
    
    async def run_test(self, scenario: VoiceTestScenario) -> Dict[str, any]:
        """Run a single voice test scenario"""
        result = {
            "test_id": scenario.id,
            "category": scenario.category.value,
            "command": scenario.command,
            "status": "pending",
            "recognition_accuracy": 0.0,
            "intent_match": False,
            "response_appropriate": False,
            "response_time_ms": 0,
            "errors": []
        }
        
        try:
            # Simulate voice recognition with noise
            recognition_accuracy = self._simulate_recognition(
                scenario.command,
                scenario.background_noise_level,
                scenario.accent
            )
            result["recognition_accuracy"] = recognition_accuracy
            
            # Simulate intent matching
            if recognition_accuracy > 0.8:
                result["intent_match"] = True
                
                # Simulate response time based on conditions
                response_time = self._calculate_response_time(
                    scenario.category,
                    scenario.context.get("speed", 0)
                )
                result["response_time_ms"] = response_time
                
                # Check if response is appropriate
                result["response_appropriate"] = response_time < 200  # Target: <200ms
                
                if scenario.safety_critical and response_time > 100:
                    result["errors"].append("Safety-critical response too slow")
            else:
                result["errors"].append("Recognition accuracy too low")
            
            result["status"] = "passed" if not result["errors"] else "failed"
            
        except Exception as e:
            result["status"] = "error"
            result["errors"].append(str(e))
        
        return result
    
    def _simulate_recognition(self, command: str, noise_level: str, accent: str) -> float:
        """Simulate voice recognition accuracy"""
        base_accuracy = 0.95
        
        # Noise penalties
        noise_penalties = {
            "quiet": 0.0,
            "moderate": 0.05,
            "loud": 0.15,
            "extreme": 0.30
        }
        
        # Accent penalties
        accent_penalties = {
            "standard": 0.0,
            "southern": 0.03,
            "british": 0.02,
            "spanish": 0.05,
            "indian": 0.04,
            "child": 0.08,
            "elderly": 0.06
        }
        
        # Command complexity penalty
        complexity_penalty = min(len(command.split()) * 0.01, 0.1)
        
        accuracy = base_accuracy - noise_penalties.get(noise_level, 0) - \
                  accent_penalties.get(accent, 0) - complexity_penalty
        
        # Add some randomness
        accuracy += random.uniform(-0.05, 0.05)
        
        return max(0.0, min(1.0, accuracy))
    
    def _calculate_response_time(self, category: VoiceTestCategory, speed: int) -> int:
        """Calculate simulated response time in milliseconds"""
        base_times = {
            VoiceTestCategory.NAVIGATION: 80,
            VoiceTestCategory.BOOKING: 150,
            VoiceTestCategory.ENTERTAINMENT: 120,
            VoiceTestCategory.INFORMATION: 100,
            VoiceTestCategory.SAFETY: 50,
            VoiceTestCategory.PREFERENCES: 90,
            VoiceTestCategory.EMERGENCY: 30,
            VoiceTestCategory.FAMILY: 100,
            VoiceTestCategory.RIDESHARE: 110,
            VoiceTestCategory.MULTILINGUAL: 130
        }
        
        base_time = base_times.get(category, 100)
        
        # Add speed penalty for complex operations
        if speed > 60 and category in [VoiceTestCategory.BOOKING, VoiceTestCategory.INFORMATION]:
            base_time += 50
        
        # Add randomness
        base_time += random.randint(-20, 30)
        
        return max(20, base_time)
    
    async def run_all_tests(self) -> Dict[str, any]:
        """Run all test scenarios"""
        print(f"Running {len(self.test_suite.test_scenarios)} voice tests...")
        
        for scenario in self.test_suite.test_scenarios:
            result = await self.run_test(scenario)
            self.results.append(result)
            
            # Print progress
            if len(self.results) % 10 == 0:
                print(f"  Completed {len(self.results)} tests...")
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, any]:
        """Generate test results report"""
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["status"] == "passed")
        failed_tests = sum(1 for r in self.results if r["status"] == "failed")
        
        # Calculate metrics
        avg_recognition = np.mean([r["recognition_accuracy"] for r in self.results])
        avg_response_time = np.mean([r["response_time_ms"] for r in self.results if r["response_time_ms"] > 0])
        
        # Category breakdown
        category_stats = {}
        for category in VoiceTestCategory:
            category_results = [r for r in self.results if r["category"] == category.value]
            if category_results:
                category_stats[category.value] = {
                    "total": len(category_results),
                    "passed": sum(1 for r in category_results if r["status"] == "passed"),
                    "avg_accuracy": np.mean([r["recognition_accuracy"] for r in category_results]),
                    "avg_response_ms": np.mean([r["response_time_ms"] for r in category_results if r["response_time_ms"] > 0])
                }
        
        # Safety-critical performance
        safety_results = [r for r in self.results if r["test_id"].startswith(("SAFE", "NAV"))]
        safety_stats = {
            "total": len(safety_results),
            "passed": sum(1 for r in safety_results if r["status"] == "passed"),
            "avg_response_ms": np.mean([r["response_time_ms"] for r in safety_results if r["response_time_ms"] > 0])
        }
        
        report = {
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "pass_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "avg_recognition_accuracy": avg_recognition * 100,
                "avg_response_time_ms": avg_response_time
            },
            "category_breakdown": category_stats,
            "safety_critical": safety_stats,
            "failed_tests": [
                {
                    "id": r["test_id"],
                    "command": r["command"],
                    "errors": r["errors"]
                }
                for r in self.results if r["status"] == "failed"
            ]
        }
        
        return report


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # Create test suite
        test_suite = VoiceTestSuite()
        
        # Print test summary
        summary = test_suite.generate_test_report()
        print("\nVoice Test Suite Summary:")
        print(f"Total Tests: {summary['total_tests']}")
        print(f"Safety Critical: {summary['safety_critical']}")
        print("\nCategories:")
        for category, count in summary['categories'].items():
            print(f"  {category}: {count}")
        
        # Run tests
        runner = VoiceTestRunner(test_suite)
        report = await runner.run_all_tests()
        
        # Print results
        print("\n" + "="*50)
        print("VOICE TEST RESULTS")
        print("="*50)
        print(f"Pass Rate: {report['summary']['pass_rate']:.1f}%")
        print(f"Avg Recognition Accuracy: {report['summary']['avg_recognition_accuracy']:.1f}%")
        print(f"Avg Response Time: {report['summary']['avg_response_time_ms']:.0f}ms")
        
        print("\nCategory Performance:")
        for category, stats in report['category_breakdown'].items():
            print(f"\n{category}:")
            print(f"  Pass Rate: {(stats['passed']/stats['total']*100):.1f}%")
            print(f"  Avg Accuracy: {stats['avg_accuracy']*100:.1f}%")
            print(f"  Avg Response: {stats['avg_response_ms']:.0f}ms")
        
        if report['failed_tests']:
            print(f"\nFailed Tests ({len(report['failed_tests'])}):")
            for test in report['failed_tests'][:5]:  # Show first 5
                print(f"  {test['id']}: {test['errors'][0]}")
    
    asyncio.run(main())