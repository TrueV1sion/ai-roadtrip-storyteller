"""
Accent and Dialect Recognition Testing Framework
Tests voice recognition accuracy across various accents, dialects, and speech patterns
"""
import numpy as np
import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import asyncio


class AccentType(Enum):
    """Common accent types for testing"""
    # American English variants
    STANDARD_AMERICAN = "standard_american"
    SOUTHERN_US = "southern_us"
    NEW_YORK = "new_york"
    BOSTON = "boston"
    MIDWEST = "midwest"
    CALIFORNIA = "california"
    TEXAS = "texas"
    
    # British English variants
    RECEIVED_PRONUNCIATION = "british_rp"
    COCKNEY = "cockney"
    SCOTTISH = "scottish"
    IRISH = "irish"
    WELSH = "welsh"
    
    # Other English variants
    AUSTRALIAN = "australian"
    NEW_ZEALAND = "new_zealand"
    CANADIAN = "canadian"
    SOUTH_AFRICAN = "south_african"
    
    # Non-native English speakers
    SPANISH_ACCENT = "spanish_accent"
    FRENCH_ACCENT = "french_accent"
    GERMAN_ACCENT = "german_accent"
    ITALIAN_ACCENT = "italian_accent"
    CHINESE_ACCENT = "chinese_accent"
    JAPANESE_ACCENT = "japanese_accent"
    INDIAN_ACCENT = "indian_accent"
    ARABIC_ACCENT = "arabic_accent"
    RUSSIAN_ACCENT = "russian_accent"
    KOREAN_ACCENT = "korean_accent"


class SpeechPattern(Enum):
    """Speech pattern variations"""
    NORMAL = "normal"
    FAST = "fast"
    SLOW = "slow"
    MUMBLED = "mumbled"
    LOUD = "loud"
    QUIET = "quiet"
    EMOTIONAL = "emotional"
    TIRED = "tired"
    EXCITED = "excited"
    STRESSED = "stressed"


@dataclass
class AccentProfile:
    """Detailed accent profile for testing"""
    accent_type: AccentType
    name: str
    description: str
    phonetic_features: Dict[str, Any]
    common_variations: List[str]
    difficulty_level: float  # 0-1, where 1 is most difficult
    expected_accuracy: float  # Expected recognition accuracy


@dataclass
class TestPhrase:
    """Phrase for accent testing"""
    id: str
    text: str
    category: str  # navigation, booking, emergency, etc.
    complexity: str  # simple, moderate, complex
    phonetic_challenges: List[str]  # specific sounds that may be challenging


@dataclass
class AccentTestResult:
    """Result of accent recognition test"""
    accent_type: AccentType
    phrase: TestPhrase
    speech_pattern: SpeechPattern
    recognition_accuracy: float
    word_error_rate: float
    phoneme_accuracy: Dict[str, float]
    response_time_ms: float
    confidence_score: float
    errors: List[str]
    timestamp: datetime


class AccentDialectTester:
    """Comprehensive accent and dialect testing system"""
    
    def __init__(self):
        self.accent_profiles = self._create_accent_profiles()
        self.test_phrases = self._create_test_phrases()
        self.test_results: List[AccentTestResult] = []
    
    def _create_accent_profiles(self) -> Dict[AccentType, AccentProfile]:
        """Create detailed accent profiles"""
        profiles = {
            AccentType.STANDARD_AMERICAN: AccentProfile(
                accent_type=AccentType.STANDARD_AMERICAN,
                name="Standard American English",
                description="General American accent, commonly used in media",
                phonetic_features={
                    "rhoticity": "full",
                    "vowel_shifts": "minimal",
                    "intonation": "standard"
                },
                common_variations=[],
                difficulty_level=0.1,
                expected_accuracy=0.95
            ),
            
            AccentType.SOUTHERN_US: AccentProfile(
                accent_type=AccentType.SOUTHERN_US,
                name="Southern US English",
                description="Southern American English with distinctive drawl",
                phonetic_features={
                    "rhoticity": "variable",
                    "vowel_shifts": "pin-pen merger",
                    "intonation": "melodic",
                    "drawl": True
                },
                common_variations=["y'all", "fixin' to", "might could"],
                difficulty_level=0.3,
                expected_accuracy=0.88
            ),
            
            AccentType.BRITISH_RP: AccentProfile(
                accent_type=AccentType.BRITISH_RP,
                name="British Received Pronunciation",
                description="Standard British English, BBC English",
                phonetic_features={
                    "rhoticity": "non-rhotic",
                    "vowel_shifts": "bath-trap split",
                    "intonation": "varied"
                },
                common_variations=["whilst", "queue", "car park"],
                difficulty_level=0.2,
                expected_accuracy=0.92
            ),
            
            AccentType.SCOTTISH: AccentProfile(
                accent_type=AccentType.SCOTTISH,
                name="Scottish English",
                description="Scottish accent with rolled Rs",
                phonetic_features={
                    "rhoticity": "strong",
                    "vowel_shifts": "distinctive",
                    "intonation": "rising",
                    "rolled_r": True
                },
                common_variations=["wee", "aye", "ken"],
                difficulty_level=0.4,
                expected_accuracy=0.85
            ),
            
            AccentType.AUSTRALIAN: AccentProfile(
                accent_type=AccentType.AUSTRALIAN,
                name="Australian English",
                description="Australian accent with distinctive vowels",
                phonetic_features={
                    "rhoticity": "non-rhotic",
                    "vowel_shifts": "wide diphthongs",
                    "intonation": "rising terminal"
                },
                common_variations=["mate", "arvo", "servo"],
                difficulty_level=0.25,
                expected_accuracy=0.90
            ),
            
            AccentType.INDIAN_ACCENT: AccentProfile(
                accent_type=AccentType.INDIAN_ACCENT,
                name="Indian English",
                description="Indian-accented English",
                phonetic_features={
                    "rhoticity": "variable",
                    "retroflex": True,
                    "syllable_timing": True,
                    "v_w_distinction": "merged"
                },
                common_variations=["only", "itself", "prepone"],
                difficulty_level=0.35,
                expected_accuracy=0.87
            ),
            
            AccentType.SPANISH_ACCENT: AccentProfile(
                accent_type=AccentType.SPANISH_ACCENT,
                name="Spanish-accented English",
                description="English spoken with Spanish phonetics",
                phonetic_features={
                    "vowel_reduction": "minimal",
                    "consonant_clusters": "simplified",
                    "b_v_distinction": "merged",
                    "syllable_timing": True
                },
                common_variations=["no?", "how you say"],
                difficulty_level=0.4,
                expected_accuracy=0.85
            ),
            
            AccentType.CHINESE_ACCENT: AccentProfile(
                accent_type=AccentType.CHINESE_ACCENT,
                name="Chinese-accented English",
                description="English with Mandarin/Cantonese influence",
                phonetic_features={
                    "l_r_distinction": "merged",
                    "final_consonants": "dropped",
                    "tone_influence": True,
                    "syllable_timing": True
                },
                common_variations=["la" particle, simplified plurals],
                difficulty_level=0.45,
                expected_accuracy=0.83
            )
        }
        
        # Add more accent profiles
        for accent_type in AccentType:
            if accent_type not in profiles:
                # Default profile for unlisted accents
                profiles[accent_type] = AccentProfile(
                    accent_type=accent_type,
                    name=accent_type.value.replace("_", " ").title(),
                    description=f"Profile for {accent_type.value}",
                    phonetic_features={},
                    common_variations=[],
                    difficulty_level=0.5,
                    expected_accuracy=0.85
                )
        
        return profiles
    
    def _create_test_phrases(self) -> List[TestPhrase]:
        """Create comprehensive test phrases"""
        phrases = [
            # Navigation phrases
            TestPhrase(
                id="NAV001",
                text="Navigate to the nearest gas station",
                category="navigation",
                complexity="simple",
                phonetic_challenges=["consonant_clusters", "vowel_reduction"]
            ),
            TestPhrase(
                id="NAV002",
                text="Take the third exit after the traffic light",
                category="navigation",
                complexity="moderate",
                phonetic_challenges=["th_sound", "ordinal_numbers"]
            ),
            TestPhrase(
                id="NAV003",
                text="Reroute through the mountainous terrain avoiding highways",
                category="navigation",
                complexity="complex",
                phonetic_challenges=["r_sound", "diphthongs", "multisyllabic"]
            ),
            
            # Booking phrases
            TestPhrase(
                id="BOOK001",
                text="Book a hotel room for tonight",
                category="booking",
                complexity="simple",
                phonetic_challenges=["vowel_sounds"]
            ),
            TestPhrase(
                id="BOOK002",
                text="Reserve a table for four at an Italian restaurant",
                category="booking",
                complexity="moderate",
                phonetic_challenges=["r_sound", "numbers", "nationality_adjective"]
            ),
            TestPhrase(
                id="BOOK003",
                text="Find availability at pet-friendly accommodations with swimming pool",
                category="booking",
                complexity="complex",
                phonetic_challenges=["compound_words", "consonant_clusters"]
            ),
            
            # Emergency phrases
            TestPhrase(
                id="EMG001",
                text="Call emergency services immediately",
                category="emergency",
                complexity="simple",
                phonetic_challenges=["clear_articulation", "stress_patterns"]
            ),
            TestPhrase(
                id="EMG002",
                text="There's been an accident ahead on the highway",
                category="emergency",
                complexity="moderate",
                phonetic_challenges=["th_sound", "contractions", "past_participle"]
            ),
            
            # Complex phrases with multiple challenges
            TestPhrase(
                id="CPLX001",
                text="Search for vegetarian restaurants with wheelchair accessibility",
                category="complex",
                complexity="complex",
                phonetic_challenges=["multisyllabic", "technical_terms"]
            ),
            TestPhrase(
                id="CPLX002",
                text="Calculate the estimated arrival time considering current traffic",
                category="complex",
                complexity="complex",
                phonetic_challenges=["technical_vocabulary", "consonant_clusters"]
            ),
            
            # Phrases with numbers and special characters
            TestPhrase(
                id="NUM001",
                text="Navigate to 1234 Fifth Avenue Suite 567",
                category="address",
                complexity="moderate",
                phonetic_challenges=["numbers", "ordinals", "address_format"]
            ),
            TestPhrase(
                id="NUM002",
                text="The confirmation number is A1B2C3D4",
                category="alphanumeric",
                complexity="moderate",
                phonetic_challenges=["letter_number_mix", "clear_articulation"]
            ),
            
            # Colloquial phrases
            TestPhrase(
                id="COL001",
                text="What's the quickest way to get there",
                category="colloquial",
                complexity="simple",
                phonetic_challenges=["contractions", "casual_speech"]
            ),
            TestPhrase(
                id="COL002",
                text="I'm gonna need to stop for gas pretty soon",
                category="colloquial",
                complexity="moderate",
                phonetic_challenges=["gonna", "informal_speech"]
            )
        ]
        
        return phrases
    
    async def test_accent_recognition(
        self,
        accent_type: AccentType,
        phrase: TestPhrase,
        speech_pattern: SpeechPattern = SpeechPattern.NORMAL
    ) -> AccentTestResult:
        """Test recognition for a specific accent and phrase"""
        
        profile = self.accent_profiles[accent_type]
        
        # Simulate recognition with accent-specific challenges
        base_accuracy = profile.expected_accuracy
        
        # Apply speech pattern modifiers
        pattern_modifiers = {
            SpeechPattern.NORMAL: 1.0,
            SpeechPattern.FAST: 0.85,
            SpeechPattern.SLOW: 1.05,
            SpeechPattern.MUMBLED: 0.70,
            SpeechPattern.LOUD: 0.95,
            SpeechPattern.QUIET: 0.80,
            SpeechPattern.EMOTIONAL: 0.85,
            SpeechPattern.TIRED: 0.75,
            SpeechPattern.EXCITED: 0.80,
            SpeechPattern.STRESSED: 0.78
        }
        
        pattern_modifier = pattern_modifiers.get(speech_pattern, 1.0)
        
        # Apply phrase complexity modifier
        complexity_modifiers = {
            "simple": 1.0,
            "moderate": 0.95,
            "complex": 0.85
        }
        complexity_modifier = complexity_modifiers.get(phrase.complexity, 0.9)
        
        # Calculate final accuracy
        recognition_accuracy = base_accuracy * pattern_modifier * complexity_modifier
        
        # Add some randomness
        recognition_accuracy += np.random.normal(0, 0.02)
        recognition_accuracy = max(0.0, min(1.0, recognition_accuracy))
        
        # Calculate word error rate
        words = phrase.text.split()
        word_errors = int((1 - recognition_accuracy) * len(words))
        word_error_rate = word_errors / len(words)
        
        # Simulate phoneme accuracy for specific challenges
        phoneme_accuracy = {}
        for challenge in phrase.phonetic_challenges:
            # Accent-specific phoneme difficulties
            if challenge in profile.phonetic_features:
                difficulty_factor = 0.7
            else:
                difficulty_factor = 0.9
            
            phoneme_accuracy[challenge] = min(1.0, recognition_accuracy * difficulty_factor)
        
        # Simulate response time (slower for difficult accents)
        base_response_time = 150  # ms
        response_time = base_response_time * (1 + profile.difficulty_level)
        response_time += np.random.normal(0, 20)
        
        # Create test result
        result = AccentTestResult(
            accent_type=accent_type,
            phrase=phrase,
            speech_pattern=speech_pattern,
            recognition_accuracy=recognition_accuracy,
            word_error_rate=word_error_rate,
            phoneme_accuracy=phoneme_accuracy,
            response_time_ms=response_time,
            confidence_score=recognition_accuracy * 0.9,
            errors=[],
            timestamp=datetime.now()
        )
        
        # Add errors if accuracy is low
        if recognition_accuracy < 0.8:
            result.errors.append(f"Low recognition accuracy: {recognition_accuracy:.1%}")
        if word_error_rate > 0.2:
            result.errors.append(f"High word error rate: {word_error_rate:.1%}")
        
        self.test_results.append(result)
        return result
    
    async def run_comprehensive_accent_tests(self) -> Dict[str, Any]:
        """Run comprehensive accent recognition tests"""
        
        print("\n" + "="*60)
        print("COMPREHENSIVE ACCENT RECOGNITION TESTING")
        print("="*60)
        
        # Test matrix: accents x phrases x speech patterns
        test_accents = [
            AccentType.STANDARD_AMERICAN,
            AccentType.SOUTHERN_US,
            AccentType.BRITISH_RP,
            AccentType.SCOTTISH,
            AccentType.AUSTRALIAN,
            AccentType.INDIAN_ACCENT,
            AccentType.SPANISH_ACCENT,
            AccentType.CHINESE_ACCENT
        ]
        
        # Select representative phrases
        test_phrases = [
            p for p in self.test_phrases 
            if p.id in ["NAV001", "BOOK001", "EMG001", "CPLX001", "COL001"]
        ]
        
        # Test patterns
        test_patterns = [
            SpeechPattern.NORMAL,
            SpeechPattern.FAST,
            SpeechPattern.MUMBLED,
            SpeechPattern.EMOTIONAL
        ]
        
        results_by_accent = {}
        
        for accent in test_accents:
            print(f"\nTesting {self.accent_profiles[accent].name}:")
            accent_results = []
            
            for phrase in test_phrases:
                for pattern in test_patterns:
                    result = await self.test_accent_recognition(accent, phrase, pattern)
                    accent_results.append(result)
                    
                    if pattern == SpeechPattern.NORMAL:  # Only print normal pattern results
                        print(f"  {phrase.id}: {result.recognition_accuracy:.1%} accuracy")
            
            results_by_accent[accent] = accent_results
        
        # Generate comprehensive report
        return self.generate_accent_report(results_by_accent)
    
    async def test_phonetic_challenges(self) -> Dict[str, Any]:
        """Test specific phonetic challenges across accents"""
        
        print("\n" + "="*60)
        print("PHONETIC CHALLENGE TESTING")
        print("="*60)
        
        # Group phrases by phonetic challenges
        challenge_groups = {}
        for phrase in self.test_phrases:
            for challenge in phrase.phonetic_challenges:
                if challenge not in challenge_groups:
                    challenge_groups[challenge] = []
                challenge_groups[challenge].append(phrase)
        
        challenge_results = {}
        
        for challenge, phrases in challenge_groups.items():
            print(f"\nTesting '{challenge}' across accents:")
            challenge_results[challenge] = {}
            
            # Test each accent with phrases containing this challenge
            for accent_type in [AccentType.STANDARD_AMERICAN, AccentType.BRITISH_RP,
                              AccentType.INDIAN_ACCENT, AccentType.SPANISH_ACCENT]:
                
                accuracies = []
                for phrase in phrases[:3]:  # Test up to 3 phrases per challenge
                    result = await self.test_accent_recognition(
                        accent_type, phrase, SpeechPattern.NORMAL
                    )
                    if challenge in result.phoneme_accuracy:
                        accuracies.append(result.phoneme_accuracy[challenge])
                
                avg_accuracy = np.mean(accuracies) if accuracies else 0
                challenge_results[challenge][accent_type.value] = avg_accuracy
                print(f"  {accent_type.value}: {avg_accuracy:.1%}")
        
        return challenge_results
    
    def generate_accent_report(self, results_by_accent: Dict[AccentType, List[AccentTestResult]]) -> Dict[str, Any]:
        """Generate comprehensive accent testing report"""
        
        report = {
            "summary": {},
            "accent_performance": {},
            "phrase_difficulty": {},
            "speech_pattern_impact": {},
            "phonetic_challenges": {},
            "recommendations": []
        }
        
        # Overall summary
        all_results = []
        for accent_results in results_by_accent.values():
            all_results.extend(accent_results)
        
        if all_results:
            report["summary"] = {
                "total_tests": len(all_results),
                "avg_accuracy": np.mean([r.recognition_accuracy for r in all_results]),
                "avg_word_error_rate": np.mean([r.word_error_rate for r in all_results]),
                "avg_response_time": np.mean([r.response_time_ms for r in all_results])
            }
        
        # Performance by accent
        for accent, results in results_by_accent.items():
            if results:
                profile = self.accent_profiles[accent]
                accuracies = [r.recognition_accuracy for r in results]
                report["accent_performance"][accent.value] = {
                    "name": profile.name,
                    "avg_accuracy": np.mean(accuracies),
                    "min_accuracy": np.min(accuracies),
                    "max_accuracy": np.max(accuracies),
                    "expected_accuracy": profile.expected_accuracy,
                    "performance_vs_expected": np.mean(accuracies) / profile.expected_accuracy
                }
        
        # Phrase difficulty analysis
        phrase_performance = {}
        for result in all_results:
            phrase_id = result.phrase.id
            if phrase_id not in phrase_performance:
                phrase_performance[phrase_id] = []
            phrase_performance[phrase_id].append(result.recognition_accuracy)
        
        for phrase_id, accuracies in phrase_performance.items():
            report["phrase_difficulty"][phrase_id] = {
                "avg_accuracy": np.mean(accuracies),
                "variance": np.var(accuracies)
            }
        
        # Speech pattern impact
        pattern_performance = {}
        for result in all_results:
            pattern = result.speech_pattern
            if pattern not in pattern_performance:
                pattern_performance[pattern] = []
            pattern_performance[pattern].append(result.recognition_accuracy)
        
        for pattern, accuracies in pattern_performance.items():
            report["speech_pattern_impact"][pattern.value] = {
                "avg_accuracy": np.mean(accuracies),
                "impact": 1.0 - (np.mean(accuracies) / report["summary"]["avg_accuracy"])
            }
        
        # Generate recommendations
        report["recommendations"] = self._generate_accent_recommendations(report)
        
        # Save report
        with open(f"accent_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        return report
    
    def _generate_accent_recommendations(self, report: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on accent test results"""
        
        recommendations = []
        
        # Check accent performance
        for accent, performance in report["accent_performance"].items():
            if performance["performance_vs_expected"] < 0.9:
                recommendations.append(
                    f"Accent '{performance['name']}' performing below expectations "
                    f"({performance['avg_accuracy']:.1%} vs {performance['expected_accuracy']:.1%} expected). "
                    f"Consider accent-specific training data."
                )
            
            if performance["min_accuracy"] < 0.7:
                recommendations.append(
                    f"Critical: '{performance['name']}' has scenarios with <70% accuracy. "
                    f"Review specific failure cases."
                )
        
        # Check phrase difficulty
        difficult_phrases = [
            phrase_id for phrase_id, stats in report["phrase_difficulty"].items()
            if stats["avg_accuracy"] < 0.8
        ]
        if difficult_phrases:
            recommendations.append(
                f"Phrases {', '.join(difficult_phrases)} consistently difficult across accents. "
                f"Consider rephrasing or alternative commands."
            )
        
        # Check speech pattern impact
        problematic_patterns = [
            pattern for pattern, stats in report["speech_pattern_impact"].items()
            if stats["impact"] > 0.15
        ]
        if problematic_patterns:
            recommendations.append(
                f"Speech patterns {', '.join(problematic_patterns)} significantly impact accuracy. "
                f"Enhance robustness to speech variations."
            )
        
        if not recommendations:
            recommendations.append("Accent recognition meets performance targets across all tested variants.")
        
        return recommendations


# Example usage
async def main():
    """Run accent and dialect recognition tests"""
    tester = AccentDialectTester()
    
    # Run comprehensive tests
    accent_report = await tester.run_comprehensive_accent_tests()
    
    # Test phonetic challenges
    phonetic_report = await tester.test_phonetic_challenges()
    
    # Print summary
    print("\n" + "="*60)
    print("ACCENT TESTING SUMMARY")
    print("="*60)
    
    print(f"\nOverall Performance:")
    print(f"  Average Accuracy: {accent_report['summary']['avg_accuracy']:.1%}")
    print(f"  Average Word Error Rate: {accent_report['summary']['avg_word_error_rate']:.1%}")
    print(f"  Average Response Time: {accent_report['summary']['avg_response_time']:.0f}ms")
    
    print(f"\nTop Performing Accents:")
    sorted_accents = sorted(
        accent_report['accent_performance'].items(),
        key=lambda x: x[1]['avg_accuracy'],
        reverse=True
    )
    for i, (accent, performance) in enumerate(sorted_accents[:3]):
        print(f"  {i+1}. {performance['name']}: {performance['avg_accuracy']:.1%}")
    
    print(f"\nMost Challenging Accents:")
    for i, (accent, performance) in enumerate(sorted_accents[-3:]):
        print(f"  {i+1}. {performance['name']}: {performance['avg_accuracy']:.1%}")
    
    print(f"\nRecommendations:")
    for i, rec in enumerate(accent_report['recommendations'], 1):
        print(f"  {i}. {rec}")
    
    print(f"\nDetailed report saved to: accent_test_report_*.json")


if __name__ == "__main__":
    asyncio.run(main())