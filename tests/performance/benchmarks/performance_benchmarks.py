"""
Performance Benchmarking Suite
==============================

Comprehensive performance benchmarking for API endpoints, database queries,
cache operations, and AI service integrations.
"""

import asyncio
import time
import statistics
import json
import psutil
import tracemalloc
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import redis.asyncio as redis
import aiohttp
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Individual benchmark result"""
    name: str
    category: str
    iterations: int
    total_time_ms: float
    avg_time_ms: float
    min_time_ms: float
    max_time_ms: float
    p50_time_ms: float
    p95_time_ms: float
    p99_time_ms: float
    std_dev_ms: float
    throughput_per_second: float
    memory_usage_mb: float
    cpu_usage_percent: float
    success_rate: float
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BenchmarkSuite:
    """Collection of benchmark results"""
    name: str
    timestamp: datetime
    environment: Dict[str, Any]
    results: List[BenchmarkResult] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "name": self.name,
            "timestamp": self.timestamp.isoformat(),
            "environment": self.environment,
            "results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "iterations": r.iterations,
                    "avg_time_ms": r.avg_time_ms,
                    "p95_time_ms": r.p95_time_ms,
                    "p99_time_ms": r.p99_time_ms,
                    "throughput_per_second": r.throughput_per_second,
                    "success_rate": r.success_rate
                }
                for r in self.results
            ]
        }


class PerformanceBenchmark:
    """Main performance benchmarking class"""
    
    def __init__(self, 
                 api_base_url: str = "http://localhost:8000",
                 database_url: str = None,
                 redis_url: str = "redis://localhost:6379"):
        self.api_base_url = api_base_url
        self.database_url = database_url or "postgresql://postgres:postgres@localhost/roadtrip"
        self.redis_url = redis_url
        self.session: Optional[aiohttp.ClientSession] = None
        self.redis_client: Optional[redis.Redis] = None
        self.db_engine = None
        self.auth_token = None
        
    async def setup(self):
        """Initialize benchmark environment"""
        logger.info("Setting up benchmark environment...")
        
        # HTTP session
        self.session = aiohttp.ClientSession()
        
        # Redis client
        try:
            self.redis_client = await redis.from_url(self.redis_url)
            await self.redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            
        # Database engine
        try:
            self.db_engine = create_engine(
                self.database_url,
                poolclass=NullPool,  # No connection pooling for benchmarks
                echo=False
            )
        except Exception as e:
            logger.warning(f"Database connection failed: {e}")
            
        # Get auth token
        await self._authenticate()
        
    async def teardown(self):
        """Cleanup benchmark environment"""
        if self.session:
            await self.session.close()
        if self.redis_client:
            await self.redis_client.close()
        if self.db_engine:
            self.db_engine.dispose()
            
    async def _authenticate(self):
        """Get authentication token for API calls"""
        try:
            async with self.session.post(
                f"{self.api_base_url}/api/auth/login",
                json={
                    "email": "benchmark@example.com",
                    "password": "BenchmarkTest123!"
                }
            ) as response:
                if response.status_code == 200:
                    data = await response.json()
                    self.auth_token = data.get("access_token")
                else:
                    # Register user
                    async with self.session.post(
                        f"{self.api_base_url}/api/auth/register",
                        json={
                            "email": "benchmark@example.com",
                            "password": "BenchmarkTest123!",
                            "full_name": "Benchmark User"
                        }
                    ) as reg_response:
                        if reg_response.status_code in [200, 201]:
                            await self._authenticate()
        except Exception as e:
            logger.warning(f"Authentication failed: {e}")
            
    async def run_benchmark(self,
                          name: str,
                          category: str,
                          func: Callable,
                          iterations: int = 100,
                          warmup_iterations: int = 10) -> BenchmarkResult:
        """Run a single benchmark"""
        logger.info(f"Running benchmark: {name} ({iterations} iterations)")
        
        # Warmup
        for _ in range(warmup_iterations):
            try:
                await func()
            except:
                pass
                
        # Start monitoring
        tracemalloc.start()
        process = psutil.Process()
        cpu_start = process.cpu_percent()
        
        # Run benchmark
        times = []
        errors = []
        successes = 0
        
        for i in range(iterations):
            try:
                start = time.perf_counter()
                await func()
                elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
                times.append(elapsed)
                successes += 1
            except Exception as e:
                errors.append(str(e))
                
        # Stop monitoring
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        cpu_end = process.cpu_percent()
        
        # Calculate statistics
        if times:
            result = BenchmarkResult(
                name=name,
                category=category,
                iterations=iterations,
                total_time_ms=sum(times),
                avg_time_ms=statistics.mean(times),
                min_time_ms=min(times),
                max_time_ms=max(times),
                p50_time_ms=np.percentile(times, 50),
                p95_time_ms=np.percentile(times, 95),
                p99_time_ms=np.percentile(times, 99),
                std_dev_ms=statistics.stdev(times) if len(times) > 1 else 0,
                throughput_per_second=1000 / statistics.mean(times),
                memory_usage_mb=peak / 1024 / 1024,
                cpu_usage_percent=(cpu_end - cpu_start) / iterations,
                success_rate=successes / iterations,
                errors=errors[:10]  # Keep first 10 errors
            )
        else:
            # All failed
            result = BenchmarkResult(
                name=name,
                category=category,
                iterations=iterations,
                total_time_ms=0,
                avg_time_ms=0,
                min_time_ms=0,
                max_time_ms=0,
                p50_time_ms=0,
                p95_time_ms=0,
                p99_time_ms=0,
                std_dev_ms=0,
                throughput_per_second=0,
                memory_usage_mb=0,
                cpu_usage_percent=0,
                success_rate=0,
                errors=errors[:10]
            )
            
        logger.info(f"Completed {name}: avg={result.avg_time_ms:.2f}ms, "
                   f"p95={result.p95_time_ms:.2f}ms, success={result.success_rate:.2%}")
        
        return result
        
    async def benchmark_api_endpoints(self) -> List[BenchmarkResult]:
        """Benchmark all major API endpoints"""
        results = []
        headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        
        # Voice Assistant
        async def voice_assistant():
            async with self.session.post(
                f"{self.api_base_url}/api/voice-assistant/interact",
                json={
                    "user_input": "Find restaurants near San Francisco",
                    "context": {"location": {"lat": 37.7749, "lng": -122.4194}}
                },
                headers=headers
            ) as response:
                await response.text()
                response.raise_for_status()
                
        result = await self.run_benchmark(
            "Voice Assistant Query",
            "API",
            voice_assistant,
            iterations=50
        )
        results.append(result)
        
        # Story Generation
        async def generate_story():
            async with self.session.post(
                f"{self.api_base_url}/api/personalized-story",
                json={
                    "origin": "San Francisco, CA",
                    "destination": "Los Angeles, CA",
                    "interests": ["history", "nature"],
                    "story_length": "medium"
                },
                headers=headers
            ) as response:
                await response.text()
                response.raise_for_status()
                
        result = await self.run_benchmark(
            "AI Story Generation",
            "API",
            generate_story,
            iterations=20  # Fewer iterations for expensive operation
        )
        results.append(result)
        
        # Directions
        async def get_directions():
            async with self.session.post(
                f"{self.api_base_url}/api/directions",
                json={
                    "origin": "San Francisco, CA",
                    "destination": "Los Angeles, CA",
                    "preferences": {"scenic_route": True}
                },
                headers=headers
            ) as response:
                await response.text()
                response.raise_for_status()
                
        result = await self.run_benchmark(
            "Get Directions",
            "API",
            get_directions,
            iterations=100
        )
        results.append(result)
        
        # POI Search
        async def search_poi():
            async with self.session.get(
                f"{self.api_base_url}/api/poi/search",
                params={
                    "lat": 37.7749,
                    "lng": -122.4194,
                    "radius": 5000,
                    "type": "restaurant"
                },
                headers=headers
            ) as response:
                await response.text()
                response.raise_for_status()
                
        result = await self.run_benchmark(
            "POI Search",
            "API",
            search_poi,
            iterations=100
        )
        results.append(result)
        
        # Hotel Search
        async def search_hotels():
            async with self.session.get(
                f"{self.api_base_url}/api/booking/hotels/search",
                params={
                    "location": "San Francisco, CA",
                    "checkin": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
                    "checkout": (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d"),
                    "guests": 2
                },
                headers=headers
            ) as response:
                await response.text()
                response.raise_for_status()
                
        result = await self.run_benchmark(
            "Hotel Search",
            "API",
            search_hotels,
            iterations=50
        )
        results.append(result)
        
        return results
        
    async def benchmark_database_queries(self) -> List[BenchmarkResult]:
        """Benchmark critical database queries"""
        if not self.db_engine:
            logger.warning("Database not available for benchmarking")
            return []
            
        results = []
        
        # User lookup by email
        async def user_lookup():
            with self.db_engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM users WHERE email = :email"),
                    {"email": "benchmark@example.com"}
                )
                result.fetchone()
                
        result = await self.run_benchmark(
            "User Lookup by Email",
            "Database",
            user_lookup,
            iterations=1000
        )
        results.append(result)
        
        # Journey history query
        async def journey_history():
            with self.db_engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT j.*, COUNT(s.id) as story_count
                        FROM journeys j
                        LEFT JOIN stories s ON j.id = s.journey_id
                        WHERE j.user_id = :user_id
                        GROUP BY j.id
                        ORDER BY j.created_at DESC
                        LIMIT 10
                    """),
                    {"user_id": 1}
                )
                result.fetchall()
                
        result = await self.run_benchmark(
            "Journey History with Stories",
            "Database",
            journey_history,
            iterations=500
        )
        results.append(result)
        
        # Popular destinations
        async def popular_destinations():
            with self.db_engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT destination, COUNT(*) as visit_count
                        FROM journeys
                        WHERE created_at > :date_limit
                        GROUP BY destination
                        ORDER BY visit_count DESC
                        LIMIT 20
                    """),
                    {"date_limit": datetime.now() - timedelta(days=30)}
                )
                result.fetchall()
                
        result = await self.run_benchmark(
            "Popular Destinations (30 days)",
            "Database",
            popular_destinations,
            iterations=200
        )
        results.append(result)
        
        # Complex analytics query
        async def revenue_analytics():
            with self.db_engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT 
                            DATE_TRUNC('day', b.created_at) as booking_date,
                            COUNT(DISTINCT b.id) as bookings,
                            SUM(b.total_amount) as revenue,
                            AVG(b.commission_amount) as avg_commission
                        FROM bookings b
                        JOIN users u ON b.user_id = u.id
                        WHERE b.created_at > :start_date
                        GROUP BY booking_date
                        ORDER BY booking_date DESC
                    """),
                    {"start_date": datetime.now() - timedelta(days=90)}
                )
                result.fetchall()
                
        result = await self.run_benchmark(
            "Revenue Analytics (90 days)",
            "Database",
            revenue_analytics,
            iterations=100
        )
        results.append(result)
        
        return results
        
    async def benchmark_cache_operations(self) -> List[BenchmarkResult]:
        """Benchmark Redis cache operations"""
        if not self.redis_client:
            logger.warning("Redis not available for benchmarking")
            return []
            
        results = []
        
        # Simple key-value set/get
        async def cache_set_get():
            key = f"benchmark:{time.time()}"
            value = json.dumps({"data": "test" * 100})
            await self.redis_client.set(key, value, ex=60)
            await self.redis_client.get(key)
            await self.redis_client.delete(key)
            
        result = await self.run_benchmark(
            "Cache Set/Get/Delete",
            "Cache",
            cache_set_get,
            iterations=1000
        )
        results.append(result)
        
        # Cached AI response
        test_ai_response = json.dumps({
            "response": "This is a sample AI response " * 50,
            "metadata": {
                "model": "gemini-1.5-pro",
                "tokens": 500,
                "processing_time": 1.5
            }
        })
        
        async def cache_ai_response():
            key = f"ai_response:{time.time()}"
            await self.redis_client.set(key, test_ai_response, ex=300)
            cached = await self.redis_client.get(key)
            if cached:
                json.loads(cached)
            await self.redis_client.delete(key)
            
        result = await self.run_benchmark(
            "AI Response Cache",
            "Cache",
            cache_ai_response,
            iterations=500
        )
        results.append(result)
        
        # Cache invalidation pattern
        async def cache_invalidation():
            pattern = f"journey:user:1:*"
            keys = []
            async for key in self.redis_client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await self.redis_client.delete(*keys)
                
        result = await self.run_benchmark(
            "Cache Pattern Invalidation",
            "Cache",
            cache_invalidation,
            iterations=200
        )
        results.append(result)
        
        # Distributed lock
        async def distributed_lock():
            lock_key = "benchmark:lock"
            lock_value = str(time.time())
            
            # Try to acquire lock
            acquired = await self.redis_client.set(
                lock_key, lock_value, nx=True, ex=5
            )
            
            if acquired:
                # Simulate work
                await asyncio.sleep(0.01)
                # Release lock
                await self.redis_client.delete(lock_key)
                
        result = await self.run_benchmark(
            "Distributed Lock Operations",
            "Cache",
            distributed_lock,
            iterations=500
        )
        results.append(result)
        
        return results
        
    async def benchmark_ai_operations(self) -> List[BenchmarkResult]:
        """Benchmark AI service operations"""
        results = []
        headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        
        # Text generation (short)
        async def ai_text_short():
            async with self.session.post(
                f"{self.api_base_url}/api/ai/generate",
                json={
                    "prompt": "Tell me a short fact about California",
                    "max_tokens": 100
                },
                headers=headers
            ) as response:
                await response.text()
                response.raise_for_status()
                
        result = await self.run_benchmark(
            "AI Text Generation (Short)",
            "AI",
            ai_text_short,
            iterations=30
        )
        results.append(result)
        
        # Text generation (long)
        async def ai_text_long():
            async with self.session.post(
                f"{self.api_base_url}/api/ai/generate",
                json={
                    "prompt": "Write a detailed story about a road trip through California",
                    "max_tokens": 1000
                },
                headers=headers
            ) as response:
                await response.text()
                response.raise_for_status()
                
        result = await self.run_benchmark(
            "AI Text Generation (Long)",
            "AI",
            ai_text_long,
            iterations=10
        )
        results.append(result)
        
        # Voice synthesis
        async def voice_synthesis():
            async with self.session.post(
                f"{self.api_base_url}/api/tts/synthesize",
                json={
                    "text": "Welcome to your road trip adventure!",
                    "voice": "en-US-Wavenet-D",
                    "speed": 1.0
                },
                headers=headers
            ) as response:
                await response.read()  # Binary audio data
                response.raise_for_status()
                
        result = await self.run_benchmark(
            "Voice Synthesis (TTS)",
            "AI",
            voice_synthesis,
            iterations=50
        )
        results.append(result)
        
        return results
        
    async def benchmark_concurrent_operations(self) -> List[BenchmarkResult]:
        """Benchmark concurrent operation handling"""
        results = []
        headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        
        # Concurrent API calls
        async def concurrent_api_calls():
            tasks = []
            for _ in range(10):
                task = self.session.get(
                    f"{self.api_base_url}/api/health",
                    headers=headers
                )
                tasks.append(task)
                
            responses = await asyncio.gather(*tasks)
            for response in responses:
                response.close()
                
        result = await self.run_benchmark(
            "10 Concurrent API Calls",
            "Concurrency",
            concurrent_api_calls,
            iterations=50
        )
        results.append(result)
        
        # Mixed concurrent operations
        async def mixed_concurrent():
            tasks = []
            
            # API call
            tasks.append(self.session.get(
                f"{self.api_base_url}/api/health",
                headers=headers
            ))
            
            # Cache operation
            if self.redis_client:
                tasks.append(self.redis_client.get("test_key"))
                
            # Database query
            if self.db_engine:
                tasks.append(asyncio.to_thread(
                    lambda: self.db_engine.connect().execute(
                        text("SELECT 1")
                    ).scalar()
                ))
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Cleanup
            if hasattr(results[0], 'close'):
                results[0].close()
                
        result = await self.run_benchmark(
            "Mixed Concurrent Operations",
            "Concurrency",
            mixed_concurrent,
            iterations=100
        )
        results.append(result)
        
        return results
        
    async def run_all_benchmarks(self) -> BenchmarkSuite:
        """Run all benchmark suites"""
        logger.info("Starting comprehensive performance benchmarks...")
        
        # Collect environment info
        environment = {
            "timestamp": datetime.now().isoformat(),
            "python_version": psutil.Process().name(),
            "cpu_count": psutil.cpu_count(),
            "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            "platform": {
                "system": psutil.Process().name(),
                "processor": psutil.cpu_freq().current if hasattr(psutil.cpu_freq(), 'current') else "unknown"
            }
        }
        
        suite = BenchmarkSuite(
            name="AI Road Trip Storyteller Performance Benchmarks",
            timestamp=datetime.now(),
            environment=environment
        )
        
        # Run all benchmark categories
        benchmark_categories = [
            ("API Endpoints", self.benchmark_api_endpoints()),
            ("Database Queries", self.benchmark_database_queries()),
            ("Cache Operations", self.benchmark_cache_operations()),
            ("AI Operations", self.benchmark_ai_operations()),
            ("Concurrent Operations", self.benchmark_concurrent_operations())
        ]
        
        for category_name, benchmark_coro in benchmark_categories:
            logger.info(f"Running {category_name} benchmarks...")
            try:
                results = await benchmark_coro
                suite.results.extend(results)
            except Exception as e:
                logger.error(f"Failed to run {category_name} benchmarks: {e}")
                
        return suite
        
    def generate_report(self, suite: BenchmarkSuite, output_dir: str = "tests/performance/reports"):
        """Generate benchmark report with visualizations"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_dir = output_path / f"benchmark_{timestamp}"
        report_dir.mkdir(exist_ok=True)
        
        # Save raw data
        with open(report_dir / "benchmark_results.json", "w") as f:
            json.dump(suite.to_dict(), f, indent=2)
            
        # Generate visualizations
        self._generate_benchmark_charts(suite, report_dir)
        
        # Generate comparison with baselines
        self._compare_with_baselines(suite, report_dir)
        
        # Generate HTML report
        self._generate_benchmark_html(suite, report_dir)
        
        logger.info(f"Benchmark report generated at: {report_dir}")
        
    def _generate_benchmark_charts(self, suite: BenchmarkSuite, output_dir: Path):
        """Generate benchmark visualization charts"""
        if not suite.results:
            return
            
        # Group results by category
        categories = {}
        for result in suite.results:
            if result.category not in categories:
                categories[result.category] = []
            categories[result.category].append(result)
            
        # Response time comparison chart
        plt.figure(figsize=(15, 8))
        
        all_names = []
        all_avg_times = []
        all_p95_times = []
        all_p99_times = []
        
        for category, results in categories.items():
            for r in results:
                all_names.append(f"{r.name[:20]}...")
                all_avg_times.append(r.avg_time_ms)
                all_p95_times.append(r.p95_time_ms)
                all_p99_times.append(r.p99_time_ms)
                
        x = np.arange(len(all_names))
        width = 0.25
        
        plt.bar(x - width, all_avg_times, width, label='Average', alpha=0.8)
        plt.bar(x, all_p95_times, width, label='95th percentile', alpha=0.8)
        plt.bar(x + width, all_p99_times, width, label='99th percentile', alpha=0.8)
        
        plt.xlabel('Operation')
        plt.ylabel('Response Time (ms)')
        plt.title('Response Time Comparison')
        plt.xticks(x, all_names, rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / 'response_times_comparison.png', dpi=150)
        plt.close()
        
        # Throughput chart
        plt.figure(figsize=(12, 6))
        
        throughputs = [r.throughput_per_second for r in suite.results]
        names = [f"{r.name[:30]}..." for r in suite.results]
        
        plt.barh(names, throughputs)
        plt.xlabel('Operations per Second')
        plt.title('Throughput Comparison')
        plt.tight_layout()
        plt.savefig(output_dir / 'throughput_comparison.png', dpi=150)
        plt.close()
        
        # Category performance radar chart
        categories_avg = {}
        for category, results in categories.items():
            avg_time = statistics.mean(r.avg_time_ms for r in results)
            categories_avg[category] = avg_time
            
        if len(categories_avg) >= 3:
            labels = list(categories_avg.keys())
            values = list(categories_avg.values())
            
            angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False)
            values = np.concatenate((values, [values[0]]))
            angles = np.concatenate((angles, [angles[0]]))
            
            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
            ax.plot(angles, values, 'o-', linewidth=2)
            ax.fill(angles, values, alpha=0.25)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(labels)
            ax.set_ylabel('Average Response Time (ms)')
            ax.set_title('Performance by Category')
            plt.savefig(output_dir / 'category_performance_radar.png', dpi=150)
            plt.close()
            
    def _compare_with_baselines(self, suite: BenchmarkSuite, output_dir: Path):
        """Compare results with baseline performance targets"""
        baselines = {
            "Voice Assistant Query": {"target_ms": 200, "acceptable_ms": 500},
            "AI Story Generation": {"target_ms": 2000, "acceptable_ms": 5000},
            "Get Directions": {"target_ms": 150, "acceptable_ms": 300},
            "POI Search": {"target_ms": 100, "acceptable_ms": 200},
            "Hotel Search": {"target_ms": 300, "acceptable_ms": 600},
            "User Lookup by Email": {"target_ms": 5, "acceptable_ms": 10},
            "Cache Set/Get/Delete": {"target_ms": 2, "acceptable_ms": 5}
        }
        
        comparison_data = []
        for result in suite.results:
            if result.name in baselines:
                baseline = baselines[result.name]
                status = "EXCELLENT" if result.avg_time_ms < baseline["target_ms"] else \
                        "ACCEPTABLE" if result.avg_time_ms < baseline["acceptable_ms"] else \
                        "NEEDS IMPROVEMENT"
                
                comparison_data.append({
                    "operation": result.name,
                    "actual_ms": result.avg_time_ms,
                    "target_ms": baseline["target_ms"],
                    "acceptable_ms": baseline["acceptable_ms"],
                    "status": status
                })
                
        # Save comparison
        with open(output_dir / "baseline_comparison.json", "w") as f:
            json.dump(comparison_data, f, indent=2)
            
        # Create comparison chart
        if comparison_data:
            df = pd.DataFrame(comparison_data)
            
            fig, ax = plt.subplots(figsize=(12, 8))
            x = np.arange(len(df))
            width = 0.25
            
            ax.bar(x - width, df['actual_ms'], width, label='Actual', 
                  color=['green' if s == 'EXCELLENT' else 'orange' if s == 'ACCEPTABLE' else 'red' 
                         for s in df['status']])
            ax.bar(x, df['target_ms'], width, label='Target', alpha=0.5, color='blue')
            ax.bar(x + width, df['acceptable_ms'], width, label='Acceptable', alpha=0.5, color='gray')
            
            ax.set_xlabel('Operation')
            ax.set_ylabel('Response Time (ms)')
            ax.set_title('Performance vs Baselines')
            ax.set_xticks(x)
            ax.set_xticklabels(df['operation'], rotation=45, ha='right')
            ax.legend()
            
            plt.tight_layout()
            plt.savefig(output_dir / 'baseline_comparison.png', dpi=150)
            plt.close()
            
    def _generate_benchmark_html(self, suite: BenchmarkSuite, output_dir: Path):
        """Generate HTML benchmark report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Benchmark Report - {suite.timestamp.strftime('%Y-%m-%d %H:%M')}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                       margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; 
                            padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #2c3e50; margin-bottom: 10px; }}
                h2 {{ color: #34495e; margin-top: 30px; }}
                .summary {{ background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0; }}
                .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
                .metric-label {{ font-size: 14px; color: #7f8c8d; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th {{ background: #3498db; color: white; padding: 12px; text-align: left; }}
                td {{ padding: 10px; border-bottom: 1px solid #ecf0f1; }}
                tr:hover {{ background: #f8f9fa; }}
                .status-excellent {{ color: #27ae60; font-weight: bold; }}
                .status-acceptable {{ color: #f39c12; font-weight: bold; }}
                .status-poor {{ color: #e74c3c; font-weight: bold; }}
                img {{ max-width: 100%; margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }}
                .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
                @media (max-width: 768px) {{ .chart-grid {{ grid-template-columns: 1fr; }} }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Performance Benchmark Report</h1>
                <p>Generated: {suite.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <div class="summary">
                    <h2>Summary</h2>
                    {self._generate_summary_metrics(suite)}
                </div>
                
                <h2>Performance Charts</h2>
                <div class="chart-grid">
                    <div>
                        <img src="response_times_comparison.png" alt="Response Times">
                    </div>
                    <div>
                        <img src="throughput_comparison.png" alt="Throughput">
                    </div>
                </div>
                
                <img src="baseline_comparison.png" alt="Baseline Comparison">
                
                <h2>Detailed Results</h2>
                <table>
                    <tr>
                        <th>Operation</th>
                        <th>Category</th>
                        <th>Avg (ms)</th>
                        <th>P95 (ms)</th>
                        <th>P99 (ms)</th>
                        <th>Throughput (ops/s)</th>
                        <th>Success Rate</th>
                        <th>Status</th>
                    </tr>
                    {self._generate_result_rows(suite)}
                </table>
                
                <h2>Environment</h2>
                <pre>{json.dumps(suite.environment, indent=2)}</pre>
                
                <h2>Recommendations</h2>
                {self._generate_recommendations_html(suite)}
            </div>
        </body>
        </html>
        """
        
        with open(output_dir / 'benchmark_report.html', 'w') as f:
            f.write(html_content)
            
    def _generate_summary_metrics(self, suite: BenchmarkSuite) -> str:
        """Generate summary metrics HTML"""
        total_operations = sum(r.iterations for r in suite.results)
        avg_success_rate = statistics.mean(r.success_rate for r in suite.results)
        
        fastest_op = min(suite.results, key=lambda r: r.avg_time_ms)
        slowest_op = max(suite.results, key=lambda r: r.avg_time_ms)
        
        return f"""
        <div class="metric">
            <div class="metric-label">Total Operations</div>
            <div class="metric-value">{total_operations:,}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Average Success Rate</div>
            <div class="metric-value">{avg_success_rate:.1%}</div>
        </div>
        <div class="metric">
            <div class="metric-label">Fastest Operation</div>
            <div class="metric-value">{fastest_op.name} ({fastest_op.avg_time_ms:.1f}ms)</div>
        </div>
        <div class="metric">
            <div class="metric-label">Slowest Operation</div>
            <div class="metric-value">{slowest_op.name} ({slowest_op.avg_time_ms:.1f}ms)</div>
        </div>
        """
        
    def _generate_result_rows(self, suite: BenchmarkSuite) -> str:
        """Generate result table rows"""
        rows = []
        for r in sorted(suite.results, key=lambda x: x.category):
            status = self._get_performance_status(r)
            status_class = f"status-{status.lower()}"
            
            rows.append(f"""
            <tr>
                <td>{r.name}</td>
                <td>{r.category}</td>
                <td>{r.avg_time_ms:.2f}</td>
                <td>{r.p95_time_ms:.2f}</td>
                <td>{r.p99_time_ms:.2f}</td>
                <td>{r.throughput_per_second:.2f}</td>
                <td>{r.success_rate:.1%}</td>
                <td class="{status_class}">{status}</td>
            </tr>
            """)
            
        return '\n'.join(rows)
        
    def _get_performance_status(self, result: BenchmarkResult) -> str:
        """Determine performance status"""
        # Category-specific thresholds
        thresholds = {
            "API": {"excellent": 200, "acceptable": 500},
            "Database": {"excellent": 10, "acceptable": 50},
            "Cache": {"excellent": 5, "acceptable": 10},
            "AI": {"excellent": 1000, "acceptable": 3000},
            "Concurrency": {"excellent": 100, "acceptable": 300}
        }
        
        category_threshold = thresholds.get(result.category, {"excellent": 100, "acceptable": 500})
        
        if result.avg_time_ms < category_threshold["excellent"] and result.success_rate > 0.99:
            return "EXCELLENT"
        elif result.avg_time_ms < category_threshold["acceptable"] and result.success_rate > 0.95:
            return "ACCEPTABLE"
        else:
            return "POOR"
            
    def _generate_recommendations_html(self, suite: BenchmarkSuite) -> str:
        """Generate performance recommendations"""
        recommendations = []
        
        # Analyze results
        slow_operations = [r for r in suite.results if self._get_performance_status(r) == "POOR"]
        failed_operations = [r for r in suite.results if r.success_rate < 0.95]
        
        if slow_operations:
            recommendations.append(
                f"<li><strong>Slow Operations:</strong> {len(slow_operations)} operations need performance optimization. "
                f"Focus on: {', '.join(op.name for op in slow_operations[:3])}</li>"
            )
            
        if failed_operations:
            recommendations.append(
                f"<li><strong>Reliability Issues:</strong> {len(failed_operations)} operations have high failure rates. "
                f"Investigate: {', '.join(op.name for op in failed_operations[:3])}</li>"
            )
            
        # Category-specific recommendations
        categories = {}
        for r in suite.results:
            if r.category not in categories:
                categories[r.category] = []
            categories[r.category].append(r)
            
        for category, results in categories.items():
            avg_time = statistics.mean(r.avg_time_ms for r in results)
            if category == "API" and avg_time > 300:
                recommendations.append(
                    f"<li><strong>API Performance:</strong> Average response time of {avg_time:.0f}ms is high. "
                    "Consider implementing response caching, query optimization, or horizontal scaling.</li>"
                )
            elif category == "Database" and avg_time > 20:
                recommendations.append(
                    f"<li><strong>Database Performance:</strong> Query performance averaging {avg_time:.0f}ms. "
                    "Review query plans, add appropriate indexes, and consider connection pooling optimization.</li>"
                )
            elif category == "AI" and avg_time > 2000:
                recommendations.append(
                    f"<li><strong>AI Service Performance:</strong> AI operations averaging {avg_time:.0f}ms. "
                    "Implement aggressive caching, consider model optimization, or use lighter models for simple queries.</li>"
                )
                
        if not recommendations:
            recommendations.append("<li>All operations are performing within acceptable parameters. Good job!</li>")
            
        return "<ul>" + "\n".join(recommendations) + "</ul>"


async def main():
    """Run comprehensive performance benchmarks"""
    benchmark = PerformanceBenchmark()
    
    try:
        await benchmark.setup()
        
        # Run all benchmarks
        suite = await benchmark.run_all_benchmarks()
        
        # Generate report
        benchmark.generate_report(suite)
        
        # Print summary
        print("\n" + "="*60)
        print("BENCHMARK SUMMARY")
        print("="*60)
        
        for result in suite.results:
            status = benchmark._get_performance_status(result)
            print(f"{result.name:40} | {result.avg_time_ms:8.2f}ms | {status}")
            
    finally:
        await benchmark.teardown()


if __name__ == "__main__":
    asyncio.run(main())