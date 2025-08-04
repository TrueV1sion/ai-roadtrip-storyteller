# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🚨 MANDATORY: Knowledge Graph Integration 🚨

**CRITICAL: The Knowledge Graph MUST be consulted before ANY code operation.**

### Starting the Knowledge Graph:
```bash
# Check if running
curl http://localhost:8000/api/health

# If not running, start it:
cd knowledge_graph && python3 blazing_server.py &

# Verify it's ready
curl http://localhost:8000/api/health
```

### Required Workflow for ALL Operations:

#### 1. Before Reading/Analyzing Code:
```bash
# First search the knowledge graph
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "search terms related to task"}'
```

#### 2. Before Editing ANY File:
```bash
# Check impact analysis FIRST
curl -X POST http://localhost:8000/api/impact/analyze \
  -H "Content-Type: application/json" \
  -d '{"node_id": "path/to/file.py"}'
```

#### 3. Before Creating New Code:
```bash
# Find existing patterns
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "similar function or pattern"}'
```

#### 4. After Making Changes:
```bash
# Document for future agents
curl -X POST http://localhost:8000/api/agent/note \
  -H "Content-Type: application/json" \
  -d '{"node_id": "file_path", "agent_id": "Claude", "note": "what changed and why"}'
```

### Knowledge Graph Dashboard:
- **URL**: http://localhost:8000
- **Search**: Find code semantically
- **Impact**: See what breaks before you change it
- **Patterns**: Learn from existing code

### Integration Checklist:
- [ ] Knowledge Graph running at http://localhost:8000
- [ ] Searched for existing implementations
- [ ] Analyzed impact before modifications
- [ ] Found patterns before writing new code
- [ ] Documented changes after completion

**NEVER skip the Knowledge Graph. It prevents disasters and ensures consistency.**

## 🔧 Context7 MCP Integration

**Context7 MCP provides real-time, version-specific documentation directly in your development workflow.**

### What is Context7 MCP?
Context7 is a Model Context Protocol server that dynamically fetches up-to-date documentation for libraries and frameworks you're using, preventing outdated code suggestions.

### Installation & Usage:
```bash
# Install globally (already done)
npm install -g @upstash/context7-mcp@latest

# Run Context7 for this project
./scripts/utilities/run-context7.sh

# Or use directly with npx
npx -y @upstash/context7-mcp@latest
```

### How to Use:
Simply add "use context7" to any prompt to fetch current documentation:
- "How do I implement voice recognition in React Native? use context7"
- "Show me the latest FastAPI security patterns use context7"
- "What's the current Google Cloud TTS API? use context7"

### Project Configuration:
Context7 is configured for our tech stack in `.mcp/context7.json`:
- FastAPI, React Native, Expo
- Google Cloud services
- SQLAlchemy, Redis, Celery
- TypeScript, Python

### Benefits:
- Always get current API documentation
- Avoid deprecated methods
- Access version-specific examples
- Reduce errors from outdated information

## Project Overview

AI Road Trip Storyteller - A **fully implemented, production-ready** AI-powered road trip companion that transforms drives into magical journeys through storytelling, voice personalities, and real-time booking integration.

**Current Status:**
- ✅ Backend: **Deployed to production** at `https://roadtrip-mvp-792001900150.us-central1.run.app`
- ✅ AI: **Real Google Vertex AI integration** actively generating stories
- ✅ Voice: **Google Cloud TTS** with 20+ personalities implemented
- ✅ Bookings: **Real API integrations** (Ticketmaster, OpenTable, Recreation.gov, Viator)
- 🚧 Mobile: **Fully functional** but needs 4-5 weeks of security hardening

**Tech Stack:**
- Backend: FastAPI (Python 3.9+), PostgreSQL, Redis, Google Vertex AI
- Mobile: React Native + Expo, TypeScript
- Infrastructure: Google Cloud Run, Docker, Cloud SQL

## Essential Commands

### Development Setup
```bash
# Initial setup
./scripts/development/setup_dev_environment.sh

# Start all services
docker-compose -f infrastructure/docker/docker-compose.yml up -d

# Start backend server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Start mobile app
cd mobile && npm start
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend/app --cov-report=html

# Run MVP tests only
pytest -m mvp

# Mobile tests
cd mobile && npm test
```

### Code Quality
```bash
# Python formatting and linting
black backend/
flake8 backend/
mypy backend/

# Mobile linting
cd mobile && npm run lint
```

### Database
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Reset database (development only)
alembic downgrade base && alembic upgrade head
```

### Deployment
```bash
# Backend is already deployed! Check health:
curl https://roadtrip-mvp-792001900150.us-central1.run.app/health

# Deploy backend updates to Google Cloud Run
./scripts/deployment/deploy.sh --project-id roadtrip-mvp

# Mobile app production build
cd mobile
eas build --platform all --profile production

# Submit to app stores (after security hardening)
eas submit --platform ios
eas submit --platform android
```

## High-Level Architecture

### Backend Structure
The backend follows a modular microservices-inspired architecture:

```
backend/app/
├── core/           # Authentication, AI client, caching, configuration
├── services/       # Business logic - 40+ specialized services including:
│   ├── master_orchestration_agent.py  # Main AI orchestrator
│   ├── booking_services.py            # Partner integrations
│   ├── voice_services.py              # TTS/STT handling
│   └── storytelling_services.py       # Story generation
├── routes/         # API endpoints organized by feature
├── models/         # SQLAlchemy database models
├── schemas/        # Pydantic validation schemas
├── middleware/     # Security, monitoring, performance layers
└── integrations/   # External API clients (Maps, Weather, etc.)
```

**Key Architectural Patterns:**
1. **Master Orchestration Agent**: Routes requests to 5 specialized sub-agents (Navigation, Booking, Storytelling, Voice, Emergency)
2. **Repository Pattern**: Database operations abstracted through repository classes
3. **Middleware Pipeline**: Layered security (JWT, CSRF, rate limiting) and monitoring
4. **Cache-First Strategy**: Redis caching for AI responses to reduce API costs
5. **Event-Driven Processing**: Celery for async tasks like story generation

### Mobile App Structure
React Native app with TypeScript:

```
mobile/src/
├── components/     # Reusable UI components
├── screens/        # 30+ feature screens
├── services/       # API and device services
├── navigation/     # React Navigation setup
└── hooks/          # Custom React hooks
```

### Knowledge Graph System
AI-powered code intelligence system:

```
knowledge_graph/
├── blazing_server.py    # Main FastAPI server
├── core/               # Graph database and analysis
├── analyzers/          # Code pattern detection
├── agents/             # Automated code agents
└── ui/                # Web dashboard interface
```

### AI Integration
- **Primary AI**: Google Vertex AI (Gemini 1.5) for story generation
- **Voice**: Google Cloud TTS/STT with 20+ personality options
- **Caching**: AI responses cached in Redis with intelligent invalidation

### Security Architecture
- JWT authentication with refresh tokens
- Two-factor authentication (2FA) support
- CSRF protection on all state-changing operations
- Rate limiting per user and endpoint
- Security headers middleware
- Intrusion detection and automated threat response

## Critical Development Notes

### When Working with AI Services
- Always check for cached responses before making AI API calls
- Use the master orchestration agent for routing - don't call sub-agents directly
- Voice personalities are defined in `backend/app/services/voice_services.py`
- AI responses are cached with 1-hour TTL by default

### Database Considerations
- Always use connection pooling (already configured)
- Write migrations for any schema changes
- Use repository pattern for data access
- Connection pool settings: min=5, max=20 connections

### Testing Requirements
- Minimum 80% code coverage required
- Always write tests for new features
- Use pytest markers: @pytest.mark.mvp, @pytest.mark.integration, etc.
- Run specific test: `pytest -k "test_name"`
- Skip slow tests: `pytest -m "not slow"`

### API Development
- All endpoints must have Pydantic schemas for request/response
- Include proper error handling and logging
- Document endpoints with OpenAPI annotations
- Use dependency injection for services

### Mobile Development
- Test on both iOS and Android simulators
- Handle offline scenarios gracefully
- Voice features require device permissions
- Minimum iOS 13.0, Android API 23

### Deployment Checklist
- Run full test suite
- Update environment variables in Secret Manager
- Verify database migrations
- Check monitoring dashboards post-deployment
- Ensure all API keys are properly secured

## Common Tasks

### Adding a New API Endpoint
1. Create route in `backend/app/routes/`
2. Add Pydantic schemas in `backend/app/schemas/`
3. Implement business logic in `backend/app/services/`
4. Add tests in `tests/unit/` and `tests/integration/`
5. Update API documentation

### Adding a New Voice Personality
1. Define personality in `backend/app/services/voice_services.py`
2. Add voice configuration and prompts
3. Test with various story scenarios
4. Update mobile app to include new option

### Implementing a New Booking Partner
1. Create integration client in `backend/app/integrations/`
2. Add booking service methods in `backend/app/services/booking_services.py`
3. Implement commission tracking
4. Add comprehensive tests
5. Update orchestration agent routing

### Performance Optimization
- Check Redis cache hit rates
- Monitor database query performance
- Use async operations for external API calls
- Profile with `cProfile` for bottlenecks

## Environment Variables

Critical environment variables (set in .env):
- `GOOGLE_CLOUD_PROJECT`: GCP project ID
- `VERTEX_AI_LOCATION`: AI model region
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `JWT_SECRET_KEY`: Authentication secret
- API keys for: Google Maps, OpenWeatherMap, Ticketmaster, etc.

## Monitoring and Debugging

- API Docs: http://localhost:8000/docs
- Prometheus: http://localhost:9090 (when monitoring profile enabled)
- Grafana: http://localhost:3000
- Logs: `docker-compose logs -f [service]`

## Production Considerations

### Backend (Already in Production):
- ✅ Deployed on Google Cloud Run
- ✅ PostgreSQL on Cloud SQL with backups
- ✅ Redis caching configured
- ✅ Monitoring with Prometheus
- ✅ Auto-scaling configured
- ⚠️ Ensure all API keys are in Secret Manager (not .env)

### Mobile App (Pre-Production):
- 🚨 Remove all console.log statements before production
- 🚨 Replace hardcoded API keys with environment variables
- 🚨 Implement certificate pinning for API calls
- 🚨 Enable crash reporting (Sentry)
- 🚨 Configure proper code obfuscation
- 📱 Add app store assets (icons, screenshots)
- 📱 Complete security audit items from PRODUCTION_READINESS_AUDIT.md

### Current Production URLs:
- Backend API: `https://roadtrip-mvp-792001900150.us-central1.run.app`
- API Docs: `https://roadtrip-mvp-792001900150.us-central1.run.app/docs`
- Health Check: `https://roadtrip-mvp-792001900150.us-central1.run.app/health`

## Quick Reference

### Running Single Tests
```bash
# Backend specific test
pytest tests/unit/test_voice_services.py::test_personality_generation

# Mobile specific test
cd mobile && npm test -- PersonalitySelector.test.tsx

# Test with debugging
pytest -s -vv tests/unit/test_specific.py
```

### Common Port Usage
- Backend API: 8000
- Knowledge Graph: 8000 (when backend not running)
- PostgreSQL: 5432
- Redis: 6379
- Prometheus: 9090
- Grafana: 3000

### Environment Setup Order
1. Start Docker services first
2. Run database migrations
3. Start backend server
4. Start mobile app (if needed)
5. Verify Knowledge Graph is accessible