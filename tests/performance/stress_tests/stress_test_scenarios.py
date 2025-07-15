"""
Advanced Stress Testing Scenarios
=================================

This module implements stress testing scenarios to identify system breaking points,
cascade failures, and recovery capabilities.
"""

import asyncio
import aiohttp
import random
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class StressTestResult:
    """Results from a stress test scenario"""
    scenario_name: str
    start_time: datetime
    end_time: datetime
    max_concurrent_users: int
    breaking_point_users: Optional[int]
    breaking_point_rps: Optional[float]
    error_threshold_reached: bool
    response_time_degradation: Dict[int, float]  # users -> avg response time
    error_rates: Dict[int, float]  # users -> error rate
    recovery_time_seconds: Optional[float]
    cascade_failures: List[str]
    system_metrics: Dict[str, Any]


class StressTestScenarios:
    """Advanced stress testing scenarios"""
    
    def __init__(self, base_url: str = "http://localhost:8000", 
                 auth_token: Optional[str] = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        self.session: Optional[aiohttp.ClientSession] = None
        self.metrics = {
            "requests_sent": 0,
            "requests_succeeded": 0,
            "requests_failed": 0,
            "response_times": [],
            "errors": []
        }
        
    async def setup(self):
        """Initialize test session"""
        self.session = aiohttp.ClientSession()
        
    async def teardown(self):
        """Cleanup test session"""
        if self.session:
            await self.session.close()
            
    async def run_breaking_point_test(self) -> StressTestResult:
        """Find the system's breaking point by gradually increasing load"""
        logger.info("Starting breaking point test...")
        
        start_time = datetime.now()
        result = StressTestResult(
            scenario_name="Breaking Point Test",
            start_time=start_time,
            end_time=datetime.now(),
            max_concurrent_users=0,
            breaking_point_users=None,
            breaking_point_rps=None,
            error_threshold_reached=False,
            response_time_degradation={},
            error_rates={},
            recovery_time_seconds=None,
            cascade_failures=[],
            system_metrics={}
        )
        
        # Start with baseline
        users = 50
        increment = 50
        error_threshold = 0.05  # 5% error rate
        response_time_threshold = 2000  # 2 seconds
        
        while users <= 5000:  # Safety limit
            logger.info(f"Testing with {users} concurrent users...")
            
            # Reset metrics for this round
            self.metrics = {
                "requests_sent": 0,
                "requests_succeeded": 0,
                "requests_failed": 0,
                "response_times": [],
                "errors": []
            }
            
            # Run load test for this user count
            await self._run_concurrent_load(users, duration_seconds=60)
            
            # Calculate metrics
            error_rate = (self.metrics["requests_failed"] / 
                         self.metrics["requests_sent"]) if self.metrics["requests_sent"] > 0 else 0
            avg_response_time = (np.mean(self.metrics["response_times"]) 
                               if self.metrics["response_times"] else 0)
            
            result.response_time_degradation[users] = avg_response_time
            result.error_rates[users] = error_rate
            result.max_concurrent_users = users
            
            # Check if we've hit the breaking point
            if error_rate > error_threshold or avg_response_time > response_time_threshold:
                result.breaking_point_users = users
                result.breaking_point_rps = (self.metrics["requests_sent"] / 60)  # RPS
                result.error_threshold_reached = True
                logger.warning(f"Breaking point reached at {users} users!")
                break
                
            # Increase load
            users += increment
            if users > 500:
                increment = 100  # Larger increments at higher loads
                
            # Cool down between rounds
            await asyncio.sleep(30)
            
        result.end_time = datetime.now()
        return result
        
    async def run_spike_test(self) -> StressTestResult:
        """Test system response to sudden traffic spikes"""
        logger.info("Starting spike test...")
        
        start_time = datetime.now()
        result = StressTestResult(
            scenario_name="Spike Test",
            start_time=start_time,
            end_time=datetime.now(),
            max_concurrent_users=0,
            breaking_point_users=None,
            breaking_point_rps=None,
            error_threshold_reached=False,
            response_time_degradation={},
            error_rates={},
            recovery_time_seconds=None,
            cascade_failures=[],
            system_metrics={}
        )
        
        # Normal load
        normal_users = 100
        spike_users = 2000
        
        # Phase 1: Normal load
        logger.info(f"Phase 1: Normal load ({normal_users} users)")
        await self._run_concurrent_load(normal_users, duration_seconds=60)
        
        normal_metrics = self.metrics.copy()
        
        # Phase 2: Sudden spike
        logger.info(f"Phase 2: Traffic spike ({spike_users} users)")
        spike_start = time.time()
        await self._run_concurrent_load(spike_users, duration_seconds=120)
        
        spike_metrics = self.metrics.copy()
        
        # Phase 3: Return to normal
        logger.info(f"Phase 3: Return to normal ({normal_users} users)")
        recovery_start = time.time()
        await self._run_concurrent_load(normal_users, duration_seconds=60)
        
        # Measure recovery time
        recovery_complete = False
        recovery_checks = 0
        while not recovery_complete and recovery_checks < 10:
            await asyncio.sleep(10)
            # Check if system has recovered
            test_response_times = await self._send_test_requests(10)
            avg_response = np.mean(test_response_times) if test_response_times else float('inf')
            
            if avg_response < normal_metrics["response_times"][0] * 1.1:  # Within 10% of normal
                recovery_complete = True
                result.recovery_time_seconds = time.time() - recovery_start
                
            recovery_checks += 1
            
        result.max_concurrent_users = spike_users
        result.end_time = datetime.now()
        return result
        
    async def run_sustained_load_test(self) -> StressTestResult:
        """Test system under sustained high load (soak test)"""
        logger.info("Starting sustained load test...")
        
        start_time = datetime.now()
        result = StressTestResult(
            scenario_name="Sustained Load Test",
            start_time=start_time,
            end_time=datetime.now(),
            max_concurrent_users=500,
            breaking_point_users=None,
            breaking_point_rps=None,
            error_threshold_reached=False,
            response_time_degradation={},
            error_rates={},
            recovery_time_seconds=None,
            cascade_failures=[],
            system_metrics={}
        )
        
        # Run sustained load for 1 hour
        users = 500
        duration_minutes = 60
        check_interval_minutes = 5
        
        for minute in range(0, duration_minutes, check_interval_minutes):
            logger.info(f"Sustained load test: {minute}/{duration_minutes} minutes")
            
            # Reset metrics
            self.metrics = {
                "requests_sent": 0,
                "requests_succeeded": 0,
                "requests_failed": 0,
                "response_times": [],
                "errors": []
            }
            
            # Run load for interval
            await self._run_concurrent_load(users, duration_seconds=check_interval_minutes * 60)
            
            # Record metrics at this point
            error_rate = (self.metrics["requests_failed"] / 
                         self.metrics["requests_sent"]) if self.metrics["requests_sent"] > 0 else 0
            avg_response_time = (np.mean(self.metrics["response_times"]) 
                               if self.metrics["response_times"] else 0)
            
            result.response_time_degradation[minute] = avg_response_time
            result.error_rates[minute] = error_rate
            
            # Check for degradation
            if minute > 0 and avg_response_time > result.response_time_degradation[0] * 2:
                logger.warning(f"Significant performance degradation detected at {minute} minutes")
                result.cascade_failures.append(f"Performance degradation at {minute} minutes")
                
        result.end_time = datetime.now()
        return result
        
    async def run_cascade_failure_test(self) -> StressTestResult:
        """Test cascade failure scenarios"""
        logger.info("Starting cascade failure test...")
        
        start_time = datetime.now()
        result = StressTestResult(
            scenario_name="Cascade Failure Test",
            start_time=start_time,
            end_time=datetime.now(),
            max_concurrent_users=1000,
            breaking_point_users=None,
            breaking_point_rps=None,
            error_threshold_reached=False,
            response_time_degradation={},
            error_rates={},
            recovery_time_seconds=None,
            cascade_failures=[],
            system_metrics={}
        )
        
        # Scenario 1: Database connection exhaustion
        logger.info("Testing database connection exhaustion...")
        await self._test_database_exhaustion()
        
        # Scenario 2: Cache stampede
        logger.info("Testing cache stampede...")
        await self._test_cache_stampede()
        
        # Scenario 3: AI API rate limiting cascade
        logger.info("Testing AI API rate limit cascade...")
        await self._test_ai_api_cascade()
        
        # Scenario 4: Memory exhaustion
        logger.info("Testing memory exhaustion...")
        await self._test_memory_exhaustion()
        
        result.end_time = datetime.now()
        return result
        
    async def run_geographic_distribution_test(self) -> StressTestResult:
        """Test with geographically distributed load"""
        logger.info("Starting geographic distribution test...")
        
        start_time = datetime.now()
        result = StressTestResult(
            scenario_name="Geographic Distribution Test",
            start_time=start_time,
            end_time=datetime.now(),
            max_concurrent_users=1000,
            breaking_point_users=None,
            breaking_point_rps=None,
            error_threshold_reached=False,
            response_time_degradation={},
            error_rates={},
            recovery_time_seconds=None,
            cascade_failures=[],
            system_metrics={}
        )
        
        # Simulate users from different regions
        regions = [
            {"name": "US West", "lat": 37.7749, "lng": -122.4194, "users": 400},
            {"name": "US East", "lat": 40.7128, "lng": -74.0060, "users": 300},
            {"name": "US Central", "lat": 41.8781, "lng": -87.6298, "users": 200},
            {"name": "International", "lat": 51.5074, "lng": -0.1278, "users": 100}
        ]
        
        tasks = []
        for region in regions:
            task = self._run_regional_load(region)
            tasks.append(task)
            
        # Run all regions concurrently
        results = await asyncio.gather(*tasks)
        
        # Aggregate results
        for region, region_result in zip(regions, results):
            result.system_metrics[region["name"]] = region_result
            
        result.end_time = datetime.now()
        return result
        
    async def _run_concurrent_load(self, num_users: int, duration_seconds: int):
        """Run concurrent load with specified users"""
        tasks = []
        users_per_batch = min(100, num_users)
        
        for batch in range(0, num_users, users_per_batch):
            batch_size = min(users_per_batch, num_users - batch)
            for _ in range(batch_size):
                task = self._simulate_user_session(duration_seconds)
                tasks.append(task)
                
            # Stagger user starts
            await asyncio.sleep(0.1)
            
        # Wait for all users to complete
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _simulate_user_session(self, duration_seconds: int):
        """Simulate a single user session"""
        end_time = time.time() + duration_seconds
        
        while time.time() < end_time:
            # Pick random action
            action = random.choice([
                self._voice_query,
                self._get_directions,
                self._search_poi,
                self._generate_story,
                self._book_hotel
            ])
            
            try:
                start = time.time()
                await action()
                response_time = (time.time() - start) * 1000  # Convert to ms
                
                self.metrics["requests_sent"] += 1
                self.metrics["requests_succeeded"] += 1
                self.metrics["response_times"].append(response_time)
                
            except Exception as e:
                self.metrics["requests_sent"] += 1
                self.metrics["requests_failed"] += 1
                self.metrics["errors"].append(str(e))
                
            # Wait before next action
            await asyncio.sleep(random.uniform(1, 3))
            
    async def _voice_query(self):
        """Simulate voice assistant query"""
        if not self.session:
            return
            
        data = {
            "user_input": "Find restaurants near me",
            "context": {
                "location": {"lat": 37.7749, "lng": -122.4194}
            }
        }
        
        async with self.session.post(
            f"{self.base_url}/api/voice-assistant/interact",
            json=data,
            headers=self.headers
        ) as response:
            await response.text()
            response.raise_for_status()
            
    async def _get_directions(self):
        """Simulate getting directions"""
        if not self.session:
            return
            
        data = {
            "origin": "San Francisco, CA",
            "destination": "Los Angeles, CA"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/directions",
            json=data,
            headers=self.headers
        ) as response:
            await response.text()
            response.raise_for_status()
            
    async def _search_poi(self):
        """Simulate POI search"""
        if not self.session:
            return
            
        params = {
            "lat": 37.7749,
            "lng": -122.4194,
            "radius": 5000,
            "type": "restaurant"
        }
        
        async with self.session.get(
            f"{self.base_url}/api/poi/search",
            params=params,
            headers=self.headers
        ) as response:
            await response.text()
            response.raise_for_status()
            
    async def _generate_story(self):
        """Simulate story generation"""
        if not self.session:
            return
            
        data = {
            "location": {"lat": 37.7749, "lng": -122.4194},
            "interests": ["history", "culture"],
            "story_type": "historical"
        }
        
        async with self.session.post(
            f"{self.base_url}/api/stories/generate",
            json=data,
            headers=self.headers
        ) as response:
            await response.text()
            response.raise_for_status()
            
    async def _book_hotel(self):
        """Simulate hotel booking"""
        if not self.session:
            return
            
        params = {
            "location": "San Francisco, CA",
            "checkin": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "checkout": (datetime.now() + timedelta(days=31)).strftime("%Y-%m-%d"),
            "guests": 2
        }
        
        async with self.session.get(
            f"{self.base_url}/api/booking/hotels/search",
            params=params,
            headers=self.headers
        ) as response:
            await response.text()
            response.raise_for_status()
            
    async def _send_test_requests(self, count: int) -> List[float]:
        """Send test requests and return response times"""
        response_times = []
        
        for _ in range(count):
            try:
                start = time.time()
                await self._voice_query()
                response_time = (time.time() - start) * 1000
                response_times.append(response_time)
            except:
                pass
                
        return response_times
        
    async def _test_database_exhaustion(self):
        """Test database connection pool exhaustion"""
        # Create many long-running queries
        tasks = []
        for _ in range(200):  # More than typical pool size
            task = self._long_running_query()
            tasks.append(task)
            
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _long_running_query(self):
        """Simulate a long-running database query"""
        if not self.session:
            return
            
        # Query that might take time
        params = {
            "start_date": "2020-01-01",
            "end_date": "2024-12-31",
            "include_details": True
        }
        
        async with self.session.get(
            f"{self.base_url}/api/analytics/full-report",
            params=params,
            headers=self.headers,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            await response.text()
            
    async def _test_cache_stampede(self):
        """Test cache stampede scenario"""
        # Invalidate popular cache keys
        cache_keys = [
            "popular_destinations",
            "trending_stories",
            "featured_restaurants"
        ]
        
        # Simulate many users requesting same uncached data
        tasks = []
        for key in cache_keys:
            for _ in range(100):
                task = self._request_uncached_data(key)
                tasks.append(task)
                
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _request_uncached_data(self, cache_key: str):
        """Request data that should be cached but isn't"""
        if not self.session:
            return
            
        endpoint_map = {
            "popular_destinations": "/api/destinations/popular",
            "trending_stories": "/api/stories/trending",
            "featured_restaurants": "/api/restaurants/featured"
        }
        
        endpoint = endpoint_map.get(cache_key, "/api/destinations/popular")
        
        async with self.session.get(
            f"{self.base_url}{endpoint}",
            headers=self.headers
        ) as response:
            await response.text()
            
    async def _test_ai_api_cascade(self):
        """Test AI API rate limiting cascade"""
        # Send many AI requests simultaneously
        tasks = []
        for _ in range(500):
            task = self._generate_story()
            tasks.append(task)
            
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _test_memory_exhaustion(self):
        """Test memory exhaustion scenario"""
        # Request large data sets
        tasks = []
        for _ in range(50):
            task = self._request_large_dataset()
            tasks.append(task)
            
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _request_large_dataset(self):
        """Request large dataset"""
        if not self.session:
            return
            
        params = {
            "include_all": True,
            "page_size": 10000,
            "include_metadata": True
        }
        
        async with self.session.get(
            f"{self.base_url}/api/export/all-journeys",
            params=params,
            headers=self.headers
        ) as response:
            await response.text()
            
    async def _run_regional_load(self, region: Dict[str, Any]) -> Dict[str, Any]:
        """Run load test for a specific region"""
        logger.info(f"Running load test for {region['name']} with {region['users']} users")
        
        # Simulate regional latency
        latency_ms = self._calculate_regional_latency(region)
        
        metrics = {
            "region": region["name"],
            "users": region["users"],
            "latency_ms": latency_ms,
            "requests_sent": 0,
            "requests_succeeded": 0,
            "response_times": []
        }
        
        # Run regional load
        tasks = []
        for _ in range(region["users"]):
            task = self._simulate_regional_user(region, metrics)
            tasks.append(task)
            
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Calculate final metrics
        metrics["avg_response_time"] = (
            np.mean(metrics["response_times"]) if metrics["response_times"] else 0
        )
        metrics["success_rate"] = (
            metrics["requests_succeeded"] / metrics["requests_sent"] 
            if metrics["requests_sent"] > 0 else 0
        )
        
        return metrics
        
    def _calculate_regional_latency(self, region: Dict[str, Any]) -> float:
        """Calculate simulated network latency based on region"""
        # Simplified latency calculation
        if region["name"] == "US West":
            return random.uniform(10, 30)
        elif region["name"] == "US East":
            return random.uniform(40, 80)
        elif region["name"] == "US Central":
            return random.uniform(30, 60)
        else:  # International
            return random.uniform(100, 200)
            
    async def _simulate_regional_user(self, region: Dict[str, Any], metrics: Dict[str, Any]):
        """Simulate a user from a specific region"""
        # Add regional latency
        latency_seconds = region.get("latency_ms", 0) / 1000
        
        for _ in range(10):  # Each user makes 10 requests
            await asyncio.sleep(latency_seconds)  # Simulate network latency
            
            try:
                start = time.time()
                await self._voice_query()
                response_time = (time.time() - start) * 1000
                
                metrics["requests_sent"] += 1
                metrics["requests_succeeded"] += 1
                metrics["response_times"].append(response_time)
                
            except:
                metrics["requests_sent"] += 1
                
            await asyncio.sleep(random.uniform(2, 5))


async def run_all_stress_tests():
    """Run all stress test scenarios"""
    tester = StressTestScenarios()
    
    try:
        await tester.setup()
        
        results = []
        
        # Run each test scenario
        scenarios = [
            tester.run_breaking_point_test(),
            tester.run_spike_test(),
            tester.run_sustained_load_test(),
            tester.run_cascade_failure_test(),
            tester.run_geographic_distribution_test()
        ]
        
        for scenario in scenarios:
            try:
                result = await scenario
                results.append(result)
                logger.info(f"Completed: {result.scenario_name}")
                
                # Cool down between tests
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Test scenario failed: {e}")
                
        # Generate report
        generate_stress_test_report(results)
        
    finally:
        await tester.teardown()


def generate_stress_test_report(results: List[StressTestResult]):
    """Generate comprehensive stress test report"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "scenarios_run": len(results),
            "scenarios_passed": sum(1 for r in results if not r.error_threshold_reached),
            "breaking_points_found": sum(1 for r in results if r.breaking_point_users),
            "cascade_failures_detected": sum(len(r.cascade_failures) for r in results)
        },
        "detailed_results": []
    }
    
    for result in results:
        detailed = {
            "scenario": result.scenario_name,
            "duration_seconds": (result.end_time - result.start_time).total_seconds(),
            "max_concurrent_users": result.max_concurrent_users,
            "breaking_point": {
                "users": result.breaking_point_users,
                "rps": result.breaking_point_rps
            },
            "performance_degradation": result.response_time_degradation,
            "error_rates": result.error_rates,
            "recovery_time": result.recovery_time_seconds,
            "cascade_failures": result.cascade_failures,
            "recommendations": generate_recommendations(result)
        }
        report["detailed_results"].append(detailed)
        
    # Save report
    with open("stress_test_report.json", "w") as f:
        json.dump(report, f, indent=2)
        
    logger.info("Stress test report generated: stress_test_report.json")
    

def generate_recommendations(result: StressTestResult) -> List[str]:
    """Generate recommendations based on stress test results"""
    recommendations = []
    
    if result.breaking_point_users and result.breaking_point_users < 1000:
        recommendations.append(
            f"System breaks at {result.breaking_point_users} users. "
            "Consider horizontal scaling or performance optimization."
        )
        
    if result.recovery_time_seconds and result.recovery_time_seconds > 300:
        recommendations.append(
            f"Recovery time of {result.recovery_time_seconds}s is too long. "
            "Implement circuit breakers and better error handling."
        )
        
    if result.cascade_failures:
        recommendations.append(
            f"Cascade failures detected: {', '.join(result.cascade_failures)}. "
            "Implement proper isolation and fallback mechanisms."
        )
        
    # Check for performance degradation patterns
    if result.response_time_degradation:
        times = list(result.response_time_degradation.values())
        if len(times) > 1 and times[-1] > times[0] * 3:
            recommendations.append(
                "Significant performance degradation under load. "
                "Review database queries, caching strategy, and resource allocation."
            )
            
    return recommendations


if __name__ == "__main__":
    asyncio.run(run_all_stress_tests())