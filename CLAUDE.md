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

### IMPORTANT: Knowledge Graph Consultation
- **Always consult the knowledge graph and claude.md files before any code operation.**

## Project Overview

AI Road Trip Storyteller - An AI-powered road trip companion that transforms drives into magical journeys through storytelling, voice personalities, and real-time booking integration.

**Tech Stack:**
- Backend: FastAPI (Python 3.9+), PostgreSQL, Redis, Google Vertex AI
- Mobile: React Native + Expo, TypeScript
- Infrastructure: Google Cloud Run, Docker, Terraform

## Essential Commands

### Development Setup
```bash
# Initial setup
./setup_dev_environment.sh

# Start all services
docker-compose up -d

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
```

### Deployment
```bash
# Deploy to Google Cloud Run
./scripts/deployment/deploy.sh --project-id YOUR_PROJECT_ID
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

### Database Considerations
- Always use connection pooling (already configured)
- Write migrations for any schema changes
- Use repository pattern for data access

### Testing Requirements
- Minimum 80% code coverage required
- Always write tests for new features
- Use pytest markers: @pytest.mark.mvp, @pytest.mark.integration, etc.

### API Development
- All endpoints must have Pydantic schemas for request/response
- Include proper error handling and logging
- Document endpoints with OpenAPI annotations

### Mobile Development
- Test on both iOS and Android simulators
- Handle offline scenarios gracefully
- Voice features require device permissions

### Deployment Checklist
- Run full test suite
- Update environment variables in Secret Manager
- Verify database migrations
- Check monitoring dashboards post-deployment

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

- All secrets must be in Google Secret Manager
- Enable Cloud Monitoring and Logging
- Set up alerting for error rates and latency
- Configure auto-scaling in Cloud Run
- Implement proper backup strategy for PostgreSQL