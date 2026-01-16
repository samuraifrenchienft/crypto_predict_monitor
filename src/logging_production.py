"""
Production-Ready Logging Configuration
Enhanced logging with structured output, monitoring, and alerting
"""

import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for production logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                          'pathname', 'filename', 'module', 'exc_info', 
                          'exc_text', 'stack_info', 'lineno', 'funcName', 
                          'created', 'msecs', 'relativeCreated', 'thread', 
                          'threadName', 'processName', 'process', 'message']:
                log_entry[key] = value
        
        return json.dumps(log_entry)

class PnLCardFilter(logging.Filter):
    """Custom filter for P&L card system logs"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        # Add P&L card specific context
        if 'pnl' in record.name.lower() or 'card' in record.getMessage().lower():
            record.service = 'pnl_cards'
        else:
            record.service = 'monitor'
        
        return True

class AlertingHandler(logging.Handler):
    """Handler that sends critical logs to monitoring/alerting"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        super().__init__(logging.ERROR)
        self.webhook_url = webhook_url
    
    def emit(self, record: logging.LogRecord):
        if not self.webhook_url or record.levelno < logging.ERROR:
            return
        
        try:
            from src.webhook import send_webhook
            from src.schemas import WebhookPayload
            
            # Create alert message
            alert_msg = f"🚨 **{record.levelname}** in {record.name}\n"
            alert_msg += f"**Message:** {record.getMessage()}\n"
            alert_msg += f"**Module:** {record.module}:{record.lineno}\n"
            
            if record.exc_info:
                alert_msg += f"**Exception:** {self.formatException(record.exc_info)}"
            
            # Send to Discord webhook
            payload = WebhookPayload(content=alert_msg)
            send_webhook(self.webhook_url, payload, timeout_seconds=10)
            
        except Exception as e:
            # Don't let logging errors crash the application
            print(f"Failed to send alert: {e}", file=sys.stderr)

def setup_production_logging(
    log_level: str = "INFO",
    log_file: Optional[str] = None,
    webhook_url: Optional[str] = None,
    enable_structured: bool = True
) -> None:
    """Setup production-ready logging configuration"""
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    if enable_structured:
        console_handler.setFormatter(StructuredFormatter())
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
    
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        
        if enable_structured:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
        
        root_logger.addHandler(file_handler)
    
    # Error file handler (only errors and above)
    error_file = logs_dir / "errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        filename=error_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(error_handler)
    
    # P&L card specific log file
    pnl_log_file = logs_dir / "pnl_cards.log"
    pnl_handler = logging.handlers.RotatingFileHandler(
        filename=pnl_log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    pnl_handler.setLevel(logging.DEBUG)
    pnl_handler.setFormatter(StructuredFormatter())
    pnl_handler.addFilter(PnLCardFilter())
    root_logger.addHandler(pnl_handler)
    
    # Alerting handler for critical errors
    if webhook_url:
        alert_handler = AlertingHandler(webhook_url)
        root_logger.addHandler(alert_handler)
    
    # Configure specific loggers
    configure_specific_loggers()
    
    # Log startup message
    logger = logging.getLogger("crypto_predict_monitor")
    logger.info(
        "Production logging initialized",
        extra={
            "log_level": log_level,
            "log_file": log_file,
            "structured": enable_structured,
            "alerting": bool(webhook_url)
        }
    )

def configure_specific_loggers():
    """Configure logging for specific components"""
    
    # P&L Card System
    pnl_logger = logging.getLogger("src.social")
    pnl_logger.setLevel(logging.INFO)
    
    # Database operations
    db_logger = logging.getLogger("src.database")
    db_logger.setLevel(logging.INFO)
    
    # API routes
    api_logger = logging.getLogger("src.api")
    api_logger.setLevel(logging.INFO)
    
    # HTTP client (reduce verbosity)
    http_logger = logging.getLogger("src.http_client")
    http_logger.setLevel(logging.WARNING)
    
    # External libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)

class LogMetrics:
    """Simple metrics collection for logging"""
    
    def __init__(self):
        self.metrics = {
            'total_logs': 0,
            'error_count': 0,
            'warning_count': 0,
            'pnl_card_requests': 0,
            'database_queries': 0,
            'api_requests': 0
        }
    
    def increment(self, metric: str):
        """Increment a metric counter"""
        if metric in self.metrics:
            self.metrics[metric] += 1
    
    def get_metrics(self) -> Dict[str, int]:
        """Get current metrics"""
        return self.metrics.copy()
    
    def reset(self):
        """Reset all metrics"""
        for key in self.metrics:
            self.metrics[key] = 0

# Global metrics instance
log_metrics = LogMetrics()

class MetricsFilter(logging.Filter):
    """Filter that collects metrics"""
    
    def filter(self, record: logging.LogRecord) -> bool:
        log_metrics.increment('total_logs')
        
        if record.levelno >= logging.ERROR:
            log_metrics.increment('error_count')
        elif record.levelno >= logging.WARNING:
            log_metrics.increment('warning_count')
        
        # Service-specific metrics
        if 'pnl' in record.name.lower() or 'card' in record.getMessage().lower():
            log_metrics.increment('pnl_card_requests')
        elif 'database' in record.name.lower():
            log_metrics.increment('database_queries')
        elif 'api' in record.name.lower():
            log_metrics.increment('api_requests')
        
        return True

def setup_monitoring_logging():
    """Setup logging with metrics collection"""
    setup_production_logging()
    
    # Add metrics filter to all handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(MetricsFilter())

def get_log_summary() -> Dict[str, Any]:
    """Get a summary of recent log activity"""
    return {
        'metrics': log_metrics.get_metrics(),
        'timestamp': datetime.utcnow().isoformat(),
        'log_files': {
            'main': 'logs/app.log' if Path('logs/app.log').exists() else None,
            'errors': 'logs/errors.log' if Path('logs/errors.log').exists() else None,
            'pnl_cards': 'logs/pnl_cards.log' if Path('logs/pnl_cards.log').exists() else None,
        }
    }

# Example usage in main application
if __name__ == "__main__":
    # Setup production logging
    webhook_url = os.getenv('DISCORD_HEALTH_WEBHOOK_URL')
    setup_production_logging(
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        log_file='logs/app.log',
        webhook_url=webhook_url,
        enable_structured=True
    )
    
    # Test logging
    logger = logging.getLogger("test")
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")
    
    # Print metrics
    print("Log metrics:", get_log_summary())
