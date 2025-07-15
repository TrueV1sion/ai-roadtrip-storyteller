"""
Voice Test Executor - Runs comprehensive voice tests with noise simulation
Integrates test scenarios, background noise, and safety validation
"""
import asyncio
import numpy as np
import json
import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from tests.voice.voice_test_scenarios import (
    VoiceTestSuite, VoiceTestScenario, VoiceTestCategory
)
from tests.voice.background_noise_simulator import (
    BackgroundNoiseSimulator, DrivingCondition, NoiseType
)
from backend.app.services.voice_safety_enhanced import (
    EnhancedVoiceSafetyValidator, DrivingContext, VoiceSafetyMetrics
)
from backend.app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VoiceTestExecution:
    """Result of a single voice test execution"""
    scenario: VoiceTestScenario
    noise_condition: DrivingCondition
    snr_db: float
    recognition_success: bool
    recognition_accuracy: float
    intent_matched: bool
    safety_passed: bool
    response_time_ms: float
    safety_details: Dict[str, Any]
    errors: List[str]
    timestamp: datetime


class VoiceTestExecutor:
    """Executes voice tests with realistic conditions"""
    
    def __init__(self):
        self.test_suite = VoiceTestSuite()
        self.noise_simulator = BackgroundNoiseSimulator()
        self.safety_validator = EnhancedVoiceSafetyValidator()
        self.safety_metrics = VoiceSafetyMetrics()
        self.executions: List[VoiceTestExecution] = []
        
    async def execute_scenario_with_noise(
        self,
        scenario: VoiceTestScenario,
        noise_condition: DrivingCondition,
        snr_db: float = 10
    ) -> VoiceTestExecution:
        """Execute a single test scenario with background noise"""
        
        logger.info(f"Executing scenario {scenario.id} with {noise_condition.value} noise at {snr_db}dB SNR")
        
        # Create execution result
        execution = VoiceTestExecution(
            scenario=scenario,
            noise_condition=noise_condition,
            snr_db=snr_db,
            recognition_success=False,
            recognition_accuracy=0.0,
            intent_matched=False,
            safety_passed=False,
            response_time_ms=0.0,
            safety_details={},
            errors=[],
            timestamp=datetime.now()
        )
        
        try:
            # Simulate voice command with noise
            start_time = time.time()
            
            # Generate background noise
            noise_duration = 5.0  # seconds
            background_noise = self.noise_simulator.simulate_driving_condition(
                noise_condition, noise_duration
            )
            
            # Simulate voice recognition with noise impact
            recognition_result = await self._simulate_voice_recognition(
                scenario.command,
                scenario.accent,
                noise_condition,
                snr_db
            )
            
            execution.recognition_success = recognition_result["success"]
            execution.recognition_accuracy = recognition_result["accuracy"]
            
            if execution.recognition_success:
                # Test intent matching
                execution.intent_matched = await self._test_intent_matching(
                    recognition_result["recognized_text"],
                    scenario.expected_intent
                )
                
                # Create driving context from scenario
                driving_context = DrivingContext(
                    speed=scenario.context.get("speed", 30),
                    location=scenario.context.get("location"),
                    heading=scenario.context.get("heading", 0),
                    is_highway=noise_condition in [
                        DrivingCondition.HIGHWAY_SMOOTH,
                        DrivingCondition.HIGHWAY_ROUGH
                    ],
                    traffic_level="heavy" if noise_condition == DrivingCondition.TRAFFIC_JAM else "moderate",
                    weather_condition="rain" if "RAIN" in noise_condition.value else "clear",
                    time_of_day="day",
                    passengers=scenario.context.get("passengers", 1)
                )
                
                # Validate with enhanced safety system
                safety_result = await self.safety_validator.validate_command_enhanced(
                    scenario.command,
                    driving_context
                )
                
                execution.safety_passed = safety_result.get("safe", False)
                execution.safety_details = safety_result
                
                # Record in safety metrics
                self.safety_metrics.record_command(safety_result, driving_context)
                
            # Calculate response time
            execution.response_time_ms = (time.time() - start_time) * 1000
            
            # Check response time requirements
            if scenario.safety_critical and execution.response_time_ms > 100:
                execution.errors.append(f"Safety-critical response too slow: {execution.response_time_ms:.0f}ms")
            
        except Exception as e:
            execution.errors.append(f"Execution error: {str(e)}")
            logger.error(f"Error executing scenario {scenario.id}: {e}")
        
        self.executions.append(execution)
        return execution
    
    async def _simulate_voice_recognition(
        self,
        command: str,
        accent: str,
        noise_condition: DrivingCondition,
        snr_db: float
    ) -> Dict[str, Any]:
        """Simulate voice recognition with noise impact"""
        
        # Base accuracy for different conditions
        condition_accuracy = {
            DrivingCondition.CITY_QUIET: 0.95,
            DrivingCondition.CITY_BUSY: 0.85,
            DrivingCondition.HIGHWAY_SMOOTH: 0.88,
            DrivingCondition.HIGHWAY_ROUGH: 0.80,
            DrivingCondition.SUBURBAN: 0.92,
            DrivingCondition.RURAL: 0.94,
            DrivingCondition.PARKING: 0.96,
            DrivingCondition.TRAFFIC_JAM: 0.82,
            DrivingCondition.RAIN_LIGHT: 0.85,
            DrivingCondition.RAIN_HEAVY: 0.75,
            DrivingCondition.WINDOWS_DOWN: 0.70,
            DrivingCondition.EMERGENCY: 0.65
        }
        
        # Accent impact
        accent_modifiers = {
            "standard": 1.0,
            "southern": 0.97,
            "british": 0.98,
            "spanish": 0.95,
            "indian": 0.96,
            "australian": 0.98,
            "child": 0.92,
            "elderly": 0.94
        }
        
        # Calculate accuracy
        base_accuracy = condition_accuracy.get(noise_condition, 0.85)
        accent_modifier = accent_modifiers.get(accent, 0.95)
        
        # SNR impact (lower SNR = worse accuracy)
        snr_modifier = min(1.0, 0.5 + (snr_db / 40))  # 0.5 at 0dB, 1.0 at 20dB
        
        # Command length impact
        length_modifier = max(0.8, 1.0 - (len(command.split()) - 5) * 0.02)
        
        final_accuracy = base_accuracy * accent_modifier * snr_modifier * length_modifier
        
        # Add some randomness
        final_accuracy += np.random.normal(0, 0.02)
        final_accuracy = max(0.0, min(1.0, final_accuracy))
        
        # Simulate recognition success
        success = final_accuracy > 0.75  # 75% threshold for successful recognition
        
        # Simulate recognized text (may have errors if accuracy is low)
        recognized_text = command
        if final_accuracy < 0.95:
            # Introduce some recognition errors
            words = command.split()
            num_errors = int((1 - final_accuracy) * len(words))
            for _ in range(num_errors):
                if words:
                    idx = np.random.randint(0, len(words))
                    # Simple error simulation
                    words[idx] = words[idx][:-1] if len(words[idx]) > 1 else "?"
            recognized_text = " ".join(words)
        
        return {
            "success": success,
            "accuracy": final_accuracy,
            "recognized_text": recognized_text,
            "confidence": final_accuracy
        }
    
    async def _test_intent_matching(
        self,
        recognized_text: str,
        expected_intent: str
    ) -> bool:
        """Test if recognized text matches expected intent"""
        
        # Simple intent matching based on keywords
        intent_keywords = {
            "navigate_to_destination": ["navigate", "go to", "take me", "drive to"],
            "find_nearby_poi": ["find", "nearest", "closest", "nearby"],
            "book_hotel": ["book", "hotel", "room", "accommodation"],
            "make_reservation": ["reserve", "reservation", "table", "restaurant"],
            "play_music": ["play", "music", "song", "playlist"],
            "start_trivia": ["trivia", "game", "quiz"],
            "emergency_call": ["911", "emergency", "help"],
            "find_emergency_services": ["hospital", "police", "emergency"],
            "change_voice_personality": ["voice", "personality", "switch", "change"]
        }
        
        recognized_lower = recognized_text.lower()
        
        # Check if any keywords match
        if expected_intent in intent_keywords:
            keywords = intent_keywords[expected_intent]
            return any(keyword in recognized_lower for keyword in keywords)
        
        # Default: check if intent name is partially in recognized text
        return expected_intent.replace("_", " ") in recognized_lower
    
    async def run_comprehensive_test_suite(self) -> Dict[str, Any]:
        """Run complete test suite with various noise conditions"""
        
        print("\n" + "="*60)
        print("COMPREHENSIVE VOICE TESTING SUITE")
        print("="*60)
        
        # Test conditions matrix
        test_conditions = [
            (DrivingCondition.CITY_QUIET, 20),
            (DrivingCondition.CITY_BUSY, 15),
            (DrivingCondition.HIGHWAY_SMOOTH, 10),
            (DrivingCondition.HIGHWAY_ROUGH, 5),
            (DrivingCondition.RAIN_HEAVY, 5),
            (DrivingCondition.WINDOWS_DOWN, 0),
            (DrivingCondition.EMERGENCY, 0)
        ]
        
        # Get critical test scenarios
        critical_scenarios = self.test_suite.get_safety_critical_tests()
        regular_scenarios = [s for s in self.test_suite.test_scenarios if not s.safety_critical]
        
        # Test safety-critical scenarios in all conditions
        print("\nTesting Safety-Critical Scenarios:")
        for scenario in critical_scenarios[:5]:  # Test first 5 critical scenarios
            print(f"\n  Scenario: {scenario.id} - {scenario.command}")
            for condition, snr in test_conditions:
                execution = await self.execute_scenario_with_noise(scenario, condition, snr)
                print(f"    {condition.value} ({snr}dB): ", end="")
                if execution.recognition_success and execution.safety_passed:
                    print("✓ PASS")
                else:
                    print(f"✗ FAIL - {execution.errors[0] if execution.errors else 'Recognition failed'}")
        
        # Test regular scenarios in moderate conditions
        print("\nTesting Regular Scenarios:")
        moderate_conditions = [
            (DrivingCondition.CITY_QUIET, 15),
            (DrivingCondition.HIGHWAY_SMOOTH, 10),
            (DrivingCondition.SUBURBAN, 15)
        ]
        
        for scenario in regular_scenarios[:10]:  # Test first 10 regular scenarios
            print(f"\n  Scenario: {scenario.id} - {scenario.command}")
            for condition, snr in moderate_conditions:
                execution = await self.execute_scenario_with_noise(scenario, condition, snr)
                print(f"    {condition.value} ({snr}dB): ", end="")
                if execution.recognition_success and execution.intent_matched:
                    print("✓ PASS")
                else:
                    print("✗ FAIL")
        
        # Generate comprehensive report
        return self.generate_comprehensive_report()
    
    async def test_accent_variations(self) -> Dict[str, Any]:
        """Test voice recognition with different accents"""
        
        print("\n" + "="*60)
        print("ACCENT VARIATION TESTING")
        print("="*60)
        
        # Get accent test scenarios
        accent_scenarios = [s for s in self.test_suite.test_scenarios 
                          if s.category == VoiceTestCategory.MULTILINGUAL]
        
        # Test each accent in different noise conditions
        conditions = [
            (DrivingCondition.CITY_QUIET, 20),
            (DrivingCondition.CITY_BUSY, 10),
            (DrivingCondition.HIGHWAY_SMOOTH, 10)
        ]
        
        accent_results = {}
        
        for scenario in accent_scenarios:
            accent = scenario.accent
            if accent not in accent_results:
                accent_results[accent] = {
                    "total": 0,
                    "successful": 0,
                    "accuracies": []
                }
            
            print(f"\nTesting {accent} accent: {scenario.command}")
            
            for condition, snr in conditions:
                execution = await self.execute_scenario_with_noise(scenario, condition, snr)
                
                accent_results[accent]["total"] += 1
                if execution.recognition_success:
                    accent_results[accent]["successful"] += 1
                accent_results[accent]["accuracies"].append(execution.recognition_accuracy)
                
                print(f"  {condition.value}: {execution.recognition_accuracy:.1%} accuracy")
        
        # Calculate accent performance
        print("\nAccent Performance Summary:")
        for accent, results in accent_results.items():
            success_rate = results["successful"] / results["total"] * 100 if results["total"] > 0 else 0
            avg_accuracy = np.mean(results["accuracies"]) if results["accuracies"] else 0
            print(f"  {accent}: {success_rate:.1f}% success rate, {avg_accuracy:.1%} avg accuracy")
        
        return accent_results
    
    async def test_emergency_scenarios(self) -> Dict[str, Any]:
        """Test emergency command handling in extreme conditions"""
        
        print("\n" + "="*60)
        print("EMERGENCY SCENARIO TESTING")
        print("="*60)
        
        # Get emergency scenarios
        emergency_scenarios = [s for s in self.test_suite.test_scenarios 
                             if s.category == VoiceTestCategory.EMERGENCY]
        
        # Test in extreme conditions
        extreme_conditions = [
            (DrivingCondition.EMERGENCY, 0),
            (DrivingCondition.RAIN_HEAVY, 5),
            (DrivingCondition.WINDOWS_DOWN, 0),
            (DrivingCondition.HIGHWAY_ROUGH, 5)
        ]
        
        emergency_results = []
        
        for scenario in emergency_scenarios:
            print(f"\nEmergency Command: {scenario.command}")
            
            for condition, snr in extreme_conditions:
                execution = await self.execute_scenario_with_noise(scenario, condition, snr)
                
                # Check if emergency was properly handled
                is_emergency = execution.safety_details.get("emergency", False)
                immediate = execution.safety_details.get("immediate_response", False)
                
                print(f"  {condition.value}: ", end="")
                if is_emergency and immediate and execution.response_time_ms < 100:
                    print(f"✓ PASS - {execution.response_time_ms:.0f}ms response")
                else:
                    print(f"✗ FAIL - Not recognized as emergency or too slow")
                
                emergency_results.append({
                    "scenario": scenario.id,
                    "condition": condition.value,
                    "recognized": is_emergency,
                    "immediate": immediate,
                    "response_time": execution.response_time_ms
                })
        
        return emergency_results
    
    def generate_comprehensive_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        
        total_executions = len(self.executions)
        if total_executions == 0:
            return {"error": "No test executions found"}
        
        # Calculate overall metrics
        recognition_successes = sum(1 for e in self.executions if e.recognition_success)
        intent_matches = sum(1 for e in self.executions if e.intent_matched)
        safety_passes = sum(1 for e in self.executions if e.safety_passed)
        
        # Average metrics
        avg_accuracy = np.mean([e.recognition_accuracy for e in self.executions])
        avg_response_time = np.mean([e.response_time_ms for e in self.executions])
        
        # Group by noise condition
        condition_performance = {}
        for execution in self.executions:
            condition = execution.noise_condition.value
            if condition not in condition_performance:
                condition_performance[condition] = {
                    "total": 0,
                    "recognition_success": 0,
                    "safety_passed": 0,
                    "avg_accuracy": [],
                    "avg_response_time": []
                }
            
            stats = condition_performance[condition]
            stats["total"] += 1
            if execution.recognition_success:
                stats["recognition_success"] += 1
            if execution.safety_passed:
                stats["safety_passed"] += 1
            stats["avg_accuracy"].append(execution.recognition_accuracy)
            stats["avg_response_time"].append(execution.response_time_ms)
        
        # Calculate condition averages
        for condition, stats in condition_performance.items():
            stats["recognition_rate"] = stats["recognition_success"] / stats["total"] * 100
            stats["safety_rate"] = stats["safety_passed"] / stats["total"] * 100
            stats["avg_accuracy"] = np.mean(stats["avg_accuracy"])
            stats["avg_response_time"] = np.mean(stats["avg_response_time"])
        
        # Get safety report
        safety_report = self.safety_metrics.get_safety_report()
        
        # Identify problem areas
        problem_conditions = [
            condition for condition, stats in condition_performance.items()
            if stats["recognition_rate"] < 80 or stats["safety_rate"] < 90
        ]
        
        report = {
            "summary": {
                "total_executions": total_executions,
                "recognition_success_rate": recognition_successes / total_executions * 100,
                "intent_match_rate": intent_matches / total_executions * 100,
                "safety_pass_rate": safety_passes / total_executions * 100,
                "avg_recognition_accuracy": avg_accuracy * 100,
                "avg_response_time_ms": avg_response_time
            },
            "condition_performance": condition_performance,
            "safety_metrics": safety_report,
            "problem_areas": problem_conditions,
            "test_timestamp": datetime.now().isoformat(),
            "recommendations": self._generate_recommendations(condition_performance, safety_report)
        }
        
        # Save report
        with open(f"voice_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def _generate_recommendations(
        self,
        condition_performance: Dict[str, Any],
        safety_report: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on test results"""
        
        recommendations = []
        
        # Check recognition rates
        for condition, stats in condition_performance.items():
            if stats["recognition_rate"] < 70:
                recommendations.append(
                    f"Critical: {condition} has very low recognition rate ({stats['recognition_rate']:.1f}%). "
                    f"Consider enhanced noise cancellation or alternative input methods."
                )
            elif stats["recognition_rate"] < 85:
                recommendations.append(
                    f"Warning: {condition} recognition needs improvement ({stats['recognition_rate']:.1f}%)."
                )
        
        # Check response times
        slow_conditions = [
            condition for condition, stats in condition_performance.items()
            if stats["avg_response_time"] > 200
        ]
        if slow_conditions:
            recommendations.append(
                f"Response times exceed 200ms target in: {', '.join(slow_conditions)}. "
                f"Consider optimization or edge computing."
            )
        
        # Safety recommendations
        if safety_report["overview"]["safety_rate"] < 95:
            recommendations.append(
                f"Safety rate below target ({safety_report['overview']['safety_rate']:.1f}%). "
                f"Review safety validation rules and thresholds."
            )
        
        # Add safety report recommendations
        recommendations.extend(safety_report.get("recommendations", []))
        
        if not recommendations:
            recommendations.append("All metrics meet or exceed targets. System ready for production.")
        
        return recommendations


# Example usage
async def main():
    """Run comprehensive voice tests"""
    executor = VoiceTestExecutor()
    
    # Run full test suite
    print("Starting comprehensive voice testing...")
    report = await executor.run_comprehensive_test_suite()
    
    # Test accent variations
    print("\n" + "="*60)
    accent_results = await executor.test_accent_variations()
    
    # Test emergency scenarios
    print("\n" + "="*60)
    emergency_results = await executor.test_emergency_scenarios()
    
    # Print final summary
    print("\n" + "="*60)
    print("VOICE TESTING COMPLETE")
    print("="*60)
    print(f"Recognition Success Rate: {report['summary']['recognition_success_rate']:.1f}%")
    print(f"Intent Match Rate: {report['summary']['intent_match_rate']:.1f}%")
    print(f"Safety Pass Rate: {report['summary']['safety_pass_rate']:.1f}%")
    print(f"Average Accuracy: {report['summary']['avg_recognition_accuracy']:.1f}%")
    print(f"Average Response Time: {report['summary']['avg_response_time_ms']:.0f}ms")
    
    print("\nProblem Areas:")
    if report['problem_areas']:
        for area in report['problem_areas']:
            print(f"  - {area}")
    else:
        print("  None - All conditions meet targets!")
    
    print("\nRecommendations:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"  {i}. {rec}")
    
    print(f"\nDetailed report saved to: voice_test_report_*.json")


if __name__ == "__main__":
    asyncio.run(main())