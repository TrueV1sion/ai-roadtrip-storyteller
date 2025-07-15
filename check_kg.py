#!/usr/bin/env python3
"""Check if Knowledge Graph is being used properly"""
import sys
import httpx

def check_kg():
    try:
        response = httpx.get("http://localhost:8000/api/health", timeout=2)
        if response.status_code == 200:
            stats = response.json()["stats"]
            print(f"✅ Knowledge Graph is running")
            print(f"📊 Indexed: {stats['indexed_files']} files")
            print(f"🔗 Graph: {stats['nodes']} nodes, {stats['links']} links")
            return True
    except:
        pass
    
    print("❌ Knowledge Graph is NOT running!")
    print("Start it with: cd knowledge_graph && python3 blazing_server.py")
    return False

if __name__ == "__main__":
    if not check_kg():
        sys.exit(1)
