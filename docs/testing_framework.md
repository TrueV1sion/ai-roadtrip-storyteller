# Testing Framework Documentation

## Overview

The Road Trip application has a comprehensive testing framework covering unit tests, integration tests, end-to-end tests, and performance tests for all new components.

## Test Structure

```
tests/
├── unit/                         # Unit tests for individual components
│   ├── test_master_orchestration_agent.py
│   ├── test_booking_agent.py
│   ├── test_commission_calculator.py
│   └── test_revenue_analytics.py
├── integration/                  # Integration tests
│   ├── test_booking_flows.py
│   └── test_api_client_error_handling.py
├── e2e/                         # End-to-end tests
│   └── test_voice_interactions.py
└── load/                        # Load and performance tests
    └── test_load_personalized_stories.py

mobile/src/components/__tests__/  # Mobile component tests
├── BookingFlow.test.tsx
└── VoiceAssistant.test.tsx
```

## Running Tests

### Quick Start

```bash
# Run all tests
python run_tests.py

# Run specific test categories
python run_tests.py --type unit
python run_tests.py --type integration
python run_tests.py --type booking
python run_tests.py --type voice

# Run with coverage
python run_tests.py --coverage

# Run specific component tests
python run_tests.py --type specific
```

### Backend Tests

```bash
# Run all backend tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific markers
pytest -m booking
pytest -m voice
pytest -m orchestration
pytest -m commission
pytest -m analytics

# Run in parallel
pytest -n auto
```

### Mobile Tests

```bash
cd mobile

# Run all tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test file
npm test BookingFlow.test.tsx

# Run in watch mode
npm test -- --watch
```

## Test Categories

### 1. Master Orchestration Agent Tests

**File:** `tests/unit/test_master_orchestration_agent.py`

Tests the central AI orchestration system:
- Intent classification for various command types
- Multi-agent coordination
- Parallel and sequential execution
- Error handling and recovery
- Context preservation
- Performance monitoring

**Key Test Cases:**
- `test_intent_classification_*` - Validates intent detection
- `test_multi_intent_detection` - Complex command handling
- `test_parallel_execution` - Concurrent agent execution
- `test_agent_coordination` - Inter-agent communication

### 2. Booking Agent Tests

**File:** `tests/unit/test_booking_agent.py`

Tests the booking functionality:
- Restaurant reservation parsing and creation
- Attraction ticket booking
- Hotel reservations
- Availability checking
- Cancellations and modifications
- User preference handling

**Key Test Cases:**
- `test_parse_*_booking_request` - Command parsing
- `test_*_booking_success` - Successful booking flows
- `test_booking_with_preferences` - Preference integration
- `test_booking_cancellation` - Cancellation handling

### 3. Commission Calculator Tests

**File:** `tests/unit/test_commission_calculator.py`

Tests commission calculation logic:
- Basic commission rates by booking type
- Vendor-specific rates
- Volume-based tiers
- Promotional rates
- Bulk booking discounts
- Revenue sharing

**Key Test Cases:**
- `test_default_commission_rates` - Base rate validation
- `test_volume_based_tiers` - Tier calculation
- `test_commission_validation` - Input validation
- `test_partner_revenue_share` - Revenue splitting

### 4. Revenue Analytics Tests

**File:** `tests/unit/test_revenue_analytics.py`

Tests analytics and reporting:
- Revenue metrics calculation
- Trend analysis
- Forecasting
- Vendor performance
- Geographic analysis
- Cohort analysis

**Key Test Cases:**
- `test_calculate_basic_metrics` - Core metrics
- `test_revenue_forecasting` - Prediction accuracy
- `test_anomaly_detection` - Outlier detection
- `test_dashboard_metrics` - Real-time metrics

### 5. Booking Flow Integration Tests

**File:** `tests/integration/test_booking_flows.py`

Tests complete booking workflows:
- Voice-initiated bookings
- Multi-step booking processes
- Family booking scenarios
- Modification flows
- Payment processing
- Error recovery

**Key Test Cases:**
- `test_restaurant_booking_flow_via_voice` - Voice to booking
- `test_multi_step_booking_with_preferences` - Complex flows
- `test_concurrent_booking_handling` - Race conditions
- `test_booking_with_payment_processing` - Payment integration

### 6. Voice Interaction E2E Tests

**File:** `tests/e2e/test_voice_interactions.py`

Tests voice functionality end-to-end:
- Continuous conversations
- Real-time navigation updates
- Multi-agent voice commands
- Language switching
- Offline transitions
- Accessibility features

**Key Test Cases:**
- `test_continuous_voice_conversation` - WebSocket streaming
- `test_voice_navigation_with_updates` - Real-time updates
- `test_voice_multi_agent_coordination` - Complex commands
- `test_voice_accessibility_features` - Accessibility support

### 7. API Error Handling Tests

**File:** `tests/integration/test_api_client_error_handling.py`

Tests error scenarios:
- Network error retry logic
- Rate limit handling
- Authentication refresh
- Circuit breaker pattern
- Graceful degradation
- Error context preservation

**Key Test Cases:**
- `test_network_error_retry` - Retry mechanisms
- `test_circuit_breaker_pattern` - Failure protection
- `test_graceful_degradation` - Fallback behavior
- `test_error_aggregation_in_parallel_requests` - Concurrent errors

## Mobile Component Tests

### BookingFlow Tests

**File:** `mobile/src/components/__tests__/BookingFlow.test.tsx`

Tests React Native booking components:
- Booking type selection
- Voice command processing
- Form pre-filling
- Restaurant search and selection
- Availability checking
- Booking confirmation
- Error handling

### VoiceAssistant Tests

**File:** `mobile/src/components/__tests__/VoiceAssistant.test.tsx`

Tests voice UI components:
- Voice button interactions
- Real-time transcription display
- Voice visualizer animations
- Conversation history
- Language switching
- Accessibility settings

## Test Configuration

### pytest.ini

Configures pytest with:
- Test discovery patterns
- Coverage requirements (80% minimum)
- Test markers for categorization
- Async test support
- Timeout settings
- Environment variables

### GitHub Actions Workflow

`.github/workflows/test.yml` provides:
- Automated testing on push/PR
- Parallel backend and mobile tests
- PostgreSQL and Redis services
- Coverage reporting to Codecov
- Test result artifacts

## Best Practices

### Writing Tests

1. **Use descriptive test names**
   ```python
   def test_booking_agent_handles_restaurant_unavailability():
       # Clear what the test validates
   ```

2. **Follow AAA pattern**
   ```python
   # Arrange
   booking_service = BookingService()
   
   # Act
   result = booking_service.create_booking(...)
   
   # Assert
   assert result.status == "confirmed"
   ```

3. **Mock external dependencies**
   ```python
   with patch('external_api.call') as mock_api:
       mock_api.return_value = {"success": True}
       # Test logic
   ```

4. **Test edge cases**
   - Empty inputs
   - Invalid data
   - Concurrent operations
   - Network failures

### Running Tests Locally

1. **Set up test environment**
   ```bash
   # Create test database
   createdb roadtrip_test
   
   # Start Redis
   redis-server
   
   # Install dependencies
   pip install -r requirements-dev.txt
   ```

2. **Run tests with debugging**
   ```bash
   # Run with print statements
   pytest -s
   
   # Run with debugger
   pytest --pdb
   
   # Run specific test
   pytest -k test_booking_flow
   ```

3. **Check coverage gaps**
   ```bash
   pytest --cov=backend --cov-report=term-missing
   ```

## Continuous Integration

Tests run automatically on:
- Every push to main/develop branches
- Pull request creation/update
- Scheduled nightly builds

Failed tests block deployment and notify the team via:
- GitHub status checks
- Slack notifications
- Email alerts

## Performance Testing

Load tests validate:
- API response times under load
- Concurrent booking handling
- Voice processing latency
- Database query performance

Run performance tests:
```bash
pytest tests/load/ -v
```

## Future Enhancements

1. **Visual regression testing** for mobile UI
2. **Contract testing** for API integrations
3. **Mutation testing** for test quality
4. **Chaos engineering** for resilience
5. **A/B testing framework** for features