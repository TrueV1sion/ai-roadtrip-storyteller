#!/bin/bash
# honest_cleanup.sh - The REAL cleanup script for RoadTrip

echo "🔍 Starting HONEST RoadTrip cleanup..."
echo "This will reduce the codebase to focus on FUN road trip features!"
echo ""

# Count current files
BEFORE_COUNT=$(find . -type f | wc -l)
echo "Files before cleanup: $BEFORE_COUNT"

# Create archive structure if not exists
echo "📦 Creating archive structure..."
mkdir -p archive/{future-expansion,failed-attempts,documentation-graveyard}
mkdir -p archive/future-expansion/{monetization,enterprise,transport-modes,infrastructure,advanced-ai}
mkdir -p archive/failed-attempts/{mvp-iterations,deployment-scripts,old-dockerfiles}
mkdir -p archive/documentation-graveyard/{unrealistic-plans,complex-guides}

# Archive future features
echo "📦 Archiving future features..."

# Transport modes (airport, rideshare)
find backend/app -name "*airport*" -o -name "*rideshare*" | while read f; do
    mv "$f" archive/future-expansion/transport-modes/ 2>/dev/null
done

# Enterprise security
find backend/app -name "*security_*" -o -name "*intrusion*" -o -name "*threat*" -o -name "*two_factor*" | while read f; do
    mv "$f" archive/future-expansion/enterprise/ 2>/dev/null
done

# Revenue and monetization
find backend/app -name "*revenue*" -o -name "*commission*" -o -name "*payment*" -o -name "*booking*" | while read f; do
    mv "$f" archive/future-expansion/monetization/ 2>/dev/null
done

# Archive failed attempts
echo "📦 Archiving failed attempts..."

# MVP iterations
find . -name "*mvp*" -type f | while read f; do
    mv "$f" archive/failed-attempts/mvp-iterations/ 2>/dev/null
done

# Failed deployment scripts
find . -name "deploy*fixed*" -o -name "fix_*" -o -name "emergency_*" | while read f; do
    mv "$f" archive/failed-attempts/deployment-scripts/ 2>/dev/null
done

# Old Dockerfiles
find . -name "Dockerfile.*" | while read f; do
    mv "$f" archive/failed-attempts/old-dockerfiles/ 2>/dev/null
done

# Delete junk files
echo "🗑️ Deleting junk files..."
find . -name "*.log" -delete 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null
find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null
find . -name "test_*.ps1" -delete 2>/dev/null
find . -name "check_*.ps1" -delete 2>/dev/null

# Clean up backend routes - keep only entertainment
echo "🎮 Keeping only entertainment routes..."
KEEP_ROUTES="auth.py health.py story.py ai_stories.py games.py spatial_audio.py ar.py interactive_narrative.py voice_personality.py tts.py serendipity.py side_quest.py spotify.py navigation.py user.py"

cd backend/app/routes 2>/dev/null
for route in *.py; do
    if [[ ! " $KEEP_ROUTES " =~ " $route " ]] && [[ "$route" != "__init__.py" ]]; then
        echo "  Archiving route: $route"
        mv "$route" ../../../archive/future-expansion/advanced-ai/ 2>/dev/null
    fi
done
cd - > /dev/null

# Clean up backend services - keep only core
echo "🎯 Keeping only core services..."
KEEP_SERVICES="game_engine.py story_generation_agent.py voice_personalities.py spatial_audio_engine.py ar booking_agent.py navigation_agent.py master_orchestration_agent.py"

cd backend/app/services 2>/dev/null
for service in *.py; do
    if [[ ! " $KEEP_SERVICES " =~ " $service " ]] && [[ "$service" != "__init__.py" ]] && [[ ! -d "$service" ]]; then
        echo "  Archiving service: $service"
        mv "$service" ../../../archive/future-expansion/advanced-ai/ 2>/dev/null
    fi
done
cd - > /dev/null

# Simplify requirements
echo "📋 Simplifying requirements..."
if [ -f requirements.txt ] && [ -f requirements.prod.txt ]; then
    cp requirements.txt requirements.backup.txt
    # Keep only essential packages
    cat > requirements.txt << 'EOF'
# Core
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9
asyncpg==0.29.0

# AI & ML
google-cloud-aiplatform==1.38.1
google-cloud-texttospeech==2.14.1
google-cloud-speech==2.21.0
langchain==0.0.340
langchain-google-vertexai==0.0.3

# Auth & Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Caching
redis==5.0.1
hiredis==2.2.3

# HTTP & API
httpx==0.25.2
aiohttp==3.9.1

# Utils
pendulum==2.1.2
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0
EOF
fi

# Archive complex documentation
echo "📚 Archiving complex documentation..."
find docs -name "*PRODUCTION*" -o -name "*DEPLOYMENT*" -o -name "*LAUNCH*" | while read f; do
    mv "$f" archive/documentation-graveyard/unrealistic-plans/ 2>/dev/null
done

# Create simple documentation
echo "📝 Creating honest documentation..."
cat > README_HONEST.md << 'EOF'
# AI Road Trip Storyteller 🚗✨

A fun road trip companion that makes drives entertaining through AI storytelling, games, and immersive audio.

## What It Actually Does

- **AI Storytelling**: Generates contextual stories based on your location
- **Voice Personalities**: 20+ fun characters (pirates, tour guides, comedians)
- **Road Trip Games**: Trivia, scavenger hunts, "I Spy"
- **Spatial Audio**: 3D sound experiences
- **AR Features**: Point camera at landmarks for info
- **Music Integration**: Spotify support

## Tech Stack (Simple)

- Backend: FastAPI + PostgreSQL
- AI: Google Vertex AI (Gemini)
- Mobile: React Native
- Deploy: Docker → Google Cloud Run

## Quick Start

```bash
# Backend
docker-compose up -d
cd backend
uvicorn app.main:app --reload

# Mobile
cd mobile
npm install
npm start
```

## Current Status

- Core features work
- Needs testing and polish
- Ready for friends & family beta

That's it! No enterprise monitoring, no complex infrastructure, just fun road trip features.
EOF

# Count after cleanup
AFTER_COUNT=$(find . -type f | wc -l)
echo ""
echo "✅ Cleanup complete!"
echo "Files before: $BEFORE_COUNT"
echo "Files after: $AFTER_COUNT"
echo "Removed: $((BEFORE_COUNT - AFTER_COUNT)) files"
echo ""
echo "🎯 Next steps:"
echo "1. Review remaining files in backend/app/routes and backend/app/services"
echo "2. Test core entertainment features"
echo "3. Deploy simple version to Cloud Run"
echo "4. Ship to beta users!"
echo ""
echo "Focus on making road trips FUN, not building enterprise software! 🎮🎵🚗"