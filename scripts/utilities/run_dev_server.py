#!/usr/bin/env python3
"""
Development server runner for AI Road Trip Storyteller.
Can run without Docker for quick testing.
"""
import os
import sys
import subprocess
import time
from pathlib import Path


def check_docker():
    """Check if Docker is available and running."""
    try:
        result = subprocess.run(['docker', 'info'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_service(host, port):
    """Check if a service is running on given host:port."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        return False


def start_mock_services():
    """Start mock services for development without Docker."""
    print("\n🔧 Starting in mock mode (no Docker required)...")
    
    # Update .env for mock mode
    env_path = Path('.env')
    if env_path.exists():
        content = env_path.read_text()
        if 'USE_MOCK_APIS=false' in content:
            content = content.replace('USE_MOCK_APIS=false', 'USE_MOCK_APIS=true')
            env_path.write_text(content)
            print("✓ Enabled mock APIs in .env")
    
    # Set environment variables for mock mode
    os.environ['USE_MOCK_APIS'] = 'true'
    os.environ['SKIP_DB_CHECK'] = 'true'
    os.environ['MOCK_REDIS'] = 'true'
    
    print("✓ Mock services configured")
    print("\nNote: Running in mock mode with:")
    print("  - In-memory database (SQLite)")
    print("  - Mock Redis cache")
    print("  - Mock external APIs")


def start_docker_services():
    """Start Docker services if available."""
    print("\n🐳 Starting Docker services...")
    
    # Start PostgreSQL and Redis
    result = subprocess.run(['docker-compose', 'up', '-d', 'db', 'redis'], 
                          capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Failed to start Docker services: {result.stderr}")
        return False
    
    print("✓ Docker services started")
    
    # Wait for services
    print("\n⏳ Waiting for services to be ready...")
    max_attempts = 30
    
    for service, port in [('PostgreSQL', 5432), ('Redis', 6379)]:
        attempt = 0
        while attempt < max_attempts:
            if check_service('localhost', port):
                print(f"✓ {service} is ready on port {port}")
                break
            attempt += 1
            time.sleep(1)
            if attempt % 5 == 0:
                print(f"  Still waiting for {service}...")
        else:
            print(f"⚠️  {service} did not start in time")
    
    return True


def run_migrations():
    """Run database migrations."""
    print("\n📊 Running database migrations...")
    
    try:
        result = subprocess.run(['alembic', 'upgrade', 'head'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Migrations completed successfully")
        else:
            print(f"⚠️  Migration warning: {result.stderr}")
    except FileNotFoundError:
        print("⚠️  Alembic not found - skipping migrations")


def start_api_server():
    """Start the FastAPI server."""
    print("\n🚀 Starting API server...")
    print("\n" + "="*60)
    print("API Server starting at: http://localhost:8000")
    print("API Documentation at: http://localhost:8000/docs")
    print("Health Check at: http://localhost:8000/health/detailed")
    print("="*60 + "\n")
    
    # Start uvicorn
    try:
        subprocess.run([
            sys.executable, '-m', 'uvicorn',
            'backend.app.main:app',
            '--reload',
            '--host', '0.0.0.0',
            '--port', '8000'
        ])
    except KeyboardInterrupt:
        print("\n\n✋ Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server error: {e}")


def main():
    """Main entry point."""
    print("="*60)
    print("🚗 AI Road Trip Storyteller - Development Server")
    print("="*60)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    
    # Check if .env exists
    if not Path('.env').exists():
        print("❌ .env file not found")
        print("Please create one from .env.template or run configure_production.py")
        sys.exit(1)
    
    # Check Docker availability
    docker_available = check_docker()
    
    if docker_available:
        print("✓ Docker is available")
        use_docker = input("\nUse Docker for PostgreSQL and Redis? (Y/n): ").lower() != 'n'
        
        if use_docker:
            if start_docker_services():
                run_migrations()
            else:
                print("\n⚠️  Falling back to mock mode")
                start_mock_services()
        else:
            start_mock_services()
    else:
        print("⚠️  Docker not available - using mock mode")
        start_mock_services()
    
    # Install dependencies if needed
    try:
        import fastapi
        import uvicorn
    except ImportError:
        print("\n📦 Installing required dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
    
    # Start the API server
    try:
        start_api_server()
    except Exception as e:
        print(f"\n❌ Failed to start server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()