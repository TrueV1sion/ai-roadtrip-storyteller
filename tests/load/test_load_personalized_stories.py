"""Load test for the personalized stories endpoint."""
import asyncio
import json
import time
import statistics
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
import aiohttp
import pytest
import random
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000"
ENDPOINT = "/api/stories/personalized"
TOTAL_REQUESTS = 100
CONCURRENT_USERS = 10
REQUEST_TIMEOUT = 30  # seconds

# Sample user data
SAMPLE_USERS = [
    {"user_id": str(uuid.uuid4()), "name": "Family A", "interests": ["history", "nature", "music"]},
    {"user_id": str(uuid.uuid4()), "name": "Family B", "interests": ["science", "architecture", "food"]},
    {"user_id": str(uuid.uuid4()), "name": "Family C", "interests": ["art", "sports", "literature"]},
    {"user_id": str(uuid.uuid4()), "name": "Family D", "interests": ["photography", "wildlife", "hiking"]},
    {"user_id": str(uuid.uuid4()), "name": "Family E", "interests": ["astronomy", "geology", "technology"]},
]

# Sample locations (latitude, longitude)
SAMPLE_LOCATIONS = [
    {"latitude": 34.0522, "longitude": -118.2437},  # Los Angeles
    {"latitude": 37.7749, "longitude": -122.4194},  # San Francisco
    {"latitude": 40.7128, "longitude": -74.0060},   # New York
    {"latitude": 29.7604, "longitude": -95.3698},   # Houston
    {"latitude": 41.8781, "longitude": -87.6298},   # Chicago
    {"latitude": 33.4484, "longitude": -112.0740},  # Phoenix
    {"latitude": 39.9526, "longitude": -75.1652},   # Philadelphia
    {"latitude": 32.7157, "longitude": -117.1611},  # San Diego
    {"latitude": 30.2672, "longitude": -97.7431},   # Austin
    {"latitude": 43.0389, "longitude": -87.9065},   # Milwaukee
]

class LoadTestResults:
    """Class to store and analyze load test results."""
    
    def __init__(self):
        self.response_times: List[float] = []
        self.status_codes: Dict[int, int] = {}
        self.errors: List[str] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def start(self):
        """Mark the start of the test."""
        self.start_time = time.time()
    
    def end(self):
        """Mark the end of the test."""
        self.end_time = time.time()
    
    def add_response(self, status_code: int, response_time: float):
        """Add a response to the results."""
        self.response_times.append(response_time)
        self.status_codes[status_code] = self.status_codes.get(status_code, 0) + 1
    
    def add_error(self, error_message: str):
        """Add an error to the results."""
        self.errors.append(error_message)
    
    def get_summary(self) -> Dict[str, Any]:
        """Generate a summary of the test results."""
        if not self.response_times or self.start_time is None or self.end_time is None:
            return {"error": "No test data available"}
        
        total_time = self.end_time - self.start_time
        
        return {
            "total_requests": len(self.response_times) + len(self.errors),
            "successful_requests": len(self.response_times),
            "failed_requests": len(self.errors),
            "total_time": total_time,
            "requests_per_second": len(self.response_times) / total_time,
            "response_times": {
                "min": min(self.response_times),
                "max": max(self.response_times),
                "avg": statistics.mean(self.response_times),
                "median": statistics.median(self.response_times),
                "p95": statistics.quantiles(sorted(self.response_times), n=20)[18] if len(self.response_times) >= 20 else None,
                "p99": statistics.quantiles(sorted(self.response_times), n=100)[98] if len(self.response_times) >= 100 else None,
            },
            "status_code_distribution": self.status_codes,
            "errors": self.errors[:10]  # Only include first 10 errors
        }

async def make_request(session: aiohttp.ClientSession, results: LoadTestResults) -> None:
    """Make a single request to the API and record the result."""
    # Generate random request data
    user = random.choice(SAMPLE_USERS)
    location = random.choice(SAMPLE_LOCATIONS)
    
    data = {
        "user_id": user["user_id"],
        "location": location,
        "interests": user["interests"],
        "preferences": {
            "content_type": random.choice(["historical", "nature", "cultural", "fictional"]),
            "story_length": random.choice(["short", "medium", "long"]),
            "include_facts": random.choice([True, False]),
        },
        "context": {
            "time_of_day": random.choice(["morning", "afternoon", "evening", "night"]),
            "weather": random.choice(["sunny", "cloudy", "rainy", "snowy"]),
            "mood": random.choice(["excited", "relaxed", "curious", "tired"]),
        }
    }
    
    start_time = time.time()
    
    try:
        async with session.post(
            f"{BASE_URL}{ENDPOINT}",
            json=data,
            timeout=REQUEST_TIMEOUT
        ) as response:
            status = response.status
            await response.read()  # Read and discard the response body
            
            # Record the result
            response_time = time.time() - start_time
            results.add_response(status, response_time)
            
            if status != 200:
                error_message = f"Error {status}: Request failed"
                results.add_error(error_message)
                
    except Exception as e:
        results.add_error(f"Exception: {str(e)}")

async def run_load_test(requests: int, concurrent_users: int) -> LoadTestResults:
    """Run a load test against the API."""
    results = LoadTestResults()
    results.start()
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        # Create a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(concurrent_users)
        
        # Helper function to acquire and release the semaphore
        async def bounded_request():
            async with semaphore:
                await make_request(session, results)
        
        # Create all the tasks
        for _ in range(requests):
            tasks.append(asyncio.create_task(bounded_request()))
        
        # Wait for all tasks to complete
        await asyncio.gather(*tasks)
    
    results.end()
    return results

@pytest.mark.asyncio
async def test_personalized_stories_load():
    """Test the load capacity of the personalized stories endpoint."""
    logger.info(f"Starting load test with {TOTAL_REQUESTS} requests, {CONCURRENT_USERS} concurrent users")
    
    results = await run_load_test(TOTAL_REQUESTS, CONCURRENT_USERS)
    summary = results.get_summary()
    
    logger.info("Load test results:")
    logger.info(f"Total requests: {summary['total_requests']}")
    logger.info(f"Successful requests: {summary['successful_requests']}")
    logger.info(f"Failed requests: {summary['failed_requests']}")
    logger.info(f"Requests per second: {summary['requests_per_second']:.2f}")
    logger.info(f"Average response time: {summary['response_times']['avg']:.2f}s")
    logger.info(f"95th percentile response time: {summary['response_times'].get('p95', 'N/A')}s")
    
    # Write detailed results to a JSON file for analysis
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"load_test_results_{timestamp}.json", "w") as f:
        json.dump(summary, f, indent=2)
    
    # Basic assertions to verify the test was successful
    assert summary["failed_requests"] / summary["total_requests"] < 0.1, "More than 10% of requests failed"
    assert summary["response_times"]["avg"] < 5.0, "Average response time is too high"

if __name__ == "__main__":
    # Run the test directly if the script is executed
    asyncio.run(test_personalized_stories_load()) 