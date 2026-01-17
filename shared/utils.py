"""
Shared Utilities Module
Common helper functions and utilities
"""

import os
import re
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from shared.logger import get_logger


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison
    
    Args:
        text: Input text
        
    Returns:
        Normalized text (lowercase, trimmed, special chars removed)
    """
    if not text:
        return ""
    
    # Convert to lowercase and trim
    normalized = text.lower().strip()
    
    # Remove special characters except spaces and hyphens
    normalized = re.sub(r'[^\w\s\-]', ' ', normalized)
    
    # Replace multiple spaces with single space
    normalized = re.sub(r'\s+', ' ', normalized)
    
    return normalized.strip()


def calculate_spread_percentage(bid_price: float, ask_price: float) -> float:
    """
    Calculate spread percentage between bid and ask prices
    
    Args:
        bid_price: Bid price
        ask_price: Ask price
        
    Returns:
        Spread percentage
    """
    if bid_price <= 0 or ask_price <= 0:
        return 0.0
    
    spread = ask_price - bid_price
    mid_price = (bid_price + ask_price) / 2
    return (spread / mid_price) * 100


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    Format a value as percentage
    
    Args:
        value: Value to format
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    return f"{value:.{decimals}f}%"


def format_currency(value: float, currency: str = "USD") -> str:
    """
    Format a value as currency
    
    Args:
        value: Value to format
        currency: Currency code
        
    Returns:
        Formatted currency string
    """
    return f"{currency} {value:,.2f}"


def generate_hash(data: Union[str, Dict[str, Any]]) -> str:
    """
    Generate SHA256 hash for data
    
    Args:
        data: Data to hash
        
    Returns:
        Hexadecimal hash string
    """
    if isinstance(data, dict):
        data = json.dumps(data, sort_keys=True)
    
    return hashlib.sha256(data.encode()).hexdigest()


def ensure_directory(path: Union[str, Path]) -> Path:
    """
    Ensure directory exists, create if necessary
    
    Args:
        path: Directory path
        
    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_env_var(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Load environment variable with optional default
    
    Args:
        name: Environment variable name
        default: Default value if not found
        
    Returns:
        Environment variable value or default
    """
    value = os.getenv(name)
    return value if value is not None else default


def validate_url(url: str) -> bool:
    """
    Validate URL format
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid URL, False otherwise
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return url_pattern.match(url) is not None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file system usage
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return sanitized or "unnamed"


def parse_datetime(datetime_str: str) -> Optional[datetime]:
    """
    Parse datetime string in various formats
    
    Args:
        datetime_str: Datetime string
        
    Returns:
        Parsed datetime or None if invalid
    """
    if not datetime_str:
        return None
    
    # Common datetime formats
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%d',
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(datetime_str, fmt)
            # Add timezone if missing
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    
    return None


def chunks(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split list into chunks
    
    Args:
        lst: List to split
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Flatten nested dictionary
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator between keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def retry_on_exception(max_retries: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Decorator to retry function on exception
    
    Args:
        max_retries: Maximum number of retries
        delay: Delay between retries
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    logger.warning(f"Function {func.__name__} failed (attempt {attempt + 1}): {e}")
                    import time
                    time.sleep(delay * (2 ** attempt))
        return wrapper
    return decorator


def cache_result(ttl_seconds: int = 300):
    """
    Decorator to cache function result
    
    Args:
        ttl_seconds: Time to live in seconds
    """
    def decorator(func):
        cache = {}
        
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            
            # Create cache key
            cache_key = str(args) + str(sorted(kwargs.items()))
            current_time = datetime.now().timestamp()
            
            # Check cache
            if cache_key in cache:
                result, timestamp = cache[cache_key]
                if current_time - timestamp < ttl_seconds:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache[cache_key] = (result, current_time)
            logger.debug(f"Cached result for {func.__name__}")
            
            return result
        
        return wrapper
    return decorator


class Timer:
    """Simple timer context manager"""
    
    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time = None
        self.logger = get_logger(__name__)
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Started {self.name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            self.logger.info(f"{self.name} completed in {elapsed.total_seconds():.2f}s")
    
    def elapsed(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0


def safe_get(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary value
    
    Args:
        data: Dictionary to get value from
        key_path: Dot-separated key path (e.g., 'user.profile.name')
        default: Default value if key not found
        
    Returns:
        Value or default
    """
    keys = key_path.split('.')
    current = data
    
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default
