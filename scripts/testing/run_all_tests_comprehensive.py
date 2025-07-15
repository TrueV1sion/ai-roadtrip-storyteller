#!/usr/bin/env python3
"""
Comprehensive Test Runner for AI Road Trip Storyteller
Runs all types of tests including unit, integration, and API tests
"""

import asyncio
import subprocess
import sys
import time
import json
from pathlib import Path
from typing import Dict, List, Any
import concurrent.futures


class ComprehensiveTestRunner:
    """Runs all test suites and generates a comprehensive report."""
    
    def __init__(self):
        self.results = {}
        self.start_time = time.time()
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all test categories."""
        print("🔬 AI Road Trip Storyteller - Comprehensive Test Suite")
        print("=" * 60)
        
        test_categories = [
            ("Unit Tests", self._run_unit_tests),
            ("API Integration Tests", self._run_api_tests),
            ("Database Tests", self._run_database_tests),
            ("End-to-End Tests", self._run_e2e_tests),
            ("Performance Tests", self._run_performance_tests),
            ("Security Tests", self._run_security_tests),
        ]
        
        for category_name, test_function in test_categories:
            print(f"\n📋 Running {category_name}")
            print("-" * 40)
            
            try:
                result = test_function()
                self.results[category_name] = result
                
                if result.get("status") == "passed":
                    print(f"✅ {category_name}: PASSED")
                else:
                    print(f"❌ {category_name}: FAILED")
                    
            except Exception as e:
                print(f"💥 {category_name}: CRASHED - {e}")
                self.results[category_name] = {
                    "status": "crashed",
                    "error": str(e),
                    "tests_run": 0,
                    "tests_passed": 0
                }
        
        # Generate final report
        return self._generate_final_report()
    
    def _run_unit_tests(self) -> Dict[str, Any]:
        """Run unit tests using pytest."""
        try:
            # Run backend unit tests
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/unit/", 
                "-v", 
                "--tb=short",
                "--json-report",
                "--json-report-file=test_results_unit.json"
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            # Parse results
            try:
                with open("test_results_unit.json") as f:
                    pytest_results = json.load(f)
                
                return {
                    "status": "passed" if result.returncode == 0 else "failed",
                    "tests_run": pytest_results.get("summary", {}).get("total", 0),
                    "tests_passed": pytest_results.get("summary", {}).get("passed", 0),
                    "tests_failed": pytest_results.get("summary", {}).get("failed", 0),
                    "duration": pytest_results.get("duration", 0),
                    "output": result.stdout,
                    "errors": result.stderr
                }
            except FileNotFoundError:
                # Fallback if JSON report not available
                return {
                    "status": "passed" if result.returncode == 0 else "failed",
                    "output": result.stdout,
                    "errors": result.stderr
                }
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _run_api_tests(self) -> Dict[str, Any]:
        """Run simple API tests."""
        try:
            result = subprocess.run([
                sys.executable, "test_apis_simple.py"
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "output": result.stdout,
                "errors": result.stderr
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _run_database_tests(self) -> Dict[str, Any]:
        """Run database-specific tests."""
        try:
            # Run database migration check
            result = subprocess.run([
                sys.executable, "-m", "pytest", 
                "tests/integration/test_database.py", 
                "-v"
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "output": result.stdout,
                "errors": result.stderr
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _run_e2e_tests(self) -> Dict[str, Any]:
        """Run end-to-end tests."""
        try:
            result = subprocess.run([
                sys.executable, "test_comprehensive_integration.py"
            ], capture_output=True, text=True, cwd=Path.cwd())
            
            # Try to load detailed results
            try:
                with open("test_results_comprehensive.json") as f:
                    detailed_results = json.load(f)
                
                return {
                    "status": "passed" if result.returncode == 0 else "failed",
                    "summary": detailed_results.get("summary", {}),
                    "output": result.stdout,
                    "errors": result.stderr
                }
            except FileNotFoundError:
                return {
                    "status": "passed" if result.returncode == 0 else "failed",
                    "output": result.stdout,
                    "errors": result.stderr
                }
                
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _run_performance_tests(self) -> Dict[str, Any]:
        """Run performance tests."""
        try:
            # Simple performance check - load test the health endpoint
            result = subprocess.run([
                sys.executable, "-c", """
import asyncio
import httpx
import time

async def load_test():
    async with httpx.AsyncClient() as client:
        start_time = time.time()
        tasks = []
        
        for _ in range(10):  # 10 concurrent requests
            tasks.append(client.get('http://localhost:8000/health'))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
        
        print(f"Performance Test: {successful}/10 requests successful in {end_time - start_time:.2f}s")
        return successful == 10

success = asyncio.run(load_test())
exit(0 if success else 1)
"""
            ], capture_output=True, text=True)
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "output": result.stdout,
                "errors": result.stderr
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _run_security_tests(self) -> Dict[str, Any]:
        """Run basic security tests."""
        try:
            # Simple security checks
            result = subprocess.run([
                sys.executable, "-c", """
import httpx
import asyncio

async def security_test():
    async with httpx.AsyncClient() as client:
        tests_passed = 0
        total_tests = 3
        
        # Test 1: Check for security headers
        try:
            response = await client.get('http://localhost:8000/health')
            if 'x-frame-options' in response.headers:
                tests_passed += 1
                print("✓ Security headers present")
            else:
                print("✗ Security headers missing")
        except:
            print("✗ Security headers test failed")
        
        # Test 2: Check that sensitive endpoints require auth
        try:
            response = await client.get('http://localhost:8000/api/users/me')
            if response.status_code == 401:
                tests_passed += 1
                print("✓ Protected endpoints require authentication")
            else:
                print("✗ Protected endpoints accessible without auth")
        except:
            print("✗ Auth test failed")
        
        # Test 3: Check for CORS headers
        try:
            response = await client.options('http://localhost:8000/health')
            if 'access-control-allow-origin' in response.headers:
                tests_passed += 1
                print("✓ CORS configured")
            else:
                print("✗ CORS not configured")
        except:
            print("✗ CORS test failed")
        
        print(f"Security tests: {tests_passed}/{total_tests} passed")
        return tests_passed == total_tests

success = asyncio.run(security_test())
exit(0 if success else 1)
"""
            ], capture_output=True, text=True)
            
            return {
                "status": "passed" if result.returncode == 0 else "failed",
                "output": result.stdout,
                "errors": result.stderr
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        total_time = time.time() - self.start_time
        
        # Calculate overall statistics
        categories_passed = sum(1 for r in self.results.values() if r.get("status") == "passed")
        total_categories = len(self.results)
        
        # Create summary
        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_time_seconds": round(total_time, 2),
            "categories": {
                "total": total_categories,
                "passed": categories_passed,
                "failed": total_categories - categories_passed,
                "success_rate": round(categories_passed / total_categories * 100, 1) if total_categories > 0 else 0
            },
            "results_by_category": self.results
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 60)
        print(f"Test Categories: {total_categories}")
        print(f"Categories Passed: {categories_passed}")
        print(f"Categories Failed: {total_categories - categories_passed}")
        print(f"Overall Success Rate: {summary['categories']['success_rate']}%")
        print(f"Total Time: {summary['total_time_seconds']} seconds")
        
        # Show failed categories
        failed_categories = [name for name, result in self.results.items() if result.get("status") != "passed"]
        if failed_categories:
            print(f"\n❌ FAILED CATEGORIES:")
            for category in failed_categories:
                print(f"  - {category}")
        
        # Save detailed report
        report_file = Path("test_results_comprehensive_report.json")
        with open(report_file, "w") as f:
            json.dump(summary, f, indent=2, default=str)
        
        print(f"\n📄 Detailed report saved to: {report_file}")
        
        return summary


def main():
    """Run comprehensive test suite."""
    runner = ComprehensiveTestRunner()
    
    try:
        results = runner.run_all_tests()
        
        # Determine exit code based on success rate
        success_rate = results["categories"]["success_rate"]
        
        if success_rate >= 80:
            print("\n🎉 COMPREHENSIVE TESTS PASSED!")
            return 0
        elif success_rate >= 60:
            print(f"\n⚠️  TESTS PARTIALLY PASSED ({success_rate}% success rate)")
            return 1
        else:
            print(f"\n❌ TESTS FAILED ({success_rate}% success rate)")
            return 1
            
    except Exception as e:
        print(f"\n💥 Test runner crashed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)