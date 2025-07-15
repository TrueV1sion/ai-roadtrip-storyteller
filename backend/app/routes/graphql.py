"""
GraphQL route integration with FastAPI.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Request, WebSocket
from strawberry.asgi import GraphQL
from strawberry.subscriptions import GRAPHQL_TRANSPORT_WS_PROTOCOL, GRAPHQL_WS_PROTOCOL

from backend.app.graphql.schema import schema
from backend.app.core.auth import get_current_user_optional
from backend.app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/graphql", tags=["GraphQL"])

# Create GraphQL app with WebSocket support
graphql_app = GraphQL(
    schema,
    subscription_protocols=[
        GRAPHQL_TRANSPORT_WS_PROTOCOL,
        GRAPHQL_WS_PROTOCOL,
    ],
)


@router.get("")
async def graphql_playground():
    """Serve GraphQL Playground for development."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>GraphQL Playground</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/css/index.css" />
        <script src="https://cdn.jsdelivr.net/npm/graphql-playground-react/build/static/js/middleware.js"></script>
    </head>
    <body>
        <div id="root"></div>
        <script>
            window.addEventListener('load', function() {
                GraphQLPlayground.init(document.getElementById('root'), {
                    endpoint: '/api/graphql',
                    subscriptionEndpoint: 'ws://localhost:8000/api/graphql',
                    settings: {
                        'request.credentials': 'include',
                        'schema.polling.enable': true,
                        'schema.polling.interval': 2000,
                    },
                    tabs: [
                        {
                            endpoint: '/api/graphql',
                            query: `# Welcome to AI Road Trip GraphQL API
# 
# Example queries:

# Get current user info
query Me {
  me {
    id
    email
    name
    journeyCount
    totalMiles
    favoritePersonality
  }
}

# Search for events
query SearchEvents {
  searchEvents(
    location: "San Francisco, CA"
    dateFrom: "2024-02-01T00:00:00Z"
    dateTo: "2024-03-01T00:00:00Z"
  ) {
    eventId
    eventName
    venueName
    eventDate
    personality
  }
}

# Start a journey
mutation StartJourney {
  startJourney(
    context: {
      origin: "San Francisco, CA"
      destination: "Los Angeles, CA"
      theme: ADVENTURE
      partySize: 4
    }
  ) {
    success
    journey {
      id
      personality
      distanceMiles
      durationMinutes
    }
  }
}

# Subscribe to journey updates
subscription JourneyUpdates {
  journeyUpdates(journeyId: "123") {
    updateType
    location {
      latitude
      longitude
      speedMph
    }
    timestamp
  }
}`
                        }
                    ]
                })
            })
        </script>
    </body>
    </html>
    """


@router.post("")
async def graphql_post(
    request: Request,
    user=Depends(get_current_user_optional)
):
    """Handle GraphQL POST requests."""
    request.state.user = user  # Add user to request state
    return await graphql_app.handle_request(request)


@router.websocket("")
async def graphql_websocket(
    websocket: WebSocket,
    user=Depends(get_current_user_optional)
):
    """Handle GraphQL WebSocket connections for subscriptions."""
    # Add user to WebSocket state
    websocket.state.user = user
    
    await graphql_app.handle_websocket(websocket)


# Middleware to add correlation ID to GraphQL requests
@router.middleware("http")
async def add_correlation_id(request: Request, call_next):
    """Add correlation ID to all GraphQL requests for tracing."""
    import uuid
    
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    
    return response