#!/usr/bin/env python3
"""
Automated health check monitoring script for AI Road Trip Storyteller.
Performs continuous monitoring and sends alerts when issues are detected.
"""

import asyncio
import aiohttp
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import logging
from dataclasses import dataclass
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration
HEALTH_CHECK_ENDPOINTS = {
    "basic": "/health",
    "readiness": "/health/ready",
    "deep": "/health/v2/deep",
    "performance": "/health/v2/performance"
}

DEFAULT_CHECK_INTERVAL = 60  # seconds
DEEP_CHECK_INTERVAL = 300  # 5 minutes
ALERT_COOLDOWN = 1800  # 30 minutes between same alerts


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    endpoint: str
    status: HealthStatus
    response_time: float
    details: Dict[str, Any]
    timestamp: datetime
    error: Optional[str] = None


@dataclass
class Alert:
    severity: str
    title: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime


class HealthCheckMonitor:
    def __init__(self, base_url: str, config: Dict[str, Any]):
        self.base_url = base_url.rstrip("/")
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self.results_history: List[HealthCheckResult] = []
        self.alerts_sent: Dict[str, datetime] = {}
        self.logger = self._setup_logging()
        
    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        logger = logging.getLogger("health_monitor")
        logger.setLevel(logging.INFO)
        
        # Console handler
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console.setFormatter(formatter)
        logger.addHandler(console)
        
        # File handler
        if self.config.get("log_file"):
            file_handler = logging.FileHandler(self.config["log_file"])
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    async def start(self):
        """Start the monitoring process."""
        self.session = aiohttp.ClientSession()
        self.logger.info(f"Starting health check monitoring for {self.base_url}")
        
        try:
            # Start monitoring tasks
            tasks = [
                self._monitor_basic_health(),
                self._monitor_deep_health(),
                self._monitor_performance(),
                self._cleanup_history()
            ]
            
            await asyncio.gather(*tasks)
            
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources."""
        if self.session:
            await self.session.close()
    
    async def _monitor_basic_health(self):
        """Monitor basic health endpoints."""
        while True:
            try:
                # Check basic health
                result = await self._check_endpoint("basic")
                await self._process_result(result)
                
                # Check readiness
                result = await self._check_endpoint("readiness")
                await self._process_result(result)
                
            except Exception as e:
                self.logger.error(f"Basic health monitoring error: {e}")
            
            await asyncio.sleep(self.config.get("check_interval", DEFAULT_CHECK_INTERVAL))
    
    async def _monitor_deep_health(self):
        """Monitor deep health endpoint."""
        await asyncio.sleep(10)  # Initial delay
        
        while True:
            try:
                result = await self._check_endpoint("deep")
                await self._process_result(result)
                
                # Analyze deep health results
                if result.status != HealthStatus.HEALTHY:
                    await self._analyze_deep_health(result)
                
            except Exception as e:
                self.logger.error(f"Deep health monitoring error: {e}")
            
            await asyncio.sleep(self.config.get("deep_check_interval", DEEP_CHECK_INTERVAL))
    
    async def _monitor_performance(self):
        """Monitor performance metrics."""
        await asyncio.sleep(20)  # Initial delay
        
        while True:
            try:
                result = await self._check_endpoint("performance")
                await self._process_result(result)
                
                # Analyze performance metrics
                if result.details:
                    await self._analyze_performance(result.details.get("metrics", {}))
                
            except Exception as e:
                self.logger.error(f"Performance monitoring error: {e}")
            
            await asyncio.sleep(self.config.get("check_interval", DEFAULT_CHECK_INTERVAL))
    
    async def _check_endpoint(self, endpoint_name: str) -> HealthCheckResult:
        """Check a specific health endpoint."""
        endpoint = HEALTH_CHECK_ENDPOINTS.get(endpoint_name)
        url = f"{self.base_url}{endpoint}"
        
        start_time = datetime.utcnow()
        
        try:
            async with self.session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                response_time = (datetime.utcnow() - start_time).total_seconds()
                
                if response.status == 200:
                    data = await response.json()
                    status = self._parse_health_status(data)
                elif response.status == 503:
                    data = await response.json()
                    status = HealthStatus.CRITICAL
                else:
                    data = {"status_code": response.status}
                    status = HealthStatus.CRITICAL
                
                return HealthCheckResult(
                    endpoint=endpoint_name,
                    status=status,
                    response_time=response_time,
                    details=data,
                    timestamp=datetime.utcnow()
                )
                
        except asyncio.TimeoutError:
            return HealthCheckResult(
                endpoint=endpoint_name,
                status=HealthStatus.CRITICAL,
                response_time=30.0,
                details={},
                timestamp=datetime.utcnow(),
                error="Timeout"
            )
        except Exception as e:
            return HealthCheckResult(
                endpoint=endpoint_name,
                status=HealthStatus.UNKNOWN,
                response_time=0,
                details={},
                timestamp=datetime.utcnow(),
                error=str(e)
            )
    
    def _parse_health_status(self, data: Dict[str, Any]) -> HealthStatus:
        """Parse health status from response data."""
        status_str = data.get("status", "").lower()
        
        if status_str in ["healthy", "ready", "alive"]:
            return HealthStatus.HEALTHY
        elif status_str in ["degraded", "not_ready"]:
            return HealthStatus.DEGRADED
        elif status_str in ["unhealthy", "critical"]:
            return HealthStatus.CRITICAL
        else:
            return HealthStatus.UNKNOWN
    
    async def _process_result(self, result: HealthCheckResult):
        """Process health check result."""
        # Add to history
        self.results_history.append(result)
        
        # Log result
        log_level = logging.INFO
        if result.status == HealthStatus.CRITICAL:
            log_level = logging.ERROR
        elif result.status == HealthStatus.DEGRADED:
            log_level = logging.WARNING
        
        self.logger.log(
            log_level,
            f"Health check {result.endpoint}: {result.status.value} "
            f"(response time: {result.response_time:.2f}s)"
        )
        
        # Check if alert needed
        if result.status in [HealthStatus.CRITICAL, HealthStatus.DEGRADED]:
            await self._check_alert_needed(result)
    
    async def _check_alert_needed(self, result: HealthCheckResult):
        """Check if an alert should be sent."""
        alert_key = f"{result.endpoint}:{result.status.value}"
        
        # Check cooldown
        last_alert = self.alerts_sent.get(alert_key)
        if last_alert and (datetime.utcnow() - last_alert).total_seconds() < ALERT_COOLDOWN:
            return
        
        # Create alert
        alert = Alert(
            severity="critical" if result.status == HealthStatus.CRITICAL else "warning",
            title=f"Health Check Alert: {result.endpoint}",
            message=f"Endpoint {result.endpoint} is {result.status.value}",
            details=result.details,
            timestamp=datetime.utcnow()
        )
        
        await self._send_alert(alert)
        self.alerts_sent[alert_key] = datetime.utcnow()
    
    async def _analyze_deep_health(self, result: HealthCheckResult):
        """Analyze deep health check results for specific issues."""
        components = result.details.get("components", {})
        
        # Check database
        db_health = components.get("database", {})
        if db_health.get("status") != "healthy":
            await self._send_alert(Alert(
                severity="critical",
                title="Database Health Critical",
                message="Database is not healthy",
                details=db_health,
                timestamp=datetime.utcnow()
            ))
        
        # Check high connection count
        db_checks = db_health.get("checks", {})
        if db_checks.get("active_connections", 0) > 50:
            await self._send_alert(Alert(
                severity="warning",
                title="High Database Connections",
                message=f"Active connections: {db_checks['active_connections']}",
                details=db_checks,
                timestamp=datetime.utcnow()
            ))
        
        # Check Redis
        cache_health = components.get("cache", {})
        if cache_health.get("status") == "unhealthy":
            await self._send_alert(Alert(
                severity="warning",
                title="Cache Health Warning",
                message="Redis cache is unhealthy",
                details=cache_health,
                timestamp=datetime.utcnow()
            ))
        
        # Check system resources
        system = result.details.get("system", {})
        if system.get("cpu_percent", 0) > 80:
            await self._send_alert(Alert(
                severity="warning",
                title="High CPU Usage",
                message=f"CPU usage: {system['cpu_percent']}%",
                details=system,
                timestamp=datetime.utcnow()
            ))
        
        if system.get("memory", {}).get("percent", 0) > 85:
            await self._send_alert(Alert(
                severity="warning",
                title="High Memory Usage",
                message=f"Memory usage: {system['memory']['percent']}%",
                details=system,
                timestamp=datetime.utcnow()
            ))
    
    async def _analyze_performance(self, metrics: Dict[str, Any]):
        """Analyze performance metrics for issues."""
        # Check error rate
        error_rate = metrics.get("error_rate", {})
        if error_rate.get("current", 0) > 0.05:
            await self._send_alert(Alert(
                severity="warning",
                title="High Error Rate",
                message=f"Current error rate: {error_rate['current']*100:.1f}%",
                details=error_rate,
                timestamp=datetime.utcnow()
            ))
        
        # Check response times
        response_times = metrics.get("response_times", {})
        if response_times.get("p95", 0) > 2000:  # 2 seconds
            await self._send_alert(Alert(
                severity="warning",
                title="High Response Times",
                message=f"P95 response time: {response_times['p95']}ms",
                details=response_times,
                timestamp=datetime.utcnow()
            ))
    
    async def _send_alert(self, alert: Alert):
        """Send alert via configured channels."""
        self.logger.warning(f"ALERT: {alert.title} - {alert.message}")
        
        # Send email if configured
        if self.config.get("email", {}).get("enabled"):
            await self._send_email_alert(alert)
        
        # Send to webhook if configured
        if self.config.get("webhook", {}).get("url"):
            await self._send_webhook_alert(alert)
    
    async def _send_email_alert(self, alert: Alert):
        """Send alert via email."""
        email_config = self.config.get("email", {})
        
        try:
            msg = MIMEMultipart()
            msg["From"] = email_config["from"]
            msg["To"] = ", ".join(email_config["to"])
            msg["Subject"] = f"[{alert.severity.upper()}] {alert.title}"
            
            body = f"""
Alert: {alert.title}
Severity: {alert.severity}
Time: {alert.timestamp.isoformat()}

Message: {alert.message}

Details:
{json.dumps(alert.details, indent=2)}
"""
            
            msg.attach(MIMEText(body, "plain"))
            
            with smtplib.SMTP(email_config["smtp_host"], email_config["smtp_port"]) as server:
                if email_config.get("smtp_tls"):
                    server.starttls()
                if email_config.get("smtp_user"):
                    server.login(email_config["smtp_user"], email_config["smtp_password"])
                server.send_message(msg)
                
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")
    
    async def _send_webhook_alert(self, alert: Alert):
        """Send alert to webhook."""
        webhook_config = self.config.get("webhook", {})
        
        payload = {
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "details": alert.details,
            "timestamp": alert.timestamp.isoformat()
        }
        
        try:
            async with self.session.post(
                webhook_config["url"],
                json=payload,
                headers=webhook_config.get("headers", {})
            ) as response:
                if response.status != 200:
                    self.logger.error(f"Webhook failed with status {response.status}")
        except Exception as e:
            self.logger.error(f"Failed to send webhook alert: {e}")
    
    async def _cleanup_history(self):
        """Clean up old history entries."""
        while True:
            await asyncio.sleep(3600)  # Every hour
            
            cutoff = datetime.utcnow() - timedelta(hours=24)
            self.results_history = [
                r for r in self.results_history 
                if r.timestamp > cutoff
            ]
            
            self.logger.info(f"Cleaned up history, {len(self.results_history)} entries remaining")


def load_config(config_file: str) -> Dict[str, Any]:
    """Load configuration from file."""
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    else:
        # Default configuration
        return {
            "check_interval": 60,
            "deep_check_interval": 300,
            "log_file": "health_monitor.log",
            "email": {
                "enabled": False,
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "smtp_tls": True,
                "from": "monitoring@roadtrip.ai",
                "to": ["ops@roadtrip.ai"]
            },
            "webhook": {
                "url": None,
                "headers": {}
            }
        }


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Health Check Monitor for Road Trip AI")
    parser.add_argument("url", help="Base URL of the service to monitor")
    parser.add_argument("-c", "--config", default="monitor_config.json", 
                       help="Configuration file path")
    
    args = parser.parse_args()
    
    config = load_config(args.config)
    monitor = HealthCheckMonitor(args.url, config)
    
    await monitor.start()


if __name__ == "__main__":
    asyncio.run(main())