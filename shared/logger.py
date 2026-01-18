"""
Shared Logger Module
Centralized logging configuration for the entire system
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

import yaml


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
        
        import json
        return json.dumps(log_entry)


class SimpleFormatter(logging.Formatter):
    """Simple formatter for development"""
    
    def __init__(self):
        super().__init__(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


def setup_logging(config_path: str = "config.yaml") -> None:
    """
    Setup centralized logging configuration
    
    Args:
        config_path: Path to config file
    """
    # Load config
    config = load_config(config_path)
    
    # Handle None config gracefully
    if config is None:
        config = {
            'logging': {
                'level': 'INFO',
                'format': 'simple',
                'file_path': 'data/logs/cpm.log',
                'enable_console': True
            }
        }
    
    log_config = config.get('logging', {})
    
    # Create logs directory
    log_file = log_config.get('file_path', 'data/logs/cpm.log')
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Choose formatter
    formatter_type = log_config.get('format', 'simple')
    if formatter_type == 'structured':
        formatter = StructuredFormatter()
    else:
        formatter = SimpleFormatter()
    
    # File handler with rotation
    if log_file:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=log_config.get('max_file_size', 10485760),  # 10MB
            backupCount=log_config.get('backup_count', 5)
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Console handler
    if log_config.get('enable_console', True):
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('aiohttp').setLevel(logging.WARNING)


def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            # Handle empty YAML file (returns None)
            if config is None:
                config = {}
            return config
    except FileNotFoundError:
        # Return default config if file not found
        return {
            'logging': {
                'level': 'INFO',
                'format': 'simple',
                'file_path': 'data/logs/cpm.log',
                'enable_console': True
            }
        }
    except Exception:
        # Return default config on any error
        return {
            'logging': {
                'level': 'INFO',
                'format': 'simple',
                'file_path': 'data/logs/cpm.log',
                'enable_console': True
            }
        }


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class"""
    
    @property
    def logger(self) -> logging.Logger:
        """Get logger for this class"""
        return get_logger(self.__class__.__module__ + '.' + self.__class__.__name__)


def log_function_call(func):
    """Decorator to log function calls"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"Calling {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed with error: {e}")
            raise
    return wrapper


def log_performance(func):
    """Decorator to log function performance"""
    import time
    
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.2f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"{func.__name__} failed after {execution_time:.2f}s: {e}")
            raise
    return wrapper


# Initialize logging when module is imported
setup_logging()
