#!/usr/bin/env python3
"""
Monitor Beta Usage
Real-time monitoring of beta launch metrics and user activity
"""
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
from pathlib import Path
from collections import defaultdict
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.database import get_db
from backend.app.core.logger import get_logger
from backend.app.monitoring.metrics import MetricsCollector

logger = get_logger(__name__)


class BetaUsageMonitor:
    """Monitors beta launch usage and metrics"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.monitoring_interval = 60  # seconds
        self.alert_thresholds = {
            "error_rate": 0.05,  # 5%
            "response_time_p95": 200,  # ms
            "crash_rate": 0.02,  # 2%
            "api_availability": 0.99  # 99%
        }
        
        self.current_metrics = {}
        self.historical_data = defaultdict(list)
        self.alerts_triggered = []
    
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect current metrics"""
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "users": await self._get_user_metrics(),
            "api": await self._get_api_metrics(),
            "voice": await self._get_voice_metrics(),
            "bookings": await self._get_booking_metrics(),
            "performance": await self._get_performance_metrics(),
            "errors": await self._get_error_metrics()
        }
        
        return metrics
    
    async def _get_user_metrics(self) -> Dict[str, Any]:
        """Get user activity metrics"""
        async with get_db() as db:
            # Simulated queries - replace with actual
            total_beta_users = 100
            
            # Active users (last 24 hours)
            active_users_24h = 45
            
            # New signups today
            new_signups_today = 12
            
            # User sessions
            active_sessions = 23
            
            # Platform breakdown
            platform_breakdown = {
                "ios": 55,
                "android": 40,
                "web": 5
            }
            
            # Category activity
            category_activity = {
                "family_travelers": 28,
                "business_travelers": 22,
                "event_attendees": 26,
                "rideshare_drivers": 24
            }
        
        return {
            "total_beta_users": total_beta_users,
            "active_users_24h": active_users_24h,
            "activation_rate": active_users_24h / total_beta_users,
            "new_signups_today": new_signups_today,
            "active_sessions": active_sessions,
            "platform_breakdown": platform_breakdown,
            "category_activity": category_activity
        }
    
    async def _get_api_metrics(self) -> Dict[str, Any]:
        """Get API performance metrics"""
        # Simulated metrics - replace with actual Prometheus queries
        return {
            "requests_per_minute": 342,
            "response_time_p50": 45,  # ms
            "response_time_p95": 120,  # ms
            "response_time_p99": 180,  # ms
            "error_rate": 0.012,  # 1.2%
            "availability": 0.998,  # 99.8%
            "endpoints": {
                "/api/voice-assistant/interact": {
                    "rpm": 156,
                    "avg_response_time": 85,
                    "error_rate": 0.008
                },
                "/api/stories/generate": {
                    "rpm": 89,
                    "avg_response_time": 120,
                    "error_rate": 0.015
                },
                "/api/bookings/search": {
                    "rpm": 45,
                    "avg_response_time": 95,
                    "error_rate": 0.02
                }
            }
        }
    
    async def _get_voice_metrics(self) -> Dict[str, Any]:
        """Get voice interaction metrics"""
        return {
            "total_commands_today": 1847,
            "recognition_accuracy": 0.92,  # 92%
            "avg_response_time": 95,  # ms
            "edge_processing_rate": 0.68,  # 68% processed on edge
            "popular_commands": [
                {"command": "navigate", "count": 423},
                {"command": "play music", "count": 312},
                {"command": "find restaurant", "count": 198},
                {"command": "tell story", "count": 167},
                {"command": "book hotel", "count": 89}
            ],
            "voice_personalities_used": {
                "Captain": 234,
                "Mickey Mouse": 189,
                "DJ Voice": 156,
                "Professional Assistant": 145,
                "Storyteller": 123
            }
        }
    
    async def _get_booking_metrics(self) -> Dict[str, Any]:
        """Get booking metrics"""
        return {
            "searches_today": 234,
            "bookings_attempted": 45,
            "bookings_completed": 38,
            "conversion_rate": 0.162,  # 16.2%
            "booking_types": {
                "hotels": 18,
                "restaurants": 12,
                "parking": 8,
                "activities": 0
            },
            "estimated_revenue": 342.50,  # Commission earned
            "avg_booking_value": 85.25
        }
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get system performance metrics"""
        return {
            "cpu_usage": 0.42,  # 42%
            "memory_usage": 0.68,  # 68%
            "cache_hit_rate": 0.84,  # 84%
            "database_connections": 23,
            "redis_operations_per_sec": 456,
            "ai_model_latency": {
                "gemini-nano": 25,  # ms
                "gemini-1.5-flash": 85,  # ms
                "gemini-1.5-pro": 145  # ms
            }
        }
    
    async def _get_error_metrics(self) -> Dict[str, Any]:
        """Get error and crash metrics"""
        return {
            "app_crashes_today": 3,
            "crash_rate": 0.007,  # 0.7%
            "api_errors_today": 89,
            "error_types": {
                "timeout": 34,
                "rate_limit": 12,
                "validation": 23,
                "server_error": 15,
                "network": 5
            },
            "affected_users": 8,
            "critical_errors": []
        }
    
    def check_alerts(self, metrics: Dict[str, Any]):
        """Check if any metrics exceed alert thresholds"""
        alerts = []
        
        # Check error rate
        error_rate = metrics["api"]["error_rate"]
        if error_rate > self.alert_thresholds["error_rate"]:
            alerts.append({
                "type": "error_rate",
                "severity": "high",
                "message": f"Error rate {error_rate:.1%} exceeds threshold {self.alert_thresholds['error_rate']:.1%}",
                "value": error_rate
            })
        
        # Check response time
        p95_time = metrics["api"]["response_time_p95"]
        if p95_time > self.alert_thresholds["response_time_p95"]:
            alerts.append({
                "type": "response_time",
                "severity": "medium",
                "message": f"P95 response time {p95_time}ms exceeds threshold {self.alert_thresholds['response_time_p95']}ms",
                "value": p95_time
            })
        
        # Check crash rate
        crash_rate = metrics["errors"]["crash_rate"]
        if crash_rate > self.alert_thresholds["crash_rate"]:
            alerts.append({
                "type": "crash_rate",
                "severity": "critical",
                "message": f"Crash rate {crash_rate:.1%} exceeds threshold {self.alert_thresholds['crash_rate']:.1%}",
                "value": crash_rate
            })
        
        # Check availability
        availability = metrics["api"]["availability"]
        if availability < self.alert_thresholds["api_availability"]:
            alerts.append({
                "type": "availability",
                "severity": "critical",
                "message": f"API availability {availability:.1%} below threshold {self.alert_thresholds['api_availability']:.1%}",
                "value": availability
            })
        
        self.alerts_triggered.extend(alerts)
        return alerts
    
    async def generate_dashboard(self, metrics: Dict[str, Any]):
        """Generate monitoring dashboard"""
        print("\033[2J\033[H")  # Clear screen
        print("🚀 AI ROAD TRIP STORYTELLER - BETA MONITORING DASHBOARD")
        print("=" * 80)
        print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # User Metrics
        print("👥 USER METRICS")
        print("-" * 40)
        user_metrics = metrics["users"]
        print(f"Total Beta Users:     {user_metrics['total_beta_users']}")
        print(f"Active (24h):         {user_metrics['active_users_24h']} ({user_metrics['activation_rate']:.1%})")
        print(f"New Signups Today:    {user_metrics['new_signups_today']}")
        print(f"Active Sessions:      {user_metrics['active_sessions']}")
        print()
        
        # API Performance
        print("⚡ API PERFORMANCE")
        print("-" * 40)
        api_metrics = metrics["api"]
        print(f"Requests/min:         {api_metrics['requests_per_minute']}")
        print(f"Response Time (P50):  {api_metrics['response_time_p50']}ms")
        print(f"Response Time (P95):  {api_metrics['response_time_p95']}ms")
        print(f"Error Rate:           {api_metrics['error_rate']:.2%}")
        print(f"Availability:         {api_metrics['availability']:.2%}")
        print()
        
        # Voice Metrics
        print("🎤 VOICE INTERACTIONS")
        print("-" * 40)
        voice_metrics = metrics["voice"]
        print(f"Commands Today:       {voice_metrics['total_commands_today']}")
        print(f"Recognition Accuracy: {voice_metrics['recognition_accuracy']:.1%}")
        print(f"Avg Response Time:    {voice_metrics['avg_response_time']}ms")
        print(f"Edge Processing:      {voice_metrics['edge_processing_rate']:.1%}")
        print()
        
        # Booking Metrics
        print("💰 BOOKINGS")
        print("-" * 40)
        booking_metrics = metrics["bookings"]
        print(f"Searches:             {booking_metrics['searches_today']}")
        print(f"Completed:            {booking_metrics['bookings_completed']}/{booking_metrics['bookings_attempted']}")
        print(f"Conversion Rate:      {booking_metrics['conversion_rate']:.1%}")
        print(f"Est. Revenue Today:   ${booking_metrics['estimated_revenue']:.2f}")
        print()
        
        # System Health
        print("🔧 SYSTEM HEALTH")
        print("-" * 40)
        perf_metrics = metrics["performance"]
        print(f"CPU Usage:            {perf_metrics['cpu_usage']:.1%}")
        print(f"Memory Usage:         {perf_metrics['memory_usage']:.1%}")
        print(f"Cache Hit Rate:       {perf_metrics['cache_hit_rate']:.1%}")
        print()
        
        # Alerts
        alerts = self.check_alerts(metrics)
        if alerts:
            print("🚨 ACTIVE ALERTS")
            print("-" * 40)
            for alert in alerts:
                severity_icon = {"critical": "❌", "high": "⚠️", "medium": "⚡"}
                print(f"{severity_icon.get(alert['severity'], '•')} {alert['message']}")
            print()
        else:
            print("✅ All systems operating normally")
            print()
        
        # Top Issues
        if metrics["errors"]["critical_errors"]:
            print("❗ CRITICAL ISSUES")
            print("-" * 40)
            for error in metrics["errors"]["critical_errors"][:5]:
                print(f"  • {error}")
            print()
    
    async def save_metrics_snapshot(self, metrics: Dict[str, Any]):
        """Save metrics snapshot for analysis"""
        filename = f"beta_metrics_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        # Add historical data
        for key, value in metrics.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, (int, float)):
                        self.historical_data[f"{key}.{subkey}"].append({
                            "timestamp": metrics["timestamp"],
                            "value": subvalue
                        })
        
        # Save snapshot
        with open(filename, "w") as f:
            json.dump({
                "snapshot": metrics,
                "alerts": self.alerts_triggered[-10:],  # Last 10 alerts
                "summary": self.generate_summary(metrics)
            }, f, indent=2)
    
    def generate_summary(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate metrics summary"""
        return {
            "health_score": self.calculate_health_score(metrics),
            "key_metrics": {
                "activation_rate": metrics["users"]["activation_rate"],
                "api_error_rate": metrics["api"]["error_rate"],
                "voice_accuracy": metrics["voice"]["recognition_accuracy"],
                "booking_conversion": metrics["bookings"]["conversion_rate"]
            },
            "trends": self.calculate_trends(),
            "recommendations": self.generate_recommendations(metrics)
        }
    
    def calculate_health_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate overall system health score (0-100)"""
        scores = []
        
        # API health (40% weight)
        api_score = (
            (1 - metrics["api"]["error_rate"]) * 50 +
            metrics["api"]["availability"] * 50
        )
        scores.append(api_score * 0.4)
        
        # User engagement (30% weight)
        user_score = metrics["users"]["activation_rate"] * 100
        scores.append(user_score * 0.3)
        
        # Voice performance (20% weight)
        voice_score = metrics["voice"]["recognition_accuracy"] * 100
        scores.append(voice_score * 0.2)
        
        # System performance (10% weight)
        perf_score = (
            (1 - metrics["performance"]["cpu_usage"]) * 50 +
            (1 - metrics["performance"]["memory_usage"]) * 50
        )
        scores.append(perf_score * 0.1)
        
        return sum(scores)
    
    def calculate_trends(self) -> Dict[str, str]:
        """Calculate metric trends"""
        trends = {}
        
        # Simple trend calculation based on recent history
        for metric_name, history in self.historical_data.items():
            if len(history) >= 5:
                recent_values = [h["value"] for h in history[-5:]]
                if recent_values[-1] > np.mean(recent_values[:-1]) * 1.1:
                    trends[metric_name] = "increasing"
                elif recent_values[-1] < np.mean(recent_values[:-1]) * 0.9:
                    trends[metric_name] = "decreasing"
                else:
                    trends[metric_name] = "stable"
        
        return trends
    
    def generate_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on metrics"""
        recommendations = []
        
        # Check activation rate
        if metrics["users"]["activation_rate"] < 0.6:
            recommendations.append(
                "Low activation rate - consider improving onboarding flow or sending reminder emails"
            )
        
        # Check voice accuracy
        if metrics["voice"]["recognition_accuracy"] < 0.9:
            recommendations.append(
                "Voice recognition below target - review accent test results and adjust models"
            )
        
        # Check booking conversion
        if metrics["bookings"]["conversion_rate"] < 0.15:
            recommendations.append(
                "Low booking conversion - analyze user flow and simplify booking process"
            )
        
        # Check edge processing
        if metrics["voice"]["edge_processing_rate"] < 0.7:
            recommendations.append(
                "Low edge processing rate - verify edge models are properly deployed"
            )
        
        if not recommendations:
            recommendations.append("All metrics within acceptable ranges - continue monitoring")
        
        return recommendations
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        print("Starting beta monitoring...")
        print(f"Refresh interval: {self.monitoring_interval} seconds")
        print("Press Ctrl+C to stop")
        print()
        
        while True:
            try:
                # Collect metrics
                metrics = await self.collect_metrics()
                self.current_metrics = metrics
                
                # Generate dashboard
                await self.generate_dashboard(metrics)
                
                # Save snapshot every 5 minutes
                if datetime.now().minute % 5 == 0:
                    await self.save_metrics_snapshot(metrics)
                
                # Wait for next interval
                await asyncio.sleep(self.monitoring_interval)
                
            except KeyboardInterrupt:
                print("\n\nMonitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                await asyncio.sleep(self.monitoring_interval)


async def main():
    """Main function"""
    monitor = BetaUsageMonitor()
    
    try:
        await monitor.monitor_loop()
    except Exception as e:
        print(f"\n❌ Monitoring failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())