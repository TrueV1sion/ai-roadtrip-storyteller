#!/usr/bin/env python3
"""
Test script to verify health endpoints are properly implemented.
Run this with: python test_health_endpoints.py
"""

import requests
import json
import sys
from typing import Dict, Any


def test_endpoint(url: str, expected_status: int = 200) -> Dict[str, Any]:
    """Test a single endpoint and return results."""
    try:
        response = requests.get(url, timeout=5)
        return {
            "url": url,
            "status_code": response.status_code,
            "success": response.status_code == expected_status,
            "data": response.json() if response.status_code == 200 else None,
            "error": None
        }
    except requests.exceptions.ConnectionError:
        return {
            "url": url,
            "status_code": None,
            "success": False,
            "data": None,
            "error": "Connection refused - is the server running?"
        }
    except Exception as e:
        return {
            "url": url,
            "status_code": None,
            "success": False,
            "data": None,
            "error": str(e)
        }


def main():
    """Test all health endpoints."""
    base_url = "http://localhost:8000"
    
    # Health endpoints to test
    endpoints = [
        "/health/",
        "/health/live",
        "/health/ready",
        "/health/detailed",
        "/health/metrics"
    ]
    
    print("Testing Health Endpoints")
    print("=" * 50)
    print(f"Base URL: {base_url}")
    print()
    
    all_success = True
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        result = test_endpoint(url)
        
        # Print results
        status_symbol = "✓" if result["success"] else "✗"
        print(f"{status_symbol} {endpoint}")
        print(f"  Status: {result['status_code']}")
        
        if result["error"]:
            print(f"  Error: {result['error']}")
            all_success = False
        elif result["data"]:
            # Print key information from response
            data = result["data"]
            if isinstance(data, dict):
                if "status" in data:
                    print(f"  Response Status: {data['status']}")
                if "timestamp" in data:
                    print(f"  Timestamp: {data['timestamp']}")
                if "version" in data:
                    print(f"  Version: {data['version']}")
                if "checks" in data:
                    print(f"  Health Checks: {len(data['checks'])} components")
            elif endpoint == "/health/metrics":
                # Metrics endpoint returns plain text
                print(f"  Metrics: Prometheus format (text/plain)")
        
        print()
    
    # Summary
    print("=" * 50)
    if all_success:
        print("✓ All health endpoints are working correctly!")
        return 0
    else:
        print("✗ Some health endpoints failed. Please check the server.")
        return 1


if __name__ == "__main__":
    sys.exit(main())