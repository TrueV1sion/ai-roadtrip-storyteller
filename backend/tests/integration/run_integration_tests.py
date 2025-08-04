#!/usr/bin/env python3
"""
Run integration tests and generate a comprehensive report
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from test_all_integrations import IntegrationTestSuite


async def main():
    """Run all integration tests"""
    
    print("RoadTrip Application - Integration Test Suite")
    print("=" * 60)
    print("Testing all integrations between components and services...")
    print()
    
    # Create test suite
    suite = IntegrationTestSuite()
    
    # Run all tests
    report = await suite.run_all_tests()
    
    # Save report
    report_path = Path(__file__).parent / "integration_test_report.md"
    with open(report_path, "w") as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_path}")
    
    # Check for failures
    total_errors = len(suite.results.errors)
    if total_errors > 0:
        print(f"\n❌ Integration tests completed with {total_errors} errors")
        return 1
    else:
        print("\n✅ All integration tests passed!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())