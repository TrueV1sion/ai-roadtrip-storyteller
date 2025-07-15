# Live Integration Tests

This directory contains integration test suites for external booking APIs that support both mock and live testing modes.

## Test Suites

### 1. OpenTable Integration (`test_opentable_integration.py`)
Tests restaurant reservation functionality including:
- Restaurant search
- Availability checking
- Reservation creation/cancellation
- Commission tracking
- Voice-to-booking flows

### 2. Recreation.gov Integration (`test_recreation_gov_integration.py`)
Tests campground and activity booking including:
- Campground search
- Campsite availability
- Reservation creation
- Activity/permit booking
- Commission tracking
- Voice-to-booking flows

### 3. Shell Recharge Integration (`test_shell_recharge_integration.py`)
Tests EV charging station functionality including:
- Station search
- Real-time availability
- Charging reservations
- Session management
- Route planning with charging stops
- Commission tracking
- Voice-to-charging flows

## Running Tests

### Mock Mode (Default)
```bash
# Run all integration tests in mock mode
pytest tests/integration/live/

# Run specific test suite
pytest tests/integration/live/test_opentable_integration.py -v
```

### Live Mode
To run tests against real APIs, set environment variables:

```bash
# OpenTable
export OPENTABLE_TEST_MODE=live
export OPENTABLE_API_KEY=your_api_key
export OPENTABLE_PARTNER_ID=your_partner_id

# Recreation.gov
export RECREATION_GOV_TEST_MODE=live
export RECREATION_GOV_API_KEY=your_api_key
export RECREATION_GOV_AFFILIATE_ID=your_affiliate_id

# Shell Recharge
export SHELL_RECHARGE_TEST_MODE=live
export SHELL_RECHARGE_API_KEY=your_api_key
export SHELL_RECHARGE_PARTNER_ID=your_partner_id
export SHELL_RECHARGE_ENV=sandbox  # or production

# Generate test reports
export GENERATE_TEST_REPORTS=true

# Run tests
pytest tests/integration/live/test_opentable_integration.py -v
```

## Test Reports

When `GENERATE_TEST_REPORTS=true`, test results are saved to:
`tests/integration/live/reports/<service>_<mode>_<timestamp>.json`

Reports include:
- Test execution details
- Pass/fail status
- Commission tracking
- Performance metrics
- Error details

## Test Coverage

Each test suite validates:

### Critical Paths
- Search functionality
- Availability checking
- Booking creation
- Booking management

### Error Scenarios
- Invalid inputs
- No availability
- API errors
- Network failures

### Commission Tracking
- Accurate calculation
- Different booking types
- Commission reporting

### Voice Integration
- Natural language parsing
- End-to-end booking flows
- Multiple command variations

## Safety Notes

- Live tests may create real bookings - ensure test accounts are used
- Some services may charge fees even for test bookings
- Always clean up test reservations when possible
- Monitor commission calculations in live mode
- Use sandbox/test environments when available