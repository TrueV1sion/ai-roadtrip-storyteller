"""
Enhanced OpenAPI Documentation Configuration
Provides comprehensive API documentation with rich examples, schemas, and interactive features
"""

from typing import Dict, Any, List, Optional
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.responses import HTMLResponse, JSONResponse
import json
from datetime import datetime, timezone
from pathlib import Path
try:
    import yaml
except ImportError:
    yaml = None

from ..core.config import settings


class OpenAPIEnhancer:
    """Enhanced OpenAPI documentation with comprehensive examples and schemas"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.base_url = "https://api.roadtripstoryteller.com"
        self.staging_url = "https://staging-api.roadtripstoryteller.com"
        self.local_url = "http://localhost:8000"
    
    def generate_enhanced_schema(self) -> Dict[str, Any]:
        """Generate enhanced OpenAPI schema with comprehensive documentation"""
        if self.app.openapi_schema:
            return self.app.openapi_schema
        
        # Generate base schema
        openapi_schema = get_openapi(
            title="AI Road Trip Storyteller API",
            version="1.0.0",
            description=self._get_enhanced_description(),
            routes=self.app.routes,
            tags=self._get_comprehensive_tags(),
            servers=self._get_server_configurations(),
        )
        
        # Enhance with security schemes
        openapi_schema["components"]["securitySchemes"] = self._get_security_schemes()
        
        # Add global security requirement
        openapi_schema["security"] = [{"bearerAuth": []}]
        
        # Add webhook specifications
        openapi_schema["webhooks"] = self._get_webhook_specifications()
        
        # Enhance with custom schemas and examples
        self._enhance_schemas(openapi_schema)
        
        # Add common responses
        openapi_schema["components"]["responses"] = self._get_common_responses()
        
        # Add request examples
        self._add_operation_examples(openapi_schema)
        
        # Add x-code-samples for each operation
        self._add_code_samples(openapi_schema)
        
        # Cache the schema
        self.app.openapi_schema = openapi_schema
        return openapi_schema
    
    def _get_enhanced_description(self) -> str:
        """Get enhanced API description with comprehensive overview"""
        return """
## 🚗 Welcome to the AI Road Trip Storyteller API

Transform every journey into an extraordinary adventure with AI-powered storytelling, voice interactions, and seamless travel integrations.

### 🌟 Key Features

#### **AI-Powered Storytelling**
- **Dynamic Content Generation**: Stories adapt in real-time based on location, weather, time of day, and journey context
- **Multiple Personalities**: Choose from 20+ voice personalities including Morgan Freeman, David Attenborough, and custom characters
- **Educational & Entertainment Modes**: From historical facts to whimsical tales
- **Multi-language Support**: Stories available in 10+ languages

#### **Voice Interaction System**
- **Natural Language Processing**: Conversational AI understands context and intent
- **Voice Commands**: Control the entire experience hands-free
- **Real-time Transcription**: Instant speech-to-text processing
- **Spatial Audio**: 3D audio positioning for immersive storytelling

#### **Smart Journey Features**
- **Route Optimization**: AI-powered route suggestions based on preferences
- **Points of Interest Detection**: Automatic discovery of nearby attractions
- **Weather-Aware Narratives**: Stories adapt to current conditions
- **Safety Monitoring**: Real-time alerts and emergency assistance

#### **Booking & Reservations**
- **Hotel Integration**: Real-time availability from 500,000+ properties
- **Restaurant Reservations**: Direct booking at 50,000+ restaurants
- **Activity Tickets**: Instant access to attractions and events
- **Commission Tracking**: Transparent revenue sharing for partners

### 📚 Getting Started

1. **Register**: Create an account at `/api/auth/register`
2. **Authenticate**: Get your JWT token via `/api/auth/login`
3. **Explore**: Use the token to access all API endpoints
4. **Build**: Integrate our SDKs for rapid development

### 🔐 Authentication

All API requests require JWT authentication:

```
Authorization: Bearer <your-jwt-token>
```

### ⚡ Rate Limits

| User Type | Requests/Hour | Burst Limit |
|-----------|--------------|-------------|
| Anonymous | 100 | 20 |
| Free | 1,000 | 100 |
| Premium | 10,000 | 500 |
| Enterprise | Unlimited | Custom |

### 🛠️ SDKs & Libraries

Official SDKs available for rapid integration:

- **Python**: `pip install roadtrip-storyteller`
- **JavaScript/Node**: `npm install @roadtrip/storyteller-sdk`
- **React Native**: `npm install @roadtrip/mobile-sdk`
- **Swift**: `pod 'RoadtripStoryteller'`
- **Kotlin**: `implementation 'com.roadtrip:storyteller-sdk:1.0.0'`

### 📊 API Status & Monitoring

- **Status Page**: https://status.roadtripstoryteller.com
- **Uptime**: 99.9% SLA for premium users
- **Response Time**: <100ms average latency
- **Health Check**: `/health` endpoint for monitoring

### 🤝 Support & Community

- **Documentation**: https://docs.roadtripstoryteller.com
- **Developer Portal**: https://developers.roadtripstoryteller.com
- **Discord Community**: https://discord.gg/roadtrip-dev
- **Support Email**: developers@roadtripstoryteller.com
- **Office Hours**: Weekly developer Q&A sessions

### 🚀 What's New

- **v1.0.0**: GA release with full feature set
- **Upcoming**: GraphQL API, WebSocket support, AR features
        """
    
    def _get_comprehensive_tags(self) -> List[Dict[str, Any]]:
        """Get comprehensive tag definitions with descriptions"""
        return [
            {
                "name": "Auth",
                "description": "Authentication and authorization endpoints. Manage user sessions, JWT tokens, and 2FA.",
                "externalDocs": {
                    "description": "Authentication guide",
                    "url": "https://docs.roadtripstoryteller.com/auth"
                }
            },
            {
                "name": "Story",
                "description": "AI story generation and management. Create dynamic, location-based narratives.",
                "externalDocs": {
                    "description": "Story API guide",
                    "url": "https://docs.roadtripstoryteller.com/stories"
                }
            },
            {
                "name": "Voice Assistant",
                "description": "Voice interaction and text-to-speech services. Process commands and generate audio.",
                "externalDocs": {
                    "description": "Voice integration guide",
                    "url": "https://docs.roadtripstoryteller.com/voice"
                }
            },
            {
                "name": "Bookings",
                "description": "Hotel, restaurant, and activity reservations. Real-time availability and booking.",
                "externalDocs": {
                    "description": "Booking integration guide",
                    "url": "https://docs.roadtripstoryteller.com/bookings"
                }
            },
            {
                "name": "Trip Planning",
                "description": "Create and manage road trips. Route optimization and itinerary planning.",
                "externalDocs": {
                    "description": "Trip planning guide",
                    "url": "https://docs.roadtripstoryteller.com/trips"
                }
            },
            {
                "name": "Users",
                "description": "User profile and preferences management. Personalization settings.",
                "externalDocs": {
                    "description": "User management guide",
                    "url": "https://docs.roadtripstoryteller.com/users"
                }
            },
            {
                "name": "Spatial Audio",
                "description": "3D audio positioning and immersive sound experiences.",
                "externalDocs": {
                    "description": "Spatial audio guide",
                    "url": "https://docs.roadtripstoryteller.com/spatial-audio"
                }
            },
            {
                "name": "AR",
                "description": "Augmented reality features for enhanced journey visualization.",
                "externalDocs": {
                    "description": "AR integration guide",
                    "url": "https://docs.roadtripstoryteller.com/ar"
                }
            },
            {
                "name": "Games",
                "description": "Interactive road trip games and challenges.",
                "externalDocs": {
                    "description": "Games API guide",
                    "url": "https://docs.roadtripstoryteller.com/games"
                }
            },
            {
                "name": "Analytics",
                "description": "Usage analytics and revenue tracking.",
                "externalDocs": {
                    "description": "Analytics guide",
                    "url": "https://docs.roadtripstoryteller.com/analytics"
                }
            },
            {
                "name": "Health Monitoring",
                "description": "System health checks and monitoring endpoints.",
                "externalDocs": {
                    "description": "Monitoring guide",
                    "url": "https://docs.roadtripstoryteller.com/monitoring"
                }
            },
            {
                "name": "Admin",
                "description": "Administrative endpoints for system management.",
                "externalDocs": {
                    "description": "Admin guide",
                    "url": "https://docs.roadtripstoryteller.com/admin"
                }
            }
        ]
    
    def _get_server_configurations(self) -> List[Dict[str, str]]:
        """Get server configurations with descriptions"""
        return [
            {
                "url": self.base_url,
                "description": "Production server - Stable API for production use"
            },
            {
                "url": self.staging_url,
                "description": "Staging server - Test new features before production"
            },
            {
                "url": self.local_url,
                "description": "Local development server - For local testing"
            },
            {
                "url": "https://{tenant}.api.roadtripstoryteller.com",
                "description": "Multi-tenant server",
                "variables": {
                    "tenant": {
                        "default": "demo",
                        "description": "Your tenant subdomain"
                    }
                }
            }
        ]
    
    def _get_security_schemes(self) -> Dict[str, Any]:
        """Get comprehensive security scheme definitions"""
        return {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT authentication token. Get token via /api/auth/login",
                "x-example": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            },
            "apiKey": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API key for service-to-service communication"
            },
            "oauth2": {
                "type": "oauth2",
                "flows": {
                    "authorizationCode": {
                        "authorizationUrl": f"{self.base_url}/oauth/authorize",
                        "tokenUrl": f"{self.base_url}/oauth/token",
                        "scopes": {
                            "read:stories": "Read story content",
                            "write:stories": "Create and modify stories",
                            "read:bookings": "View booking information",
                            "write:bookings": "Create and modify bookings",
                            "read:profile": "Read user profile",
                            "write:profile": "Modify user profile",
                            "admin": "Full administrative access"
                        }
                    }
                }
            }
        }
    
    def _get_webhook_specifications(self) -> Dict[str, Any]:
        """Get webhook specifications with examples"""
        return {
            "tripStarted": {
                "post": {
                    "requestBody": {
                        "description": "Trip started event notification",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/WebhookTripEvent"},
                                "example": {
                                    "event": "trip.started",
                                    "timestamp": "2024-01-01T00:00:00Z",
                                    "data": {
                                        "trip_id": "trip_123456",
                                        "user_id": "user_789",
                                        "start_location": {
                                            "latitude": 40.7128,
                                            "longitude": -74.0060,
                                            "name": "New York City"
                                        }
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Webhook processed successfully"},
                        "400": {"description": "Invalid webhook payload"},
                        "401": {"description": "Invalid webhook signature"}
                    }
                }
            },
            "storyGenerated": {
                "post": {
                    "requestBody": {
                        "description": "Story generated event notification",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/WebhookStoryEvent"}
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Webhook processed successfully"}
                    }
                }
            },
            "bookingConfirmed": {
                "post": {
                    "requestBody": {
                        "description": "Booking confirmed event notification",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/WebhookBookingEvent"}
                            }
                        }
                    },
                    "responses": {
                        "200": {"description": "Webhook processed successfully"}
                    }
                }
            }
        }
    
    def _enhance_schemas(self, openapi_schema: Dict[str, Any]):
        """Enhance schemas with detailed examples and descriptions"""
        if "components" not in openapi_schema:
            openapi_schema["components"] = {}
        
        if "schemas" not in openapi_schema["components"]:
            openapi_schema["components"]["schemas"] = {}
        
        # Add comprehensive webhook schemas
        openapi_schema["components"]["schemas"].update({
            "WebhookTripEvent": {
                "type": "object",
                "required": ["event", "timestamp", "data"],
                "properties": {
                    "event": {
                        "type": "string",
                        "enum": ["trip.started", "trip.updated", "trip.completed", "trip.cancelled"],
                        "example": "trip.started"
                    },
                    "timestamp": {
                        "type": "string",
                        "format": "date-time",
                        "example": "2024-01-01T00:00:00Z"
                    },
                    "data": {
                        "type": "object",
                        "properties": {
                            "trip_id": {
                                "type": "string",
                                "format": "uuid",
                                "example": "550e8400-e29b-41d4-a716-446655440000"
                            },
                            "user_id": {
                                "type": "string",
                                "format": "uuid"
                            },
                            "status": {
                                "type": "string",
                                "enum": ["planned", "active", "completed", "cancelled"]
                            },
                            "start_location": {
                                "$ref": "#/components/schemas/Location"
                            },
                            "current_location": {
                                "$ref": "#/components/schemas/Location"
                            }
                        }
                    },
                    "signature": {
                        "type": "string",
                        "description": "HMAC-SHA256 signature for verification",
                        "example": "sha256=abc123..."
                    }
                }
            },
            "Location": {
                "type": "object",
                "required": ["latitude", "longitude"],
                "properties": {
                    "latitude": {
                        "type": "number",
                        "format": "float",
                        "minimum": -90,
                        "maximum": 90,
                        "example": 40.7128
                    },
                    "longitude": {
                        "type": "number",
                        "format": "float",
                        "minimum": -180,
                        "maximum": 180,
                        "example": -74.0060
                    },
                    "name": {
                        "type": "string",
                        "example": "New York City"
                    },
                    "address": {
                        "type": "string",
                        "example": "123 Main St, New York, NY 10001"
                    }
                }
            },
            "Error": {
                "type": "object",
                "required": ["detail"],
                "properties": {
                    "detail": {
                        "type": "string",
                        "description": "Human-readable error message",
                        "example": "Invalid authentication credentials"
                    },
                    "type": {
                        "type": "string",
                        "description": "Error type for programmatic handling",
                        "example": "authentication_error"
                    },
                    "loc": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Location of the error in the request",
                        "example": ["body", "email"]
                    },
                    "msg": {
                        "type": "string",
                        "description": "Technical error message",
                        "example": "field required"
                    },
                    "ctx": {
                        "type": "object",
                        "description": "Additional error context",
                        "additionalProperties": true
                    }
                }
            }
        })
        
        # Enhance existing schemas with examples
        for schema_name, schema in openapi_schema["components"]["schemas"].items():
            if "example" not in schema and "properties" in schema:
                # Auto-generate examples based on property types
                schema["example"] = self._generate_schema_example(schema)
    
    def _generate_schema_example(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Generate example data for a schema"""
        example = {}
        
        if "properties" not in schema:
            return example
        
        for prop_name, prop_schema in schema["properties"].items():
            if "example" in prop_schema:
                example[prop_name] = prop_schema["example"]
            elif prop_schema.get("type") == "string":
                if prop_schema.get("format") == "email":
                    example[prop_name] = "user@example.com"
                elif prop_schema.get("format") == "date-time":
                    example[prop_name] = datetime.now(timezone.utc).isoformat()
                elif prop_schema.get("format") == "uuid":
                    example[prop_name] = "550e8400-e29b-41d4-a716-446655440000"
                elif "password" in prop_name.lower():
                    example[prop_name] = "SecurePassword123!"
                else:
                    example[prop_name] = f"example_{prop_name}"
            elif prop_schema.get("type") == "integer":
                example[prop_name] = 42
            elif prop_schema.get("type") == "number":
                example[prop_name] = 99.99
            elif prop_schema.get("type") == "boolean":
                example[prop_name] = True
            elif prop_schema.get("type") == "array":
                example[prop_name] = ["example_item"]
            elif prop_schema.get("type") == "object":
                example[prop_name] = {}
        
        return example
    
    def _get_common_responses(self) -> Dict[str, Any]:
        """Get common response definitions"""
        return {
            "UnauthorizedError": {
                "description": "Authentication token is missing or invalid",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"},
                        "examples": {
                            "missing_token": {
                                "summary": "Missing authentication token",
                                "value": {
                                    "detail": "Authentication credentials were not provided",
                                    "type": "authentication_error"
                                }
                            },
                            "invalid_token": {
                                "summary": "Invalid token",
                                "value": {
                                    "detail": "Invalid authentication credentials",
                                    "type": "authentication_error"
                                }
                            },
                            "expired_token": {
                                "summary": "Expired token",
                                "value": {
                                    "detail": "Token has expired",
                                    "type": "token_expired"
                                }
                            }
                        }
                    }
                }
            },
            "ForbiddenError": {
                "description": "User lacks required permissions",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"},
                        "example": {
                            "detail": "You do not have permission to perform this action",
                            "type": "permission_denied"
                        }
                    }
                }
            },
            "NotFoundError": {
                "description": "Resource not found",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"},
                        "example": {
                            "detail": "The requested resource was not found",
                            "type": "not_found"
                        }
                    }
                }
            },
            "ValidationError": {
                "description": "Request validation failed",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"},
                        "examples": {
                            "missing_field": {
                                "summary": "Required field missing",
                                "value": {
                                    "detail": "Validation error",
                                    "type": "validation_error",
                                    "loc": ["body", "email"],
                                    "msg": "field required"
                                }
                            },
                            "invalid_format": {
                                "summary": "Invalid field format",
                                "value": {
                                    "detail": "Validation error",
                                    "type": "validation_error",
                                    "loc": ["body", "email"],
                                    "msg": "invalid email format"
                                }
                            }
                        }
                    }
                }
            },
            "RateLimitError": {
                "description": "Rate limit exceeded",
                "headers": {
                    "X-RateLimit-Limit": {
                        "description": "Request limit per hour",
                        "schema": {"type": "integer", "example": 1000}
                    },
                    "X-RateLimit-Remaining": {
                        "description": "Remaining requests",
                        "schema": {"type": "integer", "example": 0}
                    },
                    "X-RateLimit-Reset": {
                        "description": "Reset time (Unix timestamp)",
                        "schema": {"type": "integer", "example": 1704067200}
                    },
                    "Retry-After": {
                        "description": "Seconds until rate limit resets",
                        "schema": {"type": "integer", "example": 3600}
                    }
                },
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"},
                        "example": {
                            "detail": "Rate limit exceeded. Try again in 3600 seconds.",
                            "type": "rate_limit_exceeded"
                        }
                    }
                }
            },
            "ServerError": {
                "description": "Internal server error",
                "content": {
                    "application/json": {
                        "schema": {"$ref": "#/components/schemas/Error"},
                        "example": {
                            "detail": "An unexpected error occurred. Please try again later.",
                            "type": "internal_error"
                        }
                    }
                }
            }
        }
    
    def _add_operation_examples(self, openapi_schema: Dict[str, Any]):
        """Add request/response examples to operations"""
        for path, methods in openapi_schema.get("paths", {}).items():
            for method, operation in methods.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    # Add response examples
                    self._enhance_operation_responses(operation)
                    
                    # Add request body examples
                    if "requestBody" in operation:
                        self._enhance_request_body(operation["requestBody"])
    
    def _enhance_operation_responses(self, operation: Dict[str, Any]):
        """Enhance operation responses with examples"""
        if "responses" not in operation:
            return
        
        # Add examples to successful responses
        for status_code, response in operation["responses"].items():
            if status_code.startswith("2"):  # 2xx responses
                if "content" in response and "application/json" in response["content"]:
                    content = response["content"]["application/json"]
                    if "examples" not in content and "schema" in content:
                        # Generate example based on schema
                        if "$ref" in content["schema"]:
                            # Reference to a schema - examples will be in the schema definition
                            pass
                        else:
                            content["example"] = self._generate_schema_example(content["schema"])
    
    def _enhance_request_body(self, request_body: Dict[str, Any]):
        """Enhance request body with examples"""
        if "content" in request_body and "application/json" in request_body["content"]:
            content = request_body["content"]["application/json"]
            if "examples" not in content and "example" not in content and "schema" in content:
                content["example"] = self._generate_schema_example(content["schema"])
    
    def _add_code_samples(self, openapi_schema: Dict[str, Any]):
        """Add code samples to each operation"""
        for path, methods in openapi_schema.get("paths", {}).items():
            for method, operation in methods.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    operation["x-code-samples"] = self._generate_code_samples(
                        method, path, operation
                    )
    
    def _generate_code_samples(self, method: str, path: str, operation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate code samples for an operation"""
        samples = []
        
        # cURL sample
        curl_sample = self._generate_curl_sample(method, path, operation)
        samples.append({
            "lang": "cURL",
            "label": "cURL",
            "source": curl_sample
        })
        
        # Python sample
        python_sample = self._generate_python_sample(method, path, operation)
        samples.append({
            "lang": "Python",
            "label": "Python",
            "source": python_sample
        })
        
        # JavaScript sample
        js_sample = self._generate_javascript_sample(method, path, operation)
        samples.append({
            "lang": "JavaScript",
            "label": "JavaScript",
            "source": js_sample
        })
        
        return samples
    
    def _generate_curl_sample(self, method: str, path: str, operation: Dict[str, Any]) -> str:
        """Generate cURL code sample"""
        curl_parts = [f"curl -X {method.upper()} '{self.base_url}{path}'"]
        
        # Add authentication header if required
        if operation.get("security"):
            curl_parts.append("  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'")
        
        # Add content type for request body
        if "requestBody" in operation:
            curl_parts.append("  -H 'Content-Type: application/json'")
            # Add example request body
            if "content" in operation["requestBody"]:
                content = operation["requestBody"]["content"].get("application/json", {})
                if "example" in content:
                    curl_parts.append(f"  -d '{json.dumps(content['example'])}'")
        
        return " \\\n".join(curl_parts)
    
    def _generate_python_sample(self, method: str, path: str, operation: Dict[str, Any]) -> str:
        """Generate Python code sample"""
        python_lines = [
            "import requests",
            "",
            f"url = '{self.base_url}{path}'"
        ]
        
        # Add headers
        if operation.get("security"):
            python_lines.append("headers = {'Authorization': 'Bearer YOUR_ACCESS_TOKEN'}")
        else:
            python_lines.append("headers = {}")
        
        # Add request body
        if "requestBody" in operation and "content" in operation["requestBody"]:
            content = operation["requestBody"]["content"].get("application/json", {})
            if "example" in content:
                python_lines.append(f"data = {json.dumps(content['example'], indent=4)}")
        
        # Make request
        method_lower = method.lower()
        if "requestBody" in operation:
            python_lines.append(f"response = requests.{method_lower}(url, headers=headers, json=data)")
        else:
            python_lines.append(f"response = requests.{method_lower}(url, headers=headers)")
        
        python_lines.extend([
            "",
            "print(response.status_code)",
            "print(response.json())"
        ])
        
        return "\n".join(python_lines)
    
    def _generate_javascript_sample(self, method: str, path: str, operation: Dict[str, Any]) -> str:
        """Generate JavaScript code sample"""
        js_lines = [f"const url = '{self.base_url}{path}';"]
        
        # Build fetch options
        js_lines.append("const options = {")
        js_lines.append(f"  method: '{method.upper()}',")
        js_lines.append("  headers: {")
        
        # Add headers
        if operation.get("security"):
            js_lines.append("    'Authorization': 'Bearer YOUR_ACCESS_TOKEN',")
        
        if "requestBody" in operation:
            js_lines.append("    'Content-Type': 'application/json',")
        
        js_lines.append("  },")
        
        # Add request body
        if "requestBody" in operation and "content" in operation["requestBody"]:
            content = operation["requestBody"]["content"].get("application/json", {})
            if "example" in content:
                js_lines.append(f"  body: JSON.stringify({json.dumps(content['example'], indent=4)})")
        
        js_lines.append("};")
        js_lines.append("")
        js_lines.extend([
            "fetch(url, options)",
            "  .then(response => response.json())",
            "  .then(data => console.log(data))",
            "  .catch(error => console.error('Error:', error));"
        ])
        
        return "\n".join(js_lines)


def setup_enhanced_openapi(app: FastAPI):
    """Setup enhanced OpenAPI documentation"""
    enhancer = OpenAPIEnhancer(app)
    
    # Override the default OpenAPI function
    app.openapi = enhancer.generate_enhanced_schema
    
    # Custom Swagger UI with enhanced styling
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui():
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{app.title} - Interactive API Documentation",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
            swagger_favicon_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/favicon-32x32.png"
        )
    
    # Enhanced ReDoc with custom options
    @app.get("/redoc", include_in_schema=False)
    async def enhanced_redoc():
        redoc_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{app.title} - API Reference</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                }}
                redoc {{
                    display: block;
                }}
            </style>
        </head>
        <body>
            <redoc 
                spec-url="{app.openapi_url}"
                expand-responses="200,201"
                json-sample-expand-level="2"
                hide-download-button="false"
                hide-hostname="false"
                required-props-first="true"
                path-in-middle-panel="false"
                untrusted-spec="false"
                show-extensions="true"
                scroll-y-offset="nav"
                disable-search="false"
                theme='{{"colors": {{"primary": {{"main": "#1a1a2e"}}}}}}'>
            </redoc>
            <script src="https://cdn.jsdelivr.net/npm/redoc@2/bundles/redoc.standalone.js"></script>
        </body>
        </html>
        """
        return HTMLResponse(content=redoc_html)
    
    # Export OpenAPI specification in different formats
    @app.get("/openapi.json", include_in_schema=False)
    async def get_openapi_json():
        """Export OpenAPI specification as JSON"""
        return JSONResponse(
            content=app.openapi(),
            headers={
                "Content-Disposition": "inline; filename=roadtrip-openapi.json"
            }
        )
    
    @app.get("/openapi.yaml", include_in_schema=False)
    async def get_openapi_yaml():
        """Export OpenAPI specification as YAML"""
        if yaml is None:
            return JSONResponse(
                content={"error": "YAML support not installed. Run: pip install pyyaml"},
                status_code=500
            )
        
        openapi_dict = app.openapi()
        yaml_content = yaml.dump(openapi_dict, default_flow_style=False, sort_keys=False)
        
        return HTMLResponse(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": "inline; filename=roadtrip-openapi.yaml"
            }
        )