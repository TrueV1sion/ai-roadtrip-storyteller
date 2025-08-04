#!/usr/bin/env python3
"""Check all RoadTrip deployments across Google Cloud."""

import requests
import json

deployments = [
    # roadtrip-mvp project (original)
    ("roadtrip-mvp", "https://roadtrip-mvp-792001900150.us-central1.run.app"),
    
    # roadtrip-460720 project (newer)
    ("roadtrip-api", "https://roadtrip-api-k2nimm2ira-uc.a.run.app"),
    ("roadtrip-backend-staging", "https://roadtrip-backend-staging-k2nimm2ira-uc.a.run.app"),
    ("roadtrip-mvp (460720)", "https://roadtrip-mvp-k2nimm2ira-uc.a.run.app"),
]

print("Checking all RoadTrip deployments...\n")

for name, url in deployments:
    print(f"{'='*60}")
    print(f"Service: {name}")
    print(f"URL: {url}")
    
    # Test basic endpoints
    endpoints = ["/", "/health", "/docs", "/api/stories/generate"]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{url}{endpoint}", timeout=5)
            print(f"  {endpoint}: {response.status_code}")
            
            # If it's health endpoint and successful, show the response
            if endpoint == "/health" and response.status_code == 200:
                try:
                    data = response.json()
                    print(f"    Services: {data.get('services', {})}")
                except:
                    pass
                    
            # If it's docs and successful, check how many routes
            if endpoint == "/docs" and response.status_code == 200:
                try:
                    # Get OpenAPI spec
                    spec_response = requests.get(f"{url}/openapi.json", timeout=5)
                    if spec_response.status_code == 200:
                        spec = spec_response.json()
                        routes = len(spec.get('paths', {}))
                        print(f"    Total routes: {routes}")
                except:
                    pass
                    
        except Exception as e:
            print(f"  {endpoint}: ERROR - {str(e)}")
    
    print()

print("\nRecommendation: Use the deployment with the most routes available.")