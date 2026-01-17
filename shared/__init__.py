"""
Shared Utilities Module
Common functionality across the entire system
"""

from .logger import get_logger, setup_logging, LoggerMixin
from .http_client import get_async_client, get_sync_client, close_all_clients
from .utils import (
    normalize_text, calculate_spread_percentage, format_percentage,
    format_currency, generate_hash, ensure_directory, load_env_var,
    validate_url, sanitize_filename, parse_datetime, chunks,
    flatten_dict, retry_on_exception, cache_result, Timer, safe_get
)

__all__ = [
    'get_logger', 'setup_logging', 'LoggerMixin',
    'get_async_client', 'get_sync_client', 'close_all_clients',
    'normalize_text', 'calculate_spread_percentage', 'format_percentage',
    'format_currency', 'generate_hash', 'ensure_directory', 'load_env_var',
    'validate_url', 'sanitize_filename', 'parse_datetime', 'chunks',
    'flatten_dict', 'retry_on_exception', 'cache_result', 'Timer', 'safe_get'
]
