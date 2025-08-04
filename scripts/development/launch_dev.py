#!/usr/bin/env python3
"""
AI Road Trip Storyteller - Development Environment Launcher
Simplified launcher that works without Docker or complex dependencies
"""

import os
import sys
import subprocess
import time
import signal
import json
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def kill_process_on_port(port):
    """Kill any process using the specified port"""
    try:
        result = subprocess.run(f"lsof -ti :{port}", shell=True, capture_output=True, text=True)
        if result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                subprocess.run(f"kill -9 {pid}", shell=True)
            print_success(f"Killed process on port {port}")
            time.sleep(1)
    except Exception as e:
        pass

def check_port_available(port):
    """Check if a port is available"""
    result = subprocess.run(f"lsof -i :{port}", shell=True, capture_output=True)
    return result.returncode != 0

def create_minimal_env():
    """Create minimal .env file if not exists"""
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write("""# Minimal configuration for development
ENVIRONMENT=development
SECRET_KEY=dev-secret-key-only-for-local-development
DATABASE_URL=sqlite:///./roadtrip_dev.db
REDIS_URL=memory://
GOOGLE_AI_PROJECT_ID=demo-mode
MOCK_AI_RESPONSES=true
LOG_LEVEL=INFO
JWT_SECRET_KEY=dev-jwt-secret
ALLOWED_HOSTS=localhost,127.0.0.1
""")
        print_success("Created minimal .env file")

def setup_sqlite_db():
    """Setup SQLite database for development"""
    os.chdir('backend')
    
    # Create simple init script
    init_script = """
import sys
sys.path.insert(0, '.')
from app.core.database import engine
from app.models import Base

# Create all tables
Base.metadata.create_all(bind=engine)
print("Database initialized successfully!")
"""
    
    with open('init_db.py', 'w') as f:
        f.write(init_script)
    
    result = subprocess.run([sys.executable, 'init_db.py'], capture_output=True, text=True)
    if result.returncode == 0:
        print_success("SQLite database initialized")
    else:
        print_warning("Database initialization skipped (may already exist)")
    
    os.remove('init_db.py')
    os.chdir('..')

def start_knowledge_graph():
    """Start the Knowledge Graph service"""
    if not check_port_available(8001):
        print_info("Knowledge Graph already running on port 8001")
        return None
    
    os.chdir('knowledge_graph')
    process = subprocess.Popen([sys.executable, 'blazing_server.py'], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
    os.chdir('..')
    
    # Wait for it to start
    for i in range(10):
        time.sleep(1)
        try:
            import urllib.request
            response = urllib.request.urlopen('http://localhost:8001/api/health')
            if response.status == 200:
                print_success("Knowledge Graph started on port 8001")
                return process
        except Exception as e:
            pass
    
    print_warning("Knowledge Graph may not have started properly")
    return process

def start_backend():
    """Start the backend API server"""
    # Kill existing process on port 8000
    kill_process_on_port(8000)
    
    os.chdir('backend')
    
    # Start with minimal dependencies
    env = os.environ.copy()
    env['MOCK_AI_RESPONSES'] = 'true'
    env['USE_SQLITE'] = 'true'
    
    process = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app.main:app', '--reload', '--host', '0.0.0.0', '--port', '8000'],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    os.chdir('..')
    
    # Wait for it to start
    for i in range(15):
        time.sleep(1)
        try:
            import urllib.request
            response = urllib.request.urlopen('http://localhost:8000/docs')
            if response.status == 200:
                print_success("Backend API started on port 8000")
                return process
        except Exception as e:
            pass
    
    print_error("Backend API failed to start")
    return None

def main():
    print(f"\n{BLUE}🚗 AI Road Trip Storyteller - Development Environment{RESET}")
    print("=" * 55)
    
    # Create minimal environment
    create_minimal_env()
    
    # Setup database
    print("\nSetting up database...")
    setup_sqlite_db()
    
    # Start services
    processes = []
    
    print("\nStarting services...")
    
    # Start Knowledge Graph
    kg_process = start_knowledge_graph()
    if kg_process:
        processes.append(kg_process)
    
    # Start Backend
    backend_process = start_backend()
    if backend_process:
        processes.append(backend_process)
    else:
        print_error("Failed to start backend. Check logs.")
        return
    
    # Display access information
    print("\n" + "=" * 55)
    print_success("Development environment is ready!\n")
    
    print("Access points:")
    print(f"  • API Documentation: {BLUE}http://localhost:8000/docs{RESET}")
    print(f"  • API Health Check:  {BLUE}http://localhost:8000/health{RESET}")
    print(f"  • Knowledge Graph:   {BLUE}http://localhost:8001{RESET}")
    
    print("\nFeatures available in this mode:")
    print("  ✓ Browse API documentation")
    print("  ✓ Test API endpoints")
    print("  ✓ Mock AI responses (no API keys needed)")
    print("  ✓ SQLite database (no PostgreSQL needed)")
    print("  ✓ In-memory caching (no Redis needed)")
    
    print("\nTo test the mobile app:")
    print(f"  1. cd mobile")
    print(f"  2. npm install --legacy-peer-deps")
    print(f"  3. npm start")
    
    print("\n" + "=" * 55)
    print(f"{YELLOW}Press Ctrl+C to stop all services...{RESET}\n")
    
    # Open browser
    try:
        import webbrowser
        webbrowser.open('http://localhost:8000/docs')
    except Exception as e:
        pass
    
    # Handle shutdown
    def signal_handler(sig, frame):
        print(f"\n{YELLOW}Shutting down services...{RESET}")
        for p in processes:
            if p:
                p.terminate()
        print_success("All services stopped")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    main()