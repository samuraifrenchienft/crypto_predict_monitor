"""
Security Monitoring and Threat Detection System
Comprehensive monitoring, threat detection, and automated response
"""

import os
import json
import time
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import statistics
import aiohttp
from enum import Enum

from .security_framework import get_security_framework, SecurityEvent

logger = logging.getLogger(__name__)

class ThreatLevel(Enum):
    """Threat severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertAction(Enum):
    """Automated alert actions"""
    LOG_ONLY = "log_only"
    BLOCK_IP = "block_ip"
    SUSPEND_USER = "suspend_user"
    REQUIRE_MFA = "require_mfa"
    NOTIFY_ADMIN = "notify_admin"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"

@dataclass
class ThreatPattern:
    """Threat detection pattern"""
    pattern_id: str
    name: str
    description: str
    threat_level: ThreatLevel
    conditions: Dict[str, Any]
    time_window: int  # seconds
    threshold: int
    action: AlertAction
    enabled: bool = True

@dataclass
class SecurityMetrics:
    """Security metrics and statistics"""
    total_events: int = 0
    events_by_severity: Dict[str, int] = None
    events_by_type: Dict[str, int] = None
    unique_users: int = 0
    unique_ips: int = 0
    blocked_ips: int = 0
    suspended_users: int = 0
    false_positives: int = 0
    detection_accuracy: float = 0.0
    average_response_time: float = 0.0
    
    def __post_init__(self):
        if self.events_by_severity is None:
            self.events_by_severity = defaultdict(int)
        if self.events_by_type is None:
            self.events_by_type = defaultdict(int)

@dataclass
class AlertNotification:
    """Alert notification data"""
    alert_id: str
    threat_level: ThreatLevel
    message: str
    details: Dict[str, Any]
    timestamp: datetime
    user_id: Optional[str]
    ip_address: Optional[str]
    action_taken: AlertAction
    resolved: bool = False

class ThreatDetector:
    """Advanced threat detection engine"""
    
    def __init__(self):
        self.security = get_security_framework()
        
        # Initialize threat patterns
        self.threat_patterns = self._initialize_threat_patterns()
        
        # Tracking data
        self.user_activity = defaultdict(lambda: defaultdict(deque))
        self.ip_activity = defaultdict(lambda: defaultdict(deque))
        self.global_activity = defaultdict(deque)
        
        # Blocked entities
        self.blocked_ips = set()
        self.suspended_users = set()
        self.require_mfa_users = set()
        
        # Metrics
        self.metrics = SecurityMetrics()
        self.alert_notifications = deque(maxlen=10000)
        
        # Alert handlers
        self.alert_handlers = {
            AlertAction.LOG_ONLY: self._handle_log_only,
            AlertAction.BLOCK_IP: self._handle_block_ip,
            AlertAction.SUSPEND_USER: self._handle_suspend_user,
            AlertAction.REQUIRE_MFA: self._handle_require_mfa,
            AlertAction.NOTIFY_ADMIN: self._handle_notify_admin,
            AlertAction.EMERGENCY_SHUTDOWN: self._handle_emergency_shutdown
        }
        
        # Anomaly detection thresholds
        self.anomaly_thresholds = {
            'login_attempts_per_minute': 10,
            'failed_logins_per_hour': 20,
            'api_calls_per_minute': 1000,
            'trades_per_minute': 50,
            'large_trades_per_hour': 10,
            'password_resets_per_hour': 5,
            'concurrent_sessions_per_user': 3,
            'failed_signature_verifications_per_hour': 15,
            'rate_limit_violations_per_hour': 50
        }
        
        logger.info("Threat detector initialized")
    
    def _initialize_threat_patterns(self) -> Dict[str, ThreatPattern]:
        """Initialize built-in threat detection patterns"""
        patterns = {
            'brute_force_login': ThreatPattern(
                pattern_id='brute_force_login',
                name='Brute Force Login Attack',
                description='Multiple failed login attempts from same IP',
                threat_level=ThreatLevel.HIGH,
                conditions={'event_type': 'login_attempt', 'outcome': 'failure'},
                time_window=300,  # 5 minutes
                threshold=10,
                action=AlertAction.BLOCK_IP
            ),
            
            'credential_stuffing': ThreatPattern(
                pattern_id='credential_stuffing',
                name='Credential Stuffing Attack',
                description='Multiple failed logins across different accounts',
                threat_level=ThreatLevel.CRITICAL,
                conditions={'event_type': 'login_attempt', 'outcome': 'failure'},
                time_window=600,  # 10 minutes
                threshold=50,
                action=AlertAction.BLOCK_IP
            ),
            
            'suspicious_trading': ThreatPattern(
                pattern_id='suspicious_trading',
                name='Suspicious Trading Activity',
                description='Unusual trading patterns or large trades',
                threat_level=ThreatLevel.MEDIUM,
                conditions={'event_type': 'trade', 'value': '>5000'},
                time_window=3600,  # 1 hour
                threshold=5,
                action=AlertAction.REQUIRE_MFA
            ),
            
            'api_abuse': ThreatPattern(
                pattern_id='api_abuse',
                name='API Abuse',
                description='Excessive API calls indicating potential abuse',
                threat_level=ThreatLevel.MEDIUM,
                conditions={'event_type': 'api_request'},
                time_window=60,  # 1 minute
                threshold=1000,
                action=AlertAction.BLOCK_IP
            ),
            
            'signature_attacks': ThreatPattern(
                pattern_id='signature_attacks',
                name='Signature Verification Attacks',
                description='Multiple failed signature verifications',
                threat_level=ThreatLevel.HIGH,
                conditions={'event_type': 'invalid_signature'},
                time_window=3600,  # 1 hour
                threshold=15,
                action=AlertAction.SUSPEND_USER
            ),
            
            'rate_limit_evasion': ThreatPattern(
                pattern_id='rate_limit_evasion',
                name='Rate Limit Evasion',
                description='Multiple rate limit violations',
                threat_level=ThreatLevel.MEDIUM,
                conditions={'event_type': 'rate_limit_exceeded'},
                time_window=3600,  # 1 hour
                threshold=50,
                action=AlertAction.BLOCK_IP
            ),
            
            'account_takeover': ThreatPattern(
                pattern_id='account_takeover',
                name='Account Takeover Attempt',
                description='Multiple login attempts from different IPs for same account',
                threat_level=ThreatLevel.CRITICAL,
                conditions={'event_type': 'login_attempt', 'outcome': 'failure'},
                time_window=1800,  # 30 minutes
                threshold=20,
                action=AlertAction.SUSPEND_USER
            ),
            
            'data_exfiltration': ThreatPattern(
                pattern_id='data_exfiltration',
                name='Data Exfiltration',
                description='Unusual data access patterns',
                threat_level=ThreatLevel.HIGH,
                conditions={'event_type': 'data_access'},
                time_window=300,  # 5 minutes
                threshold=100,
                action=AlertAction.SUSPEND_USER
            ),
            
            'webhook_abuse': ThreatPattern(
                pattern_id='webhook_abuse',
                name='Webhook Abuse',
                description='Excessive webhook requests',
                threat_level=ThreatLevel.MEDIUM,
                conditions={'event_type': 'webhook_request'},
                time_window=60,  # 1 minute
                threshold=200,
                action=AlertAction.BLOCK_IP
            ),
            
            'concurrent_session_abuse': ThreatPattern(
                pattern_id='concurrent_session_abuse',
                name='Concurrent Session Abuse',
                description='Too many concurrent sessions',
                threat_level=ThreatLevel.MEDIUM,
                conditions={'event_type': 'session_created'},
                time_window=300,  # 5 minutes
                threshold=5,
                action=AlertAction.REQUIRE_MFA
            )
        }
        
        return patterns
    
    async def analyze_security_event(self, event: SecurityEvent) -> List[AlertNotification]:
        """Analyze security event for threats"""
        alerts = []
        
        try:
            # Update metrics
            self.metrics.total_events += 1
            self.metrics.events_by_severity[event.severity.lower()] += 1
            self.metrics.events_by_type[event.event_type] += 1
            
            # Track activity
            await self._track_activity(event)
            
            # Check against threat patterns
            for pattern_id, pattern in self.threat_patterns.items():
                if not pattern.enabled:
                    continue
                
                if await self._matches_pattern(event, pattern):
                    alert = await self._create_alert(event, pattern)
                    alerts.append(alert)
                    
                    # Execute automated response
                    await self._execute_alert_action(alert)
            
            # Check for anomalies
            anomaly_alerts = await self._detect_anomalies(event)
            alerts.extend(anomaly_alerts)
            
            # Update response time metrics
            if alerts:
                response_time = time.time() - event.timestamp.timestamp()
                self.metrics.average_response_time = (
                    (self.metrics.average_response_time * (len(alerts) - 1) + response_time) / 
                    len(alerts)
                )
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error analyzing security event: {e}")
            return []
    
    async def _track_activity(self, event: SecurityEvent):
        """Track event activity for pattern matching"""
        current_time = time.time()
        
        # Track user activity
        if event.user_id:
            self.user_activity[event.user_id][event.event_type].append(current_time)
            # Keep only last hour of data
            if len(self.user_activity[event.user_id][event.event_type]) > 3600:
                self.user_activity[event.user_id][event.event_type].popleft()
        
        # Track IP activity
        if event.ip_address:
            self.ip_activity[event.ip_address][event.event_type].append(current_time)
            if len(self.ip_activity[event.ip_address][event.event_type]) > 3600:
                self.ip_activity[event.ip_address][event.event_type].popleft()
        
        # Track global activity
        self.global_activity[event.event_type].append(current_time)
        if len(self.global_activity[event.event_type]) > 86400:  # Keep 24 hours
            self.global_activity[event.event_type].popleft()
        
        # Update unique counts
        if event.user_id:
            self.metrics.unique_users = len(self.user_activity)
        if event.ip_address:
            self.metrics.unique_ips = len(self.ip_activity)
    
    async def _matches_pattern(self, event: SecurityEvent, pattern: ThreatPattern) -> bool:
        """Check if event matches threat pattern"""
        try:
            # Check basic conditions
            for condition_key, condition_value in pattern.conditions.items():
                event_value = getattr(event, condition_key, None)
                
                if isinstance(condition_value, str) and condition_value.startswith('>'):
                    threshold = float(condition_value[1:])
                    if not event_value or float(event_value) <= threshold:
                        return False
                elif isinstance(condition_value, str) and condition_value.startswith('<'):
                    threshold = float(condition_value[1:])
                    if not event_value or float(event_value) >= threshold:
                        return False
                elif event_value != condition_value:
                    return False
            
            # Check threshold in time window
            count = await self._count_matching_events(event, pattern)
            return count >= pattern.threshold
            
        except Exception as e:
            logger.error(f"Error matching pattern {pattern.pattern_id}: {e}")
            return False
    
    async def _count_matching_events(self, event: SecurityEvent, pattern: ThreatPattern) -> int:
        """Count events matching pattern in time window"""
        current_time = time.time()
        cutoff_time = current_time - pattern.time_window
        
        count = 0
        
        # Count from user activity
        if event.user_id and event.user_id in self.user_activity:
            user_events = self.user_activity[event.user_id].get(event.event_type, deque())
            count += sum(1 for timestamp in user_events if timestamp >= cutoff_time)
        
        # Count from IP activity
        if event.ip_address and event.ip_address in self.ip_activity:
            ip_events = self.ip_activity[event.ip_address].get(event.event_type, deque())
            count += sum(1 for timestamp in ip_events if timestamp >= cutoff_time)
        
        # Count from global activity
        global_events = self.global_activity.get(event.event_type, deque())
        count += sum(1 for timestamp in global_events if timestamp >= cutoff_time)
        
        return count
    
    async def _detect_anomalies(self, event: SecurityEvent) -> List[AlertNotification]:
        """Detect statistical anomalies"""
        alerts = []
        
        try:
            # Check for unusual login patterns
            if event.event_type == 'login_attempt':
                anomaly_alerts = await self._detect_login_anomalies(event)
                alerts.extend(anomaly_alerts)
            
            # Check for unusual trading patterns
            elif event.event_type == 'trade':
                anomaly_alerts = await self._detect_trading_anomalies(event)
                alerts.extend(anomaly_alerts)
            
            # Check for unusual API usage
            elif event.event_type == 'api_request':
                anomaly_alerts = await self._detect_api_anomalies(event)
                alerts.extend(anomaly_alerts)
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
        
        return alerts
    
    async def _detect_login_anomalies(self, event: SecurityEvent) -> List[AlertNotification]:
        """Detect login anomalies"""
        alerts = []
        
        if event.user_id:
            # Check for logins from unusual locations
            user_logins = self.user_activity[event.user_id].get('login_attempt', deque())
            recent_logins = [t for t in user_logins if time.time() - t < 3600]  # Last hour
            
            if len(recent_logins) > 10:  # More than 10 logins in an hour
                alert = AlertNotification(
                    alert_id=f"anomaly_login_{int(time.time())}",
                    threat_level=ThreatLevel.MEDIUM,
                    message="Unusual login frequency detected",
                    details={
                        'user_id': event.user_id,
                        'login_count': len(recent_logins),
                        'timeframe': '1 hour'
                    },
                    timestamp=datetime.utcnow(),
                    user_id=event.user_id,
                    ip_address=event.ip_address,
                    action_taken=AlertAction.REQUIRE_MFA
                )
                alerts.append(alert)
        
        return alerts
    
    async def _detect_trading_anomalies(self, event: SecurityEvent) -> List[AlertNotification]:
        """Detect trading anomalies"""
        alerts = []
        
        try:
            trade_value = event.details.get('value', 0)
            
            # Check for unusually large trades
            if trade_value > 10000:  # $10,000+
                alert = AlertNotification(
                    alert_id=f"anomaly_large_trade_{int(time.time())}",
                    threat_level=ThreatLevel.HIGH,
                    message="Unusually large trade detected",
                    details={
                        'user_id': event.user_id,
                        'trade_value': trade_value,
                        'market_id': event.details.get('market_id')
                    },
                    timestamp=datetime.utcnow(),
                    user_id=event.user_id,
                    ip_address=event.ip_address,
                    action_taken=AlertAction.REQUIRE_MFA
                )
                alerts.append(alert)
            
            # Check for rapid trading
            if event.user_id:
                user_trades = self.user_activity[event.user_id].get('trade', deque())
                recent_trades = [t for t in user_trades if time.time() - t < 300]  # Last 5 minutes
                
                if len(recent_trades) > 20:  # More than 20 trades in 5 minutes
                    alert = AlertNotification(
                        alert_id=f"anomaly_rapid_trading_{int(time.time())}",
                        threat_level=ThreatLevel.MEDIUM,
                        message="Rapid trading pattern detected",
                        details={
                            'user_id': event.user_id,
                            'trade_count': len(recent_trades),
                            'timeframe': '5 minutes'
                        },
                        timestamp=datetime.utcnow(),
                        user_id=event.user_id,
                        ip_address=event.ip_address,
                        action_taken=AlertAction.REQUIRE_MFA
                    )
                    alerts.append(alert)
        
        except Exception as e:
            logger.error(f"Error detecting trading anomalies: {e}")
        
        return alerts
    
    async def _detect_api_anomalies(self, event: SecurityEvent) -> List[AlertNotification]:
        """Detect API usage anomalies"""
        alerts = []
        
        try:
            # Check for API abuse patterns
            if event.ip_address:
                ip_requests = self.ip_activity[event.ip_address].get('api_request', deque())
                recent_requests = [t for t in ip_requests if time.time() - t < 60]  # Last minute
                
                if len(recent_requests) > 500:  # More than 500 requests per minute
                    alert = AlertNotification(
                        alert_id=f"anomaly_api_abuse_{int(time.time())}",
                        threat_level=ThreatLevel.HIGH,
                        message="API abuse detected",
                        details={
                            'ip_address': event.ip_address,
                            'request_count': len(recent_requests),
                            'timeframe': '1 minute'
                        },
                        timestamp=datetime.utcnow(),
                        user_id=event.user_id,
                        ip_address=event.ip_address,
                        action_taken=AlertAction.BLOCK_IP
                    )
                    alerts.append(alert)
        
        except Exception as e:
            logger.error(f"Error detecting API anomalies: {e}")
        
        return alerts
    
    async def _create_alert(self, event: SecurityEvent, pattern: ThreatPattern) -> AlertNotification:
        """Create alert notification"""
        alert_id = f"{pattern.pattern_id}_{int(time.time())}"
        
        alert = AlertNotification(
            alert_id=alert_id,
            threat_level=pattern.threat_level,
            message=f"{pattern.name} detected",
            details={
                'pattern_id': pattern.pattern_id,
                'event_type': event.event_type,
                'user_id': event.user_id,
                'ip_address': event.ip_address,
                'event_details': event.details,
                'pattern_description': pattern.description
            },
            timestamp=datetime.utcnow(),
            user_id=event.user_id,
            ip_address=event.ip_address,
            action_taken=pattern.action
        )
        
        # Store alert
        self.alert_notifications.append(alert)
        
        return alert
    
    async def _execute_alert_action(self, alert: AlertNotification):
        """Execute automated alert response"""
        try:
            handler = self.alert_handlers.get(alert.action_taken)
            if handler:
                await handler(alert)
            
            # Update metrics
            if alert.action_taken == AlertAction.BLOCK_IP:
                self.metrics.blocked_ips += 1
            elif alert.action_taken == AlertAction.SUSPEND_USER:
                self.metrics.suspended_users += 1
            
            logger.info(f"Executed alert action: {alert.action_taken.value} for {alert.alert_id}")
            
        except Exception as e:
            logger.error(f"Error executing alert action {alert.action_taken}: {e}")
    
    async def _handle_log_only(self, alert: AlertNotification):
        """Handle log-only alerts"""
        logger.warning(f"Security alert: {alert.message}")
    
    async def _handle_block_ip(self, alert: AlertNotification):
        """Handle IP blocking"""
        if alert.ip_address:
            self.blocked_ips.add(alert.ip_address)
            
            # Store in Redis with expiration
            await self.security.redis.setex(
                f"blocked_ip:{alert.ip_address}",
                86400,  # 24 hours
                json.dumps({
                    'alert_id': alert.alert_id,
                    'timestamp': alert.timestamp.isoformat(),
                    'reason': alert.message
                })
            )
            
            logger.warning(f"Blocked IP: {alert.ip_address}")
    
    async def _handle_suspend_user(self, alert: AlertNotification):
        """Handle user suspension"""
        if alert.user_id:
            self.suspended_users.add(alert.user_id)
            
            # Store in Redis
            await self.security.redis.setex(
                f"suspended_user:{alert.user_id}",
                86400 * 7,  # 7 days
                json.dumps({
                    'alert_id': alert.alert_id,
                    'timestamp': alert.timestamp.isoformat(),
                    'reason': alert.message
                })
            )
            
            logger.warning(f"Suspended user: {alert.user_id}")
    
    async def _handle_require_mfa(self, alert: AlertNotification):
        """Handle MFA requirement"""
        if alert.user_id:
            self.require_mfa_users.add(alert.user_id)
            
            # Store in Redis
            await self.security.redis.setex(
                f"require_mfa:{alert.user_id}",
                3600,  # 1 hour
                json.dumps({
                    'alert_id': alert.alert_id,
                    'timestamp': alert.timestamp.isoformat(),
                    'reason': alert.message
                })
            )
            
            logger.warning(f"MFA required for user: {alert.user_id}")
    
    async def _handle_notify_admin(self, alert: AlertNotification):
        """Handle admin notification"""
        # Send Discord notification
        await self._send_discord_alert(alert)
        
        # Send email notification (if configured)
        await self._send_email_alert(alert)
        
        logger.critical(f"Admin notification sent: {alert.message}")
    
    async def _handle_emergency_shutdown(self, alert: AlertNotification):
        """Handle emergency shutdown"""
        logger.critical(f"EMERGENCY SHUTDOWN TRIGGERED: {alert.message}")
        
        # This would implement emergency shutdown procedures
        # - Stop accepting new requests
        # - Close all connections
        # - Save all data
        # - Notify all administrators
        
        # Store emergency flag
        await self.security.redis.setex(
            "emergency_shutdown",
            3600,  # 1 hour
            json.dumps({
                'alert_id': alert.alert_id,
                'timestamp': alert.timestamp.isoformat(),
                'reason': alert.message
            })
        )
    
    async def _send_discord_alert(self, alert: AlertNotification):
        """Send Discord alert notification"""
        try:
            webhook_url = os.getenv('DISCORD_HEALTH_WEBHOOK_URL')
            if not webhook_url:
                return
            
            # Color based on threat level
            colors = {
                ThreatLevel.LOW: 0x00FF00,    # Green
                ThreatLevel.MEDIUM: 0xFFFF00,  # Yellow
                ThreatLevel.HIGH: 0xFF0000,    # Red
                ThreatLevel.CRITICAL: 0x8B0000  # Dark Red
            }
            
            embed = {
                "title": f"🚨 Security Alert: {alert.threat_level.value.upper()}",
                "description": alert.message,
                "color": colors.get(alert.threat_level, 0xFF0000),
                "timestamp": alert.timestamp.isoformat(),
                "fields": [
                    {"name": "Alert ID", "value": alert.alert_id, "inline": True},
                    {"name": "User ID", "value": alert.user_id or "N/A", "inline": True},
                    {"name": "IP Address", "value": alert.ip_address or "N/A", "inline": True},
                    {"name": "Action Taken", "value": alert.action_taken.value, "inline": True}
                ],
                "footer": {
                    "text": "Crypto Predict Monitor Security System"
                }
            }
            
            payload = {
                "embeds": [embed],
                "username": "Security Monitor"
            }
            
            async with aiohttp.ClientSession() as session:
                await session.post(webhook_url, json=payload)
                
        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
    
    async def _send_email_alert(self, alert: AlertNotification):
        """Send email alert notification"""
        # This would integrate with your email service
        # For now, just log
        logger.critical(f"Email alert would be sent for: {alert.message}")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        return ip_address in self.blocked_ips
    
    def is_user_suspended(self, user_id: str) -> bool:
        """Check if user is suspended"""
        return user_id in self.suspended_users
    
    def does_user_require_mfa(self, user_id: str) -> bool:
        """Check if user requires MFA"""
        return user_id in self.require_mfa_users
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get comprehensive security metrics"""
        return asdict(self.metrics)
    
    def get_recent_alerts(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent security alerts"""
        recent_alerts = list(self.alert_notifications)[-limit:]
        return [asdict(alert) for alert in recent_alerts]
    
    def add_threat_pattern(self, pattern: ThreatPattern):
        """Add custom threat pattern"""
        self.threat_patterns[pattern.pattern_id] = pattern
        logger.info(f"Added threat pattern: {pattern.pattern_id}")
    
    def remove_threat_pattern(self, pattern_id: str):
        """Remove threat pattern"""
        if pattern_id in self.threat_patterns:
            del self.threat_patterns[pattern_id]
            logger.info(f"Removed threat pattern: {pattern_id}")
    
    def update_threat_pattern(self, pattern_id: str, updates: Dict[str, Any]):
        """Update threat pattern"""
        if pattern_id in self.threat_patterns:
            pattern = self.threat_patterns[pattern_id]
            for key, value in updates.items():
                if hasattr(pattern, key):
                    setattr(pattern, key, value)
            logger.info(f"Updated threat pattern: {pattern_id}")
    
    async def cleanup_old_data(self):
        """Clean up old tracking data"""
        try:
            current_time = time.time()
            cutoff_time = current_time - 86400  # 24 hours ago
            
            # Clean user activity
            for user_id in list(self.user_activity.keys()):
                for event_type in list(self.user_activity[user_id].keys()):
                    events = self.user_activity[user_id][event_type]
                    self.user_activity[user_id][event_type] = deque(
                        [t for t in events if t >= cutoff_time],
                        maxlen=3600
                    )
                    if not self.user_activity[user_id][event_type]:
                        del self.user_activity[user_id][event_type]
                
                if not self.user_activity[user_id]:
                    del self.user_activity[user_id]
            
            # Clean IP activity
            for ip_address in list(self.ip_activity.keys()):
                for event_type in list(self.ip_activity[ip_address].keys()):
                    events = self.ip_activity[ip_address][event_type]
                    self.ip_activity[ip_address][event_type] = deque(
                        [t for t in events if t >= cutoff_time],
                        maxlen=3600
                    )
                    if not self.ip_activity[ip_address][event_type]:
                        del self.ip_activity[ip_address][event_type]
                
                if not self.ip_activity[ip_address]:
                    del self.ip_activity[ip_address]
            
            # Clean global activity
            for event_type in list(self.global_activity.keys()):
                events = self.global_activity[event_type]
                self.global_activity[event_type] = deque(
                    [t for t in events if t >= cutoff_time],
                    maxlen=86400
                )
                if not self.global_activity[event_type]:
                    del self.global_activity[event_type]
            
            logger.info("Security data cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during security cleanup: {e}")

# Initialize threat detector
threat_detector = ThreatDetector()
