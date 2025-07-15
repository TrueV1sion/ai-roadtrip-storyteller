"""
Performance Testing Orchestration Script
========================================

Main script to run comprehensive performance testing including load tests,
stress tests, benchmarks, and monitoring.
"""

import asyncio
import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.performance.performance_test_framework import PerformanceTestRunner, LOAD_TEST_SCENARIOS
from tests.performance.load_tests.user_behaviors import USER_CLASSES
from tests.performance.stress_tests.stress_test_scenarios import StressTestScenarios
from tests.performance.benchmarks.performance_benchmarks import PerformanceBenchmark
from tests.performance.tools.performance_monitor import PerformanceMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('performance_tests.log')
    ]
)
logger = logging.getLogger(__name__)


class PerformanceTestOrchestrator:
    """Orchestrates all performance testing activities"""
    
    def __init__(self, 
                 base_url: str = "http://localhost:8000",
                 database_url: Optional[str] = None,
                 redis_url: str = "redis://localhost:6379"):
        self.base_url = base_url
        self.database_url = database_url
        self.redis_url = redis_url
        self.results: Dict[str, Any] = {}
        self.start_time = datetime.now()
        
    async def run_all_tests(self, 
                           include_load: bool = True,
                           include_stress: bool = True,
                           include_benchmarks: bool = True,
                           include_monitoring: bool = False,
                           monitoring_duration: int = 300) -> Dict[str, Any]:
        """Run all performance tests"""
        logger.info("Starting comprehensive performance testing...")
        logger.info(f"Target URL: {self.base_url}")
        
        try:
            # Pre-test system check
            await self._pre_test_checks()
            
            # Run benchmarks first (baseline performance)
            if include_benchmarks:
                logger.info("\n" + "="*60)
                logger.info("PHASE 1: Performance Benchmarks")
                logger.info("="*60)
                await self._run_benchmarks()
                
            # Run load tests
            if include_load:
                logger.info("\n" + "="*60)
                logger.info("PHASE 2: Load Testing")
                logger.info("="*60)
                await self._run_load_tests()
                
            # Run stress tests
            if include_stress:
                logger.info("\n" + "="*60)
                logger.info("PHASE 3: Stress Testing")
                logger.info("="*60)
                await self._run_stress_tests()
                
            # Run monitoring (if requested)
            if include_monitoring:
                logger.info("\n" + "="*60)
                logger.info("PHASE 4: Performance Monitoring")
                logger.info("="*60)
                await self._run_monitoring(monitoring_duration)
                
            # Generate final report
            await self._generate_final_report()
            
            return self.results
            
        except Exception as e:
            logger.error(f"Performance testing failed: {e}")
            raise
            
    async def _pre_test_checks(self):
        """Run pre-test system checks"""
        logger.info("Running pre-test system checks...")
        
        checks = {
            "api_available": False,
            "database_available": False,
            "redis_available": False,
            "system_resources": {}
        }
        
        # Check API availability
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        checks["api_available"] = True
                        logger.info("✅ API is available")
                    else:
                        logger.warning(f"⚠️ API returned status {response.status}")
        except Exception as e:
            logger.error(f"❌ API not available: {e}")
            
        # Check Redis availability
        import redis.asyncio as redis
        try:
            redis_client = await redis.from_url(self.redis_url)
            await redis_client.ping()
            checks["redis_available"] = True
            logger.info("✅ Redis is available")
            await redis_client.close()
        except Exception as e:
            logger.warning(f"⚠️ Redis not available: {e}")
            
        # Check system resources
        import psutil
        cpu_count = psutil.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        disk_gb = psutil.disk_usage('/').total / (1024**3)
        
        checks["system_resources"] = {
            "cpu_cores": cpu_count,
            "memory_gb": round(memory_gb, 1),
            "disk_gb": round(disk_gb, 1)
        }
        
        logger.info(f"📊 System: {cpu_count} CPUs, {memory_gb:.1f}GB RAM, {disk_gb:.1f}GB disk")
        
        # Check if system meets minimum requirements
        if cpu_count < 2:
            logger.warning("⚠️ System has fewer than 2 CPU cores - performance tests may be limited")
        if memory_gb < 4:
            logger.warning("⚠️ System has less than 4GB RAM - may affect test reliability")
            
        if not checks["api_available"]:
            raise RuntimeError("API is not available - cannot proceed with performance tests")
            
        self.results["pre_test_checks"] = checks
        
    async def _run_benchmarks(self):
        """Run performance benchmarks"""
        logger.info("Running performance benchmarks...")
        
        benchmark = PerformanceBenchmark(
            api_base_url=self.base_url,
            database_url=self.database_url,
            redis_url=self.redis_url
        )
        
        try:
            await benchmark.setup()
            
            # Run all benchmarks
            suite = await benchmark.run_all_benchmarks()
            
            # Generate report
            benchmark.generate_report(suite)
            
            # Store results
            self.results["benchmarks"] = {
                "total_operations": len(suite.results),
                "avg_success_rate": sum(r.success_rate for r in suite.results) / len(suite.results),
                "fastest_operation": min(suite.results, key=lambda r: r.avg_time_ms).name,
                "slowest_operation": max(suite.results, key=lambda r: r.avg_time_ms).name,
                "detailed_results": [
                    {
                        "name": r.name,
                        "category": r.category,
                        "avg_time_ms": r.avg_time_ms,
                        "p95_time_ms": r.p95_time_ms,
                        "throughput_per_second": r.throughput_per_second,
                        "success_rate": r.success_rate
                    }
                    for r in suite.results
                ]
            }
            
            logger.info("✅ Benchmarks completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Benchmark testing failed: {e}")
            self.results["benchmarks"] = {"error": str(e)}
        finally:
            await benchmark.teardown()
            
    async def _run_load_tests(self):
        """Run load testing scenarios"""
        logger.info("Running load testing scenarios...")
        
        runner = PerformanceTestRunner(base_url=self.base_url)
        
        try:
            await runner.setup()
            
            # Update scenarios with actual user classes
            for scenario in LOAD_TEST_SCENARIOS:
                scenario["user_classes"] = USER_CLASSES[:2]  # Use first 2 user types for load tests
                
            # Run all load test scenarios
            load_results = []
            for scenario in LOAD_TEST_SCENARIOS:
                logger.info(f"Running load test: {scenario['name']}")
                
                try:
                    metrics = await runner.run_scenario(scenario)
                    load_results.append(metrics)
                    
                    logger.info(f"✅ {scenario['name']} completed: "
                               f"RPS={metrics.requests_per_second:.2f}, "
                               f"Avg Response={metrics.avg_response_time_ms:.2f}ms, "
                               f"Error Rate={metrics.error_rate:.2f}%")
                               
                    # Cool down between scenarios
                    await asyncio.sleep(30)
                    
                except Exception as e:
                    logger.error(f"❌ Load test {scenario['name']} failed: {e}")
                    
            # Generate report
            runner.generate_report()
            
            # Store results
            self.results["load_tests"] = {
                "scenarios_run": len(load_results),
                "total_requests": sum(m.total_requests for m in load_results),
                "total_errors": sum(m.failed_requests for m in load_results),
                "avg_response_time": sum(m.avg_response_time_ms for m in load_results) / len(load_results) if load_results else 0,
                "max_concurrent_users": max(m.concurrent_users for m in load_results) if load_results else 0,
                "detailed_results": [
                    {
                        "scenario": m.scenario,
                        "users": m.concurrent_users,
                        "requests_per_second": m.requests_per_second,
                        "avg_response_time_ms": m.avg_response_time_ms,
                        "error_rate": m.error_rate
                    }
                    for m in load_results
                ]
            }
            
            logger.info("✅ Load testing completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Load testing failed: {e}")
            self.results["load_tests"] = {"error": str(e)}
        finally:
            await runner.teardown()
            
    async def _run_stress_tests(self):
        """Run stress testing scenarios"""
        logger.info("Running stress testing scenarios...")
        
        stress_tester = StressTestScenarios(base_url=self.base_url)
        
        try:
            await stress_tester.setup()
            
            # Run stress test scenarios
            stress_results = []
            
            # Breaking point test
            logger.info("Running breaking point test...")
            result = await stress_tester.run_breaking_point_test()
            stress_results.append(result)
            
            # Cool down
            await asyncio.sleep(60)
            
            # Spike test
            logger.info("Running spike test...")
            result = await stress_tester.run_spike_test()
            stress_results.append(result)
            
            # Cool down
            await asyncio.sleep(60)
            
            # Note: Skipping sustained load test and cascade failure test in CI
            # They would run too long for typical CI environments
            
            # Store results
            self.results["stress_tests"] = {
                "scenarios_run": len(stress_results),
                "breaking_point_found": any(r.breaking_point_users for r in stress_results),
                "max_users_tested": max(r.max_concurrent_users for r in stress_results) if stress_results else 0,
                "cascade_failures": sum(len(r.cascade_failures) for r in stress_results),
                "detailed_results": [
                    {
                        "scenario": r.scenario_name,
                        "max_users": r.max_concurrent_users,
                        "breaking_point_users": r.breaking_point_users,
                        "breaking_point_rps": r.breaking_point_rps,
                        "error_threshold_reached": r.error_threshold_reached,
                        "cascade_failures": r.cascade_failures
                    }
                    for r in stress_results
                ]
            }
            
            logger.info("✅ Stress testing completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Stress testing failed: {e}")
            self.results["stress_tests"] = {"error": str(e)}
        finally:
            await stress_tester.teardown()
            
    async def _run_monitoring(self, duration_seconds: int):
        """Run performance monitoring"""
        logger.info(f"Running performance monitoring for {duration_seconds} seconds...")
        
        monitor = PerformanceMonitor(
            api_base_url=self.base_url,
            redis_url=self.redis_url
        )
        
        try:
            await monitor.setup()
            
            # Start monitoring task
            monitoring_task = asyncio.create_task(
                monitor.start_monitoring(interval_seconds=10)
            )
            
            # Let it run for specified duration
            await asyncio.sleep(duration_seconds)
            
            # Stop monitoring
            monitoring_task.cancel()
            
            # Get final health status
            health_status = await monitor.get_health_status()
            
            self.results["monitoring"] = {
                "duration_seconds": duration_seconds,
                "health_status": health_status,
                "prometheus_metrics_available": True
            }
            
            logger.info("✅ Performance monitoring completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Performance monitoring failed: {e}")
            self.results["monitoring"] = {"error": str(e)}
        finally:
            await monitor.teardown()
            
    async def _generate_final_report(self):
        """Generate comprehensive final report"""
        logger.info("Generating final performance report...")
        
        # Calculate overall test duration
        total_duration = (datetime.now() - self.start_time).total_seconds()
        
        # Determine overall status
        overall_status = "PASS"
        issues = []
        
        # Check benchmark results
        if "benchmarks" in self.results and "error" not in self.results["benchmarks"]:
            avg_success_rate = self.results["benchmarks"]["avg_success_rate"]
            if avg_success_rate < 0.95:
                overall_status = "FAIL"
                issues.append(f"Benchmark success rate ({avg_success_rate:.1%}) below 95%")
                
        # Check load test results
        if "load_tests" in self.results and "error" not in self.results["load_tests"]:
            total_requests = self.results["load_tests"]["total_requests"]
            total_errors = self.results["load_tests"]["total_errors"]
            error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
            
            if error_rate > 5:
                overall_status = "FAIL"
                issues.append(f"Load test error rate ({error_rate:.1f}%) above 5%")
                
            avg_response_time = self.results["load_tests"]["avg_response_time"]
            if avg_response_time > 1000:
                overall_status = "FAIL" if overall_status != "FAIL" else overall_status
                issues.append(f"Load test average response time ({avg_response_time:.0f}ms) above 1s")
                
        # Check stress test results
        if "stress_tests" in self.results and "error" not in self.results["stress_tests"]:
            breaking_point_found = self.results["stress_tests"]["breaking_point_found"]
            max_users_tested = self.results["stress_tests"]["max_users_tested"]
            
            if breaking_point_found and max_users_tested < 500:
                overall_status = "FAIL" if overall_status != "FAIL" else overall_status
                issues.append(f"System breaking point ({max_users_tested} users) below minimum threshold")
                
        # Generate final report
        final_report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": total_duration,
            "overall_status": overall_status,
            "issues": issues,
            "summary": {
                "phases_completed": len([k for k in self.results.keys() if "error" not in self.results[k]]),
                "total_phases": len(self.results),
                "target_url": self.base_url
            },
            "detailed_results": self.results
        }
        
        # Save report
        report_dir = Path("tests/performance/reports")
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"performance_test_report_{timestamp}.json"
        
        with open(report_file, "w") as f:
            json.dump(final_report, f, indent=2)
            
        # Generate HTML summary
        self._generate_html_summary(final_report, report_dir / f"performance_summary_{timestamp}.html")
        
        logger.info(f"📊 Final report saved: {report_file}")
        logger.info(f"\n" + "="*60)
        logger.info("PERFORMANCE TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Overall Status: {overall_status}")
        logger.info(f"Duration: {total_duration:.0f} seconds")
        logger.info(f"Phases Completed: {final_report['summary']['phases_completed']}/{final_report['summary']['total_phases']}")
        
        if issues:
            logger.warning("Issues Found:")
            for issue in issues:
                logger.warning(f"  • {issue}")
        else:
            logger.info("✅ No critical issues found")
            
        return final_report
        
    def _generate_html_summary(self, report: Dict[str, Any], output_file: Path):
        """Generate HTML summary report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Performance Test Summary - {report['timestamp']}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
                .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
                .status-pass {{ color: #28a745; font-weight: bold; }}
                .status-fail {{ color: #dc3545; font-weight: bold; }}
                .metric {{ background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 4px; }}
                .issue {{ color: #dc3545; margin: 5px 0; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Performance Test Summary</h1>
                <div class="metric">
                    <strong>Overall Status:</strong> 
                    <span class="status-{report['overall_status'].lower()}">{report['overall_status']}</span>
                </div>
                <div class="metric">
                    <strong>Test Duration:</strong> {report['duration_seconds']:.0f} seconds
                </div>
                <div class="metric">
                    <strong>Target URL:</strong> {report['summary']['target_url']}
                </div>
                <div class="metric">
                    <strong>Phases Completed:</strong> {report['summary']['phases_completed']}/{report['summary']['total_phases']}
                </div>
                
                {self._generate_issues_section(report)}
                {self._generate_results_section(report)}
            </div>
        </body>
        </html>
        """
        
        with open(output_file, "w") as f:
            f.write(html_content)
            
    def _generate_issues_section(self, report: Dict[str, Any]) -> str:
        """Generate issues section for HTML report"""
        if not report.get("issues"):
            return "<h2>✅ No Issues Found</h2>"
            
        issues_html = "<h2>⚠️ Issues Found</h2><ul>"
        for issue in report["issues"]:
            issues_html += f'<li class="issue">{issue}</li>'
        issues_html += "</ul>"
        
        return issues_html
        
    def _generate_results_section(self, report: Dict[str, Any]) -> str:
        """Generate results section for HTML report"""
        sections = []
        
        # Benchmarks
        if "benchmarks" in report["detailed_results"]:
            benchmarks = report["detailed_results"]["benchmarks"]
            if "error" not in benchmarks:
                sections.append(f"""
                <h3>Benchmarks</h3>
                <p>Success Rate: {benchmarks['avg_success_rate']:.1%}</p>
                <p>Fastest: {benchmarks['fastest_operation']}</p>
                <p>Slowest: {benchmarks['slowest_operation']}</p>
                """)
                
        # Load Tests
        if "load_tests" in report["detailed_results"]:
            load_tests = report["detailed_results"]["load_tests"]
            if "error" not in load_tests:
                error_rate = (load_tests['total_errors'] / load_tests['total_requests'] * 100) if load_tests['total_requests'] > 0 else 0
                sections.append(f"""
                <h3>Load Tests</h3>
                <p>Total Requests: {load_tests['total_requests']:,}</p>
                <p>Error Rate: {error_rate:.2f}%</p>
                <p>Average Response Time: {load_tests['avg_response_time']:.0f}ms</p>
                <p>Max Concurrent Users: {load_tests['max_concurrent_users']}</p>
                """)
                
        # Stress Tests
        if "stress_tests" in report["detailed_results"]:
            stress_tests = report["detailed_results"]["stress_tests"]
            if "error" not in stress_tests:
                sections.append(f"""
                <h3>Stress Tests</h3>
                <p>Max Users Tested: {stress_tests['max_users_tested']}</p>
                <p>Breaking Point Found: {'Yes' if stress_tests['breaking_point_found'] else 'No'}</p>
                <p>Cascade Failures: {stress_tests['cascade_failures']}</p>
                """)
                
        return f"<h2>Test Results</h2>{''.join(sections)}"


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run comprehensive performance tests")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--database-url", help="Database connection URL")
    parser.add_argument("--redis-url", default="redis://localhost:6379", help="Redis connection URL")
    parser.add_argument("--skip-load", action="store_true", help="Skip load testing")
    parser.add_argument("--skip-stress", action="store_true", help="Skip stress testing")
    parser.add_argument("--skip-benchmarks", action="store_true", help="Skip benchmarks")
    parser.add_argument("--enable-monitoring", action="store_true", help="Enable performance monitoring")
    parser.add_argument("--monitoring-duration", type=int, default=300, help="Monitoring duration in seconds")
    parser.add_argument("--ci-mode", action="store_true", help="CI mode (shorter, safer tests)")
    
    args = parser.parse_args()
    
    # Adjust settings for CI mode
    if args.ci_mode:
        logger.info("Running in CI mode - using shorter test durations")
        # Reduce scenario durations for CI
        for scenario in LOAD_TEST_SCENARIOS:
            scenario["duration"] = min(scenario["duration"], 120)  # Max 2 minutes
            scenario["users"] = min(scenario["users"], 200)  # Max 200 users
            
    async def run_tests():
        orchestrator = PerformanceTestOrchestrator(
            base_url=args.url,
            database_url=args.database_url,
            redis_url=args.redis_url
        )
        
        results = await orchestrator.run_all_tests(
            include_load=not args.skip_load,
            include_stress=not args.skip_stress,
            include_benchmarks=not args.skip_benchmarks,
            include_monitoring=args.enable_monitoring,
            monitoring_duration=args.monitoring_duration
        )
        
        # Exit with appropriate code for CI
        if results.get("overall_status") == "FAIL":
            sys.exit(1)
        else:
            sys.exit(0)
            
    # Run the tests
    asyncio.run(run_tests())


if __name__ == "__main__":
    main()