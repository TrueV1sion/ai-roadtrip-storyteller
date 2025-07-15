"""
API Documentation Router
Provides additional documentation endpoints and interactive examples
"""

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from typing import Dict, Any, Optional
import json
from pathlib import Path

from ..core.auth import get_current_user_optional
from ..models.user import User
from .api_examples import get_api_examples, generate_example_markdown

router = APIRouter(prefix="/api/docs", tags=["Documentation"])


@router.get("/", response_class=HTMLResponse)
async def api_documentation_home():
    """
    Interactive API documentation home page
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI Road Trip Storyteller - API Documentation</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                background-color: #1a1a2e;
                color: white;
                padding: 30px 0;
                text-align: center;
                margin-bottom: 40px;
            }
            .header h1 {
                margin: 0;
                font-size: 2.5em;
            }
            .header p {
                margin: 10px 0 0;
                opacity: 0.9;
            }
            .card {
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: box-shadow 0.3s;
            }
            .card:hover {
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }
            .card h2 {
                margin-top: 0;
                color: #1a1a2e;
            }
            .quick-links {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 40px;
            }
            .link-card {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                text-decoration: none;
                color: #333;
                transition: all 0.3s;
            }
            .link-card:hover {
                background: #e9ecef;
                transform: translateY(-2px);
            }
            .link-card h3 {
                margin: 0 0 10px;
                color: #1a1a2e;
            }
            .code-block {
                background: #f6f8fa;
                border: 1px solid #e1e4e8;
                border-radius: 6px;
                padding: 16px;
                overflow-x: auto;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 14px;
            }
            .endpoint-list {
                list-style: none;
                padding: 0;
            }
            .endpoint-list li {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            .endpoint-list li:last-child {
                border-bottom: none;
            }
            .method {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 12px;
                margin-right: 10px;
            }
            .method.get { background: #61affe; color: white; }
            .method.post { background: #49cc90; color: white; }
            .method.put { background: #fca130; color: white; }
            .method.delete { background: #f93e3e; color: white; }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="container">
                <h1>AI Road Trip Storyteller API</h1>
                <p>Transform your journey into an adventure</p>
            </div>
        </div>
        
        <div class="container">
            <div class="quick-links">
                <a href="/docs" class="link-card">
                    <h3>📘 Swagger UI</h3>
                    <p>Interactive API explorer with try-it-out functionality</p>
                </a>
                <a href="/redoc" class="link-card">
                    <h3>📗 ReDoc</h3>
                    <p>Clean, readable API reference documentation</p>
                </a>
                <a href="/api/docs/postman" class="link-card">
                    <h3>📮 Postman Collection</h3>
                    <p>Download ready-to-use Postman collection</p>
                </a>
                <a href="/api/docs/examples" class="link-card">
                    <h3>💡 Code Examples</h3>
                    <p>Sample code in multiple languages</p>
                </a>
            </div>
            
            <div class="card">
                <h2>🚀 Quick Start</h2>
                <p>Get started with the AI Road Trip Storyteller API in minutes:</p>
                
                <h3>1. Register an Account</h3>
                <div class="code-block">
curl -X POST https://api.roadtripstoryteller.com/api/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{"email": "you@example.com", "password": "YourSecurePassword123!"}'
                </div>
                
                <h3>2. Authenticate</h3>
                <div class="code-block">
curl -X POST https://api.roadtripstoryteller.com/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email": "you@example.com", "password": "YourSecurePassword123!"}'
                </div>
                
                <h3>3. Make Your First Request</h3>
                <div class="code-block">
curl -X POST https://api.roadtripstoryteller.com/api/story/generate \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"latitude": 40.7128, "longitude": -74.0060, "story_type": "historical"}'
                </div>
            </div>
            
            <div class="card">
                <h2>🔑 Key Features</h2>
                <ul class="endpoint-list">
                    <li>
                        <span class="method post">POST</span>
                        <strong>/api/story/generate</strong> - Generate AI stories based on location
                    </li>
                    <li>
                        <span class="method post">POST</span>
                        <strong>/api/voice/command</strong> - Process voice commands
                    </li>
                    <li>
                        <span class="method get">GET</span>
                        <strong>/api/bookings/hotels/search</strong> - Search for nearby hotels
                    </li>
                    <li>
                        <span class="method post">POST</span>
                        <strong>/api/trips/create</strong> - Plan a new road trip
                    </li>
                    <li>
                        <span class="method get">GET</span>
                        <strong>/api/voice/personalities</strong> - List available voice personalities
                    </li>
                </ul>
            </div>
            
            <div class="card">
                <h2>📚 Documentation Resources</h2>
                <ul>
                    <li><a href="/api/docs/authentication">Authentication Guide</a></li>
                    <li><a href="/api/docs/rate-limits">Rate Limiting Information</a></li>
                    <li><a href="/api/docs/webhooks">Webhook Configuration</a></li>
                    <li><a href="/api/docs/errors">Error Handling Reference</a></li>
                    <li><a href="/api/docs/changelog">API Changelog</a></li>
                </ul>
            </div>
            
            <div class="card">
                <h2>🛠️ SDKs & Tools</h2>
                <p>Official SDKs make integration even easier:</p>
                <ul>
                    <li><strong>Python:</strong> <code>pip install roadtrip-storyteller</code></li>
                    <li><strong>JavaScript:</strong> <code>npm install @roadtrip/storyteller-sdk</code></li>
                    <li><strong>React Native:</strong> <code>npm install @roadtrip/mobile-sdk</code></li>
                </ul>
            </div>
            
            <div class="card">
                <h2>💬 Need Help?</h2>
                <p>We're here to help you build amazing experiences:</p>
                <ul>
                    <li>📧 Email: <a href="mailto:developers@roadtripstoryteller.com">developers@roadtripstoryteller.com</a></li>
                    <li>💬 Discord: <a href="https://discord.gg/roadtrip-dev">Join our developer community</a></li>
                    <li>📖 Full Docs: <a href="https://docs.roadtripstoryteller.com">docs.roadtripstoryteller.com</a></li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/examples", response_class=HTMLResponse)
async def api_examples_page():
    """
    Interactive code examples page
    """
    examples = get_api_examples()
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>API Code Examples - AI Road Trip Storyteller</title>
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f5f5;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }
            .header {
                background-color: #1a1a2e;
                color: white;
                padding: 30px 0;
                text-align: center;
                margin-bottom: 40px;
            }
            .header h1 {
                margin: 0;
                font-size: 2.5em;
            }
            .tabs {
                display: flex;
                border-bottom: 2px solid #ddd;
                margin-bottom: 20px;
            }
            .tab {
                padding: 10px 20px;
                cursor: pointer;
                background: none;
                border: none;
                font-size: 16px;
                transition: all 0.3s;
            }
            .tab.active {
                border-bottom: 3px solid #1a1a2e;
                color: #1a1a2e;
                font-weight: bold;
            }
            .example-section {
                display: none;
            }
            .example-section.active {
                display: block;
            }
            .example-card {
                background: white;
                border-radius: 8px;
                padding: 20px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .example-card h3 {
                margin-top: 0;
                color: #1a1a2e;
            }
            .language-tabs {
                display: flex;
                gap: 10px;
                margin-bottom: 10px;
            }
            .language-tab {
                padding: 5px 15px;
                background: #f0f0f0;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                transition: all 0.3s;
            }
            .language-tab.active {
                background: #1a1a2e;
                color: white;
            }
            .code-content {
                display: none;
            }
            .code-content.active {
                display: block;
            }
            pre {
                margin: 0;
                border-radius: 4px;
                overflow-x: auto;
            }
            .response-example {
                margin-top: 20px;
            }
            .response-example h4 {
                margin-bottom: 10px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="container">
                <h1>API Code Examples</h1>
                <p>Ready-to-use code snippets in multiple languages</p>
            </div>
        </div>
        
        <div class="container">
            <div class="tabs">
    """
    
    # Add category tabs
    for i, category in enumerate(examples.keys()):
        active_class = "active" if i == 0 else ""
        html_content += f'<button class="tab {active_class}" onclick="showCategory(\'{category}\')">{category}</button>'
    
    html_content += """
            </div>
    """
    
    # Add example sections
    for i, (category, category_examples) in enumerate(examples.items()):
        active_class = "active" if i == 0 else ""
        html_content += f'<div class="example-section {active_class}" id="{category}">'
        
        for key, example in category_examples.items():
            html_content += f"""
            <div class="example-card">
                <h3>{example.title}</h3>
                <p>{example.description}</p>
                
                <div class="language-tabs">
                    <button class="language-tab active" onclick="showLanguage('{key}', 'curl')">cURL</button>
                    <button class="language-tab" onclick="showLanguage('{key}', 'python')">Python</button>
                    <button class="language-tab" onclick="showLanguage('{key}', 'javascript')">JavaScript</button>
                </div>
                
                <div class="code-content active" id="{key}-curl">
                    <pre><code class="language-bash">{example.curl_example.strip()}</code></pre>
                </div>
                
                <div class="code-content" id="{key}-python">
                    <pre><code class="language-python">{example.python_example.strip()}</code></pre>
                </div>
                
                <div class="code-content" id="{key}-javascript">
                    <pre><code class="language-javascript">{example.javascript_example.strip()}</code></pre>
                </div>
                
                <div class="response-example">
                    <h4>Example Response</h4>
                    <pre><code class="language-json">{json.dumps(example.response_example, indent=2)}</code></pre>
                </div>
            </div>
            """
        
        html_content += "</div>"
    
    html_content += """
        </div>
        
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-json.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-javascript.min.js"></script>
        
        <script>
            function showCategory(category) {
                // Hide all sections
                document.querySelectorAll('.example-section').forEach(section => {
                    section.classList.remove('active');
                });
                document.querySelectorAll('.tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                
                // Show selected section
                document.getElementById(category).classList.add('active');
                event.target.classList.add('active');
            }
            
            function showLanguage(exampleKey, language) {
                // Hide all code contents for this example
                document.querySelectorAll(`[id^="${exampleKey}-"]`).forEach(content => {
                    content.classList.remove('active');
                });
                
                // Remove active class from all language tabs in this example
                event.target.parentElement.querySelectorAll('.language-tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                
                // Show selected language
                document.getElementById(`${exampleKey}-${language}`).classList.add('active');
                event.target.classList.add('active');
                
                // Re-highlight syntax
                Prism.highlightAll();
            }
            
            // Initial syntax highlighting
            Prism.highlightAll();
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@router.get("/postman")
async def download_postman_collection(request: Request):
    """
    Download Postman collection for the API
    """
    # Get the Postman collection from the main app
    postman_url = str(request.url).replace("/api/docs/postman", "/api/docs/postman")
    
    return JSONResponse(
        content={
            "info": {
                "name": "AI Road Trip Storyteller API",
                "description": "Complete API collection for AI Road Trip Storyteller",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
            },
            "item": [],  # This would be populated by the main app's export
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
        },
        headers={
            "Content-Disposition": "attachment; filename=roadtrip-storyteller-api.postman_collection.json"
        }
    )


@router.get("/authentication")
async def authentication_guide():
    """
    Detailed authentication documentation
    """
    return {
        "authentication": {
            "type": "JWT Bearer Token",
            "description": "The API uses JWT (JSON Web Token) authentication",
            "flow": {
                "1_register": "Create account via POST /api/auth/register",
                "2_login": "Get tokens via POST /api/auth/login",
                "3_use_token": "Include token in Authorization header",
                "4_refresh": "Refresh expired tokens via POST /api/auth/refresh"
            },
            "token_format": "Authorization: Bearer <your-jwt-token>",
            "token_expiry": {
                "access_token": "1 hour",
                "refresh_token": "30 days"
            },
            "two_factor_auth": {
                "supported": True,
                "methods": ["totp", "sms"],
                "setup_endpoint": "/api/auth/2fa/setup",
                "verify_endpoint": "/api/auth/2fa/verify"
            }
        }
    }


@router.get("/rate-limits")
async def rate_limit_documentation():
    """
    Rate limiting documentation
    """
    return {
        "rate_limits": {
            "anonymous": {
                "requests_per_hour": 100,
                "burst_limit": 20
            },
            "authenticated": {
                "requests_per_hour": 1000,
                "burst_limit": 100
            },
            "premium": {
                "requests_per_hour": 10000,
                "burst_limit": 500
            },
            "headers": {
                "X-RateLimit-Limit": "Maximum requests allowed",
                "X-RateLimit-Remaining": "Requests remaining in window",
                "X-RateLimit-Reset": "Unix timestamp when limit resets"
            },
            "response_on_limit": {
                "status_code": 429,
                "error": "Too Many Requests",
                "retry_after": "Seconds until rate limit resets"
            }
        }
    }


@router.get("/errors")
async def error_documentation():
    """
    Error handling documentation
    """
    return {
        "error_format": {
            "detail": "Human-readable error message",
            "type": "Error type identifier",
            "loc": ["Field", "path", "where", "error", "occurred"],
            "msg": "Technical error message",
            "ctx": {"additional": "context", "if": "applicable"}
        },
        "common_errors": {
            "400": {
                "description": "Bad Request",
                "examples": [
                    "Invalid JSON in request body",
                    "Missing required field",
                    "Invalid field value"
                ]
            },
            "401": {
                "description": "Unauthorized",
                "examples": [
                    "Missing authentication token",
                    "Invalid or expired token",
                    "Token signature verification failed"
                ]
            },
            "403": {
                "description": "Forbidden",
                "examples": [
                    "Insufficient permissions",
                    "Premium feature requested without premium subscription",
                    "Admin endpoint accessed by regular user"
                ]
            },
            "404": {
                "description": "Not Found",
                "examples": [
                    "Resource does not exist",
                    "Endpoint not found",
                    "User or trip not found"
                ]
            },
            "422": {
                "description": "Unprocessable Entity",
                "examples": [
                    "Validation error",
                    "Business logic violation",
                    "Invalid coordinates"
                ]
            },
            "429": {
                "description": "Too Many Requests",
                "examples": [
                    "Rate limit exceeded",
                    "Too many failed login attempts",
                    "API quota exhausted"
                ]
            },
            "500": {
                "description": "Internal Server Error",
                "examples": [
                    "Unexpected server error",
                    "Database connection failed",
                    "External service unavailable"
                ]
            }
        }
    }


@router.get("/webhooks")
async def webhook_documentation():
    """
    Webhook configuration documentation
    """
    return {
        "webhooks": {
            "overview": "Webhooks allow you to receive real-time notifications about events in your application",
            "configuration": {
                "endpoint": "POST /api/users/webhooks",
                "required_fields": {
                    "url": "Your webhook endpoint URL",
                    "events": ["List of events to subscribe to"],
                    "secret": "Shared secret for signature verification"
                }
            },
            "available_events": {
                "trip.started": "Trip has been started",
                "trip.completed": "Trip has been completed",
                "trip.updated": "Trip details updated",
                "story.generated": "New story segment generated",
                "booking.confirmed": "Booking successfully confirmed",
                "booking.cancelled": "Booking cancelled",
                "voice.command_processed": "Voice command processed",
                "user.upgraded": "User upgraded to premium",
                "payment.processed": "Payment successfully processed",
                "payment.failed": "Payment failed"
            },
            "payload_format": {
                "event": "event.type",
                "timestamp": "ISO 8601 timestamp",
                "data": "Event-specific data object",
                "signature": "HMAC-SHA256 signature for verification"
            },
            "signature_verification": {
                "header": "X-Webhook-Signature",
                "algorithm": "HMAC-SHA256",
                "format": "sha256=<signature>"
            },
            "retry_policy": {
                "max_attempts": 3,
                "backoff": "exponential",
                "timeout": "5 seconds"
            }
        }
    }


@router.get("/changelog")
async def api_changelog():
    """
    API version history and changelog
    """
    return {
        "current_version": "1.0.0",
        "changelog": [
            {
                "version": "1.0.0",
                "date": "2024-01-01",
                "changes": [
                    "Initial public release",
                    "Core storytelling functionality",
                    "Voice interaction support",
                    "Hotel and activity booking integration",
                    "Trip planning features"
                ]
            }
        ],
        "deprecations": [],
        "upcoming_features": [
            "GraphQL API support",
            "WebSocket real-time updates",
            "Additional language support",
            "Advanced personalization options"
        ]
    }