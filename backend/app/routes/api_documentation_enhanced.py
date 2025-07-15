"""
Enhanced API Documentation Router
Provides comprehensive documentation portal with all features
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from typing import Dict, Any, Optional
import json
from pathlib import Path

# Import documentation modules
from ..documentation.api_portal import router as portal_router
from ..documentation.webhook_tester import router as webhook_router
from ..documentation.sdk_generator import SDKGenerator, generate_sdks_from_openapi
from .api_examples import get_api_examples

router = APIRouter(prefix="/api/docs", tags=["Documentation"])

# Include sub-routers
router.include_router(portal_router)
router.include_router(webhook_router)


@router.get("/", response_class=HTMLResponse)
async def documentation_home():
    """Enhanced API documentation home page"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Documentation - AI Road Trip Storyteller</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {
            --primary: #1a1a2e;
            --secondary: #16213e;
            --accent: #0f4c75;
            --highlight: #3282b8;
            --text: #333;
            --text-light: #666;
            --bg: #f8f9fa;
            --white: #ffffff;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 0;
            background: var(--bg);
            color: var(--text);
        }
        
        .hero {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 4rem 0;
            text-align: center;
        }
        
        .hero h1 {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        .hero p {
            font-size: 1.25rem;
            opacity: 0.9;
            max-width: 600px;
            margin: 0 auto;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .doc-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-top: -4rem;
            position: relative;
            z-index: 10;
        }
        
        .doc-card {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: all 0.3s;
            text-decoration: none;
            color: inherit;
            display: block;
        }
        
        .doc-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }
        
        .doc-icon {
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, var(--highlight), var(--accent));
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            color: white;
            margin-bottom: 1.5rem;
        }
        
        .doc-card h3 {
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: var(--primary);
        }
        
        .doc-card p {
            color: var(--text-light);
            line-height: 1.6;
        }
        
        .feature-list {
            list-style: none;
            padding: 0;
            margin: 1rem 0 0;
        }
        
        .feature-list li {
            padding: 0.5rem 0;
            color: var(--text-light);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .feature-list i {
            color: var(--highlight);
            font-size: 0.875rem;
        }
        
        .quick-links {
            background: white;
            padding: 3rem;
            margin: 3rem 0;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .quick-links h2 {
            color: var(--primary);
            margin-bottom: 2rem;
            text-align: center;
        }
        
        .link-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }
        
        .quick-link {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem;
            background: var(--bg);
            border-radius: 8px;
            text-decoration: none;
            color: var(--text);
            transition: all 0.3s;
        }
        
        .quick-link:hover {
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .quick-link i {
            color: var(--highlight);
            font-size: 1.25rem;
        }
        
        .version-info {
            background: #e3f2fd;
            border-left: 4px solid var(--highlight);
            padding: 1rem 1.5rem;
            margin: 2rem 0;
            border-radius: 4px;
        }
        
        .version-info strong {
            color: var(--highlight);
        }
    </style>
</head>
<body>
    <div class="hero">
        <h1>📚 API Documentation</h1>
        <p>Everything you need to integrate with the AI Road Trip Storyteller API</p>
    </div>
    
    <div class="container">
        <div class="doc-grid">
            <a href="/docs" class="doc-card">
                <div class="doc-icon">
                    <i class="fas fa-book"></i>
                </div>
                <h3>Interactive API Reference</h3>
                <p>Explore all endpoints with Swagger UI. Try out API calls directly in your browser.</p>
                <ul class="feature-list">
                    <li><i class="fas fa-check"></i> Live API testing</li>
                    <li><i class="fas fa-check"></i> Request/response examples</li>
                    <li><i class="fas fa-check"></i> Authentication flows</li>
                </ul>
            </a>
            
            <a href="/portal" class="doc-card">
                <div class="doc-icon">
                    <i class="fas fa-code"></i>
                </div>
                <h3>Developer Portal</h3>
                <p>Comprehensive guides, tutorials, and resources for building with our API.</p>
                <ul class="feature-list">
                    <li><i class="fas fa-check"></i> Quick start guide</li>
                    <li><i class="fas fa-check"></i> Code examples</li>
                    <li><i class="fas fa-check"></i> Best practices</li>
                </ul>
            </a>
            
            <a href="/portal/webhooks/tester" class="doc-card">
                <div class="doc-icon">
                    <i class="fas fa-plug"></i>
                </div>
                <h3>Webhook Tester</h3>
                <p>Test and debug webhook integrations with our interactive testing tool.</p>
                <ul class="feature-list">
                    <li><i class="fas fa-check"></i> Send test events</li>
                    <li><i class="fas fa-check"></i> Signature validation</li>
                    <li><i class="fas fa-check"></i> Response inspection</li>
                </ul>
            </a>
            
            <a href="/redoc" class="doc-card">
                <div class="doc-icon">
                    <i class="fas fa-file-alt"></i>
                </div>
                <h3>API Specification</h3>
                <p>Clean, readable API documentation with ReDoc. Perfect for understanding the API structure.</p>
                <ul class="feature-list">
                    <li><i class="fas fa-check"></i> Detailed schemas</li>
                    <li><i class="fas fa-check"></i> Type definitions</li>
                    <li><i class="fas fa-check"></i> Download OpenAPI spec</li>
                </ul>
            </a>
            
            <a href="/api/docs/sdks" class="doc-card">
                <div class="doc-icon">
                    <i class="fas fa-download"></i>
                </div>
                <h3>SDKs & Libraries</h3>
                <p>Official client libraries for Python, JavaScript, React Native, and more.</p>
                <ul class="feature-list">
                    <li><i class="fas fa-check"></i> Auto-generated SDKs</li>
                    <li><i class="fas fa-check"></i> Type-safe clients</li>
                    <li><i class="fas fa-check"></i> Platform-specific features</li>
                </ul>
            </a>
            
            <a href="/api/docs/postman" class="doc-card">
                <div class="doc-icon">
                    <i class="fas fa-mail-bulk"></i>
                </div>
                <h3>Postman Collection</h3>
                <p>Import our complete API collection into Postman for easy testing and development.</p>
                <ul class="feature-list">
                    <li><i class="fas fa-check"></i> Pre-configured requests</li>
                    <li><i class="fas fa-check"></i> Environment variables</li>
                    <li><i class="fas fa-check"></i> Example responses</li>
                </ul>
            </a>
        </div>
        
        <div class="version-info">
            <strong>API Version:</strong> v1.0.0 | 
            <strong>Last Updated:</strong> January 2024 | 
            <strong>Status:</strong> <a href="https://status.roadtripstoryteller.com" style="color: var(--highlight);">All Systems Operational</a>
        </div>
        
        <div class="quick-links">
            <h2>🚀 Quick Links</h2>
            <div class="link-grid">
                <a href="/portal/quickstart" class="quick-link">
                    <i class="fas fa-rocket"></i>
                    <span>Quick Start Guide</span>
                </a>
                <a href="/api/docs/authentication" class="quick-link">
                    <i class="fas fa-key"></i>
                    <span>Authentication</span>
                </a>
                <a href="/api/docs/rate-limits" class="quick-link">
                    <i class="fas fa-tachometer-alt"></i>
                    <span>Rate Limits</span>
                </a>
                <a href="/api/docs/errors" class="quick-link">
                    <i class="fas fa-exclamation-triangle"></i>
                    <span>Error Handling</span>
                </a>
                <a href="/api/docs/webhooks" class="quick-link">
                    <i class="fas fa-bell"></i>
                    <span>Webhooks</span>
                </a>
                <a href="/api/docs/changelog" class="quick-link">
                    <i class="fas fa-history"></i>
                    <span>Changelog</span>
                </a>
            </div>
        </div>
        
        <div style="text-align: center; margin-top: 3rem; color: var(--text-light);">
            <p>Need help? Contact us at <a href="mailto:developers@roadtripstoryteller.com" style="color: var(--highlight);">developers@roadtripstoryteller.com</a></p>
            <p>Join our <a href="https://discord.gg/roadtrip-dev" style="color: var(--highlight);">Discord Community</a> for support and updates</p>
        </div>
    </div>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/sdks", response_class=HTMLResponse)
async def sdks_overview():
    """SDK overview and download page"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SDKs & Client Libraries - AI Road Trip Storyteller</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 0;
            background: #f8f9fa;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        h1 {
            color: #1a1a2e;
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        
        .intro {
            font-size: 1.125rem;
            color: #666;
            margin-bottom: 3rem;
        }
        
        .sdk-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }
        
        .sdk-card {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.3s;
        }
        
        .sdk-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 4px 16px rgba(0,0,0,0.15);
        }
        
        .sdk-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        
        .sdk-icon {
            width: 60px;
            height: 60px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            background: #f0f0f0;
            border-radius: 12px;
        }
        
        .sdk-title h2 {
            margin: 0;
            color: #1a1a2e;
        }
        
        .sdk-version {
            font-size: 0.875rem;
            color: #666;
        }
        
        .install-command {
            background: #1a1a2e;
            color: #fff;
            padding: 1rem;
            border-radius: 6px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.875rem;
            margin: 1rem 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .copy-btn {
            background: #3282b8;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.75rem;
        }
        
        .copy-btn:hover {
            background: #0f4c75;
        }
        
        .sdk-features {
            list-style: none;
            padding: 0;
            margin: 1rem 0;
        }
        
        .sdk-features li {
            padding: 0.5rem 0;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .sdk-features i {
            color: #28a745;
            font-size: 0.875rem;
        }
        
        .sdk-actions {
            display: flex;
            gap: 1rem;
            margin-top: 1.5rem;
        }
        
        .btn {
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .btn-primary {
            background: #3282b8;
            color: white;
        }
        
        .btn-primary:hover {
            background: #0f4c75;
        }
        
        .btn-secondary {
            background: #e9ecef;
            color: #333;
        }
        
        .btn-secondary:hover {
            background: #dee2e6;
        }
        
        .code-example {
            background: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 1rem;
            margin-top: 1rem;
        }
        
        pre {
            margin: 0;
            overflow-x: auto;
        }
        
        .generate-section {
            background: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .generate-section h2 {
            color: #1a1a2e;
            margin-bottom: 1rem;
        }
        
        .generate-section p {
            color: #666;
            margin-bottom: 1.5rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🛠️ SDKs & Client Libraries</h1>
        <p class="intro">Official client libraries to accelerate your integration with the AI Road Trip Storyteller API</p>
        
        <div class="sdk-grid">
            <!-- Python SDK -->
            <div class="sdk-card">
                <div class="sdk-header">
                    <div class="sdk-icon">🐍</div>
                    <div class="sdk-title">
                        <h2>Python SDK</h2>
                        <div class="sdk-version">v1.0.0</div>
                    </div>
                </div>
                
                <div class="install-command">
                    <code>pip install roadtrip-storyteller</code>
                    <button class="copy-btn" onclick="copyToClipboard('pip install roadtrip-storyteller')">Copy</button>
                </div>
                
                <ul class="sdk-features">
                    <li><i class="fas fa-check"></i> Async/await support</li>
                    <li><i class="fas fa-check"></i> Type hints included</li>
                    <li><i class="fas fa-check"></i> Automatic retries</li>
                    <li><i class="fas fa-check"></i> Token management</li>
                </ul>
                
                <div class="code-example">
                    <pre><code class="language-python">from roadtrip_storyteller import RoadtripStorytellerClient

client = RoadtripStorytellerClient(access_token="your-token")
story = client.stories.generate(
    latitude=40.7128,
    longitude=-74.0060,
    personality="morgan_freeman"
)</code></pre>
                </div>
                
                <div class="sdk-actions">
                    <a href="/api/docs/sdk/python/download" class="btn btn-primary">
                        <i class="fas fa-download"></i> Download
                    </a>
                    <a href="/portal/sdk/python" class="btn btn-secondary">
                        <i class="fas fa-book"></i> Documentation
                    </a>
                </div>
            </div>
            
            <!-- JavaScript SDK -->
            <div class="sdk-card">
                <div class="sdk-header">
                    <div class="sdk-icon">📦</div>
                    <div class="sdk-title">
                        <h2>JavaScript/TypeScript</h2>
                        <div class="sdk-version">v1.0.0</div>
                    </div>
                </div>
                
                <div class="install-command">
                    <code>npm install @roadtrip/storyteller-sdk</code>
                    <button class="copy-btn" onclick="copyToClipboard('npm install @roadtrip/storyteller-sdk')">Copy</button>
                </div>
                
                <ul class="sdk-features">
                    <li><i class="fas fa-check"></i> TypeScript support</li>
                    <li><i class="fas fa-check"></i> Promise-based API</li>
                    <li><i class="fas fa-check"></i> Browser & Node.js</li>
                    <li><i class="fas fa-check"></i> Tree-shakeable</li>
                </ul>
                
                <div class="code-example">
                    <pre><code class="language-javascript">import RoadtripStorytellerClient from '@roadtrip/storyteller-sdk';

const client = new RoadtripStorytellerClient({
  accessToken: 'your-token'
});

const story = await client.stories.generate({
  latitude: 40.7128,
  longitude: -74.0060
});</code></pre>
                </div>
                
                <div class="sdk-actions">
                    <a href="/api/docs/sdk/javascript/download" class="btn btn-primary">
                        <i class="fas fa-download"></i> Download
                    </a>
                    <a href="/portal/sdk/javascript" class="btn btn-secondary">
                        <i class="fas fa-book"></i> Documentation
                    </a>
                </div>
            </div>
            
            <!-- React Native SDK -->
            <div class="sdk-card">
                <div class="sdk-header">
                    <div class="sdk-icon">📱</div>
                    <div class="sdk-title">
                        <h2>React Native</h2>
                        <div class="sdk-version">v1.0.0</div>
                    </div>
                </div>
                
                <div class="install-command">
                    <code>npm install @roadtrip/mobile-sdk</code>
                    <button class="copy-btn" onclick="copyToClipboard('npm install @roadtrip/mobile-sdk')">Copy</button>
                </div>
                
                <ul class="sdk-features">
                    <li><i class="fas fa-check"></i> Native device integration</li>
                    <li><i class="fas fa-check"></i> Location services</li>
                    <li><i class="fas fa-check"></i> Audio playback</li>
                    <li><i class="fas fa-check"></i> Offline support</li>
                </ul>
                
                <div class="code-example">
                    <pre><code class="language-javascript">import RoadtripClient from '@roadtrip/mobile-sdk';

const client = new RoadtripClient();
await client.auth.login(email, password);

// Generate story for current location
const story = await client.stories.generateForCurrentLocation();</code></pre>
                </div>
                
                <div class="sdk-actions">
                    <a href="/api/docs/sdk/react-native/download" class="btn btn-primary">
                        <i class="fas fa-download"></i> Download
                    </a>
                    <a href="/portal/sdk/react-native" class="btn btn-secondary">
                        <i class="fas fa-book"></i> Documentation
                    </a>
                </div>
            </div>
            
            <!-- Other SDKs -->
            <div class="sdk-card">
                <div class="sdk-header">
                    <div class="sdk-icon">🔧</div>
                    <div class="sdk-title">
                        <h2>More SDKs</h2>
                        <div class="sdk-version">Coming Soon</div>
                    </div>
                </div>
                
                <p style="color: #666; margin: 1rem 0;">Additional SDKs are in development:</p>
                
                <ul class="sdk-features">
                    <li><i class="fas fa-clock"></i> Swift (iOS)</li>
                    <li><i class="fas fa-clock"></i> Kotlin (Android)</li>
                    <li><i class="fas fa-clock"></i> Go</li>
                    <li><i class="fas fa-clock"></i> Ruby</li>
                    <li><i class="fas fa-clock"></i> PHP</li>
                    <li><i class="fas fa-clock"></i> Java</li>
                </ul>
                
                <p style="color: #666; margin-top: 1rem;">
                    Can't find your language? Use our OpenAPI specification to generate a client.
                </p>
                
                <div class="sdk-actions">
                    <a href="/openapi.json" class="btn btn-primary">
                        <i class="fas fa-file-code"></i> OpenAPI Spec
                    </a>
                    <a href="/api/docs/postman" class="btn btn-secondary">
                        <i class="fas fa-mail-bulk"></i> Postman
                    </a>
                </div>
            </div>
        </div>
        
        <div class="generate-section">
            <h2>🚀 Generate Custom SDKs</h2>
            <p>Generate SDKs from our OpenAPI specification using popular tools</p>
            
            <div style="display: flex; gap: 1rem; justify-content: center;">
                <a href="/api/docs/generate-sdks" class="btn btn-primary">
                    <i class="fas fa-magic"></i> Auto-Generate SDKs
                </a>
                <a href="/openapi.yaml" class="btn btn-secondary">
                    <i class="fas fa-download"></i> Download OpenAPI YAML
                </a>
            </div>
            
            <div style="margin-top: 2rem; text-align: left; background: #f6f8fa; padding: 1.5rem; border-radius: 8px;">
                <h4 style="margin-top: 0;">Using OpenAPI Generator:</h4>
                <pre style="background: #1a1a2e; color: white; padding: 1rem; border-radius: 4px;"><code># Install OpenAPI Generator
npm install -g @openapitools/openapi-generator-cli

# Generate a client (e.g., for Java)
openapi-generator-cli generate \\
  -i https://api.roadtripstoryteller.com/openapi.json \\
  -g java \\
  -o ./roadtrip-java-sdk</code></pre>
            </div>
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-javascript.min.js"></script>
    
    <script>
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = 'Copied!';
                setTimeout(() => {
                    btn.textContent = originalText;
                }, 2000);
            });
        }
        
        Prism.highlightAll();
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/sdk/{language}/download")
async def download_sdk(language: str):
    """Download SDK for specific language"""
    try:
        # Get the current OpenAPI spec
        from ..main import app
        openapi_spec = app.openapi()
        
        # Generate SDK
        generator = SDKGenerator(openapi_spec)
        
        sdk_content = ""
        filename = ""
        content_type = "text/plain"
        
        if language == "python":
            sdk_content = generator.generate_python_sdk()
            filename = "roadtrip_storyteller.py"
            content_type = "text/x-python"
        elif language == "javascript":
            sdk_content = generator.generate_javascript_sdk()
            filename = "roadtrip-storyteller.js"
            content_type = "text/javascript"
        elif language == "react-native":
            sdk_content = generator.generate_react_native_sdk()
            filename = "roadtrip-storyteller-mobile.js"
            content_type = "text/javascript"
        else:
            raise HTTPException(status_code=404, detail="SDK not found")
        
        return HTMLResponse(
            content=sdk_content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/generate-all-sdks")
async def generate_all_sdks_endpoint():
    """Generate all SDKs from current OpenAPI spec"""
    try:
        from ..main import app
        openapi_spec = app.openapi()
        
        output_dir = Path(__file__).parent.parent / "generated_sdks"
        output_paths = generate_sdks_from_openapi(openapi_spec, output_dir)
        
        return {
            "status": "success",
            "message": "SDKs generated successfully",
            "files": {
                language: str(path) for language, path in output_paths.items()
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))