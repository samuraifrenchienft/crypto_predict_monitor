"""
Error Monitoring and Alerting System
Comprehensive error tracking, alerting, and recovery
"""

import asyncio
import logging
import os
import time
import traceback
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque

from src.webhook import send_webhook
from src.schemas import WebhookPayload

logger = logging.getLogger("error_monitor")

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorEvent:
    """Structured error event for tracking"""
    timestamp: datetime
    error_type: str
    message: str
    severity: ErrorSeverity
    service: str
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolution_time: Optional[datetime] = None

class ErrorMonitor:
    """Comprehensive error monitoring and alerting system"""
    
    def __init__(self, webhook_url: Optional[str] = None, max_events: int = 1000):
        self.webhook_url = webhook_url
        self.max_events = max_events
        
        # Error storage
        self.error_events: deque = deque(maxlen=max_events)
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_by_service: Dict[str, List[ErrorEvent]] = defaultdict(list)
        
        # Alert thresholds
        self.alert_thresholds = {
            ErrorSeverity.LOW: 50,      # 50 low errors per hour
            ErrorSeverity.MEDIUM: 20,  # 20 medium errors per hour
            ErrorSeverity.HIGH: 5,      # 5 high errors per hour
            ErrorSeverity.CRITICAL: 1   # 1 critical error immediately
        }
        
        # Rate limiting for alerts
        self.last_alerts: Dict[str, datetime] = {}
        self.alert_cooldown = timedelta(minutes=5)
        
        # Recovery actions
        self.recovery_actions: Dict[str, List[Callable]] = {}
        
        # Health checks
        self.service_health: Dict[str, bool] = {}
        self.last_health_check: Dict[str, datetime] = {}
        
    def track_error(
        self,
        error_type: str,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        service: str = "unknown",
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        exception: Optional[Exception] = None
    ):
        """Track a new error event"""
        
        # Create error event
        error_event = ErrorEvent(
            timestamp=datetime.utcnow(),
            error_type=error_type,
            message=message,
            severity=severity,
            service=service,
            user_id=user_id,
            request_id=request_id,
            context=context or {},
            stack_trace=traceback.format_exc() if exception else None
        )
        
        # Store error
        self.error_events.append(error_event)
        self.error_counts[error_type] += 1
        self.error_by_service[service].append(error_event)
        
        # Log the error
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(severity, logging.ERROR)
        
        logger.log(
            log_level,
            f"Error tracked: {error_type} - {message}",
            extra={
                "error_type": error_type,
                "severity": severity.value,
                "service": service,
                "user_id": user_id,
                "request_id": request_id
            }
        )
        
        # Check if alert needed
        self._check_alert_conditions(error_event)
        
        # Attempt recovery if configured
        self._attempt_recovery(error_event)
    
    def _check_alert_conditions(self, error_event: ErrorEvent):
        """Check if error should trigger an alert"""
        
        # Immediate alert for critical errors
        if error_event.severity == ErrorSeverity.CRITICAL:
            self._send_alert(error_event, "Critical error detected")
            return
        
        # Check rate-based thresholds
        error_key = f"{error_event.service}:{error_event.error_type}"
        recent_errors = [
            e for e in self.error_events
            if e.timestamp > datetime.utcnow() - timedelta(hours=1) and
               e.service == error_event.service and
               e.error_type == error_event.error_type
        ]
        
        threshold = self.alert_thresholds[error_event.severity]
        if len(recent_errors) >= threshold:
            self._send_alert(
                error_event,
                f"High error rate: {len(recent_errors)} {error_event.severity.value} errors in last hour"
            )
    
    def _send_alert(self, error_event: ErrorEvent, alert_message: str):
        """Send alert to monitoring system"""
        
        # Rate limiting
        alert_key = f"{error_event.service}:{error_event.error_type}"
        now = datetime.utcnow()
        
        if alert_key in self.last_alerts:
            if now - self.last_alerts[alert_key] < self.alert_cooldown:
                return  # Skip due to cooldown
        
        self.last_alerts[alert_key] = now
        
        if not self.webhook_url:
            logger.warning("No webhook URL configured for alerts")
            return
        
        try:
            # Create alert message
            alert_content = f"🚨 **Error Alert**\n\n"
            alert_content += f"**Service:** {error_event.service}\n"
            alert_content += f"**Error:** {error_event.error_type}\n"
            alert_content += f"**Severity:** {error_event.severity.value.upper()}\n"
            alert_content += f"**Message:** {error_event.message}\n"
            alert_content += f"**Time:** {error_event.timestamp.isoformat()}\n"
            
            if error_event.user_id:
                alert_content += f"**User ID:** {error_event.user_id}\n"
            
            if error_event.request_id:
                alert_content += f"**Request ID:** {error_event.request_id}\n"
            
            alert_content += f"\n**Alert:** {alert_message}\n"
            
            if error_event.stack_trace:
                alert_content += f"\n**Stack Trace:**\n```{error_event.stack_trace[:1000]}```"
            
            # Send to Discord
            payload = WebhookPayload(content=alert_content)
            send_webhook(self.webhook_url, payload, timeout_seconds=10)
            
            logger.info(f"Alert sent for {error_event.error_type}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def _attempt_recovery(self, error_event: ErrorEvent):
        """Attempt automatic recovery for known errors"""
        
        recovery_key = f"{error_event.service}:{error_event.error_type}"
        
        if recovery_key in self.recovery_actions:
            for action in self.recovery_actions[recovery_key]:
                try:
                    action(error_event)
                    logger.info(f"Recovery action executed for {recovery_key}")
                except Exception as e:
                    logger.error(f"Recovery action failed: {e}")
    
    def register_recovery_action(
        self,
        service: str,
        error_type: str,
        action: Callable[[ErrorEvent], None]
    ):
        """Register a recovery action for specific errors"""
        
        key = f"{service}:{error_type}"
        if key not in self.recovery_actions:
            self.recovery_actions[key] = []
        
        self.recovery_actions[key].append(action)
        logger.info(f"Recovery action registered for {key}")
    
    def check_service_health(self, service: str) -> bool:
        """Check if a service is healthy based on recent errors"""
        
        # Get recent errors for this service
        recent_errors = [
            e for e in self.error_events
            if e.service == service and
               e.timestamp > datetime.utcnow() - timedelta(minutes=5)
        ]
        
        # Service is unhealthy if too many recent errors
        critical_count = sum(1 for e in recent_errors if e.severity == ErrorSeverity.CRITICAL)
        high_count = sum(1 for e in recent_errors if e.severity == ErrorSeverity.HIGH)
        
        is_healthy = critical_count == 0 and high_count < 3
        
        # Update health status
        self.service_health[service] = is_healthy
        self.last_health_check[service] = datetime.utcnow()
        
        return is_healthy
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get summary of errors in the last N hours"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        recent_errors = [e for e in self.error_events if e.timestamp > cutoff_time]
        
        # Count by severity
        severity_counts = defaultdict(int)
        for error in recent_errors:
            severity_counts[error.severity.value] += 1
        
        # Count by service
        service_counts = defaultdict(int)
        for error in recent_errors:
            service_counts[error.service] += 1
        
        # Top error types
        error_type_counts = defaultdict(int)
        for error in recent_errors:
            error_type_counts[error.error_type] += 1
        
        return {
            "period_hours": hours,
            "total_errors": len(recent_errors),
            "by_severity": dict(severity_counts),
            "by_service": dict(service_counts),
            "top_error_types": dict(
                sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "service_health": self.service_health.copy(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def resolve_error(self, error_id: str, resolution: str):
        """Mark an error as resolved"""
        
        # Find error (simplified - in production use proper IDs)
        for error in self.error_events:
            if str(id(error)) == error_id or error.error_type == error_id:
                error.resolved = True
                error.resolution_time = datetime.utcnow()
                logger.info(f"Error resolved: {error.error_type} - {resolution}")
                return True
        
        return False

# Global error monitor instance
error_monitor = ErrorMonitor(
    webhook_url=os.getenv('DISCORD_HEALTH_WEBHOOK_URL')
)

# Recovery actions for common P&L card errors
def register_pnl_recovery_actions():
    """Register recovery actions for P&L card system"""
    
    def handle_database_connection_error(error_event: ErrorEvent):
        """Recover from database connection errors"""
        logger.info("Attempting database connection recovery")
        # In production: retry connection, switch to backup DB, etc.
    
    def handle_image_generation_error(error_event: ErrorEvent):
        """Recover from image generation errors"""
        logger.info("Attempting image generation recovery")
        # In production: clear cache, restart service, etc.
    
    def handle_s3_upload_error(error_event: ErrorEvent):
        """Recover from S3 upload errors"""
        logger.info("Attempting S3 upload recovery")
        # In production: retry upload, use local storage, etc.
    
    # Register recovery actions
    error_monitor.register_recovery_action(
        "pnl_cards", "database_connection", handle_database_connection_error
    )
    error_monitor.register_recovery_action(
        "pnl_cards", "image_generation", handle_image_generation_error
    )
    error_monitor.register_recovery_action(
        "pnl_cards", "s3_upload", handle_s3_upload_error
    )

# Decorator for automatic error tracking
def track_errors(
    service: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    reraise: bool = True
):
    """Decorator to automatically track function errors"""
    
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_monitor.track_error(
                    error_type=type(e).__name__,
                    message=str(e),
                    severity=severity,
                    service=service,
                    exception=e
                )
                
                if reraise:
                    raise
                return None
        return wrapper
    return decorator

# Initialize recovery actions
register_pnl_recovery_actions()

# Example usage
if __name__ == "__main__":
    # Test error tracking
    error_monitor.track_error(
        error_type="TestError",
        message="This is a test error",
        severity=ErrorSeverity.HIGH,
        service="test_service",
        user_id="test_user"
    )
    
    # Test decorator
    @track_errors(service="test", severity=ErrorSeverity.CRITICAL)
    def failing_function():
        raise ValueError("This function always fails")
    
    try:
        failing_function()
    except:
        pass
    
    # Get summary
    summary = error_monitor.get_error_summary(hours=1)
    print("Error summary:", summary)
