# Directions Service API Documentation

## Overview

The Directions Service provides enhanced routing capabilities with real-time traffic data, place information, and route optimization. Built on top of the Google Maps Platform, it offers additional features like caching, rate limiting, and traffic predictions.

## Base URL

```
https://api.example.com/v1
```

## Authentication

All requests require a client ID to be passed in the header:

```
X-Client-ID: your_client_id
```

Rate limits are tracked per client ID:
- 50 requests per minute
- 2500 requests per day

## Endpoints

### Get Directions

```http
GET /directions
```

Fetches optimized directions between two points with optional waypoints and enhanced features.

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| origin | string | required | Starting point in "lat,lng" format or place name |
| destination | string | required | Ending point in "lat,lng" format or place name |
| mode | string | "driving" | Travel mode: "driving", "walking", "bicycling", "transit" |
| waypoints | string | null | Optional pipe-separated list of waypoints |
| optimize_route | boolean | false | Whether to optimize waypoint order |
| alternatives | boolean | false | Whether to return alternative routes |
| include_traffic | boolean | true | Include live traffic data |
| include_places | boolean | false | Include detailed place information |
| departure_time | string | null | ISO datetime for future departures |
| traffic_model | string | "best_guess" | Traffic prediction model: "best_guess", "pessimistic", "optimistic" |

#### Response Format

```json
{
  "routes": [{
    "summary": "Route summary",
    "bounds": {
      "northeast": {"lat": 40.7, "lng": -73.9},
      "southwest": {"lat": 40.6, "lng": -74.0}
    },
    "copyrights": "Map data ©2024 Google",
    "legs": [{
      "distance": {
        "text": "5 km",
        "value": 5000
      },
      "duration": {
        "text": "10 mins",
        "value": 600
      },
      "duration_in_traffic": {
        "text": "15 mins",
        "value": 900
      },
      "start_location": {
        "lat": 40.7128,
        "lng": -74.0060
      },
      "end_location": {
        "lat": 40.7614,
        "lng": -73.9776
      },
      "start_address": "New York, NY, USA",
      "end_address": "Empire State Building",
      "steps": [{
        "distance": {"text": "1 km", "value": 1000},
        "duration": {"text": "2 mins", "value": 120},
        "instructions": "Turn right onto Broadway",
        "maneuver": "turn-right",
        "coordinates": [[40.7128, -74.0060], [40.7130, -74.0058]],
        "travel_mode": "DRIVING",
        "transit_details": {}
      }]
    }],
    "traffic_speed": [{
      "speed": 45,
      "offset_meters": 0
    }],
    "fare": {
      "currency": "USD",
      "value": 2.75
    },
    "warnings": ["Construction on Broadway"],
    "overview_coordinates": [
      [40.7128, -74.0060],
      [40.7614, -73.9776]
    ]
  }],
  "optimized_waypoints": [
    "40.7527,-73.9772",
    "40.7589,-73.9851"
  ],
  "cached": false,
  "offline": false,
  "timestamp": "2024-02-20T12:00:00Z"
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| routes | array | List of available routes |
| routes[].summary | string | Brief route description |
| routes[].bounds | object | Geographic bounds of the route |
| routes[].legs | array | Route segments between waypoints |
| routes[].legs[].distance | object | Distance information |
| routes[].legs[].duration | object | Duration without traffic |
| routes[].legs[].duration_in_traffic | object | Duration with traffic |
| routes[].legs[].steps | array | Turn-by-turn directions |
| routes[].traffic_speed | array | Traffic speed data points |
| routes[].fare | object | Fare information for transit |
| routes[].warnings | array | Route warnings |
| optimized_waypoints | array | Waypoints in optimal order |
| cached | boolean | Whether response is from cache |
| offline | boolean | Whether using offline data |
| timestamp | string | Response generation time |

#### Error Responses

| Status Code | Description |
|-------------|-------------|
| 400 | Invalid request parameters |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 503 | Service temporarily unavailable |

#### Example Requests

1. Basic route:
```http
GET /directions?origin=40.7128,-74.0060&destination=40.7614,-73.9776
```

2. Optimized route with waypoints:
```http
GET /directions?origin=40.7128,-74.0060&destination=40.7614,-73.9776&waypoints=40.7527,-73.9772|40.7589,-73.9851&optimize_route=true
```

3. Future departure with traffic:
```http
GET /directions?origin=40.7128,-74.0060&destination=40.7614,-73.9776&departure_time=2024-02-21T09:00:00Z&traffic_model=pessimistic
```

## Caching

- Responses with traffic data are cached for 2 minutes
- Responses without traffic data are cached for 5 minutes
- Offline cache is available as fallback during API outages

## Rate Limiting

The service implements a token bucket rate limiter:
- Rate: 50 requests per minute
- Burst: 10 requests
- Daily limit: 2500 requests per client

When rate limited, the service returns a 429 status code.

## Best Practices

1. **Cache Usage**:
   - Use cached responses when possible
   - Include traffic data only when needed

2. **Route Optimization**:
   - Use `optimize_route=true` for routes with multiple waypoints
   - Consider time windows for traffic predictions

3. **Error Handling**:
   - Implement exponential backoff for retries
   - Handle offline mode gracefully

4. **Performance**:
   - Request only needed features
   - Use appropriate cache durations

## Changelog

### v1.1.0 (2024-02-20)
- Added waypoint optimization
- Added traffic predictions
- Enhanced place details
- Improved caching strategy

### v1.0.0 (2024-01-15)
- Initial release
- Basic directions functionality
- Rate limiting
- Basic caching