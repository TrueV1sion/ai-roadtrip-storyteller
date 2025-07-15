"""
AI Model Selection Optimizer
Dynamically selects the optimal AI model based on task complexity, latency requirements, and cost
"""
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import time
import numpy as np
from collections import defaultdict

from app.core.logger import get_logger
from app.core.config import settings

logger = get_logger(__name__)


class ModelTier(Enum):
    """AI model tiers with different capabilities"""
    NANO = "nano"  # Ultra-fast, simple tasks
    FLASH = "flash"  # Fast, moderate complexity
    PRO = "pro"  # Balanced performance
    ULTRA = "ultra"  # High complexity, best quality


class TaskType(Enum):
    """Types of AI tasks"""
    SIMPLE_COMMAND = "simple_command"
    NAVIGATION = "navigation"
    STORY_GENERATION = "story_generation"
    COMPLEX_QUERY = "complex_query"
    BOOKING_SEARCH = "booking_search"
    EMERGENCY = "emergency"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"


@dataclass
class ModelProfile:
    """Profile for each AI model"""
    tier: ModelTier
    name: str
    model_id: str
    avg_latency_ms: float
    cost_per_1k_tokens: float
    max_tokens: int
    capabilities: List[TaskType]
    accuracy_score: float  # 0-1
    context_window: int
    supports_streaming: bool
    supports_function_calling: bool


@dataclass
class TaskRequirements:
    """Requirements for a specific task"""
    task_type: TaskType
    max_latency_ms: float
    min_accuracy: float
    estimated_tokens: int
    requires_streaming: bool
    requires_function_calling: bool
    priority: str  # critical, high, medium, low


@dataclass
class ModelSelectionResult:
    """Result of model selection"""
    selected_model: ModelProfile
    reasoning: str
    estimated_latency: float
    estimated_cost: float
    fallback_model: Optional[ModelProfile]
    confidence_score: float


class AIModelOptimizer:
    """Optimizes AI model selection for performance and cost"""
    
    def __init__(self):
        self.model_profiles = self._initialize_model_profiles()
        self.performance_history = defaultdict(list)
        self.model_availability = {model.model_id: True for model in self.model_profiles.values()}
        self.cost_tracker = defaultdict(float)
        self.latency_predictor = LatencyPredictor()
        
    def _initialize_model_profiles(self) -> Dict[ModelTier, ModelProfile]:
        """Initialize available model profiles"""
        return {
            ModelTier.NANO: ModelProfile(
                tier=ModelTier.NANO,
                name="Gemini Nano",
                model_id="gemini-nano",
                avg_latency_ms=50,
                cost_per_1k_tokens=0.00025,
                max_tokens=2048,
                capabilities=[
                    TaskType.SIMPLE_COMMAND,
                    TaskType.EMERGENCY
                ],
                accuracy_score=0.85,
                context_window=4096,
                supports_streaming=True,
                supports_function_calling=False
            ),
            
            ModelTier.FLASH: ModelProfile(
                tier=ModelTier.FLASH,
                name="Gemini 1.5 Flash",
                model_id="gemini-1.5-flash",
                avg_latency_ms=100,
                cost_per_1k_tokens=0.00035,
                max_tokens=8192,
                capabilities=[
                    TaskType.SIMPLE_COMMAND,
                    TaskType.NAVIGATION,
                    TaskType.BOOKING_SEARCH,
                    TaskType.EMERGENCY,
                    TaskType.TRANSLATION
                ],
                accuracy_score=0.92,
                context_window=32768,
                supports_streaming=True,
                supports_function_calling=True
            ),
            
            ModelTier.PRO: ModelProfile(
                tier=ModelTier.PRO,
                name="Gemini 1.5 Pro",
                model_id="gemini-1.5-pro",
                avg_latency_ms=200,
                cost_per_1k_tokens=0.00125,
                max_tokens=8192,
                capabilities=[
                    TaskType.SIMPLE_COMMAND,
                    TaskType.NAVIGATION,
                    TaskType.STORY_GENERATION,
                    TaskType.COMPLEX_QUERY,
                    TaskType.BOOKING_SEARCH,
                    TaskType.EMERGENCY,
                    TaskType.TRANSLATION,
                    TaskType.SUMMARIZATION
                ],
                accuracy_score=0.96,
                context_window=128000,
                supports_streaming=True,
                supports_function_calling=True
            ),
            
            ModelTier.ULTRA: ModelProfile(
                tier=ModelTier.ULTRA,
                name="Gemini Ultra",
                model_id="gemini-ultra",
                avg_latency_ms=500,
                cost_per_1k_tokens=0.00250,
                max_tokens=8192,
                capabilities=[
                    TaskType.STORY_GENERATION,
                    TaskType.COMPLEX_QUERY,
                    TaskType.SUMMARIZATION
                ],
                accuracy_score=0.99,
                context_window=200000,
                supports_streaming=True,
                supports_function_calling=True
            )
        }
    
    async def select_optimal_model(
        self,
        requirements: TaskRequirements,
        context: Optional[Dict[str, Any]] = None
    ) -> ModelSelectionResult:
        """Select the optimal model based on requirements"""
        
        start_time = time.time()
        context = context or {}
        
        # Filter eligible models
        eligible_models = self._filter_eligible_models(requirements)
        
        if not eligible_models:
            # Fallback to most capable available model
            fallback = self._get_fallback_model(requirements)
            return ModelSelectionResult(
                selected_model=fallback,
                reasoning="No models meet all requirements, using fallback",
                estimated_latency=fallback.avg_latency_ms,
                estimated_cost=self._calculate_cost(fallback, requirements.estimated_tokens),
                fallback_model=None,
                confidence_score=0.6
            )
        
        # Score each eligible model
        model_scores = []
        for model in eligible_models:
            score = await self._score_model(model, requirements, context)
            model_scores.append((model, score))
        
        # Sort by score (higher is better)
        model_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select best model
        selected_model = model_scores[0][0]
        confidence = model_scores[0][1]
        
        # Get fallback if confidence is low
        fallback_model = None
        if confidence < 0.8 and len(model_scores) > 1:
            fallback_model = model_scores[1][0]
        
        # Predict actual latency
        predicted_latency = await self.latency_predictor.predict(
            selected_model,
            requirements,
            context
        )
        
        # Calculate cost
        estimated_cost = self._calculate_cost(selected_model, requirements.estimated_tokens)
        
        # Generate reasoning
        reasoning = self._generate_selection_reasoning(
            selected_model,
            requirements,
            model_scores
        )
        
        # Track selection
        self._track_selection(selected_model, requirements, time.time() - start_time)
        
        return ModelSelectionResult(
            selected_model=selected_model,
            reasoning=reasoning,
            estimated_latency=predicted_latency,
            estimated_cost=estimated_cost,
            fallback_model=fallback_model,
            confidence_score=confidence
        )
    
    def _filter_eligible_models(self, requirements: TaskRequirements) -> List[ModelProfile]:
        """Filter models that meet basic requirements"""
        eligible = []
        
        for model in self.model_profiles.values():
            # Check availability
            if not self.model_availability.get(model.model_id, False):
                continue
            
            # Check capabilities
            if requirements.task_type not in model.capabilities:
                continue
            
            # Check streaming support
            if requirements.requires_streaming and not model.supports_streaming:
                continue
            
            # Check function calling support
            if requirements.requires_function_calling and not model.supports_function_calling:
                continue
            
            # Check token limits
            if requirements.estimated_tokens > model.max_tokens:
                continue
            
            # Check accuracy threshold
            if model.accuracy_score < requirements.min_accuracy:
                continue
            
            eligible.append(model)
        
        return eligible
    
    async def _score_model(
        self,
        model: ModelProfile,
        requirements: TaskRequirements,
        context: Dict[str, Any]
    ) -> float:
        """Score a model based on multiple factors"""
        
        # Base scores
        latency_score = self._score_latency(model, requirements)
        accuracy_score = self._score_accuracy(model, requirements)
        cost_score = self._score_cost(model, requirements)
        
        # Historical performance score
        history_score = self._score_historical_performance(model, requirements.task_type)
        
        # Context-based adjustments
        context_score = self._score_context(model, context)
        
        # Weight factors based on priority
        if requirements.priority == "critical":
            weights = {
                "latency": 0.4,
                "accuracy": 0.4,
                "cost": 0.05,
                "history": 0.1,
                "context": 0.05
            }
        elif requirements.priority == "high":
            weights = {
                "latency": 0.3,
                "accuracy": 0.3,
                "cost": 0.15,
                "history": 0.15,
                "context": 0.1
            }
        else:
            weights = {
                "latency": 0.2,
                "accuracy": 0.25,
                "cost": 0.25,
                "history": 0.2,
                "context": 0.1
            }
        
        # Calculate weighted score
        total_score = (
            weights["latency"] * latency_score +
            weights["accuracy"] * accuracy_score +
            weights["cost"] * cost_score +
            weights["history"] * history_score +
            weights["context"] * context_score
        )
        
        return total_score
    
    def _score_latency(self, model: ModelProfile, requirements: TaskRequirements) -> float:
        """Score based on latency requirements"""
        if model.avg_latency_ms <= requirements.max_latency_ms * 0.5:
            return 1.0  # Excellent
        elif model.avg_latency_ms <= requirements.max_latency_ms * 0.75:
            return 0.9  # Very good
        elif model.avg_latency_ms <= requirements.max_latency_ms:
            return 0.7  # Acceptable
        else:
            # Penalty for exceeding requirement
            excess_ratio = model.avg_latency_ms / requirements.max_latency_ms
            return max(0, 1 - (excess_ratio - 1))
    
    def _score_accuracy(self, model: ModelProfile, requirements: TaskRequirements) -> float:
        """Score based on accuracy"""
        if model.accuracy_score >= requirements.min_accuracy + 0.1:
            return 1.0
        elif model.accuracy_score >= requirements.min_accuracy:
            return 0.8
        else:
            return model.accuracy_score / requirements.min_accuracy
    
    def _score_cost(self, model: ModelProfile, requirements: TaskRequirements) -> float:
        """Score based on cost efficiency"""
        # Normalize cost scores (lower cost = higher score)
        max_cost = max(m.cost_per_1k_tokens for m in self.model_profiles.values())
        min_cost = min(m.cost_per_1k_tokens for m in self.model_profiles.values())
        
        if max_cost == min_cost:
            return 1.0
        
        normalized_cost = (model.cost_per_1k_tokens - min_cost) / (max_cost - min_cost)
        return 1 - normalized_cost
    
    def _score_historical_performance(self, model: ModelProfile, task_type: TaskType) -> float:
        """Score based on historical performance"""
        history_key = f"{model.model_id}_{task_type.value}"
        history = self.performance_history.get(history_key, [])
        
        if not history:
            return 0.8  # Neutral score for no history
        
        # Consider recent performance (last 100 uses)
        recent_history = history[-100:]
        
        # Calculate success rate
        success_rate = sum(1 for h in recent_history if h["success"]) / len(recent_history)
        
        # Calculate average latency ratio
        latency_ratios = [h["actual_latency"] / h["predicted_latency"] for h in recent_history]
        avg_latency_ratio = np.mean(latency_ratios)
        
        # Combine scores
        performance_score = success_rate * 0.7
        if avg_latency_ratio <= 1.1:  # Within 10% of prediction
            performance_score += 0.3
        elif avg_latency_ratio <= 1.25:  # Within 25%
            performance_score += 0.2
        else:
            performance_score += 0.1
        
        return min(1.0, performance_score)
    
    def _score_context(self, model: ModelProfile, context: Dict[str, Any]) -> float:
        """Score based on context (user preferences, device, etc.)"""
        score = 0.8  # Base score
        
        # User preference
        if "preferred_model" in context:
            if context["preferred_model"] == model.model_id:
                score += 0.2
        
        # Device constraints
        if "device" in context:
            if context["device"] == "mobile" and model.tier in [ModelTier.NANO, ModelTier.FLASH]:
                score += 0.1
            elif context["device"] == "desktop" and model.tier in [ModelTier.PRO, ModelTier.ULTRA]:
                score += 0.1
        
        # Network conditions
        if "network_quality" in context:
            if context["network_quality"] == "poor" and model.tier == ModelTier.NANO:
                score += 0.15
            elif context["network_quality"] == "excellent" and model.tier == ModelTier.ULTRA:
                score += 0.1
        
        return min(1.0, score)
    
    def _calculate_cost(self, model: ModelProfile, estimated_tokens: int) -> float:
        """Calculate estimated cost for tokens"""
        return (estimated_tokens / 1000) * model.cost_per_1k_tokens
    
    def _get_fallback_model(self, requirements: TaskRequirements) -> ModelProfile:
        """Get fallback model when no models meet requirements"""
        # For emergency tasks, always use fastest available
        if requirements.task_type == TaskType.EMERGENCY:
            return self.model_profiles[ModelTier.NANO]
        
        # Otherwise, use most capable model
        return self.model_profiles[ModelTier.PRO]
    
    def _generate_selection_reasoning(
        self,
        selected_model: ModelProfile,
        requirements: TaskRequirements,
        model_scores: List[Tuple[ModelProfile, float]]
    ) -> str:
        """Generate human-readable reasoning for selection"""
        reasons = []
        
        # Primary reason
        if requirements.priority == "critical":
            reasons.append(f"Selected {selected_model.name} for critical {requirements.task_type.value} task")
        else:
            reasons.append(f"Selected {selected_model.name} for {requirements.task_type.value}")
        
        # Latency reason
        if selected_model.avg_latency_ms < requirements.max_latency_ms * 0.5:
            reasons.append(f"Excellent latency ({selected_model.avg_latency_ms}ms)")
        
        # Accuracy reason
        if selected_model.accuracy_score > requirements.min_accuracy + 0.05:
            reasons.append(f"High accuracy ({selected_model.accuracy_score:.0%})")
        
        # Cost reason
        if len(model_scores) > 1:
            cost_rank = sorted(
                [m[0] for m in model_scores],
                key=lambda x: x.cost_per_1k_tokens
            ).index(selected_model) + 1
            if cost_rank == 1:
                reasons.append("Most cost-effective option")
        
        return ". ".join(reasons)
    
    def _track_selection(
        self,
        model: ModelProfile,
        requirements: TaskRequirements,
        selection_time: float
    ):
        """Track model selection for analytics"""
        logger.info(
            f"Model selected: {model.name} for {requirements.task_type.value} "
            f"(selection time: {selection_time*1000:.1f}ms)"
        )
        
        # Update cost tracker
        estimated_cost = self._calculate_cost(model, requirements.estimated_tokens)
        self.cost_tracker[model.model_id] += estimated_cost
    
    def update_performance_history(
        self,
        model_id: str,
        task_type: TaskType,
        success: bool,
        actual_latency: float,
        predicted_latency: float
    ):
        """Update performance history after execution"""
        history_key = f"{model_id}_{task_type.value}"
        
        self.performance_history[history_key].append({
            "timestamp": datetime.now(),
            "success": success,
            "actual_latency": actual_latency,
            "predicted_latency": predicted_latency
        })
        
        # Keep only recent history
        if len(self.performance_history[history_key]) > 1000:
            self.performance_history[history_key] = self.performance_history[history_key][-1000:]
    
    def update_model_availability(self, model_id: str, available: bool):
        """Update model availability status"""
        self.model_availability[model_id] = available
        logger.warning(f"Model {model_id} availability updated to: {available}")
    
    def get_cost_report(self) -> Dict[str, Any]:
        """Get cost tracking report"""
        total_cost = sum(self.cost_tracker.values())
        
        return {
            "total_cost": total_cost,
            "cost_by_model": dict(self.cost_tracker),
            "cost_breakdown": {
                model_id: (cost / total_cost * 100) if total_cost > 0 else 0
                for model_id, cost in self.cost_tracker.items()
            }
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get performance metrics report"""
        report = {
            "model_usage": defaultdict(int),
            "task_distribution": defaultdict(int),
            "average_latencies": {},
            "success_rates": {}
        }
        
        for history_key, history in self.performance_history.items():
            if history:
                model_id, task_type = history_key.split("_", 1)
                
                report["model_usage"][model_id] += len(history)
                report["task_distribution"][task_type] += len(history)
                
                # Calculate metrics
                latencies = [h["actual_latency"] for h in history]
                successes = [h["success"] for h in history]
                
                report["average_latencies"][history_key] = np.mean(latencies)
                report["success_rates"][history_key] = sum(successes) / len(successes)
        
        return dict(report)


class LatencyPredictor:
    """Predicts actual latency based on various factors"""
    
    def __init__(self):
        self.baseline_adjustments = {
            "time_of_day": self._time_of_day_factor,
            "token_count": self._token_count_factor,
            "complexity": self._complexity_factor,
            "load": self._load_factor
        }
    
    async def predict(
        self,
        model: ModelProfile,
        requirements: TaskRequirements,
        context: Dict[str, Any]
    ) -> float:
        """Predict actual latency for model and task"""
        
        # Start with baseline
        predicted_latency = model.avg_latency_ms
        
        # Apply adjustments
        for factor_name, factor_func in self.baseline_adjustments.items():
            adjustment = factor_func(model, requirements, context)
            predicted_latency *= adjustment
        
        # Add variability
        predicted_latency += np.random.normal(0, predicted_latency * 0.1)
        
        return max(10, predicted_latency)  # Minimum 10ms
    
    def _time_of_day_factor(
        self,
        model: ModelProfile,
        requirements: TaskRequirements,
        context: Dict[str, Any]
    ) -> float:
        """Adjust for time of day (peak hours)"""
        current_hour = datetime.now().hour
        
        # Peak hours: 9-11 AM, 2-4 PM, 7-9 PM
        if current_hour in [9, 10, 14, 15, 19, 20]:
            return 1.2
        elif current_hour in [11, 16, 21]:
            return 1.1
        else:
            return 1.0
    
    def _token_count_factor(
        self,
        model: ModelProfile,
        requirements: TaskRequirements,
        context: Dict[str, Any]
    ) -> float:
        """Adjust for token count"""
        if requirements.estimated_tokens < 100:
            return 0.8
        elif requirements.estimated_tokens < 500:
            return 1.0
        elif requirements.estimated_tokens < 2000:
            return 1.2
        else:
            return 1.5
    
    def _complexity_factor(
        self,
        model: ModelProfile,
        requirements: TaskRequirements,
        context: Dict[str, Any]
    ) -> float:
        """Adjust for task complexity"""
        complexity_multipliers = {
            TaskType.SIMPLE_COMMAND: 0.9,
            TaskType.NAVIGATION: 1.0,
            TaskType.BOOKING_SEARCH: 1.1,
            TaskType.STORY_GENERATION: 1.3,
            TaskType.COMPLEX_QUERY: 1.4,
            TaskType.EMERGENCY: 0.8,  # Prioritized
            TaskType.TRANSLATION: 1.1,
            TaskType.SUMMARIZATION: 1.2
        }
        
        return complexity_multipliers.get(requirements.task_type, 1.0)
    
    def _load_factor(
        self,
        model: ModelProfile,
        requirements: TaskRequirements,
        context: Dict[str, Any]
    ) -> float:
        """Adjust for system load"""
        # This would integrate with actual load metrics
        # For now, simulate
        if context.get("system_load", "normal") == "high":
            return 1.3
        elif context.get("system_load", "normal") == "low":
            return 0.9
        else:
            return 1.0


# Usage example
async def demonstrate_model_selection():
    """Demonstrate AI model selection"""
    optimizer = AIModelOptimizer()
    
    # Example 1: Emergency command
    emergency_req = TaskRequirements(
        task_type=TaskType.EMERGENCY,
        max_latency_ms=100,
        min_accuracy=0.9,
        estimated_tokens=50,
        requires_streaming=False,
        requires_function_calling=False,
        priority="critical"
    )
    
    result = await optimizer.select_optimal_model(emergency_req)
    print(f"Emergency: {result.selected_model.name} ({result.estimated_latency:.0f}ms)")
    print(f"  Reasoning: {result.reasoning}")
    
    # Example 2: Story generation
    story_req = TaskRequirements(
        task_type=TaskType.STORY_GENERATION,
        max_latency_ms=500,
        min_accuracy=0.95,
        estimated_tokens=2000,
        requires_streaming=True,
        requires_function_calling=False,
        priority="medium"
    )
    
    result = await optimizer.select_optimal_model(story_req, {"device": "mobile"})
    print(f"\nStory: {result.selected_model.name} ({result.estimated_latency:.0f}ms)")
    print(f"  Cost: ${result.estimated_cost:.4f}")
    
    # Example 3: Complex navigation
    nav_req = TaskRequirements(
        task_type=TaskType.NAVIGATION,
        max_latency_ms=200,
        min_accuracy=0.9,
        estimated_tokens=500,
        requires_streaming=False,
        requires_function_calling=True,
        priority="high"
    )
    
    result = await optimizer.select_optimal_model(nav_req, {"network_quality": "poor"})
    print(f"\nNavigation: {result.selected_model.name} ({result.estimated_latency:.0f}ms)")
    print(f"  Confidence: {result.confidence_score:.0%}")


if __name__ == "__main__":
    asyncio.run(demonstrate_model_selection())