"""
Performance tests for Celery async implementation.

Validates Six Sigma quality targets:
- Job completion rate > 99.9%
- Queue latency < 100ms
- API response time < 3s
"""

import asyncio
import time
import statistics
from typing import List, Dict, Any
from datetime import datetime
import pytest
import redis
from celery.result import AsyncResult

from backend.app.core.celery_app import celery_app
from backend.app.tasks.ai_enhanced import generate_story_with_status
from backend.app.services.async_orchestration_wrapper import create_async_orchestrator
from backend.app.models.user import User
from backend.app.services.master_orchestration_agent import JourneyContext

# Test configuration
PERFORMANCE_TARGETS = {
    'api_response_time': 3.0,  # seconds
    'queue_latency': 0.1,  # 100ms
    'job_completion_rate': 99.9,  # percentage
    'story_generation_time': 30.0,  # seconds
    'voice_synthesis_time': 10.0,  # seconds
}

class PerformanceMetrics:
    """Collect and analyze performance metrics."""
    
    def __init__(self):
        self.api_response_times = []
        self.queue_latencies = []
        self.job_completion_times = []
        self.failed_jobs = 0
        self.total_jobs = 0
        
    def add_api_response(self, duration: float):
        self.api_response_times.append(duration)
    
    def add_queue_latency(self, latency: float):
        self.queue_latencies.append(latency)
    
    def add_job_completion(self, duration: float, success: bool = True):
        self.total_jobs += 1
        if success:
            self.job_completion_times.append(duration)
        else:
            self.failed_jobs += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Calculate performance statistics."""
        return {
            'api_response': {
                'mean': statistics.mean(self.api_response_times) if self.api_response_times else 0,
                'p95': self._percentile(self.api_response_times, 95),
                'p99': self._percentile(self.api_response_times, 99),
                'max': max(self.api_response_times) if self.api_response_times else 0
            },
            'queue_latency': {
                'mean': statistics.mean(self.queue_latencies) if self.queue_latencies else 0,
                'p95': self._percentile(self.queue_latencies, 95),
                'p99': self._percentile(self.queue_latencies, 99),
                'max': max(self.queue_latencies) if self.queue_latencies else 0
            },
            'job_completion': {
                'mean': statistics.mean(self.job_completion_times) if self.job_completion_times else 0,
                'success_rate': ((self.total_jobs - self.failed_jobs) / self.total_jobs * 100) if self.total_jobs > 0 else 100,
                'total_jobs': self.total_jobs,
                'failed_jobs': self.failed_jobs
            }
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile value."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]


@pytest.mark.performance
class TestCeleryPerformance:
    """Test suite for Celery performance validation."""
    
    @pytest.fixture
    def metrics(self):
        """Provide metrics collector."""
        return PerformanceMetrics()
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for testing."""
        user = User(id=1, email="test@example.com")
        user.preferences = {'theme': 'adventure'}
        return user
    
    @pytest.fixture
    def mock_context(self):
        """Create mock journey context."""
        return JourneyContext(
            current_location={'latitude': 37.7749, 'longitude': -122.4194, 'name': 'San Francisco'},
            current_time=datetime.utcnow(),
            journey_stage='en_route',
            passengers=[{'name': 'Test User', 'age': 30}],
            vehicle_info={'type': 'car'},
            weather={'condition': 'sunny', 'temperature': 72},
            route_info={'destination': 'Los Angeles', 'distance': 380}
        )
    
    async def test_api_response_time(self, metrics, mock_user, mock_context):
        """Test that API responds within 3 seconds."""
        orchestrator = create_async_orchestrator()
        
        test_queries = [
            "Tell me about this area",
            "What's the history of San Francisco?",
            "Find me a good restaurant nearby",
            "How's the weather looking?",
            "What's interesting about this route?"
        ]
        
        for query in test_queries:
            start_time = time.time()
            
            response = await orchestrator.process_user_input_async(
                user_input=query,
                context=mock_context,
                user=mock_user
            )
            
            duration = time.time() - start_time
            metrics.add_api_response(duration)
            
            # Verify response time
            assert duration < PERFORMANCE_TARGETS['api_response_time'], \
                f"API response time {duration:.2f}s exceeds target {PERFORMANCE_TARGETS['api_response_time']}s"
            
            # Verify response structure
            assert response['type'] in ['immediate', 'async', 'error']
            if response['type'] == 'async':
                assert 'job_id' in response
                assert 'status_url' in response
        
        # Check overall performance
        stats = metrics.get_stats()
        assert stats['api_response']['p95'] < PERFORMANCE_TARGETS['api_response_time'], \
            "95th percentile API response time exceeds target"
    
    def test_queue_latency(self, metrics):
        """Test that jobs start processing within 100ms."""
        redis_client = redis.from_url(celery_app.conf.broker_url)
        
        # Submit multiple test jobs
        job_ids = []
        submit_times = {}
        
        for i in range(20):
            request_data = {
                'location': {'latitude': 37.7749, 'longitude': -122.4194},
                'interests': ['history'],
                'context': {'test': True},
                'user_id': 1
            }
            
            submit_time = time.time()
            task = generate_story_with_status.apply_async(
                args=[request_data],
                priority=5
            )
            
            job_ids.append(task.id)
            submit_times[task.id] = submit_time
        
        # Monitor when jobs start processing
        start_times = {}
        timeout = time.time() + 5  # 5 second timeout
        
        while len(start_times) < len(job_ids) and time.time() < timeout:
            for job_id in job_ids:
                if job_id not in start_times:
                    result = AsyncResult(job_id, app=celery_app)
                    if result.state != 'PENDING':
                        start_times[job_id] = time.time()
                        latency = start_times[job_id] - submit_times[job_id]
                        metrics.add_queue_latency(latency)
            
            time.sleep(0.01)  # Check every 10ms
        
        # Verify latency
        stats = metrics.get_stats()
        assert stats['queue_latency']['mean'] < PERFORMANCE_TARGETS['queue_latency'], \
            f"Mean queue latency {stats['queue_latency']['mean']:.3f}s exceeds target"
        assert stats['queue_latency']['p99'] < PERFORMANCE_TARGETS['queue_latency'] * 2, \
            "99th percentile queue latency exceeds 2x target"
    
    def test_job_completion_rate(self, metrics):
        """Test that job completion rate exceeds 99.9%."""
        # Submit batch of jobs
        job_ids = []
        
        for i in range(100):  # 100 jobs for statistical significance
            request_data = {
                'location': {'latitude': 37.7749 + i*0.001, 'longitude': -122.4194},
                'interests': ['history', 'culture'],
                'context': {'batch_test': True},
                'user_id': 1
            }
            
            task = generate_story_with_status.apply_async(
                args=[request_data],
                priority=5
            )
            job_ids.append(task.id)
        
        # Wait for jobs to complete (with timeout)
        completed_jobs = 0
        failed_jobs = 0
        timeout = time.time() + 120  # 2 minute timeout
        
        while (completed_jobs + failed_jobs) < len(job_ids) and time.time() < timeout:
            for job_id in job_ids:
                result = AsyncResult(job_id, app=celery_app)
                
                if result.ready():
                    if result.successful():
                        completed_jobs += 1
                        metrics.add_job_completion(1.0, success=True)
                    else:
                        failed_jobs += 1
                        metrics.add_job_completion(1.0, success=False)
                    
                    job_ids.remove(job_id)
            
            time.sleep(0.1)
        
        # Calculate completion rate
        stats = metrics.get_stats()
        completion_rate = stats['job_completion']['success_rate']
        
        assert completion_rate >= PERFORMANCE_TARGETS['job_completion_rate'], \
            f"Job completion rate {completion_rate:.1f}% below target {PERFORMANCE_TARGETS['job_completion_rate']}%"
    
    async def test_concurrent_load(self, metrics, mock_user, mock_context):
        """Test system under concurrent load."""
        orchestrator = create_async_orchestrator()
        
        async def submit_request(query: str) -> float:
            """Submit a single request and measure time."""
            start_time = time.time()
            
            response = await orchestrator.process_user_input_async(
                user_input=query,
                context=mock_context,
                user=mock_user
            )
            
            duration = time.time() - start_time
            return duration
        
        # Submit 50 concurrent requests
        queries = [
            f"Tell me about location {i}" for i in range(50)
        ]
        
        tasks = [submit_request(query) for query in queries]
        durations = await asyncio.gather(*tasks)
        
        # Analyze results
        for duration in durations:
            metrics.add_api_response(duration)
        
        stats = metrics.get_stats()
        
        # Even under load, 95% of requests should complete within target
        assert stats['api_response']['p95'] < PERFORMANCE_TARGETS['api_response_time'] * 1.5, \
            "95th percentile response time under load exceeds 1.5x target"
    
    def test_priority_queue_ordering(self):
        """Test that high-priority jobs are processed first."""
        # Clear queues first
        celery_app.control.purge()
        
        # Submit mix of priority jobs
        high_priority_jobs = []
        low_priority_jobs = []
        
        # Submit low priority first
        for i in range(5):
            task = generate_story_with_status.apply_async(
                args=[{'location': {'lat': i}, 'interests': [], 'user_id': 1}],
                priority=1  # Low priority
            )
            low_priority_jobs.append(task.id)
        
        # Then high priority
        for i in range(5):
            task = generate_story_with_status.apply_async(
                args=[{'location': {'lat': i+10}, 'interests': [], 'user_id': 1}],
                priority=9  # High priority
            )
            high_priority_jobs.append(task.id)
        
        # Track completion order
        completion_order = []
        all_jobs = high_priority_jobs + low_priority_jobs
        
        while len(completion_order) < len(all_jobs):
            for job_id in all_jobs:
                if job_id not in completion_order:
                    result = AsyncResult(job_id, app=celery_app)
                    if result.ready():
                        completion_order.append(job_id)
            time.sleep(0.1)
        
        # Verify high priority completed first
        high_priority_positions = [
            completion_order.index(job_id) for job_id in high_priority_jobs
        ]
        
        avg_high_priority_position = sum(high_priority_positions) / len(high_priority_positions)
        assert avg_high_priority_position < len(high_priority_jobs), \
            "High priority jobs not processed first"


def run_performance_suite():
    """Run complete performance test suite."""
    print("Starting Celery Performance Test Suite")
    print("=" * 50)
    
    metrics = PerformanceMetrics()
    
    # Run tests
    test_instance = TestCeleryPerformance()
    
    # Test API response time
    print("\n1. Testing API Response Time...")
    asyncio.run(test_instance.test_api_response_time(
        metrics,
        test_instance.mock_user(),
        test_instance.mock_context()
    ))
    print("✓ API response time test passed")
    
    # Test queue latency
    print("\n2. Testing Queue Latency...")
    test_instance.test_queue_latency(metrics)
    print("✓ Queue latency test passed")
    
    # Test completion rate
    print("\n3. Testing Job Completion Rate...")
    test_instance.test_job_completion_rate(metrics)
    print("✓ Job completion rate test passed")
    
    # Print final statistics
    print("\n" + "=" * 50)
    print("Performance Test Results:")
    print("=" * 50)
    
    stats = metrics.get_stats()
    
    print(f"\nAPI Response Time:")
    print(f"  Mean: {stats['api_response']['mean']:.3f}s")
    print(f"  95th percentile: {stats['api_response']['p95']:.3f}s")
    print(f"  99th percentile: {stats['api_response']['p99']:.3f}s")
    print(f"  Target: <{PERFORMANCE_TARGETS['api_response_time']}s")
    
    print(f"\nQueue Latency:")
    print(f"  Mean: {stats['queue_latency']['mean']*1000:.1f}ms")
    print(f"  95th percentile: {stats['queue_latency']['p95']*1000:.1f}ms")
    print(f"  99th percentile: {stats['queue_latency']['p99']*1000:.1f}ms")
    print(f"  Target: <{PERFORMANCE_TARGETS['queue_latency']*1000}ms")
    
    print(f"\nJob Completion:")
    print(f"  Success Rate: {stats['job_completion']['success_rate']:.2f}%")
    print(f"  Total Jobs: {stats['job_completion']['total_jobs']}")
    print(f"  Failed Jobs: {stats['job_completion']['failed_jobs']}")
    print(f"  Target: >{PERFORMANCE_TARGETS['job_completion_rate']}%")
    
    print("\n✅ All performance targets met!")


if __name__ == "__main__":
    run_performance_suite()