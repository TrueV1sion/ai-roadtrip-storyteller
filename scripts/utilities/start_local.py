#!/usr/bin/env python3
"""
Start local development environment for AI Road Trip Storyteller.
Works with or without Docker.
"""
import os
import sys
import subprocess
import time


def print_banner():
    """Print startup banner."""
    print("\n" + "="*60)
    print("🚗 AI Road Trip Storyteller - Local Development")
    print("="*60 + "\n")


def check_docker():
    """Check if Docker is running."""
    try:
        result = subprocess.run(['docker', 'info'], capture_output=True)
        return result.returncode == 0
    except Exception as e:
        return False


def setup_environment():
    """Setup environment variables for local development."""
    # Set development mode
    os.environ['ENVIRONMENT'] = 'development'
    os.environ['DEBUG'] = 'true'
    
    # Check if we have Docker
    if not check_docker():
        print("⚠️  Docker not available - enabling mock mode")
        os.environ['MOCK_REDIS'] = 'true'
        os.environ['USE_MOCK_APIS'] = 'true'
        os.environ['SKIP_DB_CHECK'] = 'true'
        
        # Use SQLite for development
        os.environ['DATABASE_URL'] = 'sqlite:///./roadtrip_dev.db'
        
        print("✓ Mock mode enabled:")
        print("  - Using SQLite database")
        print("  - Using in-memory cache")
        print("  - Mock external APIs")
    else:
        print("✓ Docker is available")
        
        # Try to start services
        print("\n🐳 Starting Docker services...")
        result = subprocess.run(['docker-compose', 'up', '-d', 'db', 'redis'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Docker services started")
            print("  - PostgreSQL on port 5432")
            print("  - Redis on port 6379")
            
            # Wait a moment for services to be ready
            print("\n⏳ Waiting for services...")
            time.sleep(3)
        else:
            print("⚠️  Could not start Docker services")
            print("  Falling back to mock mode")
            os.environ['MOCK_REDIS'] = 'true'
            os.environ['USE_MOCK_APIS'] = 'true'


def check_dependencies():
    """Check if Python dependencies are installed."""
    try:
        import fastapi
        import uvicorn
        return True
    except ImportError:
        return False


def install_dependencies():
    """Install required dependencies."""
    print("\n📦 Installing dependencies...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])


def start_server():
    """Start the FastAPI development server."""
    print("\n🚀 Starting development server...")
    print("\n" + "-"*60)
    print("Server URLs:")
    print("  API:     http://localhost:8000")
    print("  Docs:    http://localhost:8000/docs")
    print("  Health:  http://localhost:8000/health/detailed")
    print("-"*60 + "\n")
    
    # Start uvicorn
    subprocess.run([
        sys.executable, '-m', 'uvicorn',
        'backend.app.main:app',
        '--reload',
        '--host', '0.0.0.0',
        '--port', '8000',
        '--log-level', 'info'
    ])


def main():
    """Main entry point."""
    print_banner()
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    # Setup environment
    setup_environment()
    
    # Check and install dependencies
    if not check_dependencies():
        install_dependencies()
    
    # Start the server
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n\n✋ Server stopped")
        
        # Cleanup Docker if used
        if check_docker() and os.getenv('MOCK_REDIS') != 'true':
            print("\n🧹 Stopping Docker services...")
            subprocess.run(['docker-compose', 'down'], capture_output=True)
            print("✓ Docker services stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()