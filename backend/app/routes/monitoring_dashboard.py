"""
Monitoring Dashboard Routes
Provides comprehensive system monitoring endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from typing import Dict, Any, List
from datetime import datetime, timedelta

from ..core.auth import get_current_user
from ..models.user import User
from ..monitoring.voice_monitoring_dashboard import voice_monitoring
from ..monitoring.metrics import metrics

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/dashboard")
async def get_monitoring_dashboard(
    current_user: User = Depends(get_current_user)
) -> HTMLResponse:
    """
    Get HTML monitoring dashboard for real-time system metrics
    """
    # Only allow admin users
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Roadtrip Voice System Monitoring</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .header {
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 20px;
            }
            .metric-card {
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .metric-value {
                font-size: 36px;
                font-weight: bold;
                margin: 10px 0;
            }
            .metric-label {
                color: #666;
                font-size: 14px;
            }
            .status-indicator {
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }
            .status-healthy { background-color: #4CAF50; }
            .status-degraded { background-color: #FF9800; }
            .status-critical { background-color: #F44336; }
            .chart-container {
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .error-list {
                max-height: 300px;
                overflow-y: auto;
            }
            .error-item {
                padding: 10px;
                border-bottom: 1px solid #eee;
            }
            .circuit-breaker {
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 12px;
                margin: 4px;
            }
            .cb-closed { background-color: #E8F5E9; color: #2E7D32; }
            .cb-open { background-color: #FFEBEE; color: #C62828; }
            .cb-half-open { background-color: #FFF3E0; color: #F57C00; }
        </style>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body>
        <div class="header">
            <h1>AI Roadtrip Voice System Monitoring</h1>
            <p>Real-time performance metrics and system health</p>
        </div>
        
        <div class="metrics-grid" id="metrics-grid">
            <!-- Metrics will be inserted here -->
        </div>
        
        <div class="chart-container">
            <h3>Response Time Trend (Last 30 Minutes)</h3>
            <canvas id="responseTimeChart"></canvas>
        </div>
        
        <div class="chart-container">
            <h3>Request Volume</h3>
            <canvas id="requestVolumeChart"></canvas>
        </div>
        
        <div class="chart-container">
            <h3>Recent Errors</h3>
            <div id="error-list" class="error-list">
                <!-- Errors will be inserted here -->
            </div>
        </div>
        
        <div class="chart-container">
            <h3>Circuit Breakers</h3>
            <div id="circuit-breakers">
                <!-- Circuit breakers will be inserted here -->
            </div>
        </div>
        
        <script>
            let responseTimeChart;
            let requestVolumeChart;
            
            async function loadMetrics() {
                try {
                    const response = await fetch('/api/voice/metrics');
                    const data = await response.json();
                    updateDashboard(data);
                } catch (error) {
                    console.error('Failed to load metrics:', error);
                }
            }
            
            function updateDashboard(data) {
                // Update metric cards
                const metricsGrid = document.getElementById('metrics-grid');
                metricsGrid.innerHTML = `
                    <div class="metric-card">
                        <div class="metric-label">System Status</div>
                        <div class="metric-value">
                            <span class="status-indicator status-${data.real_time.system_status}"></span>
                            ${data.real_time.system_status.toUpperCase()}
                        </div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Requests/Minute</div>
                        <div class="metric-value">${data.real_time.requests_per_minute}</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">P95 Response Time</div>
                        <div class="metric-value">${data.real_time.response_time.p95.toFixed(2)}s</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Error Rate</div>
                        <div class="metric-value">${(data.real_time.error_rate * 100).toFixed(1)}%</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-label">Cache Hit Rate</div>
                        <div class="metric-value">${(data.real_time.cache_hit_rate * 100).toFixed(0)}%</div>
                    </div>
                `;
                
                // Update response time chart
                updateResponseTimeChart(data.trends);
                
                // Update request volume chart
                updateRequestVolumeChart(data.trends);
                
                // Update error list
                updateErrorList(data.real_time.recent_errors);
                
                // Update circuit breakers
                updateCircuitBreakers(data.circuit_breakers);
            }
            
            function updateResponseTimeChart(trends) {
                const ctx = document.getElementById('responseTimeChart').getContext('2d');
                
                if (!responseTimeChart) {
                    responseTimeChart = new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'P95 Response Time',
                                data: [],
                                borderColor: 'rgb(75, 192, 192)',
                                tension: 0.1
                            }, {
                                label: 'Average Response Time',
                                data: [],
                                borderColor: 'rgb(153, 102, 255)',
                                tension: 0.1
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: {
                                    beginAtZero: true,
                                    title: {
                                        display: true,
                                        text: 'Response Time (seconds)'
                                    }
                                }
                            }
                        }
                    });
                }
                
                if (trends && trends.trends) {
                    responseTimeChart.data.labels = trends.trends.map(t => t.minute);
                    responseTimeChart.data.datasets[0].data = trends.trends.map(t => t.p95_response_time);
                    responseTimeChart.data.datasets[1].data = trends.trends.map(t => t.avg_response_time);
                    responseTimeChart.update();
                }
            }
            
            function updateRequestVolumeChart(trends) {
                const ctx = document.getElementById('requestVolumeChart').getContext('2d');
                
                if (!requestVolumeChart) {
                    requestVolumeChart = new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: [],
                            datasets: [{
                                label: 'Requests',
                                data: [],
                                backgroundColor: 'rgba(54, 162, 235, 0.5)'
                            }]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                }
                
                if (trends && trends.trends) {
                    requestVolumeChart.data.labels = trends.trends.map(t => t.minute);
                    requestVolumeChart.data.datasets[0].data = trends.trends.map(t => t.requests);
                    requestVolumeChart.update();
                }
            }
            
            function updateErrorList(errors) {
                const errorList = document.getElementById('error-list');
                if (!errors || errors.length === 0) {
                    errorList.innerHTML = '<p style="color: #4CAF50;">No recent errors</p>';
                    return;
                }
                
                errorList.innerHTML = errors.map(error => `
                    <div class="error-item">
                        <strong>${error.timestamp}</strong><br>
                        User: ${error.user_id}<br>
                        Intent: ${error.intent}<br>
                        Error: ${error.error}
                    </div>
                `).join('');
            }
            
            function updateCircuitBreakers(breakers) {
                const container = document.getElementById('circuit-breakers');
                container.innerHTML = Object.entries(breakers).map(([service, state]) => `
                    <span class="circuit-breaker cb-${state}">
                        ${service.toUpperCase()}: ${state}
                    </span>
                `).join('');
            }
            
            // Load initial metrics
            loadMetrics();
            
            // Refresh every 10 seconds
            setInterval(loadMetrics, 10000);
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=dashboard_html)


@router.get("/metrics/voice")
async def get_voice_metrics(
    window_minutes: int = 60,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get detailed voice system metrics"""
    # Get real-time metrics
    real_time = voice_monitoring.get_real_time_metrics()
    
    # Get performance trends
    trends = voice_monitoring.get_performance_trends(window_minutes)
    
    # Get error analysis
    errors = voice_monitoring.get_error_analysis()
    
    return {
        "real_time": real_time,
        "trends": trends,
        "errors": errors,
        "window_minutes": window_minutes
    }


@router.get("/health/voice")
async def get_voice_health() -> Dict[str, Any]:
    """Get voice system health status (no auth required for health checks)"""
    metrics = voice_monitoring.get_real_time_metrics()
    
    return {
        "status": metrics["system_status"],
        "healthy": metrics["system_status"] == "healthy",
        "slo_compliance": metrics["slo_compliance"],
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/metrics/export")
async def export_metrics(
    format: str = "json",
    current_user: User = Depends(get_current_user)
) -> Any:
    """Export metrics in various formats for analysis"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get comprehensive metrics
    metrics_data = {
        "voice": voice_monitoring.get_performance_trends(window_minutes=1440),  # 24 hours
        "errors": voice_monitoring.get_error_analysis(),
        "timestamp": datetime.utcnow().isoformat(),
        "export_format": format
    }
    
    if format == "prometheus":
        # Format for Prometheus
        prometheus_metrics = []
        
        # Add voice metrics
        real_time = voice_monitoring.get_real_time_metrics()
        prometheus_metrics.append(f'voice_requests_per_minute {real_time["requests_per_minute"]}')
        prometheus_metrics.append(f'voice_error_rate {real_time["error_rate"]}')
        prometheus_metrics.append(f'voice_cache_hit_rate {real_time["cache_hit_rate"]}')
        
        if "response_time" in real_time:
            prometheus_metrics.append(f'voice_response_time_p50 {real_time["response_time"]["p50"]}')
            prometheus_metrics.append(f'voice_response_time_p95 {real_time["response_time"]["p95"]}')
            prometheus_metrics.append(f'voice_response_time_p99 {real_time["response_time"]["p99"]}')
        
        return "\n".join(prometheus_metrics)
    
    return metrics_data