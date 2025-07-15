#!/bin/bash

# AI Road Trip Storyteller - Development Setup Script
# This script sets up the development environment

echo "🚀 Setting up AI Road Trip Storyteller development environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install backend dependencies
echo "📚 Installing backend dependencies..."
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install additional dependencies for new features
echo "🆕 Installing new feature dependencies..."
pip install openai google-cloud-aiplatform google-cloud-texttospeech google-cloud-speech
pip install redis prometheus_client httpx tenacity
pip install pytest pytest-asyncio pytest-cov pytest-mock

# Set up environment variables
echo "🔑 Setting up environment variables..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "📝 Created .env file from example. Please configure your API keys."
fi

# Run database migrations
echo "🗄️ Running database migrations..."
alembic upgrade head

# Install mobile dependencies
echo "📱 Installing mobile dependencies..."
cd mobile
npm install
cd ..

echo "✅ Development environment setup complete!"
echo ""
echo "Next steps:"
echo "1. Configure your API keys in .env file"
echo "2. Start the backend: uvicorn backend.app.main:app --reload"
echo "3. Start the mobile app: cd mobile && npm start"
echo ""
echo "🎯 Ready to implement Phase 1 features!"