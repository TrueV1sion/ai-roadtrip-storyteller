"""
Custom OpenAPI documentation configuration
Enhances the auto-generated API documentation with detailed descriptions,
examples, and better organization
"""

from typing import Dict, Any
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """
    Generate custom OpenAPI schema with enhanced documentation
    """
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title="AI Road Trip Storyteller API",
        version="1.0.0",
        description="""
## Overview

The AI Road Trip Storyteller API powers an innovative travel companion application that transforms ordinary road trips into extraordinary adventures through AI-generated storytelling, voice interactions, and seamless booking integrations.

## Key Features

### 🎭 **AI Storytelling**
- Dynamic story generation based on location, weather, and time
- Multiple storytelling personalities (Morgan Freeman, David Attenborough, etc.)
- Real-time adaptation to journey context
- Educational and entertainment modes

### 🎙️ **Voice Interaction**
- Natural language processing for voice commands
- Text-to-speech with 20+ character voices
- Real-time voice streaming
- Multi-language support

### 📍 **Location Services**
- GPS-based storytelling triggers
- Points of interest detection
- Route optimization
- Geofencing for location-based content

### 🎫 **Booking Integration**
- Real-time hotel availability and booking
- Activity and attraction reservations
- Restaurant recommendations and reservations
- Integrated payment processing

### 🚗 **Journey Features**
- Trip planning and optimization
- Real-time traffic and weather updates
- Safety alerts and emergency assistance
- Journey history and highlights

## Authentication

The API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Getting a Token

1. Register a new account via `/api/auth/register`
2. Login with credentials via `/api/auth/login`
3. Use the returned access token for authenticated requests
4. Refresh tokens via `/api/auth/refresh` when expired

## Rate Limiting

API endpoints are rate-limited to ensure fair usage:

- **Anonymous users**: 100 requests per hour
- **Authenticated users**: 1000 requests per hour
- **Premium users**: 10000 requests per hour

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Time when limit resets (Unix timestamp)

## Error Handling

The API uses standard HTTP status codes and returns detailed error messages:

### Error Response Format
```json
{
    "detail": "Error description",
    "type": "error_type",
    "loc": ["field", "name"],
    "msg": "Human-readable message",
    "ctx": {"additional": "context"}
}
```

### Common Status Codes
- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Webhooks

The API supports webhooks for real-time notifications:

### Available Webhook Events
- `trip.started`: New trip initiated
- `trip.completed`: Trip finished
- `booking.confirmed`: Booking successfully processed
- `story.generated`: New story segment created
- `voice.processed`: Voice command processed

### Webhook Payload Format
```json
{
    "event": "event.type",
    "timestamp": "2024-01-01T00:00:00Z",
    "data": {
        // Event-specific data
    }
}
```

## SDK Support

Official SDKs are available for:
- Python: `pip install roadtrip-storyteller`
- JavaScript/TypeScript: `npm install @roadtrip/storyteller-sdk`
- React Native: `npm install @roadtrip/mobile-sdk`

## Support

- **Documentation**: https://docs.roadtripstoryteller.com
- **Status Page**: https://status.roadtripstoryteller.com
- **Support Email**: support@roadtripstoryteller.com
- **Developer Discord**: https://discord.gg/roadtrip-dev
        """,
        routes=app.routes,
        tags=[
            {
                "name": "Auth",
                "description": "Authentication and authorization endpoints",
                "externalDocs": {
                    "description": "Auth documentation",
                    "url": "https://docs.roadtripstoryteller.com/auth"
                }
            },
            {
                "name": "Story",
                "description": "AI story generation and management",
                "externalDocs": {
                    "description": "Story API guide",
                    "url": "https://docs.roadtripstoryteller.com/stories"
                }
            },
            {
                "name": "Voice Assistant",
                "description": "Voice interaction and text-to-speech services"
            },
            {
                "name": "Bookings",
                "description": "Hotel, activity, and restaurant reservations"
            },
            {
                "name": "Journey",
                "description": "Trip planning and management"
            },
            {
                "name": "Users",
                "description": "User profile and preferences management"
            },
            {
                "name": "MVP Voice",
                "description": "Simplified voice endpoints for MVP testing"
            },
            {
                "name": "Health Monitoring",
                "description": "System health and monitoring endpoints"
            }
        ],
        servers=[
            {
                "url": "https://api.roadtripstoryteller.com",
                "description": "Production server"
            },
            {
                "url": "https://staging-api.roadtripstoryteller.com",
                "description": "Staging server"
            },
            {
                "url": "http://localhost:8000",
                "description": "Local development server"
            }
        ],
        components={
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                    "description": "JWT authentication token"
                },
                "apiKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "API key for service-to-service communication"
                }
            }
        }
    )
    
    # Add global security requirement
    openapi_schema["security"] = [{"bearerAuth": []}]
    
    # Add webhook specifications
    openapi_schema["webhooks"] = {
        "tripStarted": {
            "post": {
                "requestBody": {
                    "description": "Trip started event",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/WebhookTripEvent"
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Webhook processed successfully"
                    }
                }
            }
        }
    }
    
    # Add custom schemas
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    if "schemas" not in openapi_schema["components"]:
        openapi_schema["components"]["schemas"] = {}
    
    # Add example schemas
    openapi_schema["components"]["schemas"].update({
        "WebhookTripEvent": {
            "type": "object",
            "required": ["event", "timestamp", "data"],
            "properties": {
                "event": {
                    "type": "string",
                    "example": "trip.started"
                },
                "timestamp": {
                    "type": "string",
                    "format": "date-time"
                },
                "data": {
                    "type": "object",
                    "properties": {
                        "trip_id": {
                            "type": "string",
                            "format": "uuid"
                        },
                        "user_id": {
                            "type": "string",
                            "format": "uuid"
                        },
                        "start_location": {
                            "type": "object",
                            "properties": {
                                "latitude": {"type": "number"},
                                "longitude": {"type": "number"}
                            }
                        }
                    }
                }
            }
        }
    })
    
    # Add common responses
    openapi_schema["components"]["responses"] = {
        "UnauthorizedError": {
            "description": "Authentication token is missing or invalid",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "Invalid authentication credentials"
                            }
                        }
                    }
                }
            }
        },
        "RateLimitError": {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "detail": {
                                "type": "string",
                                "example": "Rate limit exceeded. Try again in 60 seconds."
                            }
                        }
                    }
                },
                "headers": {
                    "X-RateLimit-Limit": {
                        "description": "Request limit per hour",
                        "schema": {"type": "integer"}
                    },
                    "X-RateLimit-Remaining": {
                        "description": "Remaining requests",
                        "schema": {"type": "integer"}
                    },
                    "X-RateLimit-Reset": {
                        "description": "Reset time (Unix timestamp)",
                        "schema": {"type": "integer"}
                    }
                }
            }
        }
    }
    
    # Cache the schema
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def get_custom_swagger_ui_html(
    *,
    openapi_url: str,
    title: str,
    oauth2_redirect_url: str = None,
    swagger_js_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
    swagger_css_url: str = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    swagger_favicon_url: str = "https://fastapi.tiangolo.com/img/favicon.png"
) -> HTMLResponse:
    """
    Generate custom Swagger UI with branding
    """
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <link type="text/css" rel="stylesheet" href="{swagger_css_url}">
        <link rel="shortcut icon" href="{swagger_favicon_url}">
        <title>{title}</title>
        <style>
            .swagger-ui .topbar {{
                background-color: #1a1a2e;
            }}
            .swagger-ui .topbar .download-url-wrapper {{
                display: none;
            }}
            .swagger-ui .info .title {{
                color: #1a1a2e;
            }}
            .swagger-ui .scheme-container {{
                background-color: #f5f5f5;
                padding: 15px;
                border-radius: 5px;
            }}
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="{swagger_js_url}"></script>
        <script>
        const ui = SwaggerUIBundle({{
            url: '{openapi_url}',
            dom_id: '#swagger-ui',
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset
            ],
            layout: "BaseLayout",
            deepLinking: true,
            showExtensions: true,
            showCommonExtensions: true,
            tryItOutEnabled: true,
            supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch'],
            onComplete: function() {{
                console.log("Swagger UI loaded");
            }}
        }})
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


def setup_openapi_docs(app: FastAPI):
    """
    Configure custom OpenAPI documentation endpoints
    """
    # Override the default OpenAPI function
    app.openapi = lambda: custom_openapi(app)
    
    # Custom Swagger UI
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return get_custom_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - API Documentation"
        )
    
    # Custom ReDoc
    @app.get("/redoc", include_in_schema=False)
    async def redoc_html():
        return get_redoc_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - API Documentation",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
        )
    
    # API documentation in JSON format
    @app.get("/openapi.json", include_in_schema=False)
    async def openapi_json():
        return app.openapi()
    
    # Postman collection export
    @app.get("/api/docs/postman", include_in_schema=False)
    async def export_postman_collection():
        """Export API documentation as Postman collection"""
        openapi = app.openapi()
        
        # Convert OpenAPI to Postman Collection format
        postman_collection = {
            "info": {
                "name": openapi["info"]["title"],
                "description": openapi["info"]["description"],
                "version": openapi["info"]["version"],
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [],
            "auth": {
                "type": "bearer",
                "bearer": [
                    {
                        "key": "token",
                        "value": "{{access_token}}",
                        "type": "string"
                    }
                ]
            },
            "variable": [
                {
                    "key": "base_url",
                    "value": "https://api.roadtripstoryteller.com",
                    "type": "string"
                },
                {
                    "key": "access_token",
                    "value": "",
                    "type": "string"
                }
            ]
        }
        
        # Group endpoints by tags
        tag_groups = {}
        for path, methods in openapi.get("paths", {}).items():
            for method, operation in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    tags = operation.get("tags", ["Uncategorized"])
                    tag = tags[0] if tags else "Uncategorized"
                    
                    if tag not in tag_groups:
                        tag_groups[tag] = {
                            "name": tag,
                            "item": []
                        }
                    
                    # Create Postman request
                    request = {
                        "name": operation.get("summary", f"{method.upper()} {path}"),
                        "request": {
                            "method": method.upper(),
                            "header": [],
                            "url": {
                                "raw": "{{base_url}}" + path,
                                "host": ["{{base_url}}"],
                                "path": path.strip("/").split("/")
                            }
                        }
                    }
                    
                    # Add request body if present
                    if "requestBody" in operation:
                        content = operation["requestBody"].get("content", {})
                        if "application/json" in content:
                            request["request"]["body"] = {
                                "mode": "raw",
                                "raw": "{}",
                                "options": {
                                    "raw": {
                                        "language": "json"
                                    }
                                }
                            }
                            request["request"]["header"].append({
                                "key": "Content-Type",
                                "value": "application/json"
                            })
                    
                    tag_groups[tag]["item"].append(request)
        
        # Add tag groups to collection
        postman_collection["item"] = list(tag_groups.values())
        
        return postman_collection