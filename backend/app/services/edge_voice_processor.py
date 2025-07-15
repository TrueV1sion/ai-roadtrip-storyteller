"""
Edge Voice Processing System
Enables local voice processing for ultra-low latency responses
"""
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import time
import json
import numpy as np
from collections import deque

from app.core.logger import get_logger

logger = get_logger(__name__)


class EdgeProcessingMode(Enum):
    """Edge processing modes"""
    FULL_EDGE = "full_edge"  # Everything processed locally
    HYBRID = "hybrid"  # Simple commands edge, complex cloud
    CLOUD_FALLBACK = "cloud_fallback"  # Edge with cloud backup
    CLOUD_ONLY = "cloud_only"  # No edge processing


class CommandCategory(Enum):
    """Categories of voice commands for edge processing"""
    NAVIGATION_SIMPLE = "navigation_simple"  # "Next turn", "ETA"
    SAFETY_CRITICAL = "safety_critical"  # Emergency commands
    MEDIA_CONTROL = "media_control"  # Play, pause, volume
    INFORMATION_QUERY = "information_query"  # Weather, time
    SYSTEM_CONTROL = "system_control"  # Settings, preferences
    COMPLEX_REQUEST = "complex_request"  # Bookings, stories


@dataclass
class EdgeModel:
    """Lightweight model for edge processing"""
    model_id: str
    category: CommandCategory
    size_mb: float
    accuracy: float
    avg_latency_ms: float
    vocabulary_size: int
    supports_offline: bool


@dataclass
class ProcessingResult:
    """Result from edge processing"""
    success: bool
    command: str
    intent: str
    confidence: float
    processing_time_ms: float
    processed_on_edge: bool
    fallback_reason: Optional[str] = None


class EdgeVoiceProcessor:
    """Manages edge voice processing for ultra-low latency"""
    
    def __init__(self):
        self.edge_models = self._initialize_edge_models()
        self.model_cache = {}
        self.processing_mode = EdgeProcessingMode.HYBRID
        self.latency_target_ms = 50
        self.confidence_threshold = 0.85
        
        # Performance tracking
        self.edge_success_rate = deque(maxlen=1000)
        self.latency_history = deque(maxlen=1000)
        self.fallback_reasons = {}
        
        # Edge capabilities
        self.edge_vocabulary = self._load_edge_vocabulary()
        self.intent_patterns = self._load_intent_patterns()
        
        # Model loading status
        self.models_loaded = False
        asyncio.create_task(self._load_models())
    
    def _initialize_edge_models(self) -> Dict[CommandCategory, EdgeModel]:
        """Initialize available edge models"""
        return {
            CommandCategory.NAVIGATION_SIMPLE: EdgeModel(
                model_id="nav_edge_v1",
                category=CommandCategory.NAVIGATION_SIMPLE,
                size_mb=10,
                accuracy=0.95,
                avg_latency_ms=20,
                vocabulary_size=500,
                supports_offline=True
            ),
            CommandCategory.SAFETY_CRITICAL: EdgeModel(
                model_id="safety_edge_v1",
                category=CommandCategory.SAFETY_CRITICAL,
                size_mb=5,
                accuracy=0.98,
                avg_latency_ms=15,
                vocabulary_size=200,
                supports_offline=True
            ),
            CommandCategory.MEDIA_CONTROL: EdgeModel(
                model_id="media_edge_v1",
                category=CommandCategory.MEDIA_CONTROL,
                size_mb=3,
                accuracy=0.97,
                avg_latency_ms=10,
                vocabulary_size=100,
                supports_offline=True
            ),
            CommandCategory.INFORMATION_QUERY: EdgeModel(
                model_id="info_edge_v1",
                category=CommandCategory.INFORMATION_QUERY,
                size_mb=15,
                accuracy=0.92,
                avg_latency_ms=30,
                vocabulary_size=1000,
                supports_offline=False
            ),
            CommandCategory.SYSTEM_CONTROL: EdgeModel(
                model_id="system_edge_v1",
                category=CommandCategory.SYSTEM_CONTROL,
                size_mb=8,
                accuracy=0.96,
                avg_latency_ms=25,
                vocabulary_size=300,
                supports_offline=True
            )
        }
    
    def _load_edge_vocabulary(self) -> Dict[CommandCategory, List[str]]:
        """Load vocabulary for edge processing"""
        return {
            CommandCategory.NAVIGATION_SIMPLE: [
                "turn", "left", "right", "straight", "next", "exit",
                "eta", "time", "arrival", "distance", "miles", "minutes",
                "route", "traffic", "faster", "alternate", "avoid"
            ],
            CommandCategory.SAFETY_CRITICAL: [
                "emergency", "help", "stop", "911", "police", "ambulance",
                "accident", "crash", "danger", "warning", "pull", "over",
                "hospital", "nearest", "urgent", "immediately"
            ],
            CommandCategory.MEDIA_CONTROL: [
                "play", "pause", "stop", "volume", "up", "down", "next",
                "previous", "skip", "repeat", "shuffle", "music", "song",
                "louder", "quieter", "mute"
            ],
            CommandCategory.INFORMATION_QUERY: [
                "weather", "temperature", "time", "date", "traffic",
                "speed", "limit", "gas", "price", "news", "update"
            ],
            CommandCategory.SYSTEM_CONTROL: [
                "settings", "voice", "personality", "mode", "family",
                "rideshare", "preference", "language", "speed", "slower",
                "faster", "enable", "disable", "turn", "on", "off"
            ]
        }
    
    def _load_intent_patterns(self) -> Dict[str, List[Tuple[List[str], str]]]:
        """Load intent patterns for edge matching"""
        return {
            "navigation": [
                (["turn", "left"], "turn_left"),
                (["turn", "right"], "turn_right"),
                (["next", "exit"], "next_exit"),
                (["what", "eta"], "get_eta"),
                (["how", "long"], "get_eta"),
                (["alternate", "route"], "find_alternate_route"),
                (["avoid", "traffic"], "avoid_traffic")
            ],
            "safety": [
                (["call", "911"], "emergency_call"),
                (["emergency"], "emergency_assist"),
                (["pull", "over"], "safe_stop"),
                (["nearest", "hospital"], "find_hospital"),
                (["help"], "emergency_assist")
            ],
            "media": [
                (["play", "music"], "play_music"),
                (["pause"], "pause_media"),
                (["volume", "up"], "volume_increase"),
                (["volume", "down"], "volume_decrease"),
                (["next", "song"], "next_track"),
                (["skip"], "next_track")
            ],
            "system": [
                (["family", "mode"], "enable_family_mode"),
                (["change", "voice"], "change_voice_personality"),
                (["speak", "slower"], "adjust_speech_rate"),
                (["rideshare", "mode"], "enable_rideshare_mode")
            ]
        }
    
    async def process_voice_command(
        self,
        audio_features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ProcessingResult:
        """Process voice command with edge-first approach"""
        
        start_time = time.time()
        
        # Determine processing mode based on context
        mode = self._determine_processing_mode(context)
        
        if mode == EdgeProcessingMode.CLOUD_ONLY:
            return await self._process_cloud_only(audio_features, context)
        
        # Try edge processing first
        edge_result = await self._process_on_edge(audio_features, context)
        
        if edge_result and edge_result.confidence >= self.confidence_threshold:
            # Successful edge processing
            processing_time = (time.time() - start_time) * 1000
            edge_result.processing_time_ms = processing_time
            
            self._track_edge_success(True, processing_time)
            return edge_result
        
        # Fallback to cloud if needed
        if mode in [EdgeProcessingMode.HYBRID, EdgeProcessingMode.CLOUD_FALLBACK]:
            fallback_reason = "low_confidence" if edge_result else "no_edge_match"
            cloud_result = await self._process_cloud_fallback(
                audio_features,
                context,
                fallback_reason
            )
            
            processing_time = (time.time() - start_time) * 1000
            cloud_result.processing_time_ms = processing_time
            
            self._track_edge_success(False, processing_time, fallback_reason)
            return cloud_result
        
        # Full edge mode - return best effort
        if edge_result:
            processing_time = (time.time() - start_time) * 1000
            edge_result.processing_time_ms = processing_time
            return edge_result
        
        # No result
        return ProcessingResult(
            success=False,
            command="",
            intent="unknown",
            confidence=0.0,
            processing_time_ms=(time.time() - start_time) * 1000,
            processed_on_edge=True,
            fallback_reason="no_match"
        )
    
    def _determine_processing_mode(self, context: Dict[str, Any]) -> EdgeProcessingMode:
        """Determine processing mode based on context"""
        
        # Safety critical always uses hybrid for reliability
        if context.get("safety_critical", False):
            return EdgeProcessingMode.HYBRID
        
        # Check network connectivity
        if not context.get("network_available", True):
            return EdgeProcessingMode.FULL_EDGE
        
        # Check user preference
        user_preference = context.get("edge_preference", "auto")
        if user_preference == "edge_only":
            return EdgeProcessingMode.FULL_EDGE
        elif user_preference == "cloud_only":
            return EdgeProcessingMode.CLOUD_ONLY
        
        # Default mode
        return self.processing_mode
    
    async def _process_on_edge(
        self,
        audio_features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[ProcessingResult]:
        """Process command on edge device"""
        
        if not self.models_loaded:
            return None
        
        try:
            # Extract text from audio features (simplified)
            command_text = await self._extract_text_from_audio(audio_features)
            if not command_text:
                return None
            
            # Categorize command
            category = self._categorize_command(command_text)
            if not category or category == CommandCategory.COMPLEX_REQUEST:
                return None
            
            # Get appropriate edge model
            edge_model = self.edge_models.get(category)
            if not edge_model:
                return None
            
            # Process with edge model
            intent, confidence = await self._run_edge_inference(
                command_text,
                edge_model,
                context
            )
            
            if intent and confidence > 0:
                return ProcessingResult(
                    success=True,
                    command=command_text,
                    intent=intent,
                    confidence=confidence,
                    processing_time_ms=0,  # Will be set by caller
                    processed_on_edge=True
                )
            
        except Exception as e:
            logger.error(f"Edge processing error: {e}")
        
        return None
    
    async def _extract_text_from_audio(
        self,
        audio_features: Dict[str, Any]
    ) -> Optional[str]:
        """Extract text from audio features using edge ASR"""
        
        # This would use a lightweight ASR model
        # For simulation, extract from features
        return audio_features.get("transcript", "")
    
    def _categorize_command(self, command_text: str) -> Optional[CommandCategory]:
        """Categorize command for edge processing"""
        
        command_lower = command_text.lower()
        words = command_lower.split()
        
        # Check each category's vocabulary
        best_match = None
        best_score = 0
        
        for category, vocab in self.edge_vocabulary.items():
            # Count matching words
            matches = sum(1 for word in words if word in vocab)
            score = matches / len(words) if words else 0
            
            if score > best_score:
                best_score = score
                best_match = category
        
        # Require at least 40% word match
        if best_score >= 0.4:
            return best_match
        
        return None
    
    async def _run_edge_inference(
        self,
        command_text: str,
        edge_model: EdgeModel,
        context: Dict[str, Any]
    ) -> Tuple[Optional[str], float]:
        """Run inference on edge model"""
        
        command_lower = command_text.lower()
        words = command_lower.split()
        
        # Match against intent patterns
        category_patterns = {
            CommandCategory.NAVIGATION_SIMPLE: "navigation",
            CommandCategory.SAFETY_CRITICAL: "safety",
            CommandCategory.MEDIA_CONTROL: "media",
            CommandCategory.SYSTEM_CONTROL: "system"
        }
        
        pattern_key = category_patterns.get(edge_model.category)
        if not pattern_key:
            return None, 0.0
        
        patterns = self.intent_patterns.get(pattern_key, [])
        
        # Find best matching pattern
        best_intent = None
        best_confidence = 0.0
        
        for required_words, intent in patterns:
            # Check if all required words are present
            if all(word in command_lower for word in required_words):
                # Calculate confidence based on match quality
                confidence = self._calculate_pattern_confidence(
                    words,
                    required_words,
                    edge_model
                )
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_intent = intent
        
        # Apply context adjustments
        if best_intent:
            best_confidence = self._adjust_confidence_for_context(
                best_confidence,
                best_intent,
                context
            )
        
        return best_intent, best_confidence
    
    def _calculate_pattern_confidence(
        self,
        command_words: List[str],
        required_words: List[str],
        edge_model: EdgeModel
    ) -> float:
        """Calculate confidence for pattern match"""
        
        # Base confidence from model accuracy
        confidence = edge_model.accuracy
        
        # Adjust for word coverage
        coverage = len(required_words) / len(command_words) if command_words else 0
        confidence *= (0.7 + 0.3 * coverage)
        
        # Adjust for extra words (noise)
        extra_words = len(command_words) - len(required_words)
        if extra_words > 2:
            confidence *= 0.9 ** (extra_words - 2)
        
        return min(1.0, confidence)
    
    def _adjust_confidence_for_context(
        self,
        confidence: float,
        intent: str,
        context: Dict[str, Any]
    ) -> float:
        """Adjust confidence based on context"""
        
        # Boost confidence for expected intents
        if "expected_intents" in context:
            if intent in context["expected_intents"]:
                confidence *= 1.1
        
        # Reduce confidence in noisy environments
        noise_level = context.get("noise_level", "moderate")
        if noise_level == "high":
            confidence *= 0.9
        elif noise_level == "extreme":
            confidence *= 0.8
        
        # Boost for safety-critical intents
        if intent.startswith("emergency"):
            confidence *= 1.15
        
        return min(1.0, confidence)
    
    async def _process_cloud_fallback(
        self,
        audio_features: Dict[str, Any],
        context: Dict[str, Any],
        fallback_reason: str
    ) -> ProcessingResult:
        """Process via cloud when edge fails"""
        
        # This would call the actual cloud API
        # For now, simulate cloud processing
        await asyncio.sleep(0.1)  # Simulate network latency
        
        return ProcessingResult(
            success=True,
            command=audio_features.get("transcript", ""),
            intent="cloud_processed_intent",
            confidence=0.95,
            processing_time_ms=0,  # Will be set by caller
            processed_on_edge=False,
            fallback_reason=fallback_reason
        )
    
    async def _process_cloud_only(
        self,
        audio_features: Dict[str, Any],
        context: Dict[str, Any]
    ) -> ProcessingResult:
        """Process only via cloud"""
        
        return await self._process_cloud_fallback(
            audio_features,
            context,
            "cloud_only_mode"
        )
    
    async def _load_models(self):
        """Load edge models into memory"""
        
        logger.info("Loading edge models...")
        
        try:
            for category, model in self.edge_models.items():
                # Simulate model loading
                await asyncio.sleep(0.1)
                self.model_cache[model.model_id] = {
                    "loaded": True,
                    "model": model,
                    "loaded_at": datetime.now()
                }
                logger.info(f"Loaded edge model: {model.model_id}")
            
            self.models_loaded = True
            logger.info("All edge models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load edge models: {e}")
            self.models_loaded = False
    
    def _track_edge_success(
        self,
        success: bool,
        latency_ms: float,
        fallback_reason: Optional[str] = None
    ):
        """Track edge processing metrics"""
        
        self.edge_success_rate.append(success)
        self.latency_history.append(latency_ms)
        
        if fallback_reason:
            self.fallback_reasons[fallback_reason] = \
                self.fallback_reasons.get(fallback_reason, 0) + 1
    
    def update_processing_mode(self, mode: EdgeProcessingMode):
        """Update edge processing mode"""
        
        self.processing_mode = mode
        logger.info(f"Edge processing mode updated to: {mode.value}")
    
    def get_edge_models_info(self) -> Dict[str, Any]:
        """Get information about loaded edge models"""
        
        return {
            "models_loaded": self.models_loaded,
            "loaded_models": [
                {
                    "category": category.value,
                    "model_id": model.model_id,
                    "size_mb": model.size_mb,
                    "accuracy": model.accuracy,
                    "latency_ms": model.avg_latency_ms,
                    "offline_capable": model.supports_offline
                }
                for category, model in self.edge_models.items()
            ],
            "total_size_mb": sum(m.size_mb for m in self.edge_models.values())
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get edge processing performance metrics"""
        
        if not self.edge_success_rate:
            return {
                "edge_success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "fallback_reasons": {},
                "meets_target": False
            }
        
        success_rate = sum(self.edge_success_rate) / len(self.edge_success_rate)
        avg_latency = np.mean(list(self.latency_history)) if self.latency_history else 0
        
        # Calculate percentiles
        latencies = list(self.latency_history)
        p50 = np.percentile(latencies, 50) if latencies else 0
        p90 = np.percentile(latencies, 90) if latencies else 0
        p99 = np.percentile(latencies, 99) if latencies else 0
        
        return {
            "edge_success_rate": success_rate,
            "avg_latency_ms": avg_latency,
            "latency_p50": p50,
            "latency_p90": p90,
            "latency_p99": p99,
            "meets_target": avg_latency < self.latency_target_ms,
            "fallback_reasons": dict(self.fallback_reasons),
            "total_processed": len(self.edge_success_rate)
        }
    
    async def optimize_for_device(self, device_info: Dict[str, Any]):
        """Optimize edge processing for specific device"""
        
        # Adjust based on device capabilities
        cpu_cores = device_info.get("cpu_cores", 4)
        ram_gb = device_info.get("ram_gb", 4)
        
        if cpu_cores < 4 or ram_gb < 3:
            # Limited device - use only essential models
            self.processing_mode = EdgeProcessingMode.HYBRID
            logger.info("Limited device detected - using hybrid mode")
        elif cpu_cores >= 8 and ram_gb >= 6:
            # Powerful device - can handle full edge
            self.processing_mode = EdgeProcessingMode.FULL_EDGE
            logger.info("Powerful device detected - enabling full edge mode")
    
    def get_vocabulary_stats(self) -> Dict[str, Any]:
        """Get edge vocabulary statistics"""
        
        stats = {}
        for category, words in self.edge_vocabulary.items():
            stats[category.value] = {
                "word_count": len(words),
                "sample_words": words[:5]
            }
        
        total_words = sum(len(words) for words in self.edge_vocabulary.values())
        stats["total_vocabulary_size"] = total_words
        
        return stats


class EdgeModelOptimizer:
    """Optimizes edge models for deployment"""
    
    def __init__(self):
        self.optimization_strategies = {
            "quantization": self._apply_quantization,
            "pruning": self._apply_pruning,
            "knowledge_distillation": self._apply_distillation
        }
    
    async def optimize_model(
        self,
        model: EdgeModel,
        target_size_mb: float,
        target_latency_ms: float
    ) -> EdgeModel:
        """Optimize model for edge deployment"""
        
        optimized = model
        
        # Apply optimization strategies
        if model.size_mb > target_size_mb:
            optimized = await self._apply_quantization(optimized)
            
            if optimized.size_mb > target_size_mb:
                optimized = await self._apply_pruning(optimized)
        
        # Verify latency target
        if optimized.avg_latency_ms > target_latency_ms:
            logger.warning(
                f"Model {model.model_id} cannot meet latency target "
                f"({optimized.avg_latency_ms}ms > {target_latency_ms}ms)"
            )
        
        return optimized
    
    async def _apply_quantization(self, model: EdgeModel) -> EdgeModel:
        """Apply quantization to reduce model size"""
        
        # Simulate quantization impact
        quantized = EdgeModel(
            model_id=f"{model.model_id}_quantized",
            category=model.category,
            size_mb=model.size_mb * 0.25,  # 4x reduction
            accuracy=model.accuracy * 0.98,  # 2% accuracy loss
            avg_latency_ms=model.avg_latency_ms * 0.8,  # 20% faster
            vocabulary_size=model.vocabulary_size,
            supports_offline=model.supports_offline
        )
        
        return quantized
    
    async def _apply_pruning(self, model: EdgeModel) -> EdgeModel:
        """Apply pruning to reduce model complexity"""
        
        # Simulate pruning impact
        pruned = EdgeModel(
            model_id=f"{model.model_id}_pruned",
            category=model.category,
            size_mb=model.size_mb * 0.6,  # 40% reduction
            accuracy=model.accuracy * 0.97,  # 3% accuracy loss
            avg_latency_ms=model.avg_latency_ms * 0.9,  # 10% faster
            vocabulary_size=int(model.vocabulary_size * 0.8),  # Reduced vocab
            supports_offline=model.supports_offline
        )
        
        return pruned
    
    async def _apply_distillation(self, model: EdgeModel) -> EdgeModel:
        """Apply knowledge distillation for compact model"""
        
        # Simulate distillation impact
        distilled = EdgeModel(
            model_id=f"{model.model_id}_distilled",
            category=model.category,
            size_mb=model.size_mb * 0.3,  # 70% reduction
            accuracy=model.accuracy * 0.95,  # 5% accuracy loss
            avg_latency_ms=model.avg_latency_ms * 0.7,  # 30% faster
            vocabulary_size=model.vocabulary_size,
            supports_offline=model.supports_offline
        )
        
        return distilled


# Usage example
async def demonstrate_edge_processing():
    """Demonstrate edge voice processing"""
    
    processor = EdgeVoiceProcessor()
    
    # Wait for models to load
    await asyncio.sleep(1)
    
    # Test scenarios
    test_cases = [
        {
            "audio_features": {"transcript": "turn left at the next intersection"},
            "context": {"noise_level": "moderate", "network_available": True}
        },
        {
            "audio_features": {"transcript": "call 911 emergency"},
            "context": {"safety_critical": True, "noise_level": "high"}
        },
        {
            "audio_features": {"transcript": "play music"},
            "context": {"noise_level": "low", "edge_preference": "edge_only"}
        },
        {
            "audio_features": {"transcript": "book a hotel for tonight in San Francisco"},
            "context": {"noise_level": "moderate", "network_available": True}
        }
    ]
    
    print("Edge Voice Processing Demo")
    print("=" * 50)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['audio_features']['transcript']}")
        
        result = await processor.process_voice_command(
            test["audio_features"],
            test["context"]
        )
        
        print(f"  Success: {result.success}")
        print(f"  Intent: {result.intent}")
        print(f"  Confidence: {result.confidence:.2f}")
        print(f"  Latency: {result.processing_time_ms:.1f}ms")
        print(f"  Edge processed: {result.processed_on_edge}")
        if result.fallback_reason:
            print(f"  Fallback reason: {result.fallback_reason}")
    
    # Show performance metrics
    metrics = processor.get_performance_metrics()
    print(f"\nPerformance Metrics:")
    print(f"  Edge success rate: {metrics['edge_success_rate']:.1%}")
    print(f"  Average latency: {metrics['avg_latency_ms']:.1f}ms")
    print(f"  P90 latency: {metrics['latency_p90']:.1f}ms")
    print(f"  Meets target (<{processor.latency_target_ms}ms): {metrics['meets_target']}")
    
    # Show model info
    model_info = processor.get_edge_models_info()
    print(f"\nEdge Models:")
    print(f"  Total models: {len(model_info['loaded_models'])}")
    print(f"  Total size: {model_info['total_size_mb']:.1f}MB")


if __name__ == "__main__":
    asyncio.run(demonstrate_edge_processing())