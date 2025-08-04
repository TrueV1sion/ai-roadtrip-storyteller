#!/usr/bin/env python3
"""Check all deployed RoadTrip services to find the full production version."""

import requests
import json

services = [
    ("roadtrip-api", "https://roadtrip-api-k2nimm2ira-uc.a.run.app"),
    ("roadtrip-backend-staging", "https://roadtrip-backend-staging-k2nimm2ira-uc.a.run.app"),
    ("roadtrip-mvp (460720)", "https://roadtrip-mvp-k2nimm2ira-uc.a.run.app"),
    ("roadtrip-backend-mvp", "https://roadtrip-backend-mvp-k2nimm2ira-uc.a.run.app"),
    ("roadtrip-api-simple", "https://roadtrip-api-simple-k2nimm2ira-uc.a.run.app"),
]

print("Checking all RoadTrip services for full API functionality...\n")

for name, url in services:
    print(f"{'='*60}")
    print(f"Service: {name}")
    print(f"URL: {url}")
    
    try:
        # Check health
        health_resp = requests.get(f"{url}/health", timeout=5)
        print(f"Health: {health_resp.status_code}")
        
        # Check OpenAPI
        openapi_resp = requests.get(f"{url}/openapi.json", timeout=5)
        if openapi_resp.status_code == 200:
            spec = openapi_resp.json()
            paths = spec.get('paths', {})
            print(f"Total API routes: {len(paths)}")
            
            # Check for key routes
            key_routes = [
                "/api/stories/generate",
                "/api/voice/personalities", 
                "/api/auth/login",
                "/api/maps-proxy/search-nearby",
                "/api/booking/search"
            ]
            
            available_routes = []
            for route in key_routes:
                if route in paths:
                    available_routes.append(route)
            
            if available_routes:
                print(f"Key routes available: {available_routes}")
            elif len(paths) > 5:
                print(f"Sample routes: {list(paths.keys())[:5]}")
        else:
            print(f"OpenAPI: {openapi_resp.status_code}")
            
    except requests.exceptions.Timeout:
        print("Status: TIMEOUT")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    print()

print("\nSummary: Look for services with the most routes - that's likely the full production backend.")