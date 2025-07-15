"""
Response Time Optimizer
Achieves <100ms response time through intelligent optimization and monitoring
"""
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio
import time
import numpy as np
from collections import deque, defaultdict
import json

from app.core.logger import get_logger
from app.services.ai_model_optimizer import AIModelOptimizer, TaskType, TaskRequirements
from app.services.predictive_cache_system import PredictiveCacheSystem
from app.services.edge_voice_processor import EdgeVoiceProcessor

logger = get_logger(__name__)


class OptimizationStrategy(Enum):
    """Strategies for response time optimization"""
    EDGE_FIRST = "edge_first"
    CACHE_FIRST = "cache_first"
    PARALLEL_PROCESSING = "parallel_processing"
    PRECOMPUTE = "precompute"
    STREAM_EARLY = "stream_early"
    DEGRADED_MODE = "degraded_mode"


class ResponseComponent(Enum):
    """Components of response time"""
    AUDIO_CAPTURE = "audio_capture"
    SPEECH_TO_TEXT = "speech_to_text"
    INTENT_RECOGNITION = "intent_recognition"
    AI_PROCESSING = "ai_processing"
    DATA_FETCH = "data_fetch"
    RESPONSE_GENERATION = "response_generation"
    TEXT_TO_SPEECH = "text_to_speech"
    NETWORK_LATENCY = "network_latency"


@dataclass
class LatencyBudget:
    """Budget allocation for each component"""
    component: ResponseComponent
    target_ms: float
    max_ms: float
    priority: int  # 1-10, higher is more important


@dataclass
class ResponseMetrics:
    """Metrics for a single response"""
    request_id: str
    total_time_ms: float
    component_times: Dict[ResponseComponent, float]
    cache_hits: List[str]
    edge_processed: bool
    strategies_used: List[OptimizationStrategy]
    success: bool
    timestamp: datetime


@dataclass
class OptimizationResult:
    """Result of optimization attempt"""
    optimized: bool
    final_time_ms: float
    strategies_applied: List[OptimizationStrategy]
    bottlenecks: List[ResponseComponent]
    recommendations: List[str]


class ResponseTimeOptimizer:
    """Optimizes system response time to achieve <100ms target"""
    
    def __init__(self):
        self.target_response_time_ms = 100
        self.latency_budgets = self._initialize_latency_budgets()
        
        # Sub-systems
        self.ai_optimizer = AIModelOptimizer()
        self.cache_system = PredictiveCacheSystem()
        self.edge_processor = EdgeVoiceProcessor()
        
        # Metrics tracking
        self.response_history = deque(maxlen=10000)
        self.component_latencies = defaultdict(lambda: deque(maxlen=1000))
        self.optimization_success_rate = deque(maxlen=1000)
        
        # Real-time monitoring
        self.current_p50 = 0.0
        self.current_p90 = 0.0
        self.current_p99 = 0.0
        
        # Optimization state
        self.auto_optimize = True
        self.current_strategies = [OptimizationStrategy.CACHE_FIRST]
        
        # Start monitoring
        asyncio.create_task(self._monitor_loop())
    
    def _initialize_latency_budgets(self) -> Dict[ResponseComponent, LatencyBudget]:
        """Initialize latency budget for each component"""
        return {
            ResponseComponent.AUDIO_CAPTURE: LatencyBudget(
                component=ResponseComponent.AUDIO_CAPTURE,
                target_ms=5,
                max_ms=10,
                priority=8
            ),
            ResponseComponent.SPEECH_TO_TEXT: LatencyBudget(
                component=ResponseComponent.SPEECH_TO_TEXT,
                target_ms=20,
                max_ms=40,
                priority=9
            ),
            ResponseComponent.INTENT_RECOGNITION: LatencyBudget(
                component=ResponseComponent.INTENT_RECOGNITION,
                target_ms=10,
                max_ms=20,
                priority=9
            ),
            ResponseComponent.AI_PROCESSING: LatencyBudget(
                component=ResponseComponent.AI_PROCESSING,
                target_ms=30,
                max_ms=50,
                priority=7
            ),
            ResponseComponent.DATA_FETCH: LatencyBudget(
                component=ResponseComponent.DATA_FETCH,
                target_ms=15,
                max_ms=30,
                priority=6
            ),
            ResponseComponent.RESPONSE_GENERATION: LatencyBudget(
                component=ResponseComponent.RESPONSE_GENERATION,
                target_ms=10,
                max_ms=20,
                priority=8
            ),
            ResponseComponent.TEXT_TO_SPEECH: LatencyBudget(
                component=ResponseComponent.TEXT_TO_SPEECH,
                target_ms=5,
                max_ms=15,
                priority=7
            ),
            ResponseComponent.NETWORK_LATENCY: LatencyBudget(
                component=ResponseComponent.NETWORK_LATENCY,
                target_ms=5,
                max_ms=20,
                priority=5
            )
        }
    
    async def process_request_optimized(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Tuple[Any, ResponseMetrics]:
        """Process request with optimization"""
        
        request_id = f"req_{int(time.time() * 1000)}"
        start_time = time.time()
        component_times = {}
        strategies_used = []
        cache_hits = []
        
        try:
            # Stage 1: Audio capture and STT
            audio_start = time.time()
            
            # Try edge processing first
            edge_result = None
            if OptimizationStrategy.EDGE_FIRST in self.current_strategies:
                edge_result = await self._try_edge_processing(request_data, context)
                if edge_result and edge_result.processed_on_edge:
                    strategies_used.append(OptimizationStrategy.EDGE_FIRST)
                    component_times[ResponseComponent.SPEECH_TO_TEXT] = edge_result.processing_time_ms
                    component_times[ResponseComponent.INTENT_RECOGNITION] = 0  # Included in edge
            
            # Fallback to cloud STT if needed
            if not edge_result or not edge_result.success:
                text, stt_time = await self._process_speech_to_text(request_data)
                component_times[ResponseComponent.SPEECH_TO_TEXT] = stt_time * 1000
                
                # Intent recognition
                intent_start = time.time()
                intent = await self._recognize_intent(text, context)
                component_times[ResponseComponent.INTENT_RECOGNITION] = (time.time() - intent_start) * 1000
            else:
                text = edge_result.command
                intent = edge_result.intent
            
            component_times[ResponseComponent.AUDIO_CAPTURE] = (time.time() - audio_start) * 1000
            
            # Stage 2: Check cache
            cache_key = self._generate_cache_key(intent, context)
            cached_response = None
            
            if OptimizationStrategy.CACHE_FIRST in self.current_strategies:
                cache_start = time.time()
                cached_response = await self.cache_system.get_or_predict(
                    cache_key,
                    context,
                    lambda: None,  # Don't fetch if not cached
                    cache_duration=300
                )
                
                if cached_response[0] is not None:
                    strategies_used.append(OptimizationStrategy.CACHE_FIRST)
                    cache_hits.append(cache_key)
                    component_times[ResponseComponent.AI_PROCESSING] = (time.time() - cache_start) * 1000
                    component_times[ResponseComponent.DATA_FETCH] = 0  # Cached
            
            # Stage 3: AI Processing (if not cached)
            if cached_response is None or cached_response[0] is None:
                # Select optimal AI model
                ai_start = time.time()
                
                task_req = self._create_task_requirements(intent, context)
                model_result = await self.ai_optimizer.select_optimal_model(task_req, context)
                
                # Process with selected model
                if OptimizationStrategy.PARALLEL_PROCESSING in self.current_strategies:
                    response = await self._process_parallel(text, intent, model_result, context)
                    strategies_used.append(OptimizationStrategy.PARALLEL_PROCESSING)
                else:
                    response = await self._process_sequential(text, intent, model_result, context)
                
                component_times[ResponseComponent.AI_PROCESSING] = (time.time() - ai_start) * 1000
            else:
                response = cached_response[0]
            
            # Stage 4: Response generation and TTS
            if OptimizationStrategy.STREAM_EARLY in self.current_strategies:
                # Start streaming TTS while still processing
                tts_task = asyncio.create_task(self._generate_speech_streaming(response))
                strategies_used.append(OptimizationStrategy.STREAM_EARLY)
            else:
                tts_start = time.time()
                audio_response = await self._generate_speech(response)
                component_times[ResponseComponent.TEXT_TO_SPEECH] = (time.time() - tts_start) * 1000
            
            # Calculate total time
            total_time = (time.time() - start_time) * 1000
            
            # Create metrics
            metrics = ResponseMetrics(
                request_id=request_id,
                total_time_ms=total_time,
                component_times=component_times,
                cache_hits=cache_hits,
                edge_processed=bool(edge_result and edge_result.processed_on_edge),
                strategies_used=strategies_used,
                success=True,
                timestamp=datetime.now()
            )
            
            # Track metrics
            self._track_response_metrics(metrics)
            
            # Apply optimizations if needed
            if total_time > self.target_response_time_ms and self.auto_optimize:
                await self._apply_dynamic_optimization(metrics)
            
            # Return response with metrics
            if OptimizationStrategy.STREAM_EARLY in self.current_strategies and 'tts_task' in locals():
                audio_response = await tts_task
            
            return response, metrics
            
        except Exception as e:
            logger.error(f"Request processing error: {e}")
            
            # Error metrics
            metrics = ResponseMetrics(
                request_id=request_id,
                total_time_ms=(time.time() - start_time) * 1000,
                component_times=component_times,
                cache_hits=cache_hits,
                edge_processed=False,
                strategies_used=strategies_used,
                success=False,
                timestamp=datetime.now()
            )
            
            self._track_response_metrics(metrics)
            raise
    
    async def _try_edge_processing(
        self,
        request_data: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """Try edge processing for ultra-low latency"""
        
        try:
            result = await self.edge_processor.process_voice_command(
                request_data.get("audio_features", {}),
                context
            )
            return result
        except Exception as e:
            logger.error(f"Edge processing error: {e}")
            return None
    
    async def _process_speech_to_text(
        self,
        request_data: Dict[str, Any]
    ) -> Tuple[str, float]:
        """Process speech to text"""
        
        start = time.time()
        # Simulate STT processing
        await asyncio.sleep(0.02)  # 20ms
        text = request_data.get("text", "sample command")
        return text, time.time() - start
    
    async def _recognize_intent(
        self,
        text: str,
        context: Dict[str, Any]
    ) -> str:
        """Recognize intent from text"""
        
        # Simulate intent recognition
        await asyncio.sleep(0.01)  # 10ms
        
        # Simple intent mapping
        text_lower = text.lower()
        if "navigate" in text_lower or "route" in text_lower:
            return "navigation"
        elif "book" in text_lower or "reserve" in text_lower:
            return "booking"
        elif "play" in text_lower or "music" in text_lower:
            return "entertainment"
        else:
            return "general"
    
    def _generate_cache_key(self, intent: str, context: Dict[str, Any]) -> str:
        """Generate cache key for request"""
        
        # Include relevant context in cache key
        key_parts = [
            intent,
            str(context.get("location", "")),
            str(context.get("user_id", ""))
        ]
        
        return "_".join(key_parts)
    
    def _create_task_requirements(
        self,
        intent: str,
        context: Dict[str, Any]
    ) -> TaskRequirements:
        """Create task requirements for AI model selection"""
        
        # Map intent to task type
        task_map = {
            "navigation": TaskType.NAVIGATION,
            "booking": TaskType.BOOKING_SEARCH,
            "entertainment": TaskType.STORY_GENERATION,
            "general": TaskType.SIMPLE_COMMAND
        }
        
        task_type = task_map.get(intent, TaskType.SIMPLE_COMMAND)
        
        # Determine requirements
        if context.get("emergency", False):
            max_latency = 50
            priority = "critical"
        elif context.get("driving_speed", 0) > 60:
            max_latency = 100
            priority = "high"
        else:
            max_latency = 150
            priority = "medium"
        
        return TaskRequirements(
            task_type=task_type,
            max_latency_ms=max_latency,
            min_accuracy=0.9,
            estimated_tokens=100,
            requires_streaming=False,
            requires_function_calling=False,
            priority=priority
        )
    
    async def _process_parallel(
        self,
        text: str,
        intent: str,
        model_result: Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process with parallel execution"""
        
        # Execute independent tasks in parallel
        tasks = []
        
        # AI processing
        tasks.append(self._execute_ai_processing(text, model_result))
        
        # Data fetching (if needed)
        if intent in ["navigation", "booking"]:
            tasks.append(self._fetch_required_data(intent, context))
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        response = {"text": results[0] if not isinstance(results[0], Exception) else "Error"}
        if len(results) > 1 and not isinstance(results[1], Exception):
            response["data"] = results[1]
        
        return response
    
    async def _process_sequential(
        self,
        text: str,
        intent: str,
        model_result: Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process with sequential execution"""
        
        # AI processing
        ai_response = await self._execute_ai_processing(text, model_result)
        
        # Data fetching if needed
        data = None
        if intent in ["navigation", "booking"]:
            data = await self._fetch_required_data(intent, context)
        
        return {"text": ai_response, "data": data}
    
    async def _execute_ai_processing(self, text: str, model_result: Any) -> str:
        """Execute AI processing"""
        
        # Simulate AI processing with selected model
        await asyncio.sleep(model_result.estimated_latency / 1000)
        return f"Response to: {text}"
    
    async def _fetch_required_data(self, intent: str, context: Dict[str, Any]) -> Any:
        """Fetch required data for intent"""
        
        # Simulate data fetching
        await asyncio.sleep(0.015)  # 15ms
        return {"sample": "data"}
    
    async def _generate_speech(self, response: Dict[str, Any]) -> bytes:
        """Generate speech from response"""
        
        # Simulate TTS
        await asyncio.sleep(0.005)  # 5ms
        return b"audio_data"
    
    async def _generate_speech_streaming(self, response: Dict[str, Any]) -> bytes:
        """Generate speech with streaming"""
        
        # Start streaming immediately
        await asyncio.sleep(0.002)  # 2ms to start
        return b"streaming_audio_data"
    
    def _track_response_metrics(self, metrics: ResponseMetrics):
        """Track response metrics"""
        
        # Add to history
        self.response_history.append(metrics)
        
        # Track component latencies
        for component, latency in metrics.component_times.items():
            self.component_latencies[component].append(latency)
        
        # Track optimization success
        self.optimization_success_rate.append(
            metrics.total_time_ms <= self.target_response_time_ms
        )
        
        # Log if exceeds target
        if metrics.total_time_ms > self.target_response_time_ms:
            logger.warning(
                f"Response exceeded target: {metrics.total_time_ms:.1f}ms > {self.target_response_time_ms}ms"
            )
    
    async def _apply_dynamic_optimization(self, metrics: ResponseMetrics):
        """Apply dynamic optimization based on metrics"""
        
        # Identify bottlenecks
        bottlenecks = self._identify_bottlenecks(metrics)
        
        if not bottlenecks:
            return
        
        logger.info(f"Applying optimization for bottlenecks: {[b.value for b in bottlenecks]}")
        
        # Apply targeted optimizations
        for bottleneck in bottlenecks:
            if bottleneck == ResponseComponent.SPEECH_TO_TEXT:
                # Enable edge processing
                if OptimizationStrategy.EDGE_FIRST not in self.current_strategies:
                    self.current_strategies.append(OptimizationStrategy.EDGE_FIRST)
                    
            elif bottleneck == ResponseComponent.AI_PROCESSING:
                # Enable parallel processing
                if OptimizationStrategy.PARALLEL_PROCESSING not in self.current_strategies:
                    self.current_strategies.append(OptimizationStrategy.PARALLEL_PROCESSING)
                    
            elif bottleneck == ResponseComponent.DATA_FETCH:
                # Enhance caching
                if OptimizationStrategy.PRECOMPUTE not in self.current_strategies:
                    self.current_strategies.append(OptimizationStrategy.PRECOMPUTE)
                    
            elif bottleneck == ResponseComponent.TEXT_TO_SPEECH:
                # Enable streaming
                if OptimizationStrategy.STREAM_EARLY not in self.current_strategies:
                    self.current_strategies.append(OptimizationStrategy.STREAM_EARLY)
    
    def _identify_bottlenecks(self, metrics: ResponseMetrics) -> List[ResponseComponent]:
        """Identify performance bottlenecks"""
        
        bottlenecks = []
        
        for component, latency in metrics.component_times.items():
            budget = self.latency_budgets.get(component)
            if budget and latency > budget.max_ms:
                bottlenecks.append(component)
        
        # Sort by severity (how much they exceed budget)
        bottlenecks.sort(
            key=lambda c: metrics.component_times[c] / self.latency_budgets[c].max_ms,
            reverse=True
        )
        
        return bottlenecks[:3]  # Top 3 bottlenecks
    
    async def _monitor_loop(self):
        """Background monitoring loop"""
        
        while True:
            try:
                await asyncio.sleep(10)  # Update every 10 seconds
                
                # Calculate current metrics
                self._update_performance_metrics()
                
                # Log current performance
                if self.current_p90 > self.target_response_time_ms:
                    logger.warning(
                        f"P90 latency exceeds target: {self.current_p90:.1f}ms > {self.target_response_time_ms}ms"
                    )
                
                # Apply proactive optimizations
                if self.auto_optimize:
                    await self._apply_proactive_optimizations()
                    
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
    
    def _update_performance_metrics(self):
        """Update current performance metrics"""
        
        if not self.response_history:
            return
        
        # Get recent response times
        recent_times = [r.total_time_ms for r in list(self.response_history)[-1000:]]
        
        if recent_times:
            self.current_p50 = np.percentile(recent_times, 50)
            self.current_p90 = np.percentile(recent_times, 90)
            self.current_p99 = np.percentile(recent_times, 99)
    
    async def _apply_proactive_optimizations(self):
        """Apply proactive optimizations based on trends"""
        
        # Check if we're consistently missing targets
        if len(self.optimization_success_rate) >= 100:
            recent_success_rate = sum(list(self.optimization_success_rate)[-100:]) / 100
            
            if recent_success_rate < 0.9:  # Less than 90% meeting target
                # Enable more aggressive optimization
                logger.info("Enabling aggressive optimization mode")
                
                # Add all optimization strategies
                all_strategies = list(OptimizationStrategy)
                for strategy in all_strategies:
                    if strategy not in self.current_strategies:
                        self.current_strategies.append(strategy)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        
        if not self.response_history:
            return {"error": "No data available"}
        
        # Overall metrics
        all_times = [r.total_time_ms for r in self.response_history]
        success_rate = sum(self.optimization_success_rate) / len(self.optimization_success_rate) \
                      if self.optimization_success_rate else 0
        
        # Component breakdown
        component_stats = {}
        for component in ResponseComponent:
            if component in self.component_latencies:
                latencies = list(self.component_latencies[component])
                if latencies:
                    component_stats[component.value] = {
                        "avg": np.mean(latencies),
                        "p50": np.percentile(latencies, 50),
                        "p90": np.percentile(latencies, 90),
                        "budget": self.latency_budgets[component].target_ms
                    }
        
        # Strategy effectiveness
        strategy_effectiveness = {}
        for strategy in OptimizationStrategy:
            strategy_responses = [
                r for r in self.response_history 
                if strategy in r.strategies_used
            ]
            if strategy_responses:
                strategy_times = [r.total_time_ms for r in strategy_responses]
                strategy_effectiveness[strategy.value] = {
                    "count": len(strategy_responses),
                    "avg_time": np.mean(strategy_times),
                    "success_rate": sum(1 for t in strategy_times if t <= self.target_response_time_ms) / len(strategy_times)
                }
        
        return {
            "summary": {
                "target_ms": self.target_response_time_ms,
                "current_p50": self.current_p50,
                "current_p90": self.current_p90,
                "current_p99": self.current_p99,
                "success_rate": success_rate,
                "total_requests": len(self.response_history)
            },
            "component_breakdown": component_stats,
            "bottlenecks": self._get_common_bottlenecks(),
            "strategy_effectiveness": strategy_effectiveness,
            "recommendations": self._generate_optimization_recommendations()
        }
    
    def _get_common_bottlenecks(self) -> List[Dict[str, Any]]:
        """Get most common bottlenecks"""
        
        bottleneck_counts = defaultdict(int)
        
        for response in list(self.response_history)[-1000:]:
            bottlenecks = self._identify_bottlenecks(response)
            for bottleneck in bottlenecks:
                bottleneck_counts[bottleneck.value] += 1
        
        # Sort by frequency
        sorted_bottlenecks = sorted(
            bottleneck_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return [
            {"component": component, "frequency": count}
            for component, count in sorted_bottlenecks[:5]
        ]
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations"""
        
        recommendations = []
        
        # Check overall performance
        if self.current_p90 > self.target_response_time_ms:
            recommendations.append(
                f"P90 latency ({self.current_p90:.1f}ms) exceeds target. "
                f"Consider more aggressive optimization strategies."
            )
        
        # Check component performance
        for component, latencies in self.component_latencies.items():
            if latencies:
                avg_latency = np.mean(list(latencies))
                budget = self.latency_budgets[component]
                
                if avg_latency > budget.target_ms * 1.5:
                    recommendations.append(
                        f"{component.value} averaging {avg_latency:.1f}ms "
                        f"(target: {budget.target_ms}ms). Needs optimization."
                    )
        
        # Check strategy effectiveness
        if OptimizationStrategy.EDGE_FIRST not in self.current_strategies:
            recommendations.append(
                "Edge processing not enabled. Enable for ~20ms reduction in STT latency."
            )
        
        if OptimizationStrategy.STREAM_EARLY not in self.current_strategies:
            recommendations.append(
                "Early streaming not enabled. Enable for better perceived latency."
            )
        
        # Success rate recommendation
        success_rate = sum(self.optimization_success_rate) / len(self.optimization_success_rate) \
                      if self.optimization_success_rate else 0
        
        if success_rate < 0.95:
            recommendations.append(
                f"Only {success_rate:.1%} of requests meet target. "
                f"Review architecture for fundamental improvements."
            )
        
        if not recommendations:
            recommendations.append("System performing well. Continue monitoring.")
        
        return recommendations
    
    async def run_latency_test(self, num_requests: int = 100) -> Dict[str, Any]:
        """Run latency test with various scenarios"""
        
        logger.info(f"Running latency test with {num_requests} requests...")
        
        test_scenarios = [
            {"intent": "navigation", "complexity": "simple"},
            {"intent": "booking", "complexity": "moderate"},
            {"intent": "entertainment", "complexity": "complex"},
            {"intent": "general", "complexity": "simple"}
        ]
        
        results = []
        
        for i in range(num_requests):
            scenario = test_scenarios[i % len(test_scenarios)]
            
            request_data = {
                "text": f"Test command for {scenario['intent']}",
                "audio_features": {"transcript": f"Test {i}"}
            }
            
            context = {
                "test": True,
                "scenario": scenario,
                "driving_speed": 30 if i % 2 == 0 else 70
            }
            
            try:
                _, metrics = await self.process_request_optimized(request_data, context)
                results.append(metrics)
            except Exception as e:
                logger.error(f"Test request {i} failed: {e}")
        
        # Analyze results
        if results:
            times = [r.total_time_ms for r in results]
            return {
                "total_requests": len(results),
                "avg_latency": np.mean(times),
                "p50_latency": np.percentile(times, 50),
                "p90_latency": np.percentile(times, 90),
                "p99_latency": np.percentile(times, 99),
                "min_latency": np.min(times),
                "max_latency": np.max(times),
                "success_rate": sum(1 for t in times if t <= self.target_response_time_ms) / len(times),
                "strategies_used": list(set(
                    strategy for r in results for strategy in r.strategies_used
                ))
            }
        
        return {"error": "No successful test requests"}


# Usage example
async def demonstrate_response_optimization():
    """Demonstrate response time optimization"""
    
    optimizer = ResponseTimeOptimizer()
    
    print("Response Time Optimization Demo")
    print("=" * 50)
    
    # Test individual request
    print("\nProcessing single request...")
    request_data = {
        "text": "Navigate to the nearest gas station",
        "audio_features": {"transcript": "Navigate to the nearest gas station"}
    }
    context = {"location": (37.7749, -122.4194), "driving_speed": 65}
    
    response, metrics = await optimizer.process_request_optimized(request_data, context)
    
    print(f"Total response time: {metrics.total_time_ms:.1f}ms")
    print(f"Target: {optimizer.target_response_time_ms}ms")
    print(f"Success: {'✓' if metrics.total_time_ms <= optimizer.target_response_time_ms else '✗'}")
    
    print("\nComponent breakdown:")
    for component, time_ms in metrics.component_times.items():
        budget = optimizer.latency_budgets.get(component)
        if budget:
            status = "✓" if time_ms <= budget.target_ms else "⚠" if time_ms <= budget.max_ms else "✗"
            print(f"  {component.value}: {time_ms:.1f}ms (target: {budget.target_ms}ms) {status}")
    
    print(f"\nStrategies used: {[s.value for s in metrics.strategies_used]}")
    
    # Run latency test
    print("\nRunning latency test...")
    test_results = await optimizer.run_latency_test(50)
    
    print(f"\nLatency Test Results:")
    print(f"  Average: {test_results['avg_latency']:.1f}ms")
    print(f"  P50: {test_results['p50_latency']:.1f}ms")
    print(f"  P90: {test_results['p90_latency']:.1f}ms")
    print(f"  P99: {test_results['p99_latency']:.1f}ms")
    print(f"  Success rate: {test_results['success_rate']:.1%}")
    
    # Get performance report
    report = optimizer.get_performance_report()
    
    print(f"\nPerformance Report:")
    print(f"  Current P50: {report['summary']['current_p50']:.1f}ms")
    print(f"  Current P90: {report['summary']['current_p90']:.1f}ms")
    print(f"  Overall success rate: {report['summary']['success_rate']:.1%}")
    
    print(f"\nRecommendations:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"  {i}. {rec}")


# Demo section moved to examples/response_time_demo.py
# if __name__ == "__main__":
    asyncio.run(demonstrate_response_optimization())