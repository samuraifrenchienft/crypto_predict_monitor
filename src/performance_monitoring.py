"""
Performance Monitoring Dashboard
Real-time performance metrics and monitoring for P&L Card System
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging

logger = logging.getLogger("performance_monitor")

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

@dataclass
class SystemMetrics:
    """System-wide metrics"""
    cpu_percent: float
    memory_percent: float
    disk_usage_percent: float
    active_connections: int
    request_rate: float
    error_rate: float
    response_time_avg: float
    card_generation_rate: float

class PerformanceMonitor:
    """Real-time performance monitoring system"""
    
    def __init__(self, max_history: int = 10000):
        self.max_history = max_history
        
        # Metrics storage
        self.metrics: deque = deque(maxlen=max_history)
        self.metrics_by_name: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history))
        
        # System metrics
        self.system_metrics: deque = deque(maxlen=1000)
        
        # Alert thresholds
        self.alert_thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_usage_percent": 90.0,
            "error_rate": 5.0,
            "response_time_avg": 2.0,
            "card_generation_time": 5.0
        }
        
        # Performance counters
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        
        # Last alert times
        self.last_alerts: Dict[str, datetime] = {}
        self.alert_cooldown = timedelta(minutes=5)
    
    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None
    ):
        """Record a performance metric"""
        
        metric = PerformanceMetrics(
            timestamp=datetime.utcnow(),
            metric_name=name,
            value=value,
            unit=unit,
            tags=tags or {}
        )
        
        # Store metric
        self.metrics.append(metric)
        self.metrics_by_name[name].append(metric)
        
        # Check alert thresholds
        self._check_alert_thresholds(name, value)
    
    def increment_counter(self, name: str, value: int = 1):
        """Increment a performance counter"""
        self.counters[name] += value
        
        # Record as metric
        self.record_metric(f"counter.{name}", self.counters[name], "count")
    
    def record_timer(self, name: str, duration: float):
        """Record a timing measurement"""
        self.timers[name].append(duration)
        
        # Keep only recent measurements
        if len(self.timers[name]) > 1000:
            self.timers[name] = self.timers[name][-1000:]
        
        # Record as metric
        self.record_metric(f"timer.{name}", duration, "seconds")
        self.record_metric(f"timer.{name}_avg", sum(self.timers[name]) / len(self.timers[name]), "seconds")
    
    def _check_alert_thresholds(self, metric_name: str, value: float):
        """Check if metric exceeds alert threshold"""
        
        if metric_name in self.alert_thresholds:
            threshold = self.alert_thresholds[metric_name]
            
            if value > threshold:
                now = datetime.utcnow()
                
                # Check cooldown
                if metric_name not in self.last_alerts or \
                   now - self.last_alerts[metric_name] > self.alert_cooldown:
                    
                    self._send_alert(metric_name, value, threshold)
                    self.last_alerts[metric_name] = now
    
    def _send_alert(self, metric_name: str, value: float, threshold: float):
        """Send performance alert"""
        
        try:
            from src.webhook import send_webhook
            from src.schemas import WebhookPayload
            
            alert_msg = f"⚠️ **Performance Alert**\n\n"
            alert_msg += f"**Metric:** {metric_name}\n"
            alert_msg += f"**Current Value:** {value:.2f}\n"
            alert_msg += f"**Threshold:** {threshold:.2f}\n"
            alert_msg += f"**Time:** {datetime.utcnow().isoformat()}\n"
            
            webhook_url = os.getenv('DISCORD_HEALTH_WEBHOOK_URL')
            if webhook_url:
                payload = WebhookPayload(content=alert_msg)
                send_webhook(webhook_url, payload, timeout_seconds=10)
            
            logger.warning(f"Performance alert: {metric_name} = {value:.2f} (threshold: {threshold:.2f})")
            
        except Exception as e:
            logger.error(f"Failed to send performance alert: {e}")
    
    def collect_system_metrics(self):
        """Collect system-wide metrics"""
        
        try:
            import psutil
            
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network connections
            connections = len(psutil.net_connections())
            
            # Calculate rates from recent metrics
            recent_metrics = [
                m for m in self.metrics 
                if m.timestamp > datetime.utcnow() - timedelta(minutes=1)
            ]
            
            request_rate = len([m for m in recent_metrics if "request" in m.metric_name])
            error_rate = len([m for m in recent_metrics if "error" in m.metric_name])
            
            response_times = [m.value for m in recent_metrics if "response_time" in m.metric_name]
            response_time_avg = sum(response_times) / len(response_times) if response_times else 0
            
            card_generation_times = [m.value for m in recent_metrics if "card_generation" in m.metric_name]
            card_generation_rate = len(card_generation_times)
            
            system_metric = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                disk_usage_percent=disk.percent,
                active_connections=connections,
                request_rate=request_rate,
                error_rate=error_rate,
                response_time_avg=response_time_avg,
                card_generation_rate=card_generation_rate
            )
            
            self.system_metrics.append(system_metric)
            
            # Record individual metrics
            self.record_metric("system.cpu_percent", cpu_percent, "percent")
            self.record_metric("system.memory_percent", memory.percent, "percent")
            self.record_metric("system.disk_usage_percent", disk.percent, "percent")
            self.record_metric("system.active_connections", connections, "count")
            self.record_metric("system.request_rate", request_rate, "requests_per_minute")
            self.record_metric("system.error_rate", error_rate, "errors_per_minute")
            self.record_metric("system.response_time_avg", response_time_avg, "seconds")
            self.record_metric("system.card_generation_rate", card_generation_rate, "cards_per_minute")
            
        except ImportError:
            logger.warning("psutil not available for system metrics")
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
    
    def get_metrics_summary(self, minutes: int = 5) -> Dict[str, Any]:
        """Get summary of recent metrics"""
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        recent_metrics = [m for m in self.metrics if m.timestamp > cutoff_time]
        
        # Group by metric name
        metrics_by_name = defaultdict(list)
        for metric in recent_metrics:
            metrics_by_name[metric.metric_name].append(metric.value)
        
        # Calculate statistics
        summary = {}
        for name, values in metrics_by_name.items():
            if values:
                summary[name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values),
                    "latest": values[-1]
                }
        
        # Add system metrics summary
        if self.system_metrics:
            latest_system = self.system_metrics[-1]
            summary["system"] = asdict(latest_system)
        
        return {
            "period_minutes": minutes,
            "total_metrics": len(recent_metrics),
            "metrics_summary": summary,
            "counters": dict(self.counters),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for performance dashboard"""
        
        # Recent metrics (last hour)
        recent_summary = self.get_metrics_summary(minutes=60)
        
        # Top metrics by frequency
        metric_counts = defaultdict(int)
        for metric in self.metrics:
            metric_counts[metric.metric_name] += 1
        
        top_metrics = sorted(metric_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Recent alerts
        recent_alerts = [
            f"{name}: {self.last_alerts[name].isoformat()}"
            for name in self.last_alerts
            if datetime.utcnow() - self.last_alerts[name] < timedelta(hours=1)
        ]
        
        # Performance trends
        trends = {}
        for metric_name in ["system.cpu_percent", "system.memory_percent", "system.request_rate"]:
            if metric_name in self.metrics_by_name:
                values = list(self.metrics_by_name[metric_name])
                if len(values) >= 2:
                    recent_avg = sum(m.value for m in values[-10:]) / min(10, len(values))
                    older_avg = sum(m.value for m in values[-20:-10]) / min(10, len(values) - 10)
                    trend = "up" if recent_avg > older_avg else "down" if recent_avg < older_avg else "stable"
                    trends[metric_name] = {
                        "trend": trend,
                        "recent_avg": recent_avg,
                        "older_avg": older_avg,
                        "change_percent": ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
                    }
        
        return {
            "summary": recent_summary,
            "top_metrics": top_metrics,
            "recent_alerts": recent_alerts,
            "trends": trends,
            "alert_thresholds": self.alert_thresholds,
            "timestamp": datetime.utcnow().isoformat()
        }

# Performance monitoring decorators
def monitor_performance(metric_name: str):
    """Decorator to monitor function performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                performance_monitor.record_timer(f"{metric_name}.success", time.time() - start_time)
                performance_monitor.increment_counter(f"{metric_name}.success")
                return result
            except Exception as e:
                performance_monitor.record_timer(f"{metric_name}.error", time.time() - start_time)
                performance_monitor.increment_counter(f"{metric_name}.error")
                raise
        return wrapper
    return decorator

def monitor_api_response(endpoint: str):
    """Decorator to monitor API endpoint performance"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                response_time = time.time() - start_time
                
                performance_monitor.record_metric(f"api.{endpoint}.response_time", response_time, "seconds")
                performance_monitor.increment_counter(f"api.{endpoint}.requests")
                
                # Log slow responses
                if response_time > 2.0:
                    logger.warning(f"Slow API response: {endpoint} took {response_time:.2f}s")
                
                return result
            except Exception as e:
                performance_monitor.record_metric(f"api.{endpoint}.error_time", time.time() - start_time, "seconds")
                performance_monitor.increment_counter(f"api.{endpoint}.errors")
                raise
        return wrapper
    return decorator

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Background task to collect system metrics
async def start_system_metrics_collection(interval: int = 60):
    """Start background collection of system metrics"""
    
    while True:
        try:
            performance_monitor.collect_system_metrics()
            await asyncio.sleep(interval)
        except Exception as e:
            logger.error(f"System metrics collection error: {e}")
            await asyncio.sleep(interval)

# Flask integration
def create_performance_blueprint():
    """Create Flask blueprint for performance monitoring"""
    
    from flask import Blueprint, jsonify
    
    perf_bp = Blueprint('performance', __name__)
    
    @perf_bp.route('/performance/metrics')
    def get_metrics():
        """Get performance metrics"""
        minutes = request.args.get('minutes', 5, type=int)
        return jsonify(performance_monitor.get_metrics_summary(minutes))
    
    @perf_bp.route('/performance/dashboard')
    def get_dashboard():
        """Get performance dashboard data"""
        return jsonify(performance_monitor.get_dashboard_data())
    
    @perf_bp.route('/performance/counters')
    def get_counters():
        """Get performance counters"""
        return jsonify(dict(performance_monitor.counters))
    
    @perf_bp.route('/performance/alerts')
    def get_alerts():
        """Get recent alerts"""
        recent_alerts = [
            {
                "metric": name,
                "time": time.isoformat(),
                "threshold": performance_monitor.alert_thresholds.get(name, 0)
            }
            for name, time in performance_monitor.last_alerts.items()
            if datetime.utcnow() - time < timedelta(hours=24)
        ]
        return jsonify(recent_alerts)
    
    return perf_bp

# Example usage
if __name__ == "__main__":
    # Test performance monitoring
    @monitor_performance("test_function")
    def test_function():
        time.sleep(0.1)
        return "success"
    
    # Run test function
    test_function()
    
    # Collect system metrics
    performance_monitor.collect_system_metrics()
    
    # Get dashboard data
    dashboard = performance_monitor.get_dashboard_data()
    print("Dashboard data:", json.dumps(dashboard, indent=2, default=str))
