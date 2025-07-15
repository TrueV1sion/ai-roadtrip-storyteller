# Flight Tracking API Setup Guide

This guide covers the setup and configuration of flight tracking APIs for the AI Road Trip Storyteller application.

## Overview

The flight tracking client supports multiple providers with automatic fallback:
- **FlightStats** - Enterprise-grade, most comprehensive data
- **FlightAware** - Professional aviation tracking
- **AviationStack** - Free tier available, good for development
- **FlightLabs** - Affordable alternative with good coverage

## API Provider Setup

### 1. AviationStack (Recommended for Development)

**Free Tier Available**: 100 requests/month

1. Sign up at [https://aviationstack.com/signup/free](https://aviationstack.com/signup/free)
2. Get your API key from the dashboard
3. Add to `.env`:
   ```
   AVIATIONSTACK_API_KEY=your_api_key_here
   ```

**Features**:
- Real-time flight tracking
- Flight schedules
- Historical flight data
- Airport information

### 2. FlightStats (Enterprise)

**Paid Service**: Requires subscription

1. Register at [https://developer.flightstats.com/](https://developer.flightstats.com/)
2. Subscribe to a plan
3. Get your App ID and App Key
4. Add to `.env`:
   ```
   FLIGHTSTATS_APP_ID=your_app_id_here
   FLIGHTSTATS_API_KEY=your_app_key_here
   ```

**Features**:
- Most comprehensive flight data
- Weather integration
- Gate and terminal information
- Flight delays and cancellations

### 3. FlightAware (Professional)

**Paid Service**: Usage-based pricing

1. Sign up at [https://flightaware.com/commercial/aeroapi/](https://flightaware.com/commercial/aeroapi/)
2. Create an AeroAPI key
3. Add to `.env`:
   ```
   FLIGHTAWARE_API_KEY=your_api_key_here
   ```

**Features**:
- Real-time flight positions
- Detailed flight plans
- Aircraft registration data
- Historical flight tracks

### 4. FlightLabs

**Affordable Alternative**: Various pricing tiers

1. Register at [https://www.goflightlabs.com/](https://www.goflightlabs.com/)
2. Choose a plan and get API key
3. Add to `.env`:
   ```
   FLIGHTLABS_API_KEY=your_api_key_here
   ```

**Features**:
- Global flight coverage
- Airline schedules
- Airport delays
- Flight statistics

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# Flight Tracking APIs (configure at least one)
AVIATIONSTACK_API_KEY=your_aviationstack_key    # Free tier available
FLIGHTSTATS_APP_ID=your_flightstats_app_id     # Enterprise
FLIGHTSTATS_API_KEY=your_flightstats_key       # Enterprise
FLIGHTAWARE_API_KEY=your_flightaware_key       # Professional
FLIGHTLABS_API_KEY=your_flightlabs_key         # Affordable
```

### Quick Setup

Use the interactive configuration wizard:

```bash
python configure_apis_simple.py
```

Or update existing configuration:

```bash
python update_env.py
```

## Usage Examples

### Basic Flight Tracking

```python
from backend.app.integrations.flight_tracker_client import flight_tracker
from datetime import datetime, timedelta

# Track a specific flight
flight_info = await flight_tracker.track_flight(
    flight_number="AA100",  # Can include airline code
    departure_date=datetime.now() + timedelta(days=1)
)

print(f"Flight: {flight_info['flight_number']}")
print(f"Status: {flight_info['status']}")
print(f"Departure: {flight_info['departure']['airport']} at {flight_info['departure']['scheduled']}")
print(f"Arrival: {flight_info['arrival']['airport']} at {flight_info['arrival']['scheduled']}")
```

### Search Flights by Route

```python
# Find flights between airports
flights = await flight_tracker.search_flights_by_route(
    departure_airport="LAX",
    arrival_airport="JFK",
    departure_date=datetime.now() + timedelta(days=1)
)

for flight in flights[:5]:  # Show first 5 flights
    print(f"{flight['flight_number']} - {flight['airline']['name']}")
    print(f"Departs: {flight['departure']['scheduled']}")
```

### With Separate Airline Code

```python
# Track with separate airline code
flight_info = await flight_tracker.track_flight(
    flight_number="100",
    airline_code="AA",
    departure_date=datetime.now()
)
```

## Features

### Automatic Provider Fallback

The client automatically tries providers in order of availability:
1. FlightStats (if configured)
2. FlightAware (if configured)
3. AviationStack (if configured)
4. FlightLabs (if configured)

If one provider fails, the next is tried automatically.

### Caching

- Flight data is cached for 5 minutes
- Route searches are cached for 1 hour
- Reduces API calls and improves performance

### Circuit Breaker Protection

- Prevents cascading failures
- Temporarily disables failing providers
- Automatic recovery after timeout

### Rate Limiting

Each provider has different rate limits:
- **AviationStack Free**: 100 requests/month
- **FlightStats**: Varies by subscription
- **FlightAware**: Usage-based
- **FlightLabs**: Varies by plan

The circuit breaker helps prevent exceeding these limits.

## Testing

### Run Integration Tests

```bash
# Set test mode to live
export TEST_MODE=live

# Run flight tracker tests
pytest tests/integration/live/test_flight_tracker_integration.py -v

# Run specific provider test
pytest tests/integration/live/test_flight_tracker_integration.py::test_specific_provider_aviationstack -v
```

### Test Dashboard

Monitor API status:

```bash
python scripts/test_api_dashboard.py
```

## Response Format

All providers return normalized data in this format:

```json
{
    "flight_number": "AA100",
    "airline": {
        "code": "AA",
        "name": "American Airlines"
    },
    "status": "scheduled",  // scheduled, in_air, landed, cancelled, delayed, diverted
    "departure": {
        "airport": "LAX",
        "airport_name": "Los Angeles International Airport",
        "terminal": "4",
        "gate": "42B",
        "scheduled": "2024-01-20T14:30:00",
        "estimated": "2024-01-20T14:30:00",
        "actual": null,
        "delay_minutes": 0
    },
    "arrival": {
        "airport": "JFK",
        "airport_name": "John F. Kennedy International Airport",
        "terminal": "4",
        "gate": "B22",
        "scheduled": "2024-01-20T22:45:00",
        "estimated": "2024-01-20T22:45:00",
        "actual": null,
        "delay_minutes": 0
    },
    "aircraft": {
        "type": "B738",
        "tail_number": "N12345"
    },
    "duration_minutes": 315,
    "distance_miles": 2475
}
```

## Troubleshooting

### No Providers Available

If you see "No flight tracking API keys configured":
1. Check your `.env` file has at least one API key
2. Verify the key names match exactly
3. Restart the application after adding keys

### API Errors

Common issues and solutions:

1. **401 Unauthorized**: Check API key is valid
2. **429 Too Many Requests**: You've hit rate limits
3. **404 Not Found**: Flight doesn't exist or wrong date
4. **500 Server Error**: Provider issue, fallback will engage

### Mock Data

When all providers fail or no keys are configured, the system returns mock data for development. This is indicated by:
- Airline name: "Mock Airlines"
- Standard LAX-JFK route

## Best Practices

1. **Configure Multiple Providers**: Ensures reliability through fallback
2. **Start with AviationStack**: Free tier perfect for development
3. **Monitor Usage**: Track API calls to avoid overage charges
4. **Cache Aggressively**: Reduce API calls for common queries
5. **Handle Errors Gracefully**: Always have fallback logic

## Integration with Road Trip App

The flight tracker integrates with journey planning:

```python
# In voice assistant
if "flight" in user_input:
    flight_info = await flight_tracker.track_flight(
        flight_number=extracted_flight_number,
        departure_date=extracted_date
    )
    
    # Generate contextual response
    if flight_info['status'] == 'delayed':
        response = f"Your flight {flight_info['flight_number']} is delayed by {flight_info['departure']['delay_minutes']} minutes. You have extra time for your road trip to the airport!"
```

## Cost Optimization

To minimize API costs:

1. **Use Caching**: Leverage built-in caching
2. **Batch Requests**: Group related queries
3. **Off-Peak Times**: Some providers offer better rates
4. **Choose Right Provider**: 
   - Development: AviationStack (free tier)
   - Production: FlightLabs (affordable)
   - Enterprise: FlightStats (comprehensive)

## Security Considerations

1. **Never commit API keys**: Use `.env` file
2. **Rotate keys regularly**: Update quarterly
3. **Monitor usage**: Check for unusual activity
4. **Use environment-specific keys**: Separate dev/prod keys