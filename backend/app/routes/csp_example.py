"""
CSP Nonce Example Route
Demonstrates how to use CSP nonces in HTML responses
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from ..core.security_headers import (
    get_nonce_from_request, 
    create_nonce_script_tag,
    create_nonce_style_tag
)

router = APIRouter()


@router.get("/csp-example", response_class=HTMLResponse)
async def csp_example_page(request: Request):
    """
    Example page demonstrating CSP nonce usage
    
    This shows how to properly include inline scripts and styles
    with CSP nonces for security.
    """
    # Get the CSP nonce for this request
    nonce = get_nonce_from_request(request)
    
    if not nonce:
        return HTMLResponse(
            content="<h1>Error: CSP nonce not available</h1>",
            status_code=500
        )
    
    # Create HTML with properly nonce-protected inline scripts and styles
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CSP Nonce Example - RoadTrip AI</title>
        
        <!-- External stylesheets are allowed by CSP -->
        <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap">
        
        <!-- Inline styles must use nonce -->
        <style nonce="{nonce}">
            body {{
                font-family: 'Inter', sans-serif;
                margin: 40px;
                background-color: #f5f5f5;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .security-badge {{
                background: #10b981;
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 14px;
                display: inline-block;
                margin-bottom: 20px;
            }}
            code {{
                background: #f3f4f6;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: monospace;
            }}
            .example-box {{
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                padding: 20px;
                border-radius: 6px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="security-badge">✓ CSP Protected</div>
            
            <h1>CSP Nonce Example</h1>
            
            <p>This page demonstrates how to use Content Security Policy (CSP) nonces to safely include inline scripts and styles.</p>
            
            <div class="example-box">
                <h3>Current CSP Nonce</h3>
                <p>The nonce for this request is: <code>{nonce}</code></p>
                <p>This nonce is unique for each request and expires immediately after use.</p>
            </div>
            
            <div class="example-box">
                <h3>How It Works</h3>
                <ol>
                    <li>Server generates a cryptographically secure nonce for each request</li>
                    <li>The nonce is included in the CSP header: <code>script-src 'nonce-{nonce[:8]}...'</code></li>
                    <li>Inline scripts/styles must include the same nonce to execute</li>
                    <li>Scripts without the correct nonce are blocked by the browser</li>
                </ol>
            </div>
            
            <div class="example-box">
                <h3>Security Benefits</h3>
                <ul>
                    <li>Prevents XSS attacks by blocking unauthorized inline scripts</li>
                    <li>No need for 'unsafe-inline' directive</li>
                    <li>Each nonce is unique and unpredictable</li>
                    <li>Compatible with dynamic content generation</li>
                </ul>
            </div>
            
            <div id="demo-output" class="example-box">
                <h3>JavaScript Demo</h3>
                <p id="demo-text">Waiting for script execution...</p>
            </div>
        </div>
        
        <!-- Inline script with nonce -->
        <script nonce="{nonce}">
            // This script will execute because it has the correct nonce
            document.addEventListener('DOMContentLoaded', function() {{
                const demoText = document.getElementById('demo-text');
                demoText.textContent = '✓ JavaScript executed successfully with CSP nonce!';
                demoText.style.color = '#10b981';
                
                // Log security info
                console.log('CSP Nonce Example Page Loaded');
                console.log('This script executed with nonce:', '{nonce[:8]}...');
            }});
        </script>
        
        <!-- This would be blocked without a nonce:
        <script>
            alert('This would be blocked by CSP!');
        </script>
        -->
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@router.get("/api/csp-demo-data")
async def get_demo_data(request: Request):
    """
    API endpoint demonstrating that API responses don't need nonces
    
    API endpoints have a strict CSP that blocks all scripts,
    so nonces aren't needed for JSON responses.
    """
    return {
        "message": "API endpoints use strict CSP",
        "csp_policy": "default-src 'none'",
        "explanation": "API responses don't execute scripts, so they use the strictest possible CSP"
    }


# Helper endpoint for developers
@router.get("/api/csp-implementation-guide")
async def csp_implementation_guide():
    """
    Guide for implementing CSP nonces in your routes
    """
    return {
        "title": "CSP Nonce Implementation Guide",
        "steps": [
            {
                "step": 1,
                "action": "Get nonce from request",
                "code": "nonce = get_nonce_from_request(request)"
            },
            {
                "step": 2,
                "action": "Add nonce to inline scripts",
                "code": '<script nonce="{nonce}">...</script>'
            },
            {
                "step": 3,
                "action": "Add nonce to inline styles",
                "code": '<style nonce="{nonce}">...</style>'
            },
            {
                "step": 4,
                "action": "Use helper functions for dynamic content",
                "code": "create_nonce_script_tag(script_content, nonce)"
            }
        ],
        "important_notes": [
            "Never share or reuse nonces between requests",
            "Nonces are automatically generated by the security middleware",
            "External scripts/styles don't need nonces",
            "API endpoints use strict CSP without nonces"
        ],
        "security_benefits": [
            "Prevents XSS attacks",
            "No need for 'unsafe-inline'",
            "Works with server-side rendering",
            "Compatible with all modern browsers"
        ]
    }