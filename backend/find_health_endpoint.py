#!/usr/bin/env python3
"""
Find the health endpoint that's checking google_maps and gemini_ai services.
"""
import os
import re
from pathlib import Path

def search_for_health_endpoint():
    """Search for health endpoints that might be testing these services."""
    backend_dir = Path(__file__).parent
    
    patterns = [
        r'["\'](google_maps|gemini_ai)["\'].*:.*["\'](healthy|degraded|unhealthy)',
        r'services.*\[.*["\'](google_maps|gemini_ai)["\'].*\]',
        r'check.*google.*maps|check.*gemini.*ai',
        r'test.*google.*maps|test.*gemini.*ai'
    ]
    
    print("Searching for health endpoints with google_maps and gemini_ai...\n")
    
    for root, dirs, files in os.walk(backend_dir):
        # Skip __pycache__ directories
        if '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    # Check if this might be a health endpoint
                    if 'health' in content.lower() and any(svc in content for svc in ['google_maps', 'gemini_ai']):
                        print(f"Found potential match in: {filepath}")
                        
                        # Show relevant lines
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if 'google_maps' in line or 'gemini_ai' in line:
                                start = max(0, i - 3)
                                end = min(len(lines), i + 4)
                                print(f"\n  Lines {start+1}-{end+1}:")
                                for j in range(start, end):
                                    prefix = ">>>" if j == i else "   "
                                    print(f"  {prefix} {j+1}: {lines[j]}")
                        print()
                        
                except Exception as e:
                    pass

def search_for_service_checks():
    """Search for where services are being tested."""
    backend_dir = Path(__file__).parent
    
    print("\nSearching for service health checks...\n")
    
    # Look for files that might contain service checks
    for root, dirs, files in os.walk(backend_dir / "app"):
        if '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Look for service check patterns
                    if re.search(r'def.*check.*service|async def.*test.*service|service.*health.*check', content, re.IGNORECASE):
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if re.search(r'def.*check.*service|async def.*test.*service', line, re.IGNORECASE):
                                print(f"\nFound service check in {filepath}:")
                                print(f"  Line {i+1}: {line.strip()}")
                                
                except Exception as e:
                    pass

if __name__ == "__main__":
    search_for_health_endpoint()
    search_for_service_checks()