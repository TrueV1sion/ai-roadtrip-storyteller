# AI Road Trip Storyteller 🚗✨

An Imagineering-inspired road trip companion that transforms ordinary drives into magical journeys through AI-powered storytelling, dynamic voice personalities, and seamless booking integration.

## 🎯 Current Status

**Overall Readiness:** 65% Production Ready | **Launch Timeline:** 4 weeks

The application features a sophisticated AI orchestration system with 5 specialized sub-agents, 20+ dynamic voice personalities, and real-time booking capabilities. Core features are 85-90% complete, with critical infrastructure and testing work remaining.

📊 **Key Documents:**
- [PROJECT_STATUS.md](docs/project-management/PROJECT_STATUS.md) - Current implementation status
- [PRODUCTION_READINESS_REPORT.md](docs/launch/PRODUCTION_READINESS_REPORT.md) - Detailed gap analysis
- [LAUNCH_READINESS_TASKS.md](docs/launch/LAUNCH_READINESS_TASKS.md) - 67 tasks for production launch
- [MOBILE_DEVELOPMENT_PLAN.md](docs/technical/MOBILE_DEVELOPMENT_PLAN.md) - Mobile app completion roadmap

## ✨ Core Features

### AI Orchestration System
- **Master Orchestration Agent**: Intelligent routing to specialized sub-agents
- **Story Generation**: Context-aware narratives based on location and journey type
- **Booking Agent**: Detects opportunities and executes reservations
- **Navigation Assistant**: Real-time route guidance and traffic management
- **Contextual Awareness**: Proactive suggestions based on journey context
- **Local Expert**: Authentic recommendations from a knowledgeable guide

### Dynamic Voice Personalities (20+)
- **Event-Based**: Mickey for Disney trips, Rock DJ for concerts
- **Seasonal**: Santa (December), Halloween Narrator (October)
- **Regional**: Southern Charm, Texas Ranger, California Surfer
- **Professional**: Business Travel Companion, Eco-Travel Guide
- **Special Modes**: Rideshare optimization for drivers and passengers

### Smart Booking & Revenue
- **Commission-Based System**: Tiered rates across multiple providers
- **Real-Time Analytics**: Revenue tracking and forecasting
- **Integrated Partners**: OpenTable, Recreation.gov, Shell Recharge (EV)
- **Event Detection**: Ticketmaster integration for journey theming

## Tech Stack 🛠️

### Backend
- FastAPI (Python 3.9+)
- PostgreSQL with SQLAlchemy ORM
- Google Vertex AI (Gemini 1.5)
- Google Cloud Services (Maps, TTS, STT, Storage)
- Redis (Advanced AI-specialized Caching)
- Docker & Docker Compose
- Prometheus & Grafana (Monitoring)

### Mobile App
- React Native with Expo
- TypeScript
- React Native Maps
- Spotify SDK
- AsyncStorage (Offline support)

## Getting Started 🚀

### Prerequisites
- Python 3.9+
- Node.js 16+
- Docker & Docker Compose
- Google Cloud Project (for AI features)

### Required API Keys
- **Google Maps API** (Navigation & routing)
- **Google Vertex AI** (Story generation) 
- **Ticketmaster API** (Event detection)
- **OpenWeatherMap API** (Weather narratives)
- **Recreation.gov API** (Campground bookings)

See [SETUP_GUIDE.md](docs/technical/SETUP_GUIDE.md) for comprehensive setup instructions.

## Quick Start with Docker 🐳

1. Clone the repository:
```bash
git clone https://github.com/yourusername/ai-road-trip-storyteller.git
cd ai-road-trip-storyteller
```

2. Configure your API keys:
```bash
# Interactive setup wizard
python scripts/setup/configure_apis_simple.py

# Or manually copy and edit
cp .env.example .env
```

3. Launch services with Docker:
```bash
# Development environment with monitoring
docker-compose --profile monitoring up

# Or use the beta launch script
./scripts/deployment/launch_beta.sh
```

4. Start all services:
```bash
docker-compose up
```

The API will be available at http://localhost:8000

## Manual Setup

### Backend Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development tools
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your actual credentials
```

4. Start required services (PostgreSQL and Redis):
```bash
docker-compose up -d db redis
```

5. Run database migrations:
```bash
alembic upgrade head
```

6. Start the backend server:
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### Mobile App Setup

1. Navigate to the mobile directory:
```bash
cd mobile
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

## Project Structure 📁

```
roadtrip/
├── backend/            # FastAPI backend application
├── mobile/             # React Native mobile app
├── docs/               # All project documentation
│   ├── project-management/   # Status, planning, tracking
│   ├── technical/           # Architecture, setup guides
│   ├── launch/             # Launch plans and checklists
│   └── security/           # Security documentation
├── scripts/            # Utility scripts
│   ├── setup/              # Setup and configuration
│   ├── deployment/         # Deployment scripts
│   ├── testing/           # Test runners
│   ├── demos/             # Demo scripts
│   └── utilities/         # Other utilities
├── config/             # Configuration files
├── tests/              # Test suites
├── infrastructure/     # IaC and deployment configs
├── monitoring/         # Monitoring configurations
└── presentations/      # Pitch decks and demos
```

## Documentation 📚

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Demo Interface**: Run `python scripts/demos/demo_backend.py` for interactive testing

### Key Documentation
- [PROJECT_STATUS.md](docs/project-management/PROJECT_STATUS.md) - Current implementation status
- [SETUP_GUIDE.md](docs/technical/SETUP_GUIDE.md) - Comprehensive setup instructions
- [API_INTEGRATION_STATUS.md](docs/technical/API_INTEGRATION_STATUS.md) - API partnerships & roadmap
- [CLAUDE.md](CLAUDE.md) - AI assistant guidance for development

### Architecture Documentation
- [AI Orchestration](docs/agent_orchestration_flow.md) - Master agent system design
- [AI Caching System](docs/ai_caching_system.md) - Advanced caching for AI responses
- [Database Optimization](docs/database_optimization.md) - Performance monitoring
- [Security](docs/authorization.md) - Authentication and authorization

## Testing 🧪

```bash
# Run comprehensive test suite
python scripts/testing/run_all_tests_comprehensive.py

# Run specific test categories
pytest tests/unit/              # Unit tests
pytest tests/integration/        # Integration tests
python scripts/testing/test_apis_simple.py       # API connectivity tests

# Run with coverage
pytest --cov=backend --cov-report=html
```

## Deployment 🚀

**⚠️ Note: Application requires 4 weeks of work before production deployment**

```bash
# Check current readiness
python scripts/utilities/check_launch_readiness.py

# When ready, validate deployment
python scripts/utilities/validate_deployment.py

# Deploy to production
./scripts/deployment/deploy.sh
```

See [LAUNCH_READINESS_TASKS.md](docs/launch/LAUNCH_READINESS_TASKS.md) for required pre-launch tasks.

## Contributing 🤝

1. Fork the repository
2. Create a feature branch
3. Run tests and linting
4. Commit your changes
5. Push to the branch
6. Open a Pull Request

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Project Status 📊

### ✅ Completed
- **AI Orchestration**: 5 specialized agents working
- **Voice Personalities**: 20+ contextual personalities
- **Core Features**: 85-90% implementation complete
- **API Integrations**: 5 production, 5 in mock mode
- **Basic Security**: JWT auth, CSRF, rate limiting

### 🚧 In Progress (4 weeks remaining)
- **Infrastructure**: Secrets management, backups, monitoring
- **Security**: 2FA implementation, production hardening
- **Testing**: Mobile app coverage (currently <20%, target 80%)
- **Performance**: Load testing for 10k concurrent users
- **Operations**: Runbooks, disaster recovery, alerting

See [PRODUCTION_READINESS_REPORT.md](docs/launch/PRODUCTION_READINESS_REPORT.md) for detailed gaps.

## Acknowledgments 🙏

- Inspired by Disney Imagineering's storytelling principles
- Powered by Google Vertex AI (Gemini 1.5)
- Music integration via Spotify SDK
- Voice synthesis through Google Cloud TTS

## Contact 📧

For questions or feedback, please open an issue or contact the maintainers. 