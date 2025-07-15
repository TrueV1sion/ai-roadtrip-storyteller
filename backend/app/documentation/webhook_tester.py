"""
Webhook Testing Tool
Provides an interface for testing and debugging webhooks
"""

from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from typing import Dict, Any, List, Optional
import json
import asyncio
import aiohttp
from datetime import datetime, timezone
import hmac
import hashlib
from uuid import uuid4

router = APIRouter(prefix="/webhooks", tags=["Webhook Testing"])

# In-memory storage for webhook test results (in production, use Redis or DB)
webhook_tests: Dict[str, Dict[str, Any]] = {}


@router.get("/tester", response_class=HTMLResponse)
async def webhook_tester_ui():
    """Interactive webhook testing interface"""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Webhook Tester - AI Road Trip Storyteller</title>
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
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 2rem 0;
            margin: -2rem -2rem 2rem;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        
        .header p {
            opacity: 0.9;
        }
        
        .test-section {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: white;
            border-radius: 8px;
            padding: 2rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .card h2 {
            color: var(--primary);
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .form-group {
            margin-bottom: 1.5rem;
        }
        
        .form-label {
            display: block;
            font-weight: 500;
            margin-bottom: 0.5rem;
            color: var(--text);
        }
        
        .form-input, .form-select, .form-textarea {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
            font-family: inherit;
            transition: border-color 0.3s;
        }
        
        .form-input:focus, .form-select:focus, .form-textarea:focus {
            outline: none;
            border-color: var(--highlight);
        }
        
        .form-textarea {
            resize: vertical;
            min-height: 150px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.875rem;
        }
        
        .btn {
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 4px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s;
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
        }
        
        .btn-secondary {
            background: var(--bg);
            color: var(--text);
            border: 1px solid #ddd;
        }
        
        .btn-secondary:hover {
            background: #e9ecef;
        }
        
        .btn-danger {
            background: var(--danger);
            color: white;
        }
        
        .btn-danger:hover {
            background: #c82333;
        }
        
        .event-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0.5rem;
        }
        
        .event-checkbox {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem;
            background: var(--bg);
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .event-checkbox:hover {
            background: #e9ecef;
        }
        
        .event-checkbox input {
            cursor: pointer;
        }
        
        .webhook-url {
            display: flex;
            gap: 0.5rem;
            align-items: center;
            background: var(--bg);
            padding: 1rem;
            border-radius: 4px;
            margin-bottom: 1rem;
        }
        
        .webhook-url code {
            flex: 1;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.875rem;
        }
        
        .copy-btn {
            padding: 0.5rem 1rem;
            background: var(--secondary);
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.875rem;
        }
        
        .copy-btn:hover {
            background: var(--primary);
        }
        
        .results-section {
            margin-top: 2rem;
        }
        
        .result-item {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .result-event {
            font-weight: 600;
            color: var(--primary);
        }
        
        .result-time {
            font-size: 0.875rem;
            color: var(--text-light);
        }
        
        .result-status {
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 500;
        }
        
        .status-success {
            background: #d4edda;
            color: #155724;
        }
        
        .status-pending {
            background: #fff3cd;
            color: #856404;
        }
        
        .status-failed {
            background: #f8d7da;
            color: #721c24;
        }
        
        .result-details {
            background: var(--bg);
            padding: 1rem;
            border-radius: 4px;
            margin-top: 1rem;
        }
        
        .detail-row {
            display: flex;
            margin-bottom: 0.5rem;
        }
        
        .detail-label {
            font-weight: 500;
            width: 150px;
            color: var(--text-light);
        }
        
        .detail-value {
            flex: 1;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.875rem;
        }
        
        .json-preview {
            background: var(--primary);
            color: white;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.875rem;
            margin-top: 1rem;
        }
        
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(0,0,0,0.1);
            border-radius: 50%;
            border-top-color: var(--highlight);
            animation: spin 1s ease-in-out infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: var(--text-light);
        }
        
        .empty-state i {
            font-size: 3rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }
        
        @media (max-width: 768px) {
            .test-section {
                grid-template-columns: 1fr;
            }
            
            .event-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🪝 Webhook Tester</h1>
            <p>Test and debug your webhook integrations</p>
        </div>
        
        <div class="test-section">
            <div class="card">
                <h2><i class="fas fa-cog"></i> Configuration</h2>
                
                <div class="form-group">
                    <label class="form-label">Webhook URL</label>
                    <input type="url" class="form-input" id="webhook-url" 
                           placeholder="https://your-app.com/webhooks/roadtrip"
                           value="https://webhook.site/unique-url">
                    <small style="color: var(--text-light);">Your endpoint that will receive webhook events</small>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Secret Key</label>
                    <input type="text" class="form-input" id="webhook-secret" 
                           placeholder="your-webhook-secret"
                           value="test-secret-key">
                    <small style="color: var(--text-light);">Used for HMAC-SHA256 signature verification</small>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Events to Test</label>
                    <div class="event-grid">
                        <label class="event-checkbox">
                            <input type="checkbox" name="events" value="trip.started" checked>
                            <span>trip.started</span>
                        </label>
                        <label class="event-checkbox">
                            <input type="checkbox" name="events" value="trip.completed">
                            <span>trip.completed</span>
                        </label>
                        <label class="event-checkbox">
                            <input type="checkbox" name="events" value="story.generated" checked>
                            <span>story.generated</span>
                        </label>
                        <label class="event-checkbox">
                            <input type="checkbox" name="events" value="booking.confirmed">
                            <span>booking.confirmed</span>
                        </label>
                        <label class="event-checkbox">
                            <input type="checkbox" name="events" value="voice.processed">
                            <span>voice.processed</span>
                        </label>
                        <label class="event-checkbox">
                            <input type="checkbox" name="events" value="payment.processed">
                            <span>payment.processed</span>
                        </label>
                    </div>
                </div>
                
                <div class="form-group">
                    <label class="form-label">Test Data (Optional JSON)</label>
                    <textarea class="form-textarea" id="test-data" placeholder='{"custom": "data"}'>{
  "user_id": "test_user_123",
  "metadata": {
    "source": "webhook_tester",
    "environment": "test"
  }
}</textarea>
                </div>
                
                <div style="display: flex; gap: 1rem;">
                    <button class="btn btn-primary" onclick="sendTestWebhooks()">
                        <i class="fas fa-paper-plane"></i> Send Test Webhooks
                    </button>
                    <button class="btn btn-secondary" onclick="clearResults()">
                        <i class="fas fa-trash"></i> Clear Results
                    </button>
                </div>
            </div>
            
            <div class="card">
                <h2><i class="fas fa-info-circle"></i> Webhook Information</h2>
                
                <div class="webhook-url">
                    <code id="endpoint-url">https://api.roadtripstoryteller.com/webhooks/test/YOUR_ID</code>
                    <button class="copy-btn" onclick="copyEndpoint()">Copy</button>
                </div>
                
                <h3 style="margin-top: 1.5rem; margin-bottom: 1rem;">Event Payload Format</h3>
                <div class="json-preview">
{
  "event": "trip.started",
  "timestamp": "2024-01-01T00:00:00Z",
  "data": {
    // Event-specific data
  },
  "signature": "sha256=abc123..."
}</div>
                
                <h3 style="margin-top: 1.5rem; margin-bottom: 1rem;">Signature Verification</h3>
                <div style="background: var(--bg); padding: 1rem; border-radius: 4px;">
                    <p style="margin-bottom: 0.5rem;">Verify webhook authenticity using HMAC-SHA256:</p>
                    <pre style="background: var(--primary); color: white; padding: 1rem; border-radius: 4px; overflow-x: auto;">
const crypto = require('crypto');

function verifyWebhook(payload, signature, secret) {
  const expected = crypto
    .createHmac('sha256', secret)
    .update(payload, 'utf8')
    .digest('hex');
  
  return signature === `sha256=${expected}`;
}</pre>
                </div>
                
                <h3 style="margin-top: 1.5rem; margin-bottom: 1rem;">Response Requirements</h3>
                <ul style="margin-left: 1.5rem; color: var(--text-light);">
                    <li>Return HTTP 200 status for successful processing</li>
                    <li>Respond within 5 seconds</li>
                    <li>Failed webhooks will be retried up to 3 times</li>
                    <li>Exponential backoff between retries</li>
                </ul>
            </div>
        </div>
        
        <div class="results-section">
            <h2 style="margin-bottom: 1rem;">📊 Test Results</h2>
            <div id="results-container">
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No test results yet. Send a test webhook to see results here.</p>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        let testResults = [];
        
        async function sendTestWebhooks() {
            const url = document.getElementById('webhook-url').value;
            const secret = document.getElementById('webhook-secret').value;
            const events = Array.from(document.querySelectorAll('input[name="events"]:checked'))
                .map(cb => cb.value);
            
            let customData = {};
            try {
                const testDataValue = document.getElementById('test-data').value;
                if (testDataValue) {
                    customData = JSON.parse(testDataValue);
                }
            } catch (e) {
                alert('Invalid JSON in test data field');
                return;
            }
            
            if (!url) {
                alert('Please enter a webhook URL');
                return;
            }
            
            if (events.length === 0) {
                alert('Please select at least one event');
                return;
            }
            
            // Clear previous results
            testResults = [];
            updateResults();
            
            // Send test for each selected event
            for (const event of events) {
                const testId = generateTestId();
                const result = {
                    id: testId,
                    event: event,
                    status: 'pending',
                    timestamp: new Date().toISOString(),
                    url: url
                };
                
                testResults.push(result);
                updateResults();
                
                // Send the webhook test
                try {
                    const response = await fetch('/portal/webhooks/send-test', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            test_id: testId,
                            webhook_url: url,
                            secret: secret,
                            event: event,
                            custom_data: customData
                        })
                    });
                    
                    const data = await response.json();
                    
                    // Update result
                    const resultIndex = testResults.findIndex(r => r.id === testId);
                    testResults[resultIndex] = {
                        ...testResults[resultIndex],
                        ...data,
                        status: data.success ? 'success' : 'failed'
                    };
                    
                    updateResults();
                } catch (error) {
                    const resultIndex = testResults.findIndex(r => r.id === testId);
                    testResults[resultIndex].status = 'failed';
                    testResults[resultIndex].error = error.message;
                    updateResults();
                }
                
                // Small delay between webhooks
                await new Promise(resolve => setTimeout(resolve, 500));
            }
        }
        
        function updateResults() {
            const container = document.getElementById('results-container');
            
            if (testResults.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <i class="fas fa-inbox"></i>
                        <p>No test results yet. Send a test webhook to see results here.</p>
                    </div>
                `;
                return;
            }
            
            container.innerHTML = testResults.map(result => `
                <div class="result-item">
                    <div class="result-header">
                        <div>
                            <span class="result-event">${result.event}</span>
                            <span class="result-time">${new Date(result.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <span class="result-status status-${result.status}">
                            ${getStatusIcon(result.status)} ${result.status}
                        </span>
                    </div>
                    
                    ${result.status !== 'pending' ? `
                        <div class="result-details">
                            <div class="detail-row">
                                <span class="detail-label">Endpoint:</span>
                                <span class="detail-value">${result.url}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Response Time:</span>
                                <span class="detail-value">${result.response_time || 'N/A'}</span>
                            </div>
                            <div class="detail-row">
                                <span class="detail-label">Status Code:</span>
                                <span class="detail-value">${result.status_code || 'N/A'}</span>
                            </div>
                            ${result.error ? `
                                <div class="detail-row">
                                    <span class="detail-label">Error:</span>
                                    <span class="detail-value" style="color: var(--danger);">${result.error}</span>
                                </div>
                            ` : ''}
                        </div>
                        
                        ${result.payload ? `
                            <div class="json-preview">
${JSON.stringify(result.payload, null, 2)}
                            </div>
                        ` : ''}
                    ` : '<div class="loading" style="margin: 1rem 0;"></div>'}
                </div>
            `).join('');
        }
        
        function getStatusIcon(status) {
            switch (status) {
                case 'success':
                    return '<i class="fas fa-check-circle"></i>';
                case 'failed':
                    return '<i class="fas fa-times-circle"></i>';
                case 'pending':
                    return '<i class="fas fa-clock"></i>';
                default:
                    return '';
            }
        }
        
        function generateTestId() {
            return 'test_' + Math.random().toString(36).substring(2, 15);
        }
        
        function clearResults() {
            testResults = [];
            updateResults();
        }
        
        function copyEndpoint() {
            const text = document.getElementById('endpoint-url').textContent;
            navigator.clipboard.writeText(text).then(() => {
                const btn = event.target;
                const originalText = btn.textContent;
                btn.textContent = 'Copied!';
                setTimeout(() => {
                    btn.textContent = originalText;
                }, 2000);
            });
        }
        
        // Generate unique endpoint URL
        const endpointId = Math.random().toString(36).substring(2, 15);
        document.getElementById('endpoint-url').textContent = 
            `https://api.roadtripstoryteller.com/webhooks/test/${endpointId}`;
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@router.post("/send-test")
async def send_test_webhook(
    background_tasks: BackgroundTasks,
    request: Request
):
    """Send a test webhook to the specified URL"""
    data = await request.json()
    
    test_id = data.get("test_id")
    webhook_url = data.get("webhook_url")
    secret = data.get("secret", "")
    event = data.get("event")
    custom_data = data.get("custom_data", {})
    
    # Generate webhook payload
    payload = generate_webhook_payload(event, custom_data)
    
    # Generate signature
    signature = generate_webhook_signature(json.dumps(payload), secret)
    
    # Send webhook asynchronously
    background_tasks.add_task(
        send_webhook_request,
        test_id,
        webhook_url,
        payload,
        signature
    )
    
    # Return immediate response
    return {
        "test_id": test_id,
        "status": "pending",
        "message": "Webhook test initiated"
    }


def generate_webhook_payload(event: str, custom_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate realistic webhook payload for testing"""
    timestamp = datetime.now(timezone.utc).isoformat()
    
    base_payload = {
        "event": event,
        "timestamp": timestamp,
        "id": str(uuid4()),
    }
    
    # Event-specific data
    event_data = {
        "trip.started": {
            "trip_id": f"trip_{uuid4().hex[:8]}",
            "user_id": custom_data.get("user_id", "user_123"),
            "start_location": {
                "latitude": 40.7128,
                "longitude": -74.0060,
                "name": "New York City",
                "address": "New York, NY, USA"
            },
            "destination": {
                "latitude": 34.0522,
                "longitude": -118.2437,
                "name": "Los Angeles",
                "address": "Los Angeles, CA, USA"
            },
            "estimated_duration": 2880,  # minutes
            "distance_km": 4489.2
        },
        "trip.completed": {
            "trip_id": f"trip_{uuid4().hex[:8]}",
            "user_id": custom_data.get("user_id", "user_123"),
            "duration_minutes": 2920,
            "distance_km": 4489.2,
            "stories_generated": 47,
            "photos_taken": 156,
            "bookings_made": 3
        },
        "story.generated": {
            "story_id": f"story_{uuid4().hex[:8]}",
            "trip_id": f"trip_{uuid4().hex[:8]}",
            "user_id": custom_data.get("user_id", "user_123"),
            "location": {
                "latitude": 36.1699,
                "longitude": -115.1398,
                "name": "Las Vegas",
                "state": "Nevada"
            },
            "story_type": "historical",
            "personality": "morgan_freeman",
            "duration_seconds": 180,
            "audio_url": "https://storage.roadtripstoryteller.com/audio/story_sample.mp3"
        },
        "booking.confirmed": {
            "booking_id": f"booking_{uuid4().hex[:8]}",
            "user_id": custom_data.get("user_id", "user_123"),
            "type": "hotel",
            "hotel": {
                "name": "Grand Plaza Hotel",
                "address": "123 Main St, Las Vegas, NV",
                "check_in": "2024-06-15",
                "check_out": "2024-06-17",
                "total_price": 459.98,
                "commission": 45.99
            }
        },
        "voice.processed": {
            "command_id": f"cmd_{uuid4().hex[:8]}",
            "user_id": custom_data.get("user_id", "user_123"),
            "transcription": "Tell me about this area",
            "intent": "location_info",
            "confidence": 0.95,
            "response_generated": True,
            "audio_duration": 2.5
        },
        "payment.processed": {
            "payment_id": f"pay_{uuid4().hex[:8]}",
            "user_id": custom_data.get("user_id", "user_123"),
            "amount": 29.99,
            "currency": "USD",
            "type": "subscription",
            "status": "completed",
            "payment_method": {
                "type": "card",
                "last4": "4242"
            }
        }
    }
    
    # Add event-specific data
    base_payload["data"] = {
        **event_data.get(event, {}),
        **custom_data
    }
    
    return base_payload


def generate_webhook_signature(payload: str, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook"""
    if not secret:
        return ""
    
    signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return f"sha256={signature}"


async def send_webhook_request(
    test_id: str,
    webhook_url: str,
    payload: Dict[str, Any],
    signature: str
):
    """Send the actual webhook request"""
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": payload["event"],
        "X-Webhook-ID": payload["id"],
        "User-Agent": "RoadtripStoryteller-Webhook/1.0"
    }
    
    start_time = datetime.now()
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                end_time = datetime.now()
                response_time = f"{(end_time - start_time).total_seconds():.2f}s"
                
                # Store result
                webhook_tests[test_id] = {
                    "test_id": test_id,
                    "success": response.status == 200,
                    "status_code": response.status,
                    "response_time": response_time,
                    "payload": payload,
                    "response_body": await response.text(),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
    except asyncio.TimeoutError:
        webhook_tests[test_id] = {
            "test_id": test_id,
            "success": False,
            "error": "Request timeout (10s exceeded)",
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        webhook_tests[test_id] = {
            "test_id": test_id,
            "success": False,
            "error": str(e),
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@router.get("/test/{test_id}")
async def get_test_result(test_id: str):
    """Get the result of a webhook test"""
    if test_id not in webhook_tests:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return webhook_tests[test_id]


@router.post("/validate-signature")
async def validate_webhook_signature(request: Request):
    """Validate a webhook signature"""
    data = await request.json()
    
    payload = data.get("payload", "")
    signature = data.get("signature", "")
    secret = data.get("secret", "")
    
    if not all([payload, signature, secret]):
        raise HTTPException(
            status_code=400,
            detail="Missing required fields: payload, signature, secret"
        )
    
    # Generate expected signature
    expected_signature = generate_webhook_signature(
        json.dumps(payload) if isinstance(payload, dict) else payload,
        secret
    )
    
    # Compare signatures
    is_valid = hmac.compare_digest(signature, expected_signature)
    
    return {
        "valid": is_valid,
        "provided_signature": signature,
        "expected_signature": expected_signature,
        "message": "Signature is valid" if is_valid else "Signature mismatch"
    }


@router.get("/sample-code/{language}")
async def get_webhook_sample_code(language: str):
    """Get sample webhook handler code in different languages"""
    samples = {
        "python": """
# Python webhook handler example
import hmac
import hashlib
import json
from flask import Flask, request, jsonify

app = Flask(__name__)
WEBHOOK_SECRET = 'your-webhook-secret'

@app.route('/webhooks/roadtrip', methods=['POST'])
def handle_webhook():
    # Get the raw request body
    payload = request.get_data(as_text=True)
    
    # Verify signature
    signature = request.headers.get('X-Webhook-Signature', '')
    if not verify_signature(payload, signature):
        return jsonify({'error': 'Invalid signature'}), 401
    
    # Parse the webhook data
    data = json.loads(payload)
    event = data['event']
    
    # Handle different events
    if event == 'trip.started':
        handle_trip_started(data['data'])
    elif event == 'story.generated':
        handle_story_generated(data['data'])
    elif event == 'booking.confirmed':
        handle_booking_confirmed(data['data'])
    
    # Return success response
    return jsonify({'status': 'success'}), 200

def verify_signature(payload, signature):
    expected = 'sha256=' + hmac.new(
        WEBHOOK_SECRET.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

def handle_trip_started(data):
    print(f"Trip started: {data['trip_id']}")
    # Your logic here

def handle_story_generated(data):
    print(f"Story generated: {data['story_id']}")
    # Your logic here

def handle_booking_confirmed(data):
    print(f"Booking confirmed: {data['booking_id']}")
    # Your logic here
""",
        "javascript": """
// Node.js webhook handler example
const express = require('express');
const crypto = require('crypto');

const app = express();
const WEBHOOK_SECRET = 'your-webhook-secret';

// Middleware to capture raw body
app.use('/webhooks/roadtrip', express.raw({ type: 'application/json' }));

app.post('/webhooks/roadtrip', (req, res) => {
    // Get raw body as string
    const payload = req.body.toString('utf8');
    
    // Verify signature
    const signature = req.headers['x-webhook-signature'];
    if (!verifySignature(payload, signature)) {
        return res.status(401).json({ error: 'Invalid signature' });
    }
    
    // Parse the webhook data
    const data = JSON.parse(payload);
    const { event } = data;
    
    // Handle different events
    switch (event) {
        case 'trip.started':
            handleTripStarted(data.data);
            break;
        case 'story.generated':
            handleStoryGenerated(data.data);
            break;
        case 'booking.confirmed':
            handleBookingConfirmed(data.data);
            break;
        default:
            console.log(`Unhandled event: ${event}`);
    }
    
    // Return success response
    res.status(200).json({ status: 'success' });
});

function verifySignature(payload, signature) {
    const expected = 'sha256=' + crypto
        .createHmac('sha256', WEBHOOK_SECRET)
        .update(payload, 'utf8')
        .digest('hex');
    
    return crypto.timingSafeEqual(
        Buffer.from(signature),
        Buffer.from(expected)
    );
}

function handleTripStarted(data) {
    console.log(`Trip started: ${data.trip_id}`);
    // Your logic here
}

function handleStoryGenerated(data) {
    console.log(`Story generated: ${data.story_id}`);
    // Your logic here
}

function handleBookingConfirmed(data) {
    console.log(`Booking confirmed: ${data.booking_id}`);
    // Your logic here
}

app.listen(3000, () => {
    console.log('Webhook handler listening on port 3000');
});
""",
        "php": """
<?php
// PHP webhook handler example

$webhookSecret = 'your-webhook-secret';

// Get raw POST data
$payload = file_get_contents('php://input');
$headers = getallheaders();

// Verify signature
$signature = $headers['X-Webhook-Signature'] ?? '';
if (!verifySignature($payload, $signature, $webhookSecret)) {
    http_response_code(401);
    die(json_encode(['error' => 'Invalid signature']));
}

// Parse webhook data
$data = json_decode($payload, true);
$event = $data['event'];

// Handle different events
switch ($event) {
    case 'trip.started':
        handleTripStarted($data['data']);
        break;
    case 'story.generated':
        handleStoryGenerated($data['data']);
        break;
    case 'booking.confirmed':
        handleBookingConfirmed($data['data']);
        break;
    default:
        error_log("Unhandled event: $event");
}

// Return success response
http_response_code(200);
echo json_encode(['status' => 'success']);

function verifySignature($payload, $signature, $secret) {
    $expected = 'sha256=' . hash_hmac('sha256', $payload, $secret);
    return hash_equals($signature, $expected);
}

function handleTripStarted($data) {
    error_log("Trip started: " . $data['trip_id']);
    // Your logic here
}

function handleStoryGenerated($data) {
    error_log("Story generated: " . $data['story_id']);
    // Your logic here
}

function handleBookingConfirmed($data) {
    error_log("Booking confirmed: " . $data['booking_id']);
    // Your logic here
}
"""
    }
    
    if language not in samples:
        raise HTTPException(status_code=404, detail="Language not found")
    
    return {
        "language": language,
        "code": samples[language],
        "filename": {
            "python": "webhook_handler.py",
            "javascript": "webhook_handler.js",
            "php": "webhook_handler.php"
        }[language]
    }