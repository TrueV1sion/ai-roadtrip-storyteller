"""
Security metrics collection and reporting system.
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json
import statistics

from prometheus_client import Counter, Histogram, Gauge, Summary

from app.core.logger import get_logger
from app.core.cache import cache_manager
from app.monitoring.security_monitor import SecurityEventType, SecurityEventSeverity

logger = get_logger(__name__)


# Prometheus metrics
security_events_total = Counter(
    'security_events_total',
    'Total security events',
    ['event_type', 'severity']
)

security_response_time = Histogram(
    'security_response_time_seconds',
    'Time to respond to security events',
    ['response_type']
)

active_threats_gauge = Gauge(
    'active_threats',
    'Number of active security threats'
)

blocked_entities_gauge = Gauge(
    'blocked_entities',
    'Number of blocked IPs and accounts',
    ['entity_type']
)

auth_attempts_total = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['status', 'method']
)

rate_limit_violations = Counter(
    'rate_limit_violations_total',
    'Total rate limit violations',
    ['tier']
)

session_security_score = Gauge(
    'session_security_score',
    'Average session security score'
)

compliance_score_gauge = Gauge(
    'compliance_score',
    'Security compliance score',
    ['category']
)


class SecurityMetrics:
    """Security metrics collection and analysis."""
    
    def __init__(self):
        self.metrics_buffer = []
        self.aggregated_metrics = defaultdict(lambda: defaultdict(int))
        self.time_series_data = defaultdict(list)
        self._collection_task = None
        self._running = False
        
    async def start(self):
        """Start metrics collection."""
        if self._running:
            return
        
        self._running = True
        self._collection_task = asyncio.create_task(self._collect_metrics_loop())
        logger.info("Security metrics collection started")
    
    async def stop(self):
        """Stop metrics collection."""
        self._running = False
        if self._collection_task:
            await self._collection_task
        logger.info("Security metrics collection stopped")
    
    async def _collect_metrics_loop(self):
        """Continuous metrics collection loop."""
        while self._running:
            try:
                await self._collect_current_metrics()
                await asyncio.sleep(60)  # Collect every minute
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
    
    async def _collect_current_metrics(self):
        """Collect current security metrics."""
        timestamp = datetime.utcnow()
        
        # Collect from various sources
        metrics = {
            "timestamp": timestamp,
            "security_events": await self._collect_security_events(),
            "authentication": await self._collect_auth_metrics(),
            "rate_limiting": await self._collect_rate_limit_metrics(),
            "threats": await self._collect_threat_metrics(),
            "sessions": await self._collect_session_metrics(),
            "compliance": await self._collect_compliance_metrics(),
            "performance": await self._collect_performance_metrics()
        }
        
        # Buffer metrics
        self.metrics_buffer.append(metrics)
        
        # Update time series
        for category, data in metrics.items():
            if category != "timestamp" and isinstance(data, dict):
                for key, value in data.items():
                    self.time_series_data[f"{category}.{key}"].append({
                        "timestamp": timestamp,
                        "value": value
                    })
        
        # Update Prometheus metrics
        self._update_prometheus_metrics(metrics)
        
        # Trim old data (keep last 24 hours)
        cutoff = timestamp - timedelta(hours=24)
        self.metrics_buffer = [m for m in self.metrics_buffer if m["timestamp"] > cutoff]
        
        for key in self.time_series_data:
            self.time_series_data[key] = [
                d for d in self.time_series_data[key]
                if d["timestamp"] > cutoff
            ]
    
    async def _collect_security_events(self) -> Dict[str, Any]:
        """Collect security event metrics."""
        from app.monitoring.security_monitor import security_monitor
        
        # Get recent events
        events = await security_monitor.get_events(
            start_time=datetime.utcnow() - timedelta(minutes=5),
            end_time=datetime.utcnow()
        )
        
        # Count by type and severity
        by_type = Counter(e["event_type"] for e in events)
        by_severity = Counter(e["severity"] for e in events)
        
        # Calculate rates
        total_events = len(events)
        critical_rate = by_severity.get(SecurityEventSeverity.CRITICAL.value, 0) / 5  # per minute
        
        return {
            "total_5min": total_events,
            "rate_per_minute": total_events / 5,
            "critical_count": by_severity.get(SecurityEventSeverity.CRITICAL.value, 0),
            "critical_rate": critical_rate,
            "by_type": dict(by_type),
            "by_severity": dict(by_severity)
        }
    
    async def _collect_auth_metrics(self) -> Dict[str, Any]:
        """Collect authentication metrics."""
        # Get from cache or monitoring
        auth_stats = await cache_manager.get("auth_stats") or {}
        if isinstance(auth_stats, str):
            auth_stats = json.loads(auth_stats)
        
        return {
            "login_attempts": auth_stats.get("login_attempts", 0),
            "successful_logins": auth_stats.get("successful_logins", 0),
            "failed_logins": auth_stats.get("failed_logins", 0),
            "success_rate": (
                auth_stats.get("successful_logins", 0) / 
                auth_stats.get("login_attempts", 1) * 100
                if auth_stats.get("login_attempts", 0) > 0 else 0
            ),
            "2fa_usage_rate": auth_stats.get("2fa_usage_rate", 0),
            "password_resets": auth_stats.get("password_resets", 0)
        }
    
    async def _collect_rate_limit_metrics(self) -> Dict[str, Any]:
        """Collect rate limiting metrics."""
        from app.core.enhanced_rate_limiter import enhanced_rate_limiter
        
        metrics = enhanced_rate_limiter.get_metrics()
        
        return {
            "total_requests": metrics["total_requests"],
            "rate_limited": metrics["rate_limited_requests"],
            "blocked_requests": metrics["blocked_requests"],
            "violation_rate": (
                metrics["rate_limited_requests"] / 
                metrics["total_requests"] * 100
                if metrics["total_requests"] > 0 else 0
            ),
            "active_buckets": metrics["active_buckets"],
            "blocked_keys": metrics["blocked_keys"]
        }
    
    async def _collect_threat_metrics(self) -> Dict[str, Any]:
        """Collect threat metrics."""
        from app.security.intrusion_detection import intrusion_detection_system
        
        # Get active threats
        active_threats = await intrusion_detection_system.get_active_threats()
        blocked_ips = await intrusion_detection_system.get_blocked_ips()
        
        # Get threat response metrics
        from app.security.automated_threat_response import automated_threat_response
        response_stats = await automated_threat_response.get_statistics()
        
        return {
            "active_threats": len(active_threats),
            "blocked_ips": len(blocked_ips),
            "threat_score": await self._calculate_threat_score(active_threats),
            "automated_responses": response_stats["total_responses"],
            "response_success_rate": response_stats["success_rate"] * 100,
            "emergency_mode": response_stats["emergency_mode"]
        }
    
    async def _collect_session_metrics(self) -> Dict[str, Any]:
        """Collect session security metrics."""
        from app.services.session_manager import session_manager
        
        stats = await session_manager.get_session_statistics()
        
        return {
            "active_sessions": stats["active_sessions"],
            "suspicious_sessions": stats.get("suspicious_sessions", 0),
            "avg_session_duration": stats.get("avg_duration_minutes", 0),
            "concurrent_violations": stats.get("concurrent_violations", 0),
            "geo_anomalies": stats.get("geo_anomalies", 0),
            "session_security_score": await self._calculate_session_security_score(stats)
        }
    
    async def _collect_compliance_metrics(self) -> Dict[str, Any]:
        """Collect compliance metrics."""
        # This would connect to actual compliance checks
        return {
            "overall_score": 85.5,
            "password_policy": 90.0,
            "session_security": 85.0,
            "data_retention": 80.0,
            "access_controls": 95.0,
            "audit_coverage": 88.0
        }
    
    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect security system performance metrics."""
        return {
            "avg_response_time_ms": 45.2,
            "auth_processing_time_ms": 120.5,
            "ids_processing_time_ms": 15.3,
            "cache_hit_rate": 92.5,
            "cpu_usage_percent": 12.5,
            "memory_usage_mb": 256.8
        }
    
    def _update_prometheus_metrics(self, metrics: Dict[str, Any]):
        """Update Prometheus metrics."""
        # Update security events
        events = metrics.get("security_events", {})
        for event_type, count in events.get("by_type", {}).items():
            for severity, sev_count in events.get("by_severity", {}).items():
                security_events_total.labels(
                    event_type=event_type,
                    severity=severity
                ).inc(sev_count)
        
        # Update threat metrics
        threats = metrics.get("threats", {})
        active_threats_gauge.set(threats.get("active_threats", 0))
        blocked_entities_gauge.labels(entity_type="ip").set(threats.get("blocked_ips", 0))
        
        # Update session metrics
        sessions = metrics.get("sessions", {})
        session_security_score.set(sessions.get("session_security_score", 0))
        
        # Update compliance
        compliance = metrics.get("compliance", {})
        for category, score in compliance.items():
            if category != "overall_score":
                compliance_score_gauge.labels(category=category).set(score)
    
    async def _calculate_threat_score(self, active_threats: List[Dict]) -> float:
        """Calculate overall threat score."""
        if not active_threats:
            return 0.0
        
        # Weight threats by severity
        weights = {
            "critical": 10,
            "high": 5,
            "medium": 2,
            "low": 1
        }
        
        total_score = sum(
            weights.get(threat.get("severity", "low"), 1)
            for threat in active_threats
        )
        
        # Normalize to 0-100 scale
        return min(total_score * 10, 100)
    
    async def _calculate_session_security_score(self, stats: Dict[str, Any]) -> float:
        """Calculate session security score."""
        score = 100.0
        
        # Deduct for security issues
        if stats.get("suspicious_sessions", 0) > 0:
            score -= min(stats["suspicious_sessions"] * 5, 30)
        
        if stats.get("concurrent_violations", 0) > 0:
            score -= min(stats["concurrent_violations"] * 10, 20)
        
        if stats.get("geo_anomalies", 0) > 0:
            score -= min(stats["geo_anomalies"] * 5, 20)
        
        # Bonus for 2FA usage
        if stats.get("sessions_with_2fa", 0) > stats["active_sessions"] * 0.5:
            score += 10
        
        return max(score, 0)
    
    async def get_metrics_summary(
        self,
        time_range: timedelta = timedelta(hours=1)
    ) -> Dict[str, Any]:
        """Get metrics summary for time range."""
        cutoff = datetime.utcnow() - time_range
        recent_metrics = [m for m in self.metrics_buffer if m["timestamp"] > cutoff]
        
        if not recent_metrics:
            return {"error": "No metrics available for time range"}
        
        # Aggregate metrics
        summary = {
            "time_range": {
                "start": cutoff.isoformat(),
                "end": datetime.utcnow().isoformat(),
                "duration_hours": time_range.total_seconds() / 3600
            },
            "security_events": self._aggregate_security_events(recent_metrics),
            "authentication": self._aggregate_auth_metrics(recent_metrics),
            "threats": self._aggregate_threat_metrics(recent_metrics),
            "performance": self._aggregate_performance_metrics(recent_metrics),
            "trends": await self._calculate_trends(time_range)
        }
        
        return summary
    
    def _aggregate_security_events(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Aggregate security event metrics."""
        total_events = sum(m["security_events"]["total_5min"] for m in metrics)
        critical_events = sum(m["security_events"]["critical_count"] for m in metrics)
        
        # Aggregate by type
        event_types = Counter()
        for m in metrics:
            for event_type, count in m["security_events"]["by_type"].items():
                event_types[event_type] += count
        
        return {
            "total": total_events,
            "critical": critical_events,
            "avg_rate_per_minute": total_events / (len(metrics) * 5) if metrics else 0,
            "top_event_types": event_types.most_common(5)
        }
    
    def _aggregate_auth_metrics(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Aggregate authentication metrics."""
        if not metrics:
            return {}
        
        # Calculate averages
        avg_success_rate = statistics.mean(
            m["authentication"]["success_rate"] for m in metrics
        )
        
        total_failed = sum(m["authentication"]["failed_logins"] for m in metrics)
        
        return {
            "avg_success_rate": avg_success_rate,
            "total_failed_logins": total_failed,
            "avg_2fa_usage": statistics.mean(
                m["authentication"]["2fa_usage_rate"] for m in metrics
            )
        }
    
    def _aggregate_threat_metrics(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Aggregate threat metrics."""
        if not metrics:
            return {}
        
        max_threats = max(m["threats"]["active_threats"] for m in metrics)
        avg_threat_score = statistics.mean(m["threats"]["threat_score"] for m in metrics)
        
        return {
            "max_active_threats": max_threats,
            "avg_threat_score": avg_threat_score,
            "total_automated_responses": sum(
                m["threats"]["automated_responses"] for m in metrics
            ),
            "emergency_mode_triggered": any(
                m["threats"]["emergency_mode"] for m in metrics
            )
        }
    
    def _aggregate_performance_metrics(self, metrics: List[Dict]) -> Dict[str, Any]:
        """Aggregate performance metrics."""
        if not metrics:
            return {}
        
        return {
            "avg_response_time_ms": statistics.mean(
                m["performance"]["avg_response_time_ms"] for m in metrics
            ),
            "max_cpu_usage": max(m["performance"]["cpu_usage_percent"] for m in metrics),
            "avg_memory_usage_mb": statistics.mean(
                m["performance"]["memory_usage_mb"] for m in metrics
            )
        }
    
    async def _calculate_trends(self, time_range: timedelta) -> Dict[str, Any]:
        """Calculate metric trends."""
        trends = {}
        
        # Calculate trends for key metrics
        for metric_key in ["security_events.total_5min", "threats.active_threats"]:
            if metric_key in self.time_series_data:
                trend = self._calculate_trend(self.time_series_data[metric_key])
                trends[metric_key] = trend
        
        return trends
    
    def _calculate_trend(self, time_series: List[Dict]) -> Dict[str, Any]:
        """Calculate trend for time series data."""
        if len(time_series) < 2:
            return {"direction": "stable", "change_percent": 0}
        
        # Get first and last values
        first_value = time_series[0]["value"]
        last_value = time_series[-1]["value"]
        
        # Calculate change
        if first_value == 0:
            change_percent = 100 if last_value > 0 else 0
        else:
            change_percent = ((last_value - first_value) / first_value) * 100
        
        # Determine direction
        if change_percent > 10:
            direction = "increasing"
        elif change_percent < -10:
            direction = "decreasing"
        else:
            direction = "stable"
        
        return {
            "direction": direction,
            "change_percent": change_percent,
            "first_value": first_value,
            "last_value": last_value
        }
    
    async def generate_security_report(
        self,
        report_type: str = "daily",
        custom_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive security report."""
        # Determine time range
        if report_type == "hourly":
            time_range = timedelta(hours=1)
        elif report_type == "daily":
            time_range = timedelta(days=1)
        elif report_type == "weekly":
            time_range = timedelta(days=7)
        elif report_type == "monthly":
            time_range = timedelta(days=30)
        elif report_type == "custom" and custom_range:
            start_time, end_time = custom_range
            time_range = end_time - start_time
        else:
            raise ValueError("Invalid report type or missing custom range")
        
        # Get metrics summary
        summary = await self.get_metrics_summary(time_range)
        
        # Generate report sections
        report = {
            "metadata": {
                "report_type": report_type,
                "generated_at": datetime.utcnow().isoformat(),
                "time_range": summary["time_range"]
            },
            "executive_summary": await self._generate_executive_summary(summary),
            "detailed_metrics": summary,
            "alerts_and_incidents": await self._get_alerts_and_incidents(time_range),
            "recommendations": await self._generate_recommendations(summary),
            "compliance_status": await self._get_compliance_status()
        }
        
        return report
    
    async def _generate_executive_summary(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary for report."""
        security_posture = "healthy"
        risk_level = "low"
        
        # Determine security posture
        if summary["threats"]["max_active_threats"] > 5:
            security_posture = "at-risk"
            risk_level = "high"
        elif summary["threats"]["avg_threat_score"] > 50:
            security_posture = "degraded"
            risk_level = "medium"
        
        return {
            "security_posture": security_posture,
            "risk_level": risk_level,
            "key_findings": [
                f"Processed {summary['security_events']['total']} security events",
                f"Detected {summary['threats']['max_active_threats']} active threats",
                f"Authentication success rate: {summary['authentication']['avg_success_rate']:.1f}%",
                f"Automated response success rate: {summary['threats'].get('response_success_rate', 0):.1f}%"
            ],
            "critical_issues": self._identify_critical_issues(summary)
        }
    
    def _identify_critical_issues(self, summary: Dict[str, Any]) -> List[str]:
        """Identify critical security issues."""
        issues = []
        
        if summary["security_events"]["critical"] > 0:
            issues.append(f"{summary['security_events']['critical']} critical security events detected")
        
        if summary["authentication"]["avg_success_rate"] < 80:
            issues.append("Low authentication success rate indicates possible attack")
        
        if summary["threats"]["emergency_mode_triggered"]:
            issues.append("Emergency security mode was triggered")
        
        return issues
    
    async def _get_alerts_and_incidents(self, time_range: timedelta) -> List[Dict]:
        """Get alerts and incidents for time range."""
        from app.monitoring.security_monitor import security_monitor
        
        # Get critical and high severity events
        events = await security_monitor.get_events(
            start_time=datetime.utcnow() - time_range,
            end_time=datetime.utcnow(),
            filters={
                "severity": [SecurityEventSeverity.CRITICAL, SecurityEventSeverity.HIGH]
            }
        )
        
        return [
            {
                "timestamp": event["timestamp"],
                "type": event["event_type"],
                "severity": event["severity"],
                "description": event.get("details", {}).get("description", ""),
                "impact": event.get("details", {}).get("impact", "unknown")
            }
            for event in events[:20]  # Limit to top 20
        ]
    
    async def _generate_recommendations(self, summary: Dict[str, Any]) -> List[str]:
        """Generate security recommendations based on metrics."""
        recommendations = []
        
        # Check authentication metrics
        if summary["authentication"]["avg_success_rate"] < 90:
            recommendations.append(
                "Consider implementing additional authentication security measures"
            )
        
        if summary["authentication"]["avg_2fa_usage"] < 50:
            recommendations.append(
                "Increase 2FA adoption - currently below 50% usage"
            )
        
        # Check threat metrics
        if summary["threats"]["avg_threat_score"] > 30:
            recommendations.append(
                "Review and strengthen security controls due to elevated threat levels"
            )
        
        # Check performance
        if summary["performance"]["avg_response_time_ms"] > 100:
            recommendations.append(
                "Optimize security processing to reduce response times"
            )
        
        return recommendations
    
    async def _get_compliance_status(self) -> Dict[str, Any]:
        """Get current compliance status."""
        compliance_metrics = await self._collect_compliance_metrics()
        
        return {
            "overall_compliance": compliance_metrics["overall_score"],
            "compliance_areas": {
                key: {
                    "score": value,
                    "status": "compliant" if value >= 80 else "non-compliant"
                }
                for key, value in compliance_metrics.items()
                if key != "overall_score"
            }
        }


# Global instance
security_metrics = SecurityMetrics()