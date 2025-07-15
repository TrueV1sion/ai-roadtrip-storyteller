"""
Interactive API Documentation Portal
Provides a comprehensive developer portal with guides, examples, and tools
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from datetime import datetime

router = APIRouter(prefix="/portal", tags=["Developer Portal"])


@router.get("/", response_class=HTMLResponse)
async def developer_portal_home():
    """Main developer portal page"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Road Trip Storyteller - Developer Portal</title>
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
            --success: #28a745;
            --warning: #ffc107;
            --danger: #dc3545;
            --info: #17a2b8;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            line-height: 1.6;
            color: var(--text);
            background: var(--bg);
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 2rem 0;
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(50,130,184,0.1) 0%, transparent 70%);
            animation: pulse 20s ease-in-out infinite;
        }
        
        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.1); }
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 2rem;
        }
        
        .header-content {
            position: relative;
            z-index: 1;
        }
        
        .header h1 {
            font-size: 3rem;
            font-weight: 700;
            margin-bottom: 1rem;
            background: linear-gradient(to right, #fff, #3282b8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header p {
            font-size: 1.25rem;
            opacity: 0.9;
            max-width: 600px;
        }
        
        /* Navigation */
        .nav {
            background: var(--white);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 100;
        }
        
        .nav-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1rem 0;
        }
        
        .nav-links {
            display: flex;
            gap: 2rem;
            list-style: none;
        }
        
        .nav-links a {
            text-decoration: none;
            color: var(--text);
            font-weight: 500;
            transition: color 0.3s;
        }
        
        .nav-links a:hover {
            color: var(--highlight);
        }
        
        .nav-actions {
            display: flex;
            gap: 1rem;
        }
        
        .btn {
            padding: 0.5rem 1.5rem;
            border-radius: 6px;
            text-decoration: none;
            font-weight: 500;
            transition: all 0.3s;
            border: none;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .btn-primary {
            background: var(--highlight);
            color: white;
        }
        
        .btn-primary:hover {
            background: var(--accent);
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(50,130,184,0.3);
        }
        
        .btn-outline {
            border: 2px solid var(--highlight);
            color: var(--highlight);
            background: transparent;
        }
        
        .btn-outline:hover {
            background: var(--highlight);
            color: white;
        }
        
        /* Hero Section */
        .hero {
            padding: 4rem 0;
            background: white;
        }
        
        .hero-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4rem;
            align-items: center;
        }
        
        .hero-content h2 {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            color: var(--primary);
        }
        
        .hero-content p {
            font-size: 1.125rem;
            color: var(--text-light);
            margin-bottom: 2rem;
        }
        
        .hero-actions {
            display: flex;
            gap: 1rem;
            flex-wrap: wrap;
        }
        
        .hero-image {
            position: relative;
        }
        
        .code-preview {
            background: var(--primary);
            color: #fff;
            padding: 2rem;
            border-radius: 12px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.875rem;
            box-shadow: 0 8px 32px rgba(26,26,46,0.2);
            position: relative;
            overflow: hidden;
        }
        
        .code-preview::before {
            content: '';
            position: absolute;
            top: 1rem;
            left: 1rem;
            display: flex;
            gap: 0.5rem;
        }
        
        .code-preview::before {
            content: '● ● ●';
            color: #666;
            font-size: 0.75rem;
        }
        
        .code-content {
            margin-top: 1rem;
        }
        
        .code-line {
            margin: 0.25rem 0;
            opacity: 0.9;
        }
        
        .code-highlight {
            color: #3282b8;
        }
        
        /* Features Grid */
        .features {
            padding: 4rem 0;
        }
        
        .section-header {
            text-align: center;
            margin-bottom: 3rem;
        }
        
        .section-header h2 {
            font-size: 2.5rem;
            color: var(--primary);
            margin-bottom: 1rem;
        }
        
        .section-header p {
            font-size: 1.125rem;
            color: var(--text-light);
            max-width: 600px;
            margin: 0 auto;
        }
        
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
        }
        
        .feature-card {
            background: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.3s;
            position: relative;
            overflow: hidden;
        }
        
        .feature-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(to right, var(--highlight), var(--accent));
            transform: scaleX(0);
            transform-origin: left;
            transition: transform 0.3s;
        }
        
        .feature-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        }
        
        .feature-card:hover::before {
            transform: scaleX(1);
        }
        
        .feature-icon {
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
        
        .feature-card h3 {
            font-size: 1.25rem;
            margin-bottom: 1rem;
            color: var(--primary);
        }
        
        .feature-card p {
            color: var(--text-light);
            margin-bottom: 1rem;
        }
        
        .feature-link {
            color: var(--highlight);
            text-decoration: none;
            font-weight: 500;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            transition: gap 0.3s;
        }
        
        .feature-link:hover {
            gap: 1rem;
        }
        
        /* API Reference Section */
        .api-reference {
            background: white;
            padding: 4rem 0;
        }
        
        .api-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
        }
        
        .api-card {
            background: var(--bg);
            padding: 1.5rem;
            border-radius: 8px;
            border: 2px solid transparent;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .api-card:hover {
            border-color: var(--highlight);
            background: white;
        }
        
        .api-method {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
        }
        
        .method-get { background: #61affe; color: white; }
        .method-post { background: #49cc90; color: white; }
        .method-put { background: #fca130; color: white; }
        .method-delete { background: #f93e3e; color: white; }
        
        .api-path {
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.875rem;
            color: var(--text);
            margin-bottom: 0.5rem;
        }
        
        .api-description {
            font-size: 0.875rem;
            color: var(--text-light);
        }
        
        /* SDK Section */
        .sdk-section {
            padding: 4rem 0;
            background: linear-gradient(to bottom, white, var(--bg));
        }
        
        .sdk-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 2rem;
            margin-top: 3rem;
        }
        
        .sdk-card {
            text-align: center;
            padding: 2rem;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: all 0.3s;
        }
        
        .sdk-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        }
        
        .sdk-logo {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        .sdk-name {
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--primary);
            margin-bottom: 0.5rem;
        }
        
        .sdk-install {
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.75rem;
            background: var(--bg);
            padding: 0.5rem;
            border-radius: 4px;
            margin: 1rem 0;
        }
        
        /* Resources */
        .resources {
            padding: 4rem 0;
            background: white;
        }
        
        .resource-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            list-style: none;
        }
        
        .resource-item {
            display: flex;
            gap: 1rem;
            padding: 1.5rem;
            background: var(--bg);
            border-radius: 8px;
            transition: all 0.3s;
        }
        
        .resource-item:hover {
            background: white;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        
        .resource-icon {
            flex-shrink: 0;
            width: 48px;
            height: 48px;
            background: var(--highlight);
            color: white;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .resource-content h4 {
            color: var(--primary);
            margin-bottom: 0.5rem;
        }
        
        .resource-content p {
            font-size: 0.875rem;
            color: var(--text-light);
        }
        
        /* Footer */
        .footer {
            background: var(--primary);
            color: white;
            padding: 3rem 0 1rem;
        }
        
        .footer-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 3rem;
            margin-bottom: 2rem;
        }
        
        .footer-section h3 {
            margin-bottom: 1rem;
            color: var(--highlight);
        }
        
        .footer-links {
            list-style: none;
        }
        
        .footer-links li {
            margin-bottom: 0.5rem;
        }
        
        .footer-links a {
            color: rgba(255,255,255,0.8);
            text-decoration: none;
            transition: color 0.3s;
        }
        
        .footer-links a:hover {
            color: white;
        }
        
        .footer-bottom {
            border-top: 1px solid rgba(255,255,255,0.1);
            padding-top: 2rem;
            text-align: center;
            color: rgba(255,255,255,0.6);
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2rem;
            }
            
            .hero-grid {
                grid-template-columns: 1fr;
                gap: 2rem;
            }
            
            .nav-links {
                display: none;
            }
            
            .features-grid {
                grid-template-columns: 1fr;
            }
        }
        
        /* Animations */
        .fade-in {
            animation: fadeIn 0.6s ease-out;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* Loading Animation */
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: white;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <!-- Header -->
    <header class="header">
        <div class="container">
            <div class="header-content">
                <h1>AI Road Trip Storyteller</h1>
                <p>Transform journeys into adventures with our powerful API platform</p>
            </div>
        </div>
    </header>
    
    <!-- Navigation -->
    <nav class="nav">
        <div class="container">
            <div class="nav-container">
                <ul class="nav-links">
                    <li><a href="#documentation">Documentation</a></li>
                    <li><a href="#api-reference">API Reference</a></li>
                    <li><a href="#sdks">SDKs</a></li>
                    <li><a href="#guides">Guides</a></li>
                    <li><a href="#resources">Resources</a></li>
                </ul>
                <div class="nav-actions">
                    <a href="/docs" class="btn btn-outline">
                        <i class="fas fa-book"></i> API Docs
                    </a>
                    <a href="/portal/dashboard" class="btn btn-primary">
                        <i class="fas fa-code"></i> Dashboard
                    </a>
                </div>
            </div>
        </div>
    </nav>
    
    <!-- Hero Section -->
    <section class="hero">
        <div class="container">
            <div class="hero-grid">
                <div class="hero-content fade-in">
                    <h2>Build Amazing Travel Experiences</h2>
                    <p>Integrate AI-powered storytelling, voice interactions, and real-time booking capabilities into your applications with our comprehensive API.</p>
                    <div class="hero-actions">
                        <a href="/portal/quickstart" class="btn btn-primary">
                            <i class="fas fa-rocket"></i> Quick Start
                        </a>
                        <a href="/portal/examples" class="btn btn-outline">
                            <i class="fas fa-code"></i> View Examples
                        </a>
                    </div>
                </div>
                <div class="hero-image fade-in">
                    <div class="code-preview">
                        <div class="code-content">
                            <div class="code-line">
                                <span class="code-highlight">import</span> RoadtripClient <span class="code-highlight">from</span> '@roadtrip/sdk';
                            </div>
                            <div class="code-line">&nbsp;</div>
                            <div class="code-line">
                                <span class="code-highlight">const</span> client = <span class="code-highlight">new</span> RoadtripClient({
                            </div>
                            <div class="code-line">
                                &nbsp;&nbsp;apiKey: <span style="color: #98c379">'your-api-key'</span>
                            </div>
                            <div class="code-line">});</div>
                            <div class="code-line">&nbsp;</div>
                            <div class="code-line">
                                <span class="code-highlight">const</span> story = <span class="code-highlight">await</span> client.stories.generate({
                            </div>
                            <div class="code-line">
                                &nbsp;&nbsp;location: { lat: 40.7128, lng: -74.0060 },
                            </div>
                            <div class="code-line">
                                &nbsp;&nbsp;personality: <span style="color: #98c379">'morgan_freeman'</span>
                            </div>
                            <div class="code-line">});</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Features -->
    <section class="features">
        <div class="container">
            <div class="section-header">
                <h2>Powerful Features for Developers</h2>
                <p>Everything you need to create exceptional travel applications</p>
            </div>
            <div class="features-grid">
                <div class="feature-card fade-in">
                    <div class="feature-icon">
                        <i class="fas fa-microphone-alt"></i>
                    </div>
                    <h3>Voice Interactions</h3>
                    <p>Natural language processing for voice commands with 20+ personality options</p>
                    <a href="/portal/voice-guide" class="feature-link">
                        Learn more <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
                <div class="feature-card fade-in">
                    <div class="feature-icon">
                        <i class="fas fa-map-marked-alt"></i>
                    </div>
                    <h3>Location Intelligence</h3>
                    <p>Real-time location-based storytelling with GPS integration</p>
                    <a href="/portal/location-guide" class="feature-link">
                        Learn more <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
                <div class="feature-card fade-in">
                    <div class="feature-icon">
                        <i class="fas fa-hotel"></i>
                    </div>
                    <h3>Booking Integration</h3>
                    <p>Seamless hotel, restaurant, and activity booking capabilities</p>
                    <a href="/portal/booking-guide" class="feature-link">
                        Learn more <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
                <div class="feature-card fade-in">
                    <div class="feature-icon">
                        <i class="fas fa-brain"></i>
                    </div>
                    <h3>AI Storytelling</h3>
                    <p>Dynamic story generation powered by advanced AI models</p>
                    <a href="/portal/ai-guide" class="feature-link">
                        Learn more <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
                <div class="feature-card fade-in">
                    <div class="feature-icon">
                        <i class="fas fa-lock"></i>
                    </div>
                    <h3>Enterprise Security</h3>
                    <p>JWT authentication, 2FA support, and comprehensive security</p>
                    <a href="/portal/security-guide" class="feature-link">
                        Learn more <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
                <div class="feature-card fade-in">
                    <div class="feature-icon">
                        <i class="fas fa-chart-line"></i>
                    </div>
                    <h3>Analytics & Insights</h3>
                    <p>Track usage, monitor performance, and gain valuable insights</p>
                    <a href="/portal/analytics-guide" class="feature-link">
                        Learn more <i class="fas fa-arrow-right"></i>
                    </a>
                </div>
            </div>
        </div>
    </section>
    
    <!-- API Reference Preview -->
    <section class="api-reference" id="api-reference">
        <div class="container">
            <div class="section-header">
                <h2>API Reference</h2>
                <p>Explore our comprehensive API endpoints</p>
            </div>
            <div class="api-grid">
                <div class="api-card" onclick="window.location.href='/docs#/Story'">
                    <span class="api-method method-post">POST</span>
                    <div class="api-path">/api/story/generate</div>
                    <div class="api-description">Generate AI stories based on location</div>
                </div>
                <div class="api-card" onclick="window.location.href='/docs#/Voice%20Assistant'">
                    <span class="api-method method-post">POST</span>
                    <div class="api-path">/api/voice/command</div>
                    <div class="api-description">Process voice commands</div>
                </div>
                <div class="api-card" onclick="window.location.href='/docs#/Bookings'">
                    <span class="api-method method-get">GET</span>
                    <div class="api-path">/api/bookings/hotels</div>
                    <div class="api-description">Search available hotels</div>
                </div>
                <div class="api-card" onclick="window.location.href='/docs#/Trip%20Planning'">
                    <span class="api-method method-post">POST</span>
                    <div class="api-path">/api/trips/create</div>
                    <div class="api-description">Create a new road trip</div>
                </div>
            </div>
            <div style="text-align: center; margin-top: 2rem;">
                <a href="/docs" class="btn btn-primary">
                    View Full API Reference <i class="fas fa-arrow-right"></i>
                </a>
            </div>
        </div>
    </section>
    
    <!-- SDKs Section -->
    <section class="sdk-section" id="sdks">
        <div class="container">
            <div class="section-header">
                <h2>Official SDKs</h2>
                <p>Get started quickly with our official client libraries</p>
            </div>
            <div class="sdk-grid">
                <div class="sdk-card">
                    <div class="sdk-logo">🐍</div>
                    <div class="sdk-name">Python</div>
                    <div class="sdk-install">pip install roadtrip-storyteller</div>
                    <a href="/portal/sdk/python" class="btn btn-outline">Documentation</a>
                </div>
                <div class="sdk-card">
                    <div class="sdk-logo">📦</div>
                    <div class="sdk-name">JavaScript</div>
                    <div class="sdk-install">npm install @roadtrip/sdk</div>
                    <a href="/portal/sdk/javascript" class="btn btn-outline">Documentation</a>
                </div>
                <div class="sdk-card">
                    <div class="sdk-logo">📱</div>
                    <div class="sdk-name">React Native</div>
                    <div class="sdk-install">npm install @roadtrip/mobile</div>
                    <a href="/portal/sdk/react-native" class="btn btn-outline">Documentation</a>
                </div>
                <div class="sdk-card">
                    <div class="sdk-logo">🍎</div>
                    <div class="sdk-name">Swift</div>
                    <div class="sdk-install">pod 'RoadtripSDK'</div>
                    <a href="/portal/sdk/swift" class="btn btn-outline">Documentation</a>
                </div>
                <div class="sdk-card">
                    <div class="sdk-logo">🤖</div>
                    <div class="sdk-name">Kotlin</div>
                    <div class="sdk-install">implementation 'com.roadtrip:sdk'</div>
                    <a href="/portal/sdk/kotlin" class="btn btn-outline">Documentation</a>
                </div>
                <div class="sdk-card">
                    <div class="sdk-logo">📮</div>
                    <div class="sdk-name">Postman</div>
                    <div class="sdk-install">Import Collection</div>
                    <a href="/api/docs/postman" class="btn btn-outline">Download</a>
                </div>
            </div>
        </div>
    </section>
    
    <!-- Resources -->
    <section class="resources" id="resources">
        <div class="container">
            <div class="section-header">
                <h2>Developer Resources</h2>
                <p>Everything you need to succeed with our API</p>
            </div>
            <ul class="resource-list">
                <li class="resource-item">
                    <div class="resource-icon">
                        <i class="fas fa-book-open"></i>
                    </div>
                    <div class="resource-content">
                        <h4>Comprehensive Guides</h4>
                        <p>Step-by-step tutorials for common use cases and integrations</p>
                    </div>
                </li>
                <li class="resource-item">
                    <div class="resource-icon">
                        <i class="fas fa-code"></i>
                    </div>
                    <div class="resource-content">
                        <h4>Code Examples</h4>
                        <p>Ready-to-use code snippets in multiple programming languages</p>
                    </div>
                </li>
                <li class="resource-item">
                    <div class="resource-icon">
                        <i class="fas fa-video"></i>
                    </div>
                    <div class="resource-content">
                        <h4>Video Tutorials</h4>
                        <p>Watch our engineers build real applications with the API</p>
                    </div>
                </li>
                <li class="resource-item">
                    <div class="resource-icon">
                        <i class="fas fa-comments"></i>
                    </div>
                    <div class="resource-content">
                        <h4>Developer Community</h4>
                        <p>Join our Discord server to connect with other developers</p>
                    </div>
                </li>
                <li class="resource-item">
                    <div class="resource-icon">
                        <i class="fas fa-headset"></i>
                    </div>
                    <div class="resource-content">
                        <h4>Premium Support</h4>
                        <p>Get direct access to our engineering team for critical issues</p>
                    </div>
                </li>
                <li class="resource-item">
                    <div class="resource-icon">
                        <i class="fas fa-newspaper"></i>
                    </div>
                    <div class="resource-content">
                        <h4>API Changelog</h4>
                        <p>Stay updated with the latest features and improvements</p>
                    </div>
                </li>
            </ul>
        </div>
    </section>
    
    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <div class="footer-grid">
                <div class="footer-section">
                    <h3>Documentation</h3>
                    <ul class="footer-links">
                        <li><a href="/portal/quickstart">Quick Start Guide</a></li>
                        <li><a href="/docs">API Reference</a></li>
                        <li><a href="/portal/authentication">Authentication</a></li>
                        <li><a href="/portal/webhooks">Webhooks</a></li>
                        <li><a href="/portal/errors">Error Handling</a></li>
                    </ul>
                </div>
                <div class="footer-section">
                    <h3>SDKs & Tools</h3>
                    <ul class="footer-links">
                        <li><a href="/portal/sdk/python">Python SDK</a></li>
                        <li><a href="/portal/sdk/javascript">JavaScript SDK</a></li>
                        <li><a href="/portal/sdk/react-native">React Native SDK</a></li>
                        <li><a href="/portal/postman">Postman Collection</a></li>
                        <li><a href="/portal/openapi">OpenAPI Spec</a></li>
                    </ul>
                </div>
                <div class="footer-section">
                    <h3>Resources</h3>
                    <ul class="footer-links">
                        <li><a href="/portal/guides">Integration Guides</a></li>
                        <li><a href="/portal/examples">Code Examples</a></li>
                        <li><a href="/portal/best-practices">Best Practices</a></li>
                        <li><a href="/portal/changelog">API Changelog</a></li>
                        <li><a href="https://status.roadtripstoryteller.com">API Status</a></li>
                    </ul>
                </div>
                <div class="footer-section">
                    <h3>Support</h3>
                    <ul class="footer-links">
                        <li><a href="mailto:developers@roadtripstoryteller.com">Email Support</a></li>
                        <li><a href="https://discord.gg/roadtrip-dev">Discord Community</a></li>
                        <li><a href="/portal/faq">FAQ</a></li>
                        <li><a href="/portal/contact">Contact Us</a></li>
                    </ul>
                </div>
            </div>
            <div class="footer-bottom">
                <p>&copy; 2024 AI Road Trip Storyteller. All rights reserved.</p>
            </div>
        </div>
    </footer>
    
    <script>
        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
        
        // Add fade-in animation on scroll
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                }
            });
        }, observerOptions);
        
        document.querySelectorAll('.feature-card, .api-card, .sdk-card').forEach(el => {
            observer.observe(el);
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/quickstart", response_class=HTMLResponse)
async def quickstart_guide():
    """Quick start guide for developers"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quick Start Guide - AI Road Trip Storyteller API</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css">
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
            --success: #28a745;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 0;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        h1 {
            color: var(--primary);
            font-size: 2.5rem;
            margin-bottom: 1rem;
        }
        
        .intro {
            font-size: 1.125rem;
            color: var(--text-light);
            margin-bottom: 3rem;
        }
        
        .steps {
            counter-reset: step-counter;
        }
        
        .step {
            background: white;
            padding: 2rem;
            margin-bottom: 2rem;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: relative;
            padding-left: 4rem;
        }
        
        .step::before {
            counter-increment: step-counter;
            content: counter(step-counter);
            position: absolute;
            left: 1.5rem;
            top: 2rem;
            width: 2rem;
            height: 2rem;
            background: var(--highlight);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
        }
        
        .step h2 {
            color: var(--primary);
            margin-top: 0;
            margin-bottom: 1rem;
        }
        
        .step p {
            color: var(--text-light);
            margin-bottom: 1rem;
        }
        
        pre {
            background: var(--primary) !important;
            border-radius: 6px;
            padding: 1rem !important;
            overflow-x: auto;
            margin: 1rem 0 !important;
        }
        
        code {
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.875rem;
        }
        
        .note {
            background: #e3f2fd;
            border-left: 4px solid var(--highlight);
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 4px;
        }
        
        .note strong {
            color: var(--highlight);
        }
        
        .success-message {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 1rem;
            border-radius: 4px;
            margin-top: 1rem;
        }
        
        .btn {
            display: inline-block;
            padding: 0.75rem 1.5rem;
            background: var(--highlight);
            color: white;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 500;
            transition: all 0.3s;
        }
        
        .btn:hover {
            background: var(--accent);
            transform: translateY(-2px);
        }
        
        .language-tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        
        .language-tab {
            padding: 0.5rem 1rem;
            background: var(--bg);
            border: 2px solid transparent;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .language-tab.active {
            background: white;
            border-color: var(--highlight);
            color: var(--highlight);
        }
        
        .code-block {
            display: none;
        }
        
        .code-block.active {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Quick Start Guide</h1>
        <p class="intro">Get up and running with the AI Road Trip Storyteller API in just 5 minutes. This guide will walk you through creating your first AI-generated story.</p>
        
        <div class="steps">
            <div class="step">
                <h2>Create Your Account</h2>
                <p>First, you'll need to register for an API account. This will give you access to your API credentials.</p>
                
                <div class="language-tabs">
                    <button class="language-tab active" onclick="showLanguage('register', 'curl')">cURL</button>
                    <button class="language-tab" onclick="showLanguage('register', 'python')">Python</button>
                    <button class="language-tab" onclick="showLanguage('register', 'javascript')">JavaScript</button>
                </div>
                
                <div class="code-block active" id="register-curl">
                    <pre><code class="language-bash">curl -X POST https://api.roadtripstoryteller.com/api/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "your-email@example.com",
    "password": "YourSecurePassword123!",
    "full_name": "Your Name"
  }'</code></pre>
                </div>
                
                <div class="code-block" id="register-python">
                    <pre><code class="language-python">import requests

response = requests.post(
    "https://api.roadtripstoryteller.com/api/auth/register",
    json={
        "email": "your-email@example.com",
        "password": "YourSecurePassword123!",
        "full_name": "Your Name"
    }
)

user_data = response.json()
print(f"Welcome, {user_data['full_name']}!")</code></pre>
                </div>
                
                <div class="code-block" id="register-javascript">
                    <pre><code class="language-javascript">const response = await fetch('https://api.roadtripstoryteller.com/api/auth/register', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        email: 'your-email@example.com',
        password: 'YourSecurePassword123!',
        full_name: 'Your Name'
    })
});

const userData = await response.json();
console.log(`Welcome, ${userData.full_name}!`);</code></pre>
                </div>
                
                <div class="note">
                    <strong>Note:</strong> Use a strong password with at least 8 characters, including uppercase, lowercase, numbers, and special characters.
                </div>
            </div>
            
            <div class="step">
                <h2>Get Your Access Token</h2>
                <p>Now, authenticate with your credentials to receive a JWT access token.</p>
                
                <div class="language-tabs">
                    <button class="language-tab active" onclick="showLanguage('login', 'curl')">cURL</button>
                    <button class="language-tab" onclick="showLanguage('login', 'python')">Python</button>
                    <button class="language-tab" onclick="showLanguage('login', 'javascript')">JavaScript</button>
                </div>
                
                <div class="code-block active" id="login-curl">
                    <pre><code class="language-bash">curl -X POST https://api.roadtripstoryteller.com/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "your-email@example.com",
    "password": "YourSecurePassword123!"
  }'</code></pre>
                </div>
                
                <div class="code-block" id="login-python">
                    <pre><code class="language-python">response = requests.post(
    "https://api.roadtripstoryteller.com/api/auth/login",
    json={
        "email": "your-email@example.com",
        "password": "YourSecurePassword123!"
    }
)

tokens = response.json()
access_token = tokens['access_token']
print(f"Access token received: {access_token[:20]}...")</code></pre>
                </div>
                
                <div class="code-block" id="login-javascript">
                    <pre><code class="language-javascript">const response = await fetch('https://api.roadtripstoryteller.com/api/auth/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        email: 'your-email@example.com',
        password: 'YourSecurePassword123!'
    })
});

const tokens = await response.json();
const accessToken = tokens.access_token;
console.log(`Access token received: ${accessToken.substring(0, 20)}...`);</code></pre>
                </div>
                
                <div class="success-message">
                    <strong>Success!</strong> You'll receive an access token and refresh token. The access token expires in 1 hour, while the refresh token lasts 30 days.
                </div>
            </div>
            
            <div class="step">
                <h2>Generate Your First Story</h2>
                <p>Let's create an AI-generated story for Times Square in New York City!</p>
                
                <div class="language-tabs">
                    <button class="language-tab active" onclick="showLanguage('story', 'curl')">cURL</button>
                    <button class="language-tab" onclick="showLanguage('story', 'python')">Python</button>
                    <button class="language-tab" onclick="showLanguage('story', 'javascript')">JavaScript</button>
                </div>
                
                <div class="code-block active" id="story-curl">
                    <pre><code class="language-bash">curl -X POST https://api.roadtripstoryteller.com/api/story/generate \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "latitude": 40.7580,
    "longitude": -73.9855,
    "story_type": "historical",
    "personality": "morgan_freeman",
    "include_local_facts": true
  }'</code></pre>
                </div>
                
                <div class="code-block" id="story-python">
                    <pre><code class="language-python">headers = {
    "Authorization": f"Bearer {access_token}"
}

story_response = requests.post(
    "https://api.roadtripstoryteller.com/api/story/generate",
    headers=headers,
    json={
        "latitude": 40.7580,
        "longitude": -73.9855,
        "story_type": "historical",
        "personality": "morgan_freeman",
        "include_local_facts": True
    }
)

story = story_response.json()
print(f"Story: {story['content']}")
print(f"Audio URL: {story['audio_url']}")</code></pre>
                </div>
                
                <div class="code-block" id="story-javascript">
                    <pre><code class="language-javascript">const storyResponse = await fetch('https://api.roadtripstoryteller.com/api/story/generate', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        latitude: 40.7580,
        longitude: -73.9855,
        story_type: 'historical',
        personality: 'morgan_freeman',
        include_local_facts: true
    })
});

const story = await storyResponse.json();
console.log(`Story: ${story.content}`);
console.log(`Audio URL: ${story.audio_url}`);</code></pre>
                </div>
                
                <div class="note">
                    <strong>Response includes:</strong>
                    <ul style="margin: 0.5rem 0;">
                        <li>Generated story content</li>
                        <li>Audio URL with Morgan Freeman's voice</li>
                        <li>Story duration and metadata</li>
                        <li>Location information</li>
                    </ul>
                </div>
            </div>
            
            <div class="step">
                <h2>Play the Audio</h2>
                <p>The API returns an audio URL that you can play directly in your application.</p>
                
                <pre><code class="language-javascript">// Web Browser
const audio = new Audio(story.audio_url);
audio.play();

// React Native
import { Audio } from 'expo-av';
const { sound } = await Audio.Sound.createAsync(
    { uri: story.audio_url },
    { shouldPlay: true }
);</code></pre>
                
                <div class="success-message">
                    <strong>Congratulations!</strong> You've successfully generated and played your first AI story. The audio will be in Morgan Freeman's voice, telling a historical story about Times Square.
                </div>
            </div>
            
            <div class="step">
                <h2>What's Next?</h2>
                <p>Now that you've created your first story, explore these advanced features:</p>
                
                <ul style="margin: 1rem 0;">
                    <li><strong>Voice Commands:</strong> Process user voice input with <code>/api/voice/command</code></li>
                    <li><strong>Trip Planning:</strong> Create multi-stop journeys with <code>/api/trips/create</code></li>
                    <li><strong>Bookings:</strong> Search and book hotels with <code>/api/bookings/hotels/search</code></li>
                    <li><strong>Personalities:</strong> Try different voices like David Attenborough or custom characters</li>
                    <li><strong>Real-time Updates:</strong> Subscribe to webhooks for trip events</li>
                </ul>
                
                <div style="margin-top: 2rem;">
                    <a href="/docs" class="btn">Explore Full API Reference →</a>
                </div>
            </div>
        </div>
        
        <div class="note" style="margin-top: 3rem;">
            <strong>Need Help?</strong> Join our <a href="https://discord.gg/roadtrip-dev" style="color: var(--highlight);">Discord community</a> or email us at <a href="mailto:developers@roadtripstoryteller.com" style="color: var(--highlight);">developers@roadtripstoryteller.com</a>
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-javascript.min.js"></script>
    
    <script>
        function showLanguage(section, language) {
            // Hide all code blocks in section
            document.querySelectorAll(`[id^="${section}-"]`).forEach(block => {
                block.classList.remove('active');
            });
            
            // Remove active class from all tabs in section
            event.target.parentElement.querySelectorAll('.language-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected language
            document.getElementById(`${section}-${language}`).classList.add('active');
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


@router.get("/examples", response_class=HTMLResponse)
async def interactive_examples():
    """Interactive API examples with live testing"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interactive API Examples - AI Road Trip Storyteller</title>
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
            margin-bottom: 2rem;
        }
        
        .example-grid {
            display: grid;
            gap: 2rem;
        }
        
        .example-card {
            background: white;
            border-radius: 8px;
            padding: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .example-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .example-title {
            font-size: 1.5rem;
            font-weight: 600;
            color: #1a1a2e;
        }
        
        .try-it-btn {
            padding: 0.5rem 1rem;
            background: #3282b8;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.3s;
        }
        
        .try-it-btn:hover {
            background: #0f4c75;
        }
        
        .code-section {
            margin: 1.5rem 0;
        }
        
        .code-tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }
        
        .code-tab {
            padding: 0.5rem 1rem;
            background: #e9ecef;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .code-tab.active {
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
            border-radius: 6px;
        }
        
        .try-it-section {
            display: none;
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 2px solid #e9ecef;
        }
        
        .try-it-section.active {
            display: block;
        }
        
        .input-group {
            margin-bottom: 1rem;
        }
        
        .input-label {
            display: block;
            font-weight: 500;
            margin-bottom: 0.5rem;
        }
        
        .input-field {
            width: 100%;
            padding: 0.5rem;
            border: 1px solid #ced4da;
            border-radius: 4px;
            font-size: 1rem;
        }
        
        .execute-btn {
            padding: 0.75rem 2rem;
            background: #28a745;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: 500;
            font-size: 1rem;
        }
        
        .execute-btn:hover {
            background: #218838;
        }
        
        .result-section {
            margin-top: 2rem;
        }
        
        .result-box {
            background: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 1rem;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.875rem;
            overflow-x: auto;
            white-space: pre-wrap;
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(0,0,0,0.1);
            border-radius: 50%;
            border-top-color: #3282b8;
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .error-message {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
            padding: 1rem;
            border-radius: 4px;
            margin-top: 1rem;
        }
        
        .success-message {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            color: #155724;
            padding: 1rem;
            border-radius: 4px;
            margin-top: 1rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 Interactive API Examples</h1>
        <p>Try out our API endpoints directly in your browser. Click "Try It" to test with real data.</p>
        
        <div class="example-grid">
            <!-- Authentication Example -->
            <div class="example-card">
                <div class="example-header">
                    <h2 class="example-title">Authentication</h2>
                    <button class="try-it-btn" onclick="toggleTryIt('auth')">Try It</button>
                </div>
                
                <p>Login to get your access token for API requests.</p>
                
                <div class="code-section">
                    <div class="code-tabs">
                        <button class="code-tab active" onclick="showCode('auth', 'curl')">cURL</button>
                        <button class="code-tab" onclick="showCode('auth', 'python')">Python</button>
                        <button class="code-tab" onclick="showCode('auth', 'javascript')">JavaScript</button>
                    </div>
                    
                    <div class="code-content active" id="auth-curl">
                        <pre><code class="language-bash">curl -X POST https://api.roadtripstoryteller.com/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{
    "email": "demo@example.com",
    "password": "DemoPassword123!"
  }'</code></pre>
                    </div>
                    
                    <div class="code-content" id="auth-python">
                        <pre><code class="language-python">import requests

response = requests.post(
    "https://api.roadtripstoryteller.com/api/auth/login",
    json={
        "email": "demo@example.com",
        "password": "DemoPassword123!"
    }
)

tokens = response.json()
print(f"Access Token: {tokens['access_token']}")</code></pre>
                    </div>
                    
                    <div class="code-content" id="auth-javascript">
                        <pre><code class="language-javascript">const response = await fetch('https://api.roadtripstoryteller.com/api/auth/login', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        email: 'demo@example.com',
        password: 'DemoPassword123!'
    })
});

const tokens = await response.json();
console.log(`Access Token: ${tokens.access_token}`);</code></pre>
                    </div>
                </div>
                
                <div class="try-it-section" id="auth-try">
                    <h3>Try It Live</h3>
                    <div class="input-group">
                        <label class="input-label">Email</label>
                        <input type="email" class="input-field" id="auth-email" value="demo@example.com">
                    </div>
                    <div class="input-group">
                        <label class="input-label">Password</label>
                        <input type="password" class="input-field" id="auth-password" value="DemoPassword123!">
                    </div>
                    <button class="execute-btn" onclick="executeAuth()">Execute Request</button>
                    <div class="result-section" id="auth-result"></div>
                </div>
            </div>
            
            <!-- Story Generation Example -->
            <div class="example-card">
                <div class="example-header">
                    <h2 class="example-title">Generate AI Story</h2>
                    <button class="try-it-btn" onclick="toggleTryIt('story')">Try It</button>
                </div>
                
                <p>Generate a location-based story with AI and voice synthesis.</p>
                
                <div class="code-section">
                    <div class="code-tabs">
                        <button class="code-tab active" onclick="showCode('story', 'curl')">cURL</button>
                        <button class="code-tab" onclick="showCode('story', 'python')">Python</button>
                        <button class="code-tab" onclick="showCode('story', 'javascript')">JavaScript</button>
                    </div>
                    
                    <div class="code-content active" id="story-curl">
                        <pre><code class="language-bash">curl -X POST https://api.roadtripstoryteller.com/api/story/generate \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "latitude": 40.7128,
    "longitude": -74.0060,
    "story_type": "historical",
    "personality": "david_attenborough"
  }'</code></pre>
                    </div>
                    
                    <div class="code-content" id="story-python">
                        <pre><code class="language-python">response = requests.post(
    "https://api.roadtripstoryteller.com/api/story/generate",
    headers={"Authorization": f"Bearer {access_token}"},
    json={
        "latitude": 40.7128,
        "longitude": -74.0060,
        "story_type": "historical",
        "personality": "david_attenborough"
    }
)

story = response.json()
print(f"Story: {story['content'][:200]}...")
print(f"Audio: {story['audio_url']}")</code></pre>
                    </div>
                    
                    <div class="code-content" id="story-javascript">
                        <pre><code class="language-javascript">const response = await fetch('https://api.roadtripstoryteller.com/api/story/generate', {
    method: 'POST',
    headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
    },
    body: JSON.stringify({
        latitude: 40.7128,
        longitude: -74.0060,
        story_type: 'historical',
        personality: 'david_attenborough'
    })
});

const story = await response.json();
console.log(story);</code></pre>
                    </div>
                </div>
                
                <div class="try-it-section" id="story-try">
                    <h3>Try It Live</h3>
                    <div class="input-group">
                        <label class="input-label">Access Token</label>
                        <input type="text" class="input-field" id="story-token" placeholder="Paste your access token here">
                    </div>
                    <div class="input-group">
                        <label class="input-label">Latitude</label>
                        <input type="number" class="input-field" id="story-lat" value="40.7128" step="0.0001">
                    </div>
                    <div class="input-group">
                        <label class="input-label">Longitude</label>
                        <input type="number" class="input-field" id="story-lng" value="-74.0060" step="0.0001">
                    </div>
                    <div class="input-group">
                        <label class="input-label">Story Type</label>
                        <select class="input-field" id="story-type">
                            <option value="auto">Auto-detect</option>
                            <option value="historical" selected>Historical</option>
                            <option value="cultural">Cultural</option>
                            <option value="nature">Nature</option>
                            <option value="fun_facts">Fun Facts</option>
                        </select>
                    </div>
                    <div class="input-group">
                        <label class="input-label">Voice Personality</label>
                        <select class="input-field" id="story-personality">
                            <option value="morgan_freeman">Morgan Freeman</option>
                            <option value="david_attenborough" selected>David Attenborough</option>
                            <option value="james_earl_jones">James Earl Jones</option>
                            <option value="enthusiastic_guide">Enthusiastic Guide</option>
                        </select>
                    </div>
                    <button class="execute-btn" onclick="executeStory()">Generate Story</button>
                    <div class="result-section" id="story-result"></div>
                </div>
            </div>
            
            <!-- Hotel Search Example -->
            <div class="example-card">
                <div class="example-header">
                    <h2 class="example-title">Search Hotels</h2>
                    <button class="try-it-btn" onclick="toggleTryIt('hotels')">Try It</button>
                </div>
                
                <p>Find available hotels near any location with real-time pricing.</p>
                
                <div class="code-section">
                    <div class="code-tabs">
                        <button class="code-tab active" onclick="showCode('hotels', 'curl')">cURL</button>
                        <button class="code-tab" onclick="showCode('hotels', 'python')">Python</button>
                        <button class="code-tab" onclick="showCode('hotels', 'javascript')">JavaScript</button>
                    </div>
                    
                    <div class="code-content active" id="hotels-curl">
                        <pre><code class="language-bash">curl -X GET "https://api.roadtripstoryteller.com/api/bookings/hotels/search?\\
latitude=40.7128&longitude=-74.0060&radius=5&\\
checkin=2024-06-01&checkout=2024-06-03" \\
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"</code></pre>
                    </div>
                    
                    <div class="code-content" id="hotels-python">
                        <pre><code class="language-python">params = {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "radius": 5,
    "checkin": "2024-06-01",
    "checkout": "2024-06-03"
}

response = requests.get(
    "https://api.roadtripstoryteller.com/api/bookings/hotels/search",
    headers={"Authorization": f"Bearer {access_token}"},
    params=params
)

hotels = response.json()
for hotel in hotels['results'][:3]:
    print(f"{hotel['name']} - ${hotel['price_per_night']}/night")</code></pre>
                    </div>
                    
                    <div class="code-content" id="hotels-javascript">
                        <pre><code class="language-javascript">const params = new URLSearchParams({
    latitude: 40.7128,
    longitude: -74.0060,
    radius: 5,
    checkin: '2024-06-01',
    checkout: '2024-06-03'
});

const response = await fetch(
    `https://api.roadtripstoryteller.com/api/bookings/hotels/search?${params}`,
    {
        headers: {
            'Authorization': `Bearer ${accessToken}`
        }
    }
);

const hotels = await response.json();
console.log(hotels);</code></pre>
                    </div>
                </div>
                
                <div class="try-it-section" id="hotels-try">
                    <h3>Try It Live</h3>
                    <div class="input-group">
                        <label class="input-label">Access Token</label>
                        <input type="text" class="input-field" id="hotels-token" placeholder="Paste your access token here">
                    </div>
                    <div class="input-group">
                        <label class="input-label">Location</label>
                        <select class="input-field" id="hotels-location" onchange="updateLocation()">
                            <option value="40.7128,-74.0060">New York City</option>
                            <option value="34.0522,-118.2437">Los Angeles</option>
                            <option value="41.8781,-87.6298">Chicago</option>
                            <option value="25.7617,-80.1918">Miami</option>
                        </select>
                    </div>
                    <div class="input-group">
                        <label class="input-label">Check-in Date</label>
                        <input type="date" class="input-field" id="hotels-checkin" value="2024-06-01">
                    </div>
                    <div class="input-group">
                        <label class="input-label">Check-out Date</label>
                        <input type="date" class="input-field" id="hotels-checkout" value="2024-06-03">
                    </div>
                    <div class="input-group">
                        <label class="input-label">Search Radius (km)</label>
                        <input type="number" class="input-field" id="hotels-radius" value="5" min="1" max="50">
                    </div>
                    <button class="execute-btn" onclick="executeHotels()">Search Hotels</button>
                    <div class="result-section" id="hotels-result"></div>
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-bash.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-javascript.min.js"></script>
    
    <script>
        // Demo API endpoint (replace with actual endpoint)
        const API_BASE = 'https://api.roadtripstoryteller.com';
        
        function showCode(example, language) {
            // Hide all code blocks
            document.querySelectorAll(`[id^="${example}-"]`).forEach(block => {
                block.classList.remove('active');
            });
            
            // Remove active from all tabs
            event.target.parentElement.querySelectorAll('.code-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected
            document.getElementById(`${example}-${language}`).classList.add('active');
            event.target.classList.add('active');
            
            Prism.highlightAll();
        }
        
        function toggleTryIt(example) {
            const section = document.getElementById(`${example}-try`);
            section.classList.toggle('active');
        }
        
        async function executeAuth() {
            const resultDiv = document.getElementById('auth-result');
            const email = document.getElementById('auth-email').value;
            const password = document.getElementById('auth-password').value;
            
            resultDiv.innerHTML = '<div class="loading"></div> Authenticating...';
            
            try {
                // Simulate API call (replace with actual endpoint)
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                // Mock response
                const response = {
                    access_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    refresh_token: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    token_type: "bearer",
                    expires_in: 3600
                };
                
                resultDiv.innerHTML = `
                    <div class="success-message">✓ Authentication successful!</div>
                    <h4>Response:</h4>
                    <div class="result-box">${JSON.stringify(response, null, 2)}</div>
                    <p style="margin-top: 1rem;"><strong>Copy this access token for the other examples!</strong></p>
                `;
                
                // Auto-fill token in other examples
                document.getElementById('story-token').value = response.access_token;
                document.getElementById('hotels-token').value = response.access_token;
            } catch (error) {
                resultDiv.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
            }
        }
        
        async function executeStory() {
            const resultDiv = document.getElementById('story-result');
            const token = document.getElementById('story-token').value;
            
            if (!token) {
                resultDiv.innerHTML = '<div class="error-message">Please provide an access token</div>';
                return;
            }
            
            resultDiv.innerHTML = '<div class="loading"></div> Generating story...';
            
            try {
                // Simulate API call
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                // Mock response
                const response = {
                    id: "story_123456",
                    content: "As we find ourselves in the heart of New York City, let me paint you a picture of this remarkable metropolis. Standing here at these coordinates, you're witnessing centuries of human ambition carved into steel and stone...",
                    audio_url: "https://storage.roadtripstoryteller.com/audio/story_123456.mp3",
                    duration_seconds: 180,
                    location: {
                        name: "New York City",
                        state: "New York",
                        country: "USA",
                        nearby_landmarks: ["Central Park", "Times Square", "Empire State Building"]
                    },
                    personality: document.getElementById('story-personality').value,
                    story_type: document.getElementById('story-type').value,
                    created_at: new Date().toISOString()
                };
                
                resultDiv.innerHTML = `
                    <div class="success-message">✓ Story generated successfully!</div>
                    <h4>Response:</h4>
                    <div class="result-box">${JSON.stringify(response, null, 2)}</div>
                    <h4 style="margin-top: 1rem;">Preview:</h4>
                    <p style="font-style: italic;">"${response.content.substring(0, 200)}..."</p>
                    <audio controls style="margin-top: 1rem; width: 100%;">
                        <source src="${response.audio_url}" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio>
                `;
            } catch (error) {
                resultDiv.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
            }
        }
        
        async function executeHotels() {
            const resultDiv = document.getElementById('hotels-result');
            const token = document.getElementById('hotels-token').value;
            
            if (!token) {
                resultDiv.innerHTML = '<div class="error-message">Please provide an access token</div>';
                return;
            }
            
            resultDiv.innerHTML = '<div class="loading"></div> Searching hotels...';
            
            try {
                // Simulate API call
                await new Promise(resolve => setTimeout(resolve, 1500));
                
                // Mock response
                const location = document.getElementById('hotels-location').value.split(',');
                const response = {
                    results: [
                        {
                            id: "hotel_001",
                            name: "The Plaza Hotel",
                            address: "768 5th Avenue, New York, NY 10019",
                            rating: 4.7,
                            price_per_night: 699.99,
                            amenities: ["WiFi", "Pool", "Spa", "Restaurant", "Gym"],
                            availability: true,
                            images: ["https://example.com/plaza1.jpg"],
                            distance_km: 0.8
                        },
                        {
                            id: "hotel_002",
                            name: "Hilton Manhattan",
                            address: "123 Broadway, New York, NY 10001",
                            rating: 4.5,
                            price_per_night: 299.99,
                            amenities: ["WiFi", "Gym", "Restaurant", "Business Center"],
                            availability: true,
                            images: ["https://example.com/hilton1.jpg"],
                            distance_km: 1.2
                        },
                        {
                            id: "hotel_003",
                            name: "Budget Inn NYC",
                            address: "456 7th Ave, New York, NY 10001",
                            rating: 3.8,
                            price_per_night: 129.99,
                            amenities: ["WiFi", "Parking"],
                            availability: true,
                            images: ["https://example.com/budget1.jpg"],
                            distance_km: 2.1
                        }
                    ],
                    total_results: 47,
                    page: 1,
                    per_page: 10
                };
                
                let hotelHTML = '<div class="success-message">✓ Found ' + response.total_results + ' hotels</div>';
                hotelHTML += '<h4>Top Results:</h4>';
                
                response.results.forEach(hotel => {
                    hotelHTML += `
                        <div style="background: #f8f9fa; padding: 1rem; margin: 0.5rem 0; border-radius: 4px;">
                            <strong>${hotel.name}</strong> - $${hotel.price_per_night}/night
                            <br>⭐ ${hotel.rating} rating • ${hotel.distance_km}km away
                            <br><small>${hotel.amenities.join(' • ')}</small>
                        </div>
                    `;
                });
                
                hotelHTML += '<h4 style="margin-top: 1rem;">Full Response:</h4>';
                hotelHTML += `<div class="result-box">${JSON.stringify(response, null, 2)}</div>`;
                
                resultDiv.innerHTML = hotelHTML;
            } catch (error) {
                resultDiv.innerHTML = `<div class="error-message">Error: ${error.message}</div>`;
            }
        }
        
        function updateLocation() {
            // Update location based on selection
            const select = document.getElementById('hotels-location');
            const [lat, lng] = select.value.split(',');
            console.log(`Selected location: ${select.options[select.selectedIndex].text}`);
        }
        
        // Initialize
        Prism.highlightAll();
        
        // Set default dates
        const today = new Date();
        const tomorrow = new Date(today);
        tomorrow.setDate(tomorrow.getDate() + 1);
        const dayAfter = new Date(tomorrow);
        dayAfter.setDate(dayAfter.getDate() + 1);
        
        document.getElementById('hotels-checkin').valueAsDate = tomorrow;
        document.getElementById('hotels-checkout').valueAsDate = dayAfter;
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.get("/sdk/{language}", response_class=HTMLResponse)
async def sdk_documentation(language: str):
    """SDK-specific documentation pages"""
    # This would be expanded with full SDK documentation
    sdks = {
        "python": {
            "name": "Python SDK",
            "install": "pip install roadtrip-storyteller",
            "import": "from roadtrip_storyteller import RoadtripStorytellerClient"
        },
        "javascript": {
            "name": "JavaScript SDK",
            "install": "npm install @roadtrip/storyteller-sdk",
            "import": "import RoadtripStorytellerClient from '@roadtrip/storyteller-sdk';"
        },
        "react-native": {
            "name": "React Native SDK",
            "install": "npm install @roadtrip/mobile-sdk",
            "import": "import RoadtripStorytellerMobileClient from '@roadtrip/mobile-sdk';"
        }
    }
    
    if language not in sdks:
        raise HTTPException(status_code=404, detail="SDK not found")
    
    sdk_info = sdks[language]
    
    return HTMLResponse(content=f"""
    <html>
    <head>
        <title>{sdk_info['name']} - AI Road Trip Storyteller</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            body {{
                font-family: 'Inter', sans-serif;
                margin: 0;
                padding: 2rem;
                max-width: 800px;
                margin: 0 auto;
            }}
            h1 {{ color: #1a1a2e; }}
            code {{
                background: #f6f8fa;
                padding: 0.2rem 0.4rem;
                border-radius: 3px;
                font-family: 'Monaco', 'Consolas', monospace;
            }}
            pre {{
                background: #1a1a2e;
                color: white;
                padding: 1rem;
                border-radius: 6px;
                overflow-x: auto;
            }}
        </style>
    </head>
    <body>
        <h1>{sdk_info['name']} Documentation</h1>
        <h2>Installation</h2>
        <pre><code>{sdk_info['install']}</code></pre>
        
        <h2>Quick Start</h2>
        <pre><code>{sdk_info['import']}

// Initialize client
const client = new RoadtripStorytellerClient({{
    accessToken: 'your-access-token'
}});

// Generate a story
const story = await client.stories.generate({{
    latitude: 40.7128,
    longitude: -74.0060,
    personality: 'morgan_freeman'
}});

console.log(story);</code></pre>
        
        <p>Full documentation coming soon...</p>
    </body>
    </html>
    """)


@router.get("/generate-sdks")
async def generate_all_sdks():
    """Generate SDKs from current OpenAPI specification"""
    try:
        # Get OpenAPI spec from the main app
        # This would need to be imported from the main app
        from ..main import app
        openapi_spec = app.openapi()
        
        # Generate SDKs
        from .sdk_generator import generate_sdks_from_openapi
        output_dir = Path(__file__).parent / "generated_sdks"
        
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