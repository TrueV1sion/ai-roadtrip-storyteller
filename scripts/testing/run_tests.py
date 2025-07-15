#!/usr/bin/env python3
"""Test runner script for the Road Trip application."""

import sys
import subprocess
import argparse
from pathlib import Path


def run_backend_tests(test_type=None, verbose=False):
    """Run backend Python tests."""
    print("\n🧪 Running Backend Tests...")
    
    cmd = ["pytest"]
    
    if test_type:
        if test_type == "unit":
            cmd.append("tests/unit")
        elif test_type == "integration":
            cmd.append("tests/integration")
        elif test_type == "e2e":
            cmd.append("tests/e2e")
        elif test_type == "booking":
            cmd.extend(["-m", "booking"])
        elif test_type == "voice":
            cmd.extend(["-m", "voice"])
        elif test_type == "orchestration":
            cmd.extend(["-m", "orchestration"])
        elif test_type == "commission":
            cmd.extend(["-m", "commission"])
        elif test_type == "analytics":
            cmd.extend(["-m", "analytics"])
    
    if verbose:
        cmd.append("-vv")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    return result.returncode


def run_mobile_tests(verbose=False):
    """Run mobile React Native tests."""
    print("\n📱 Running Mobile Tests...")
    
    cmd = ["npm", "test"]
    if verbose:
        cmd.append("--verbose")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent / "mobile")
    return result.returncode


def run_specific_component_tests():
    """Run tests for new components."""
    print("\n🎯 Running Specific Component Tests...")
    
    # Backend component tests
    backend_tests = [
        "tests/unit/test_master_orchestration_agent.py",
        "tests/unit/test_booking_agent.py",
        "tests/unit/test_commission_calculator.py",
        "tests/unit/test_revenue_analytics.py",
        "tests/integration/test_booking_flows.py",
        "tests/integration/test_api_client_error_handling.py",
        "tests/e2e/test_voice_interactions.py"
    ]
    
    for test in backend_tests:
        print(f"\n  Running {test}...")
        result = subprocess.run(["pytest", test, "-v"], cwd=Path(__file__).parent)
        if result.returncode != 0:
            print(f"  ❌ {test} failed!")
            return 1
        print(f"  ✅ {test} passed!")
    
    # Mobile component tests
    mobile_tests = [
        "src/components/__tests__/BookingFlow.test.tsx",
        "src/components/__tests__/VoiceAssistant.test.tsx"
    ]
    
    for test in mobile_tests:
        print(f"\n  Running mobile {test}...")
        result = subprocess.run(
            ["npm", "test", test], 
            cwd=Path(__file__).parent / "mobile"
        )
        if result.returncode != 0:
            print(f"  ❌ {test} failed!")
            return 1
        print(f"  ✅ {test} passed!")
    
    return 0


def run_coverage_report():
    """Generate test coverage report."""
    print("\n📊 Generating Coverage Report...")
    
    cmd = [
        "pytest",
        "--cov=backend",
        "--cov-report=html",
        "--cov-report=term-missing",
        "tests/"
    ]
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent)
    
    if result.returncode == 0:
        print("\n✅ Coverage report generated at htmlcov/index.html")
    
    return result.returncode


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Run Road Trip application tests")
    parser.add_argument(
        "--type",
        choices=["all", "backend", "mobile", "unit", "integration", "e2e", 
                 "booking", "voice", "orchestration", "commission", "analytics",
                 "specific"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    print("""
    🚗 Road Trip Application Test Suite
    ==================================
    """)
    
    exit_code = 0
    
    if args.type == "all":
        # Run all tests
        backend_code = run_backend_tests(verbose=args.verbose)
        mobile_code = run_mobile_tests(verbose=args.verbose)
        exit_code = backend_code or mobile_code
    
    elif args.type == "backend":
        exit_code = run_backend_tests(verbose=args.verbose)
    
    elif args.type == "mobile":
        exit_code = run_mobile_tests(verbose=args.verbose)
    
    elif args.type == "specific":
        exit_code = run_specific_component_tests()
    
    elif args.type in ["unit", "integration", "e2e", "booking", "voice", 
                       "orchestration", "commission", "analytics"]:
        exit_code = run_backend_tests(test_type=args.type, verbose=args.verbose)
    
    if args.coverage and exit_code == 0:
        coverage_code = run_coverage_report()
        exit_code = exit_code or coverage_code
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print("\n❌ Some tests failed!")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())