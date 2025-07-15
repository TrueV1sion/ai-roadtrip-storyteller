#!/usr/bin/env python3
"""
Live Integration Test Runner - Six Sigma DMAIC
Runs integration tests against actual running services
"""

import asyncio
import json
import logging
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiveIntegrationTestRunner:
    """
    Runs integration tests against live services with Six Sigma methodology
    """
    
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.test_results = []
        self.performance_metrics = {}
        
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all integration tests against live services"""
        logger.info("🚀 Starting Live Integration Tests")
        
        start_time = time.time()
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "test_suites": {},
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "performance_metrics": {}
        }
        
        # Test suites to run
        test_suites = {
            "knowledge_graph": self._test_knowledge_graph_suite,
            "api_endpoints": self._test_api_endpoints_suite,
            "performance": self._test_performance_suite,
            "integration": self._test_integration_suite
        }
        
        # Run each test suite
        for suite_name, test_func in test_suites.items():
            logger.info(f"\n📋 Running {suite_name} test suite...")
            suite_results = await test_func()
            results["test_suites"][suite_name] = suite_results
            
            # Update totals
            results["total_tests"] += suite_results["total"]
            results["passed_tests"] += suite_results["passed"]
            results["failed_tests"] += suite_results["failed"]
        
        # Calculate metrics
        results["duration"] = time.time() - start_time
        results["pass_rate"] = (results["passed_tests"] / results["total_tests"] * 100) if results["total_tests"] > 0 else 0
        results["sigma_level"] = self._calculate_sigma_level(results["pass_rate"])
        
        return results
    
    async def _test_knowledge_graph_suite(self) -> Dict[str, Any]:
        """Test Knowledge Graph functionality"""
        suite_results = {
            "name": "Knowledge Graph Integration",
            "tests": [],
            "total": 0,
            "passed": 0,
            "failed": 0
        }
        
        # Test 1: Health Check
        test_result = await self._test_kg_health()
        suite_results["tests"].append(test_result)
        suite_results["total"] += 1
        if test_result["passed"]:
            suite_results["passed"] += 1
        else:
            suite_results["failed"] += 1
        
        # Test 2: Search Functionality
        test_result = await self._test_kg_search()
        suite_results["tests"].append(test_result)
        suite_results["total"] += 1
        if test_result["passed"]:
            suite_results["passed"] += 1
        else:
            suite_results["failed"] += 1
        
        # Test 3: Impact Analysis
        test_result = await self._test_kg_impact_analysis()
        suite_results["tests"].append(test_result)
        suite_results["total"] += 1
        if test_result["passed"]:
            suite_results["passed"] += 1
        else:
            suite_results["failed"] += 1
        
        # Test 4: Agent Notes
        test_result = await self._test_kg_agent_notes()
        suite_results["tests"].append(test_result)
        suite_results["total"] += 1
        if test_result["passed"]:
            suite_results["passed"] += 1
        else:
            suite_results["failed"] += 1
        
        return suite_results
    
    async def _test_api_endpoints_suite(self) -> Dict[str, Any]:
        """Test API endpoints"""
        suite_results = {
            "name": "API Endpoints",
            "tests": [],
            "total": 0,
            "passed": 0,
            "failed": 0
        }
        
        # Since backend is not running, we'll test what we can
        endpoints = [
            ("/", "Dashboard"),
            ("/api/health", "Health Check"),
            ("/api/stats", "Statistics"),
            ("/api/search", "Search")
        ]
        
        for endpoint, name in endpoints:
            test_result = await self._test_endpoint(endpoint, name)
            suite_results["tests"].append(test_result)
            suite_results["total"] += 1
            if test_result["passed"]:
                suite_results["passed"] += 1
            else:
                suite_results["failed"] += 1
        
        return suite_results
    
    async def _test_performance_suite(self) -> Dict[str, Any]:
        """Test performance characteristics"""
        suite_results = {
            "name": "Performance Tests",
            "tests": [],
            "total": 0,
            "passed": 0,
            "failed": 0
        }
        
        # Test response times
        performance_tests = [
            ("kg_health_response_time", "/api/health", 1.0),
            ("kg_search_response_time", "/api/search", 2.0),
            ("dashboard_load_time", "/", 3.0)
        ]
        
        for test_name, endpoint, target_time in performance_tests:
            test_result = await self._test_response_time(test_name, endpoint, target_time)
            suite_results["tests"].append(test_result)
            suite_results["total"] += 1
            if test_result["passed"]:
                suite_results["passed"] += 1
            else:
                suite_results["failed"] += 1
        
        return suite_results
    
    async def _test_integration_suite(self) -> Dict[str, Any]:
        """Test integration between components"""
        suite_results = {
            "name": "Component Integration",
            "tests": [],
            "total": 0,
            "passed": 0,
            "failed": 0
        }
        
        # Test search and retrieve pattern
        test_result = await self._test_search_and_retrieve()
        suite_results["tests"].append(test_result)
        suite_results["total"] += 1
        if test_result["passed"]:
            suite_results["passed"] += 1
        else:
            suite_results["failed"] += 1
        
        return suite_results
    
    async def _test_kg_health(self) -> Dict[str, Any]:
        """Test Knowledge Graph health endpoint"""
        try:
            start_time = time.time()
            req = urllib.request.Request(f"{self.base_url}/api/health")
            
            with urllib.request.urlopen(req, timeout=5) as response:
                duration = time.time() - start_time
                
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    
                    # Verify expected fields
                    if "status" in data and data["status"] == "healthy":
                        return {
                            "name": "KG Health Check",
                            "passed": True,
                            "duration": duration,
                            "details": f"Nodes: {data['stats']['nodes']}, Links: {data['stats']['links']}"
                        }
                    else:
                        return {
                            "name": "KG Health Check",
                            "passed": False,
                            "duration": duration,
                            "reason": "Unexpected response format"
                        }
                else:
                    return {
                        "name": "KG Health Check",
                        "passed": False,
                        "duration": duration,
                        "reason": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "name": "KG Health Check",
                "passed": False,
                "error": str(e)
            }
    
    async def _test_kg_search(self) -> Dict[str, Any]:
        """Test Knowledge Graph search functionality"""
        try:
            start_time = time.time()
            
            # Test search for voice services
            search_data = {"query": "voice services"}
            data = json.dumps(search_data).encode('utf-8')
            
            req = urllib.request.Request(
                f"{self.base_url}/api/search",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                duration = time.time() - start_time
                
                if response.status == 200:
                    results = json.loads(response.read().decode())
                    
                    if "results" in results and len(results["results"]) > 0:
                        return {
                            "name": "KG Search - Voice Services",
                            "passed": True,
                            "duration": duration,
                            "details": f"Found {len(results['results'])} results"
                        }
                    else:
                        return {
                            "name": "KG Search - Voice Services",
                            "passed": False,
                            "duration": duration,
                            "reason": "No results found for 'voice services'"
                        }
                else:
                    return {
                        "name": "KG Search - Voice Services",
                        "passed": False,
                        "duration": duration,
                        "reason": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "name": "KG Search - Voice Services",
                "passed": False,
                "error": str(e)
            }
    
    async def _test_kg_impact_analysis(self) -> Dict[str, Any]:
        """Test Knowledge Graph impact analysis"""
        try:
            start_time = time.time()
            
            # Test impact analysis for a known file
            impact_data = {"node_id": "backend/app/services/voice_services.py"}
            data = json.dumps(impact_data).encode('utf-8')
            
            req = urllib.request.Request(
                f"{self.base_url}/api/impact/analyze",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                duration = time.time() - start_time
                
                if response.status == 200:
                    results = json.loads(response.read().decode())
                    
                    if "impact" in results:
                        return {
                            "name": "KG Impact Analysis",
                            "passed": True,
                            "duration": duration,
                            "details": f"Analyzed impact for voice_services.py"
                        }
                    else:
                        return {
                            "name": "KG Impact Analysis",
                            "passed": False,
                            "duration": duration,
                            "reason": "No impact data returned"
                        }
                else:
                    return {
                        "name": "KG Impact Analysis",
                        "passed": False,
                        "duration": duration,
                        "reason": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "name": "KG Impact Analysis",
                "passed": False,
                "error": str(e)
            }
    
    async def _test_kg_agent_notes(self) -> Dict[str, Any]:
        """Test Knowledge Graph agent notes functionality"""
        try:
            start_time = time.time()
            
            # Add a test note
            note_data = {
                "node_id": "test_file.py",
                "agent_id": "IntegrationTestAgent",
                "note": "Test note from integration testing"
            }
            data = json.dumps(note_data).encode('utf-8')
            
            req = urllib.request.Request(
                f"{self.base_url}/api/agent/note",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                duration = time.time() - start_time
                
                if response.status == 200:
                    return {
                        "name": "KG Agent Notes",
                        "passed": True,
                        "duration": duration,
                        "details": "Successfully added agent note"
                    }
                else:
                    return {
                        "name": "KG Agent Notes",
                        "passed": False,
                        "duration": duration,
                        "reason": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "name": "KG Agent Notes",
                "passed": False,
                "error": str(e)
            }
    
    async def _test_endpoint(self, endpoint: str, name: str) -> Dict[str, Any]:
        """Test a specific endpoint"""
        try:
            start_time = time.time()
            req = urllib.request.Request(f"{self.base_url}{endpoint}")
            
            with urllib.request.urlopen(req, timeout=5) as response:
                duration = time.time() - start_time
                
                if response.status == 200:
                    return {
                        "name": f"Endpoint: {name}",
                        "passed": True,
                        "duration": duration,
                        "endpoint": endpoint
                    }
                else:
                    return {
                        "name": f"Endpoint: {name}",
                        "passed": False,
                        "duration": duration,
                        "endpoint": endpoint,
                        "reason": f"HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "name": f"Endpoint: {name}",
                "passed": False,
                "endpoint": endpoint,
                "error": str(e)
            }
    
    async def _test_response_time(self, test_name: str, endpoint: str, target_time: float) -> Dict[str, Any]:
        """Test response time for an endpoint"""
        try:
            start_time = time.time()
            req = urllib.request.Request(f"{self.base_url}{endpoint}")
            
            # For POST endpoints, add minimal data
            if endpoint == "/api/search":
                data = json.dumps({"query": "test"}).encode('utf-8')
                req = urllib.request.Request(
                    f"{self.base_url}{endpoint}",
                    data=data,
                    headers={'Content-Type': 'application/json'}
                )
            
            with urllib.request.urlopen(req, timeout=target_time + 1) as response:
                duration = time.time() - start_time
                
                passed = duration <= target_time
                
                self.performance_metrics[test_name] = {
                    "target": target_time,
                    "actual": duration,
                    "passed": passed
                }
                
                return {
                    "name": f"Performance: {test_name}",
                    "passed": passed,
                    "duration": duration,
                    "target": target_time,
                    "details": f"Response time: {duration:.3f}s (target: {target_time}s)"
                }
                    
        except Exception as e:
            return {
                "name": f"Performance: {test_name}",
                "passed": False,
                "error": str(e)
            }
    
    async def _test_search_and_retrieve(self) -> Dict[str, Any]:
        """Test search and retrieve pattern"""
        try:
            # First search for something
            search_data = {"query": "orchestration"}
            data = json.dumps(search_data).encode('utf-8')
            
            req = urllib.request.Request(
                f"{self.base_url}/api/search",
                data=data,
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    results = json.loads(response.read().decode())
                    
                    if "results" in results and len(results["results"]) > 0:
                        # Found results, try to get details of first result
                        first_result = results["results"][0]
                        
                        return {
                            "name": "Search and Retrieve Pattern",
                            "passed": True,
                            "details": f"Successfully searched and found {len(results['results'])} results"
                        }
                    else:
                        return {
                            "name": "Search and Retrieve Pattern",
                            "passed": False,
                            "reason": "Search returned no results"
                        }
                else:
                    return {
                        "name": "Search and Retrieve Pattern",
                        "passed": False,
                        "reason": f"Search failed with HTTP {response.status}"
                    }
                    
        except Exception as e:
            return {
                "name": "Search and Retrieve Pattern",
                "passed": False,
                "error": str(e)
            }
    
    def _calculate_sigma_level(self, pass_rate: float) -> float:
        """Calculate Six Sigma level from pass rate"""
        if pass_rate >= 99.99966:
            return 6.0
        elif pass_rate >= 99.977:
            return 5.0
        elif pass_rate >= 99.38:
            return 4.0
        elif pass_rate >= 93.32:
            return 3.0
        elif pass_rate >= 69.15:
            return 2.0
        else:
            return 1.0
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate comprehensive test report"""
        report = f"""
# Live Integration Test Report
## AI Road Trip Storyteller

### Executive Summary
- **Date**: {results['timestamp']}
- **Total Tests**: {results['total_tests']}
- **Passed**: {results['passed_tests']}
- **Failed**: {results['failed_tests']}
- **Pass Rate**: {results['pass_rate']:.1f}%
- **Sigma Level**: {results['sigma_level']:.1f}σ
- **Duration**: {results['duration']:.2f}s

### Test Suite Results
"""
        
        for suite_name, suite_results in results['test_suites'].items():
            report += f"\n#### {suite_results['name']}"
            report += f"\n- Tests: {suite_results['total']}"
            report += f"\n- Passed: {suite_results['passed']}"
            report += f"\n- Failed: {suite_results['failed']}"
            report += f"\n- Pass Rate: {(suite_results['passed'] / suite_results['total'] * 100) if suite_results['total'] > 0 else 0:.1f}%"
            
            report += "\n\n**Test Details:**"
            for test in suite_results['tests']:
                emoji = "✅" if test['passed'] else "❌"
                report += f"\n- {emoji} {test['name']}"
                if 'duration' in test:
                    report += f" ({test['duration']:.3f}s)"
                if 'details' in test:
                    report += f"\n  - {test['details']}"
                if 'reason' in test:
                    report += f"\n  - Failure: {test['reason']}"
                if 'error' in test:
                    report += f"\n  - Error: {test['error']}"
        
        report += "\n\n### Performance Metrics"
        for metric_name, metric_data in self.performance_metrics.items():
            emoji = "✅" if metric_data['passed'] else "⚠️"
            report += f"\n- {emoji} {metric_name}: {metric_data['actual']:.3f}s (target: {metric_data['target']}s)"
        
        report += """

### Recommendations
"""
        
        if results['sigma_level'] < 3.0:
            report += """
1. **Critical**: Service integration needs immediate attention
2. Start missing services (Backend API, Redis, PostgreSQL)
3. Fix failing integration points
4. Implement proper error handling
"""
        elif results['sigma_level'] < 5.0:
            report += """
1. Address remaining test failures
2. Optimize performance bottlenecks
3. Enhance monitoring coverage
4. Implement automated recovery
"""
        else:
            report += """
1. System performing well
2. Consider adding more comprehensive tests
3. Implement continuous monitoring
4. Set up automated regression testing
"""
        
        report += """

### Next Steps
1. Fix any failing tests identified above
2. Start missing services using Docker or local setup
3. Re-run tests after fixes
4. Target 5.0σ (99.977% pass rate) for production readiness
"""
        
        return report


async def main():
    """Execute live integration tests"""
    runner = LiveIntegrationTestRunner()
    
    logger.info("🎯 Launching Live Integration Test Runner")
    
    # Run comprehensive tests
    results = await runner.run_comprehensive_tests()
    
    # Generate report
    report = runner.generate_report(results)
    
    # Save report
    report_path = Path("live_integration_test_report.md")
    with open(report_path, "w") as f:
        f.write(report)
    
    logger.info(f"✅ Integration testing complete. Report saved to {report_path}")
    
    # Print summary
    print(f"\n📊 Test Summary:")
    print(f"   Total Tests: {results['total_tests']}")
    print(f"   Passed: {results['passed_tests']}")
    print(f"   Failed: {results['failed_tests']}")
    print(f"   Pass Rate: {results['pass_rate']:.1f}%")
    print(f"   Sigma Level: {results['sigma_level']:.1f}σ")
    
    return results


if __name__ == "__main__":
    asyncio.run(main())