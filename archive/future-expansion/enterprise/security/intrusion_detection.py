"""
Advanced Intrusion Detection System (IDS) for real-time threat detection.
"""

import asyncio
import re
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict, deque
from enum import Enum
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib

from app.core.logger import get_logger
from app.core.cache import cache_manager
from app.core.config import settings
from app.monitoring.security_monitor import security_monitor, SecurityEvent, SecurityEventType, SecurityEventSeverity
from app.monitoring.audit_logger import audit_logger, AuditEventType

logger = get_logger(__name__)


class ThreatType(Enum):
    """Types of threats detected by IDS."""
    PORT_SCAN = "port_scan"
    BRUTE_FORCE = "brute_force"
    DOS_ATTACK = "dos_attack"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    LATERAL_MOVEMENT = "lateral_movement"
    MALWARE_ACTIVITY = "malware_activity"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    CREDENTIAL_STUFFING = "credential_stuffing"
    API_ABUSE = "api_abuse"
    BOT_ACTIVITY = "bot_activity"
    ZERO_DAY_EXPLOIT = "zero_day_exploit"


class ThreatLevel(Enum):
    """Threat severity levels."""
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


class NetworkPattern:
    """Network traffic pattern analysis."""
    
    def __init__(self):
        self.request_patterns = defaultdict(lambda: deque(maxlen=1000))
        self.ip_patterns = defaultdict(lambda: deque(maxlen=100))
        self.user_patterns = defaultdict(lambda: deque(maxlen=500))
        self.endpoint_access = defaultdict(set)
        
    def add_request(self, ip: str, endpoint: str, method: str, timestamp: datetime):
        """Add request to pattern tracking."""
        request_key = f"{ip}:{endpoint}:{method}"
        self.request_patterns[request_key].append(timestamp)
        self.ip_patterns[ip].append((endpoint, timestamp))
        self.endpoint_access[endpoint].add(ip)
    
    def get_request_rate(self, ip: str, window_seconds: int = 60) -> float:
        """Calculate request rate for an IP."""
        cutoff = datetime.utcnow() - timedelta(seconds=window_seconds)
        recent_requests = [
            ts for _, ts in self.ip_patterns[ip]
            if ts > cutoff
        ]
        return len(recent_requests) / window_seconds if window_seconds > 0 else 0


class BehaviorAnalyzer:
    """Analyze user and system behavior for anomalies."""
    
    def __init__(self):
        self.user_baselines = {}
        self.system_baseline = None
        self.anomaly_detector = IsolationForest(
            contamination=0.1,
            random_state=42,
            n_estimators=100
        )
        self.is_trained = False
        
    def update_user_baseline(self, user_id: str, behavior_data: Dict[str, Any]):
        """Update user behavior baseline."""
        if user_id not in self.user_baselines:
            self.user_baselines[user_id] = {
                "access_times": [],
                "endpoints": set(),
                "ip_addresses": set(),
                "average_session_duration": 0,
                "typical_data_volume": 0,
            }
        
        baseline = self.user_baselines[user_id]
        
        # Update baseline data
        if "access_time" in behavior_data:
            baseline["access_times"].append(behavior_data["access_time"])
        if "endpoint" in behavior_data:
            baseline["endpoints"].add(behavior_data["endpoint"])
        if "ip_address" in behavior_data:
            baseline["ip_addresses"].add(behavior_data["ip_address"])
    
    def detect_anomaly(self, user_id: str, current_behavior: Dict[str, Any]) -> Tuple[bool, float]:
        """Detect anomalous behavior."""
        if not self.is_trained or user_id not in self.user_baselines:
            return False, 0.0
        
        # Extract features
        features = self._extract_features(user_id, current_behavior)
        
        # Predict anomaly
        anomaly_score = self.anomaly_detector.decision_function([features])[0]
        is_anomaly = self.anomaly_detector.predict([features])[0] == -1
        
        return is_anomaly, abs(anomaly_score)
    
    def _extract_features(self, user_id: str, behavior: Dict[str, Any]) -> List[float]:
        """Extract numerical features for ML model."""
        baseline = self.user_baselines.get(user_id, {})
        
        features = [
            # Time-based features
            behavior.get("hour_of_day", 12),
            behavior.get("day_of_week", 3),
            
            # Activity features
            behavior.get("request_count", 0),
            behavior.get("unique_endpoints", 0),
            behavior.get("data_volume", 0),
            
            # Deviation from baseline
            1 if behavior.get("ip_address") not in baseline.get("ip_addresses", set()) else 0,
            1 if behavior.get("endpoint") not in baseline.get("endpoints", set()) else 0,
        ]
        
        return features


class ThreatIntelligence:
    """Threat intelligence feed integration."""
    
    def __init__(self):
        self.known_bad_ips = set()
        self.known_bad_domains = set()
        self.known_exploits = {}
        self.threat_signatures = []
        self.last_update = None
        
    async def update_feeds(self):
        """Update threat intelligence feeds."""
        try:
            # In production, this would fetch from threat intel APIs
            # For now, we'll use static lists
            self.known_bad_ips = {
                "192.168.1.100",  # Example malicious IPs
                "10.0.0.50",
            }
            
            self.threat_signatures = [
                {
                    "name": "SQL Injection Attempt",
                    "pattern": r"(\bunion\b.*\bselect\b|\bor\b.*=.*\bor\b)",
                    "threat_type": ThreatType.API_ABUSE,
                    "level": ThreatLevel.HIGH
                },
                {
                    "name": "Command Injection",
                    "pattern": r"(;|\||&|`|\$\(|<\()",
                    "threat_type": ThreatType.MALWARE_ACTIVITY,
                    "level": ThreatLevel.CRITICAL
                },
                {
                    "name": "Path Traversal",
                    "pattern": r"(\.\./|\.\.\\|%2e%2e)",
                    "threat_type": ThreatType.API_ABUSE,
                    "level": ThreatLevel.MEDIUM
                }
            ]
            
            self.last_update = datetime.utcnow()
            logger.info("Threat intelligence feeds updated")
            
        except Exception as e:
            logger.error(f"Failed to update threat feeds: {e}")
    
    def check_ip_reputation(self, ip: str) -> Optional[Dict[str, Any]]:
        """Check IP reputation."""
        if ip in self.known_bad_ips:
            return {
                "reputation": "malicious",
                "threat_type": ThreatType.BOT_ACTIVITY,
                "confidence": 0.95
            }
        return None
    
    def check_signature_match(self, data: str) -> Optional[Dict[str, Any]]:
        """Check for threat signature matches."""
        for signature in self.threat_signatures:
            if re.search(signature["pattern"], data, re.IGNORECASE):
                return {
                    "matched": signature["name"],
                    "threat_type": signature["threat_type"],
                    "level": signature["level"]
                }
        return None


class IntrusionDetectionSystem:
    """Main IDS implementation."""
    
    def __init__(self):
        self.network_patterns = NetworkPattern()
        self.behavior_analyzer = BehaviorAnalyzer()
        self.threat_intel = ThreatIntelligence()
        self.active_threats = {}
        self.threat_correlations = defaultdict(list)
        self.is_running = False
        
        # IDS configuration
        self.config = {
            "port_scan_threshold": 10,  # ports in 60 seconds
            "brute_force_threshold": 5,  # failed attempts
            "dos_threshold": 100,  # requests per second
            "data_exfil_threshold": 100 * 1024 * 1024,  # 100MB
            "anomaly_threshold": 0.7,
        }
        
    async def start(self):
        """Start the IDS."""
        self.is_running = True
        
        # Update threat intelligence
        await self.threat_intel.update_feeds()
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_threats())
        asyncio.create_task(self._analyze_patterns())
        asyncio.create_task(self._update_threat_intel())
        
        logger.info("Intrusion Detection System started")
    
    async def stop(self):
        """Stop the IDS."""
        self.is_running = False
        logger.info("Intrusion Detection System stopped")
    
    async def analyze_request(
        self,
        request_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Analyze a request for threats."""
        threats_detected = []
        
        # Extract request information
        ip = request_data.get("ip_address", "unknown")
        endpoint = request_data.get("endpoint", "")
        method = request_data.get("method", "")
        headers = request_data.get("headers", {})
        body = request_data.get("body", "")
        user_id = request_data.get("user_id")
        
        # Update patterns
        self.network_patterns.add_request(
            ip, endpoint, method, datetime.utcnow()
        )
        
        # Check IP reputation
        ip_check = self.threat_intel.check_ip_reputation(ip)
        if ip_check:
            threats_detected.append({
                "type": ThreatType.BOT_ACTIVITY,
                "level": ThreatLevel.HIGH,
                "details": ip_check
            })
        
        # Check for port scanning
        if self._detect_port_scan(ip):
            threats_detected.append({
                "type": ThreatType.PORT_SCAN,
                "level": ThreatLevel.MEDIUM,
                "details": {"ip": ip, "behavior": "port_scanning"}
            })
        
        # Check for DoS patterns
        request_rate = self.network_patterns.get_request_rate(ip)
        if request_rate > self.config["dos_threshold"]:
            threats_detected.append({
                "type": ThreatType.DOS_ATTACK,
                "level": ThreatLevel.HIGH,
                "details": {"ip": ip, "rate": request_rate}
            })
        
        # Check request content for exploits
        request_content = f"{endpoint} {json.dumps(headers)} {body}"
        signature_match = self.threat_intel.check_signature_match(request_content)
        if signature_match:
            threats_detected.append({
                "type": signature_match["threat_type"],
                "level": signature_match["level"],
                "details": signature_match
            })
        
        # Behavioral analysis for authenticated users
        if user_id:
            behavior_data = {
                "ip_address": ip,
                "endpoint": endpoint,
                "hour_of_day": datetime.utcnow().hour,
                "day_of_week": datetime.utcnow().weekday(),
                "request_count": len(self.network_patterns.ip_patterns[ip]),
            }
            
            is_anomaly, score = self.behavior_analyzer.detect_anomaly(
                user_id, behavior_data
            )
            
            if is_anomaly and score > self.config["anomaly_threshold"]:
                threats_detected.append({
                    "type": ThreatType.ANOMALOUS_BEHAVIOR,
                    "level": ThreatLevel.MEDIUM,
                    "details": {
                        "user_id": user_id,
                        "anomaly_score": score,
                        "behavior": behavior_data
                    }
                })
        
        # Correlate threats
        if threats_detected:
            threat_id = self._generate_threat_id(threats_detected)
            self.active_threats[threat_id] = {
                "threats": threats_detected,
                "first_seen": datetime.utcnow(),
                "last_seen": datetime.utcnow(),
                "count": 1,
                "source_ip": ip,
                "user_id": user_id
            }
            
            # Log to security monitor
            for threat in threats_detected:
                await self._report_threat(threat, request_data)
            
            return {
                "threat_id": threat_id,
                "threats": threats_detected,
                "recommended_action": self._recommend_action(threats_detected)
            }
        
        return None
    
    def _detect_port_scan(self, ip: str) -> bool:
        """Detect port scanning behavior."""
        # Check endpoint access patterns
        recent_endpoints = [
            endpoint for endpoint, _ in self.network_patterns.ip_patterns[ip]
        ]
        
        # Look for sequential port access or wide endpoint scanning
        unique_endpoints = set(recent_endpoints[-20:])  # Last 20 requests
        
        # Simple heuristic: many different endpoints in short time
        return len(unique_endpoints) > self.config["port_scan_threshold"]
    
    def _detect_data_exfiltration(
        self,
        user_id: str,
        data_volume: int,
        time_window: int = 3600
    ) -> bool:
        """Detect potential data exfiltration."""
        # Check if data volume exceeds threshold
        if data_volume > self.config["data_exfil_threshold"]:
            return True
        
        # Check for unusual data access patterns
        # TODO: Implement historical comparison
        
        return False
    
    async def _report_threat(
        self,
        threat: Dict[str, Any],
        request_data: Dict[str, Any]
    ):
        """Report threat to security monitor."""
        severity_map = {
            ThreatLevel.LOW: SecurityEventSeverity.LOW,
            ThreatLevel.MEDIUM: SecurityEventSeverity.MEDIUM,
            ThreatLevel.HIGH: SecurityEventSeverity.HIGH,
            ThreatLevel.CRITICAL: SecurityEventSeverity.CRITICAL,
        }
        
        event = SecurityEvent(
            event_type=SecurityEventType.INTRUSION_DETECTED,
            severity=severity_map.get(threat["level"], SecurityEventSeverity.MEDIUM),
            user_id=request_data.get("user_id"),
            ip_address=request_data.get("ip_address"),
            details={
                "threat_type": threat["type"].value,
                "threat_details": threat["details"],
                "endpoint": request_data.get("endpoint"),
                "action_taken": "monitored"
            }
        )
        
        await security_monitor.log_event(event)
    
    def _recommend_action(self, threats: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Recommend action based on detected threats."""
        # Determine highest threat level
        max_level = max(threat["level"].value for threat in threats)
        
        if max_level >= ThreatLevel.CRITICAL.value:
            return {
                "action": "block_immediately",
                "duration": 86400,  # 24 hours
                "notify": ["security_team", "admin"]
            }
        elif max_level >= ThreatLevel.HIGH.value:
            return {
                "action": "block_temporarily",
                "duration": 3600,  # 1 hour
                "notify": ["security_team"]
            }
        elif max_level >= ThreatLevel.MEDIUM.value:
            return {
                "action": "rate_limit",
                "severity": "strict",
                "notify": ["monitoring"]
            }
        else:
            return {
                "action": "monitor",
                "alert": True
            }
    
    def _generate_threat_id(self, threats: List[Dict[str, Any]]) -> str:
        """Generate unique threat ID."""
        threat_data = json.dumps(threats, sort_keys=True, default=str)
        return hashlib.sha256(threat_data.encode()).hexdigest()[:16]
    
    async def _monitor_threats(self):
        """Monitor and correlate ongoing threats."""
        while self.is_running:
            try:
                # Check active threats
                current_time = datetime.utcnow()
                expired_threats = []
                
                for threat_id, threat_data in self.active_threats.items():
                    # Remove old threats (>1 hour)
                    if (current_time - threat_data["last_seen"]).seconds > 3600:
                        expired_threats.append(threat_id)
                    
                    # Check for threat escalation
                    if threat_data["count"] > 10:
                        await self._escalate_threat(threat_id, threat_data)
                
                # Clean up expired threats
                for threat_id in expired_threats:
                    del self.active_threats[threat_id]
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in threat monitoring: {e}")
    
    async def _escalate_threat(self, threat_id: str, threat_data: Dict[str, Any]):
        """Escalate persistent threats."""
        # Create critical security event
        event = SecurityEvent(
            event_type=SecurityEventType.INTRUSION_DETECTED,
            severity=SecurityEventSeverity.CRITICAL,
            user_id=threat_data.get("user_id"),
            ip_address=threat_data.get("source_ip"),
            details={
                "threat_id": threat_id,
                "escalation_reason": "persistent_threat",
                "occurrence_count": threat_data["count"],
                "duration": (datetime.utcnow() - threat_data["first_seen"]).seconds
            }
        )
        
        await security_monitor.log_event(event)
    
    async def _analyze_patterns(self):
        """Analyze patterns for threat detection."""
        while self.is_running:
            try:
                # Analyze network patterns
                # TODO: Implement pattern analysis
                
                await asyncio.sleep(300)  # Every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in pattern analysis: {e}")
    
    async def _update_threat_intel(self):
        """Periodically update threat intelligence."""
        while self.is_running:
            try:
                await self.threat_intel.update_feeds()
                await asyncio.sleep(3600)  # Update hourly
                
            except Exception as e:
                logger.error(f"Error updating threat intel: {e}")
    
    async def get_threat_summary(self) -> Dict[str, Any]:
        """Get current threat summary."""
        return {
            "active_threats": len(self.active_threats),
            "threat_types": self._count_threat_types(),
            "top_threat_sources": self._get_top_threat_sources(),
            "threat_timeline": self._get_threat_timeline(),
            "system_status": "active" if self.is_running else "inactive"
        }
    
    def _count_threat_types(self) -> Dict[str, int]:
        """Count threats by type."""
        counts = defaultdict(int)
        for threat_data in self.active_threats.values():
            for threat in threat_data["threats"]:
                counts[threat["type"].value] += 1
        return dict(counts)
    
    def _get_top_threat_sources(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top threat sources."""
        source_counts = defaultdict(int)
        for threat_data in self.active_threats.values():
            source_counts[threat_data["source_ip"]] += threat_data["count"]
        
        sorted_sources = sorted(
            source_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {"ip": ip, "threat_count": count}
            for ip, count in sorted_sources
        ]
    
    def _get_threat_timeline(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get threat timeline."""
        timeline = []
        current_time = datetime.utcnow()
        
        for i in range(hours):
            hour_start = current_time - timedelta(hours=i+1)
            hour_end = current_time - timedelta(hours=i)
            
            count = sum(
                1 for threat_data in self.active_threats.values()
                if hour_start <= threat_data["first_seen"] < hour_end
            )
            
            timeline.append({
                "hour": hour_start.strftime("%Y-%m-%d %H:00"),
                "threat_count": count
            })
        
        return list(reversed(timeline))


# Global IDS instance
intrusion_detection_system = IntrusionDetectionSystem()