"""
Production Intrusion Detection System
Advanced threat detection with ML-ready architecture
"""

import asyncio
import json
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import re
import statistics

from app.core.logger import get_logger
from app.core.cache import cache_manager
from app.monitoring.security_monitor_v2 import security_monitor_v2, SecurityEventType, ThreatLevel
from app.monitoring.security_metrics import security_metrics

logger = get_logger(__name__)


class AttackType(Enum):
    """Types of attacks to detect."""
    BRUTE_FORCE = "brute_force"
    CREDENTIAL_STUFFING = "credential_stuffing"
    SQL_INJECTION = "sql_injection"
    XSS = "xss"
    DDOS = "ddos"
    PORT_SCAN = "port_scan"
    PATH_TRAVERSAL = "path_traversal"
    SESSION_HIJACK = "session_hijack"
    API_ABUSE = "api_abuse"
    BOT_ACTIVITY = "bot_activity"


@dataclass
class ThreatIndicator:
    """Indicator of a potential threat."""
    indicator_type: str
    confidence: float  # 0.0 to 1.0
    details: Dict[str, Any]
    timestamp: datetime


class IntrusionDetectionSystemV2:
    """Advanced intrusion detection with pattern recognition and anomaly detection."""
    
    def __init__(self):
        self.active = False
        
        # Behavior tracking
        self._ip_behavior: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._user_behavior: Dict[str, deque] = defaultdict(lambda: deque(maxlen=500))
        self._endpoint_stats: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Attack detection state
        self._active_attacks: Dict[str, List[ThreatIndicator]] = defaultdict(list)
        self._attack_signatures: Dict[AttackType, List[re.Pattern]] = self._load_attack_signatures()
        
        # Anomaly detection baselines
        self._request_rate_baseline: Dict[str, float] = {}
        self._endpoint_timing_baseline: Dict[str, Tuple[float, float]] = {}  # mean, stddev
        
        # Detection thresholds
        self.thresholds = {
            'brute_force_attempts': 5,  # Failed logins before alert
            'request_rate_spike': 3.0,  # Times normal rate
            'endpoint_anomaly_score': 2.5,  # Standard deviations
            'bot_score_threshold': 0.7,  # Bot detection confidence
            'attack_confidence_threshold': 0.8  # Attack declaration threshold
        }
        
        # Background tasks
        self._analysis_task = None
        self._baseline_task = None
        
        logger.info("Intrusion Detection System V2 initialized")
    
    async def start(self):
        """Start the intrusion detection system."""
        self.active = True
        
        # Start background tasks
        self._analysis_task = asyncio.create_task(self._continuous_analysis())
        self._baseline_task = asyncio.create_task(self._baseline_update())
        
        # Load existing baselines
        await self._load_baselines()
        
        logger.info("Intrusion Detection System V2 started")
    
    async def stop(self):
        """Stop the intrusion detection system."""
        self.active = False
        
        # Cancel background tasks
        if self._analysis_task:
            self._analysis_task.cancel()
        if self._baseline_task:
            self._baseline_task.cancel()
        
        # Save baselines
        await self._save_baselines()
        
        logger.info("Intrusion Detection System V2 stopped")
    
    async def analyze_request(
        self,
        request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze request for intrusion indicators."""
        indicators = []
        
        # Extract request attributes
        ip_address = request_data.get('ip_address', 'unknown')
        user_id = request_data.get('user_id')
        endpoint = request_data.get('endpoint', '')
        method = request_data.get('method', '')
        user_agent = request_data.get('user_agent', '')
        
        # Record behavior
        behavior_entry = {
            'timestamp': datetime.utcnow(),
            'endpoint': endpoint,
            'method': method,
            'user_agent': user_agent,
            'data': request_data
        }
        
        self._ip_behavior[ip_address].append(behavior_entry)
        if user_id:
            self._user_behavior[user_id].append(behavior_entry)
        
        # 1. Check attack signatures
        signature_matches = self._check_attack_signatures(request_data)
        indicators.extend(signature_matches)
        
        # 2. Behavioral analysis
        behavior_indicators = await self._analyze_behavior(ip_address, user_id)
        indicators.extend(behavior_indicators)
        
        # 3. Anomaly detection
        anomaly_indicators = self._detect_anomalies(request_data)
        indicators.extend(anomaly_indicators)
        
        # 4. Bot detection
        bot_indicator = self._detect_bot_activity(ip_address, user_agent)
        if bot_indicator:
            indicators.append(bot_indicator)
        
        # Calculate overall threat assessment
        threat_assessment = self._assess_threat(indicators)
        
        # Update active attacks tracking
        if threat_assessment['attack_type']:
            self._active_attacks[ip_address].extend(indicators)
        
        # Log high-confidence attacks
        if threat_assessment['confidence'] >= self.thresholds['attack_confidence_threshold']:
            await self._handle_detected_attack(
                ip_address,
                threat_assessment['attack_type'],
                indicators,
                request_data
            )
        
        return {
            'threat_detected': threat_assessment['attack_type'] is not None,
            'attack_type': threat_assessment['attack_type'],
            'confidence': threat_assessment['confidence'],
            'indicators': [
                {
                    'type': ind.indicator_type,
                    'confidence': ind.confidence,
                    'details': ind.details
                }
                for ind in indicators
            ],
            'recommended_action': threat_assessment['recommended_action']
        }
    
    def _load_attack_signatures(self) -> Dict[AttackType, List[re.Pattern]]:
        """Load attack signature patterns."""
        return {
            AttackType.SQL_INJECTION: [
                re.compile(r"(\b(union|select|insert|update|delete|drop)\b.*\b(from|where|table)\b)", re.I),
                re.compile(r"(;|'|--|\/\*|\*\/|xp_|sp_|0x)", re.I),
                re.compile(r"(\b(and|or)\b\s*\d+\s*=\s*\d+)", re.I)
            ],
            AttackType.XSS: [
                re.compile(r"(<script[^>]*>|<\/script>|javascript:|onerror=|onload=)", re.I),
                re.compile(r"(document\.(cookie|write)|window\.location|eval\s*\()", re.I),
                re.compile(r"(<iframe|<object|<embed|<img\s+src[^>]*javascript:)", re.I)
            ],
            AttackType.PATH_TRAVERSAL: [
                re.compile(r"(\.\.\/|\.\.\\|%2e%2e%2f|%252e%252e%252f)", re.I),
                re.compile(r"(\/etc\/passwd|\/windows\/|\/proc\/|C:\\)", re.I)
            ]
        }
    
    def _check_attack_signatures(self, request_data: Dict[str, Any]) -> List[ThreatIndicator]:
        """Check request against known attack signatures."""
        indicators = []
        
        # Combine all text fields for analysis
        text_to_check = ' '.join([
            str(request_data.get('path', '')),
            str(request_data.get('query_params', '')),
            str(request_data.get('body', '')),
            str(request_data.get('headers', ''))
        ])
        
        # Check each attack type
        for attack_type, patterns in self._attack_signatures.items():
            matches = []
            for pattern in patterns:
                if pattern.search(text_to_check):
                    matches.append(pattern.pattern)
            
            if matches:
                confidence = min(1.0, len(matches) * 0.3)  # More matches = higher confidence
                indicators.append(ThreatIndicator(
                    indicator_type=f"signature_{attack_type.value}",
                    confidence=confidence,
                    details={'patterns_matched': matches},
                    timestamp=datetime.utcnow()
                ))
        
        return indicators
    
    async def _analyze_behavior(
        self,
        ip_address: str,
        user_id: Optional[str]
    ) -> List[ThreatIndicator]:
        """Analyze behavioral patterns for anomalies."""
        indicators = []
        now = datetime.utcnow()
        
        # Check IP behavior
        ip_events = list(self._ip_behavior[ip_address])
        if len(ip_events) >= 10:
            # Check for brute force
            recent_failures = sum(
                1 for event in ip_events[-20:]
                if 'login' in event['endpoint'] and event.get('failed', False)
            )
            
            if recent_failures >= self.thresholds['brute_force_attempts']:
                indicators.append(ThreatIndicator(
                    indicator_type="behavior_brute_force",
                    confidence=min(1.0, recent_failures / 10),
                    details={'failed_attempts': recent_failures},
                    timestamp=now
                ))
            
            # Check for rapid requests (potential DoS)
            recent_events = [e for e in ip_events if e['timestamp'] >= now - timedelta(minutes=1)]
            if len(recent_events) > 60:  # More than 1 per second average
                indicators.append(ThreatIndicator(
                    indicator_type="behavior_rapid_requests",
                    confidence=min(1.0, len(recent_events) / 100),
                    details={'requests_per_minute': len(recent_events)},
                    timestamp=now
                ))
            
            # Check for scanning behavior
            unique_endpoints = set(e['endpoint'] for e in ip_events[-50:])
            if len(unique_endpoints) > 20:
                indicators.append(ThreatIndicator(
                    indicator_type="behavior_scanning",
                    confidence=min(1.0, len(unique_endpoints) / 30),
                    details={'unique_endpoints': len(unique_endpoints)},
                    timestamp=now
                ))
        
        return indicators
    
    def _detect_anomalies(self, request_data: Dict[str, Any]) -> List[ThreatIndicator]:
        """Detect anomalies based on baselines."""
        indicators = []
        endpoint = request_data.get('endpoint', '')
        
        # Check endpoint timing anomaly
        if endpoint in self._endpoint_timing_baseline:
            mean, stddev = self._endpoint_timing_baseline[endpoint]
            response_time = request_data.get('response_time', 0)
            
            if stddev > 0:
                z_score = abs((response_time - mean) / stddev)
                if z_score > self.thresholds['endpoint_anomaly_score']:
                    indicators.append(ThreatIndicator(
                        indicator_type="anomaly_timing",
                        confidence=min(1.0, z_score / 5),
                        details={
                            'z_score': z_score,
                            'expected_ms': mean,
                            'actual_ms': response_time
                        },
                        timestamp=datetime.utcnow()
                    ))
        
        return indicators
    
    def _detect_bot_activity(self, ip_address: str, user_agent: str) -> Optional[ThreatIndicator]:
        """Detect potential bot activity."""
        bot_score = 0.0
        bot_indicators = []
        
        # Check user agent
        bot_ua_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
            'python-requests', 'go-http-client', 'java/', 'ruby'
        ]
        
        ua_lower = user_agent.lower()
        for pattern in bot_ua_patterns:
            if pattern in ua_lower:
                bot_score += 0.3
                bot_indicators.append(f"user_agent_contains_{pattern}")
        
        # Check behavior patterns
        ip_events = list(self._ip_behavior[ip_address])
        if len(ip_events) >= 10:
            # Check request regularity
            if len(ip_events) >= 20:
                timestamps = [e['timestamp'] for e in ip_events[-20:]]
                intervals = [
                    (timestamps[i+1] - timestamps[i]).total_seconds()
                    for i in range(len(timestamps)-1)
                ]
                
                # High regularity suggests bot
                if intervals and statistics.stdev(intervals) < 2.0:
                    bot_score += 0.4
                    bot_indicators.append("regular_request_pattern")
            
            # Check for human-like behavior
            unique_endpoints = set(e['endpoint'] for e in ip_events)
            if len(unique_endpoints) == 1:
                bot_score += 0.2
                bot_indicators.append("single_endpoint_focus")
        
        if bot_score >= self.thresholds['bot_score_threshold']:
            return ThreatIndicator(
                indicator_type="bot_activity",
                confidence=min(1.0, bot_score),
                details={'indicators': bot_indicators, 'score': bot_score},
                timestamp=datetime.utcnow()
            )
        
        return None
    
    def _assess_threat(self, indicators: List[ThreatIndicator]) -> Dict[str, Any]:
        """Assess overall threat from indicators."""
        if not indicators:
            return {
                'attack_type': None,
                'confidence': 0.0,
                'recommended_action': 'monitor'
            }
        
        # Group by attack type
        attack_scores = defaultdict(float)
        for indicator in indicators:
            if indicator.indicator_type.startswith('signature_'):
                attack_type = indicator.indicator_type.replace('signature_', '')
                attack_scores[attack_type] += indicator.confidence
            elif 'brute_force' in indicator.indicator_type:
                attack_scores['brute_force'] += indicator.confidence
            elif 'scanning' in indicator.indicator_type:
                attack_scores['port_scan'] += indicator.confidence
            elif 'bot' in indicator.indicator_type:
                attack_scores['bot_activity'] += indicator.confidence
        
        # Find highest confidence attack
        if attack_scores:
            attack_type = max(attack_scores, key=attack_scores.get)
            confidence = min(1.0, attack_scores[attack_type])
            
            # Determine action
            if confidence >= 0.9:
                action = 'block'
            elif confidence >= 0.7:
                action = 'challenge'
            elif confidence >= 0.5:
                action = 'monitor_closely'
            else:
                action = 'monitor'
            
            return {
                'attack_type': attack_type,
                'confidence': confidence,
                'recommended_action': action
            }
        
        return {
            'attack_type': None,
            'confidence': 0.0,
            'recommended_action': 'monitor'
        }
    
    async def _handle_detected_attack(
        self,
        ip_address: str,
        attack_type: str,
        indicators: List[ThreatIndicator],
        request_data: Dict[str, Any]
    ):
        """Handle detected attack."""
        # Log to security monitor
        await security_monitor_v2.log_event(
            event_type=SecurityEventType.INTRUSION_DETECTED,
            ip_address=ip_address,
            user_id=request_data.get('user_id'),
            endpoint=request_data.get('endpoint'),
            details={
                'attack_type': attack_type,
                'indicators': len(indicators),
                'confidence': max(ind.confidence for ind in indicators)
            }
        )
        
        # Auto-block for high-confidence attacks
        max_confidence = max(ind.confidence for ind in indicators)
        if max_confidence >= 0.9 and attack_type in ['sql_injection', 'xss', 'brute_force']:
            await security_monitor_v2.block_ip(
                ip_address,
                duration_seconds=3600,  # 1 hour
                reason=f"IDS: {attack_type} attack detected"
            )
    
    async def get_threat_report(self) -> Dict[str, Any]:
        """Generate current threat report."""
        now = datetime.utcnow()
        
        # Active attacks summary
        active_attacks_summary = {}
        for ip, indicators in self._active_attacks.items():
            recent_indicators = [i for i in indicators if i.timestamp >= now - timedelta(hours=1)]
            if recent_indicators:
                attack_types = set()
                for ind in recent_indicators:
                    if ind.indicator_type.startswith('signature_'):
                        attack_types.add(ind.indicator_type.replace('signature_', ''))
                
                active_attacks_summary[ip] = {
                    'attack_types': list(attack_types),
                    'indicator_count': len(recent_indicators),
                    'max_confidence': max(i.confidence for i in recent_indicators)
                }
        
        # Calculate statistics
        total_ips_monitored = len(self._ip_behavior)
        suspicious_ips = len([
            ip for ip, events in self._ip_behavior.items()
            if len(events) > 100  # High activity
        ])
        
        return {
            'timestamp': now.isoformat(),
            'active_attacks': active_attacks_summary,
            'statistics': {
                'total_ips_monitored': total_ips_monitored,
                'suspicious_ips': suspicious_ips,
                'active_attack_count': len(active_attacks_summary)
            },
            'top_attack_types': self._get_top_attack_types(),
            'recommendations': self._generate_recommendations()
        }
    
    def _get_top_attack_types(self) -> List[Dict[str, Any]]:
        """Get most common attack types."""
        attack_counts = defaultdict(int)
        
        for indicators in self._active_attacks.values():
            for ind in indicators:
                if ind.indicator_type.startswith('signature_'):
                    attack_type = ind.indicator_type.replace('signature_', '')
                    attack_counts[attack_type] += 1
        
        return [
            {'type': attack, 'count': count}
            for attack, count in sorted(
                attack_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:5]
        ]
    
    def _generate_recommendations(self) -> List[str]:
        """Generate security recommendations based on current threats."""
        recommendations = []
        
        # Check attack patterns
        attack_types = self._get_top_attack_types()
        if attack_types:
            top_attack = attack_types[0]['type']
            if top_attack == 'sql_injection':
                recommendations.append("Review and strengthen input validation")
                recommendations.append("Implement parameterized queries")
            elif top_attack == 'brute_force':
                recommendations.append("Enable account lockout policies")
                recommendations.append("Implement CAPTCHA for login")
            elif top_attack == 'bot_activity':
                recommendations.append("Implement bot detection middleware")
                recommendations.append("Add rate limiting per IP")
        
        return recommendations
    
    async def _continuous_analysis(self):
        """Background task for continuous threat analysis."""
        while self.active:
            try:
                # Analyze patterns across all IPs
                now = datetime.utcnow()
                
                # Clean old data
                cutoff = now - timedelta(hours=24)
                for ip in list(self._active_attacks.keys()):
                    self._active_attacks[ip] = [
                        i for i in self._active_attacks[ip]
                        if i.timestamp >= cutoff
                    ]
                    if not self._active_attacks[ip]:
                        del self._active_attacks[ip]
                
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"Error in IDS continuous analysis: {e}")
                await asyncio.sleep(60)
    
    async def _baseline_update(self):
        """Update behavioral baselines."""
        while self.active:
            try:
                # Update endpoint timing baselines
                for endpoint, timings in self._endpoint_stats.items():
                    if len(timings) >= 20:
                        times = [t['duration'] for t in list(timings)]
                        mean = statistics.mean(times)
                        stddev = statistics.stdev(times) if len(times) > 1 else 0
                        self._endpoint_timing_baseline[endpoint] = (mean, stddev)
                
                # Save baselines periodically
                await self._save_baselines()
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Error updating IDS baselines: {e}")
                await asyncio.sleep(300)
    
    async def _load_baselines(self):
        """Load saved baselines from cache."""
        try:
            baselines = await cache_manager.get("ids_baselines")
            if baselines:
                self._endpoint_timing_baseline = baselines.get('endpoint_timing', {})
                logger.info("Loaded IDS baselines from cache")
        except Exception as e:
            logger.error(f"Error loading IDS baselines: {e}")
    
    async def _save_baselines(self):
        """Save baselines to cache."""
        try:
            baselines = {
                'endpoint_timing': self._endpoint_timing_baseline,
                'updated_at': datetime.utcnow().isoformat()
            }
            await cache_manager.set("ids_baselines", baselines, expire=86400)  # 24 hours
        except Exception as e:
            logger.error(f"Error saving IDS baselines: {e}")


# Global instance
intrusion_detection_system_v2 = IntrusionDetectionSystemV2()