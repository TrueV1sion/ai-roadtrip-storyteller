# API Integration Clients Documentation

This document describes the enhanced production-ready API clients for OpenTable, Recreation.gov, and Shell Recharge integrations.

## Overview

All three API clients have been enhanced with the following production-ready features:

### Common Features

1. **OAuth 2.0 Authentication**
   - Automatic token refresh with 5-minute buffer
   - Support for both API key and OAuth token authentication
   - Secure credential storage via environment variables

2. **Request Signing**
   - HMAC-SHA256 signature generation for API requests
   - Timestamp-based signatures for security
   - Optional signing toggle via environment variables

3. **Advanced Error Handling**
   - Comprehensive error code mapping to user-friendly messages
   - Distinction between recoverable and non-recoverable errors
   - Detailed logging for debugging production issues

4. **Circuit Breaker Pattern**
   - Automatic circuit opening after 5 consecutive failures
   - 60-second timeout before retry attempts
   - Prevents cascading failures in production

5. **Rate Limiting**
   - Sliding window rate limiting implementation
   - Per-minute request limits with automatic throttling
   - Minimum delay between requests to prevent API abuse

6. **Response Caching**
   - Redis-based caching for GET requests
   - Configurable TTL for different endpoint types
   - Cache key generation based on request parameters

7. **Mock Mode**
   - Toggle between real API calls and mock responses
   - Comprehensive mock data for all endpoints
   - Enables testing without API credentials

8. **Retry Logic**
   - Exponential backoff with jitter
   - Configurable retry attempts
   - Retry only on transient errors

## OpenTable Client

### Configuration

```bash
# Required environment variables
OPENTABLE_API_KEY=your_api_key
OPENTABLE_API_SECRET=your_api_secret
OPENTABLE_CLIENT_ID=your_client_id
OPENTABLE_OAUTH_TOKEN=your_oauth_token
OPENTABLE_OAUTH_REFRESH_TOKEN=your_refresh_token

# Optional configuration
OPENTABLE_API_URL=https://api.opentable.com/v2
OPENTABLE_AUTH_URL=https://oauth.opentable.com/v2/token
OPENTABLE_MOCK_MODE=false
OPENTABLE_SIGN_REQUESTS=true
```

### Enhanced Features

1. **Restaurant Search**
   - Real-time availability filtering
   - Cuisine type and price range filters
   - Distance-based sorting
   - Special offers and promotions

2. **Availability Checking**
   - Time slot recommendations around preference
   - Table type availability
   - Points eligibility
   - Dynamic pricing information

3. **Reservation Management**
   - Instant booking confirmation
   - Modification and cancellation support
   - Reminder preferences
   - Loyalty program integration

4. **Error Mapping**
   - `RESTAURANT_NOT_FOUND`: Restaurant doesn't exist
   - `NO_AVAILABILITY`: No tables for requested time
   - `INVALID_PARTY_SIZE`: Party size exceeds capacity
   - `BOOKING_WINDOW_EXCEEDED`: Too far in advance
   - `DUPLICATE_RESERVATION`: Already booked
   - `PAYMENT_REQUIRED`: Payment info needed
   - `RESTAURANT_CLOSED`: Closed on selected date

### Usage Example

```python
from backend.app.integrations.open_table_client import OpenTableClient

client = OpenTableClient()

# Search restaurants
restaurants = await client.search_restaurants(
    latitude=37.7749,
    longitude=-122.4194,
    radius_miles=10,
    cuisine_type="Italian",
    party_size=4,
    datetime_str="2025-02-01T19:00:00Z"
)

# Check availability
availability = await client.check_availability(
    restaurant_id="rest_001",
    party_size=4,
    date="2025-02-01",
    time_preference="19:00"
)

# Create reservation
reservation = await client.create_reservation(
    restaurant_id="rest_001",
    party_size=4,
    date="2025-02-01",
    time="19:00",
    customer_info={
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1-555-0123",
        "special_requests": "Window table",
        "dietary_restrictions": ["vegetarian"],
        "occasion": "birthday"
    }
)
```

## Recreation.gov Client

### Configuration

```bash
# Required environment variables
RECREATION_GOV_API_KEY=your_api_key
RECREATION_GOV_API_SECRET=your_api_secret
RECREATION_GOV_ACCOUNT_ID=your_account_id

# Optional configuration
RECREATION_GOV_API_URL=https://ridb.recreation.gov/api/v1
RECREATION_GOV_BOOKING_URL=https://www.recreation.gov/api/camps/availability/campground
RECREATION_GOV_MOCK_MODE=false
RECREATION_GOV_SIGN_REQUESTS=true
```

### Enhanced Features

1. **Campground Search**
   - RIDB API integration
   - Amenity and activity filtering
   - Distance calculation
   - Real-time site availability

2. **Availability Checking**
   - Multi-night stay validation
   - Equipment compatibility checking
   - Site-specific amenities
   - ADA accessibility info

3. **Reservation Creation**
   - Booking fee calculation
   - Cancellation policy details
   - QR code generation
   - Email confirmations

4. **Permit Management**
   - Activity-based permit search
   - Lottery system support
   - Advance booking requirements
   - State-based filtering

5. **Error Mapping**
   - `FACILITY_NOT_FOUND`: Campground doesn't exist
   - `NO_AVAILABILITY`: No sites available
   - `INVALID_DATES`: Date range issues
   - `BOOKING_WINDOW_CLOSED`: Too late to book
   - `PERMIT_REQUIRED`: Need permit first
   - `MAX_STAY_EXCEEDED`: Stay too long
   - `INVALID_EQUIPMENT`: Equipment not allowed

### Usage Example

```python
from backend.app.integrations.recreation_gov_client import RecreationGovClient

client = RecreationGovClient()

# Search campgrounds
campgrounds = await client.search_campgrounds(
    latitude=39.5296,
    longitude=-121.5524,
    radius_miles=50,
    amenities=["Restrooms", "Drinking Water"],
    campground_type="National Forest"
)

# Check availability
availability = await client.check_availability(
    campground_id="camp_001",
    start_date="2025-06-01",
    end_date="2025-06-03",
    equipment_type="tent"
)

# Create reservation
reservation = await client.create_reservation(
    campground_id="camp_001",
    site_id="A12",
    start_date="2025-06-01",
    end_date="2025-06-03",
    customer_info={
        "name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "+1-555-0124",
        "adults": 2,
        "children": 2,
        "equipment_type": "tent",
        "vehicles": 1
    }
)
```

## Shell Recharge Client

### Configuration

```bash
# Required environment variables
SHELL_RECHARGE_API_KEY=your_api_key
SHELL_RECHARGE_API_SECRET=your_api_secret
SHELL_RECHARGE_CLIENT_ID=your_client_id
SHELL_RECHARGE_OAUTH_TOKEN=your_oauth_token
SHELL_RECHARGE_OAUTH_REFRESH_TOKEN=your_refresh_token

# Optional configuration
SHELL_RECHARGE_API_URL=https://api.shellrecharge.com/v2
SHELL_RECHARGE_AUTH_URL=https://auth.shellrecharge.com/oauth/token
SHELL_RECHARGE_WS_URL=wss://ws.shellrecharge.com/v2
SHELL_RECHARGE_MOCK_MODE=false
SHELL_RECHARGE_SIGN_REQUESTS=true
```

### Enhanced Features

1. **Station Search**
   - Real-time connector availability
   - Power output filtering
   - Amenity information
   - User ratings and reviews

2. **Real-time Monitoring**
   - WebSocket connections for live updates
   - Session progress tracking
   - Power delivery monitoring
   - Cost accumulation updates

3. **Smart Pricing**
   - Time-of-use pricing support
   - kWh and time-based billing
   - Session fee calculation
   - Currency conversion

4. **Session Management**
   - Remote start/stop capabilities
   - Emergency stop codes
   - Charging curve estimation
   - Battery SOC tracking

5. **Environmental Impact**
   - CO2 savings calculation
   - Renewable energy percentage
   - Green certification tracking
   - Sustainability metrics

6. **Error Mapping**
   - `STATION_NOT_FOUND`: Station doesn't exist
   - `CONNECTOR_UNAVAILABLE`: Connector in use
   - `INVALID_SESSION`: Session expired
   - `PAYMENT_REQUIRED`: Payment needed
   - `VEHICLE_INCOMPATIBLE`: Wrong connector type
   - `RESERVATION_CONFLICT`: Time slot taken
   - `MAX_DURATION_EXCEEDED`: Too long duration

### Usage Example

```python
from backend.app.integrations.shell_recharge_client import ShellRechargeClient

client = ShellRechargeClient()

# Search charging stations
stations = await client.search_charging_stations(
    latitude=37.7749,
    longitude=-122.4194,
    radius_miles=25,
    connector_type="CCS",
    min_power_kw=100,
    available_only=True
)

# Check availability
availability = await client.check_availability(
    station_id="shell_ev_001",
    connector_id="conn_001",
    duration_minutes=30
)

# Create reservation
reservation = await client.create_reservation(
    station_id="shell_ev_001",
    connector_id="conn_001",
    start_time="2025-01-25T14:00:00Z",
    duration_minutes=30,
    vehicle_info={
        "make": "Tesla",
        "model": "Model 3",
        "battery_capacity": 75,
        "connector_type": "CCS",
        "driver_name": "Bob Johnson",
        "driver_email": "bob@example.com",
        "target_soc": 80
    }
)

# Start charging session
session = await client.start_charging_session(
    reservation_id=reservation["reservation_id"],
    connector_id="conn_001"
)

# Monitor session status
status = await client.get_session_status(session["session_id"])

# Stop charging
receipt = await client.stop_charging_session(session["session_id"])
```

## Production Deployment Checklist

### 1. Environment Variables
- [ ] Set all required API credentials
- [ ] Configure API URLs for production endpoints
- [ ] Disable mock mode
- [ ] Enable request signing

### 2. Redis Configuration
- [ ] Configure Redis connection for caching
- [ ] Set appropriate cache TTL values
- [ ] Monitor cache hit rates

### 3. Monitoring
- [ ] Set up logging aggregation
- [ ] Configure error alerting
- [ ] Monitor circuit breaker status
- [ ] Track API rate limit usage

### 4. Security
- [ ] Rotate API credentials regularly
- [ ] Use secure credential storage (e.g., AWS Secrets Manager)
- [ ] Enable request signing for all production calls
- [ ] Implement IP whitelisting if supported

### 5. Performance
- [ ] Tune rate limiting parameters
- [ ] Optimize cache TTL values
- [ ] Configure connection pooling
- [ ] Set appropriate timeout values

### 6. Testing
- [ ] Run integration tests with mock mode
- [ ] Test circuit breaker behavior
- [ ] Verify error handling
- [ ] Load test rate limiting

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Check API credentials in environment
   - Verify OAuth token hasn't expired
   - Ensure request signing is configured correctly

2. **Rate Limiting**
   - Monitor request counts in logs
   - Adjust rate limit parameters if needed
   - Implement request queuing for high volume

3. **Circuit Breaker Open**
   - Check API service status
   - Review error logs for root cause
   - Wait for timeout before retry

4. **Cache Issues**
   - Verify Redis connection
   - Check cache key generation
   - Monitor cache memory usage

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger("backend.app.integrations").setLevel(logging.DEBUG)
```

## Future Enhancements

1. **Webhook Support**
   - Real-time reservation updates
   - Charging session events
   - Cancellation notifications

2. **Batch Operations**
   - Bulk availability checking
   - Multiple reservation creation
   - Batch cancellations

3. **Advanced Analytics**
   - Usage pattern tracking
   - Cost optimization suggestions
   - Predictive availability

4. **Multi-region Support**
   - Geographic API endpoint routing
   - Currency localization
   - Time zone handling