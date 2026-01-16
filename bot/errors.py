"""
Error handling utilities for the crypto prediction monitor bot.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, Union

import httpx

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorType(Enum):
    """Categories of errors for different handling strategies."""
    NETWORK = "network"  # Network issues, timeouts, DNS
    RATE_LIMIT = "rate_limit"  # API rate limits (HTTP 429)
    SERVER_ERROR = "server_error"  # Server errors (5xx)
    CLIENT_ERROR = "client_error"  # Client errors (4xx, except 429)
    DATA_ERROR = "data_error"  # Malformed data, validation errors
    CONFIG_ERROR = "config_error"  # Configuration issues
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Structured error information."""
    error_type: ErrorType
    message: str
    adapter_name: Optional[str] = None
    market_id: Optional[str] = None
    status_code: Optional[int] = None
    retry_count: int = 0
    timestamp: float = field(default_factory=time.time)
    context: dict[str, Any] = field(default_factory=dict)


class AdapterError(Exception):
    """Base class for adapter errors."""
    def __init__(self, message: str, error_type: ErrorType = ErrorType.UNKNOWN, **kwargs):
        super().__init__(message)
        # Filter out kwargs that match ErrorInfo fields
        info_kwargs = {k: v for k, v in kwargs.items() if k in ErrorInfo.__dataclass_fields__}
        self.error_info = ErrorInfo(
            error_type=error_type,
            message=message,
            **info_kwargs
        )


class RetryableError(AdapterError):
    """Transient errors that should be retried."""
    pass


class FatalError(AdapterError):
    """Permanent errors that shouldn't be retried."""
    pass


def classify_http_error(response: httpx.Response) -> ErrorType:
    """Classify HTTP response into error type."""
    status = response.status_code
    
    if status == 429:
        return ErrorType.RATE_LIMIT
    elif 500 <= status < 600:
        return ErrorType.SERVER_ERROR
    elif 400 <= status < 500:
        return ErrorType.CLIENT_ERROR
    else:
        return ErrorType.UNKNOWN


def classify_exception(exc: Exception) -> ErrorType:
    """Classify exception into error type."""
    if isinstance(exc, httpx.TimeoutException):
        return ErrorType.NETWORK
    elif isinstance(exc, httpx.NetworkError):
        return ErrorType.NETWORK
    elif isinstance(exc, httpx.HTTPStatusError):
        return classify_http_error(exc.response)
    elif isinstance(exc, (ValueError, TypeError, KeyError)):
        return ErrorType.DATA_ERROR
    elif isinstance(exc, (FileNotFoundError, PermissionError)):
        return ErrorType.CONFIG_ERROR
    else:
        return ErrorType.UNKNOWN


def should_retry(error_info: ErrorInfo) -> bool:
    """Determine if an error should be retried."""
    # Don't retry client errors (except rate limits)
    if error_info.error_type == ErrorType.CLIENT_ERROR:
        return False
    
    # Retry network errors, rate limits, server errors
    if error_info.error_type in [ErrorType.NETWORK, ErrorType.RATE_LIMIT, ErrorType.SERVER_ERROR]:
        return True
    
    # Retry data errors a few times (might be temporary API issues)
    if error_info.error_type == ErrorType.DATA_ERROR and error_info.retry_count < 2:
        return True
    
    return False


def get_retry_delay(error_info: ErrorInfo) -> float:
    """Calculate retry delay based on error type and attempt count."""
    base_delay = 1.0
    
    if error_info.error_type == ErrorType.RATE_LIMIT:
        # Exponential backoff for rate limits, start at 5 seconds
        return min(5.0 * (2 ** error_info.retry_count), 60.0)
    elif error_info.error_type == ErrorType.SERVER_ERROR:
        # Server errors: 2, 4, 8 seconds
        return base_delay * (2 ** error_info.retry_count)
    elif error_info.error_type == ErrorType.NETWORK:
        # Network errors: 1, 2, 4 seconds
        return base_delay * (2 ** error_info.retry_count)
    else:
        # Default: 1 second
        return base_delay


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = 3,
    adapter_name: Optional[str] = None,
    market_id: Optional[str] = None,
    **kwargs
) -> T:
    """
    Execute function with exponential backoff retry logic.
    
    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        adapter_name: Name of the adapter for logging
        market_id: Market ID for context
        
    Returns:
        Result of the function call
        
    Raises:
        AdapterError: If all retries are exhausted
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            error_type = classify_exception(exc)
            
            # Create error info
            error_info = ErrorInfo(
                error_type=error_type,
                message=str(exc),
                adapter_name=adapter_name,
                market_id=market_id,
                retry_count=attempt,
                status_code=getattr(exc.response, "status_code", None) if hasattr(exc, "response") else None
            )
            
            # Log the error
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries + 1} failed for {adapter_name}: {exc}"
            )
            
            # Check if we should retry
            if attempt == max_retries or not should_retry(error_info):
                # Log final failure
                logger.error(
                    f"Final failure for {adapter_name}: {exc} "
                    f"(attempts: {attempt + 1}, error_type: {error_type.value})"
                )
                
                # Raise appropriate error type
                if error_type in [ErrorType.CLIENT_ERROR, ErrorType.CONFIG_ERROR]:
                    raise FatalError(str(exc), error_type, **error_info.__dict__) from exc
                else:
                    raise RetryableError(str(exc), error_type, **error_info.__dict__) from exc
            
            # Calculate delay and wait
            delay = get_retry_delay(error_info)
            logger.info(f"Retrying {adapter_name} in {delay:.1f}s...")
            await asyncio.sleep(delay)
            
            last_error = exc
    
    # This should never be reached, but just in case
    raise RetryableError(str(last_error or "Unknown error"))


async def safe_http_request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs
) -> httpx.Response:
    """
    Make HTTP request with better error handling.
    
    Args:
        client: httpx async client
        method: HTTP method
        url: Request URL
        **kwargs: Additional request parameters
        
    Returns:
        httpx.Response object
        
    Raises:
        AdapterError: For various HTTP errors
    """
    try:
        response = await client.request(method, url, **kwargs)
        return response
    except httpx.TimeoutException as exc:
        raise AdapterError(f"Request timeout: {url}", ErrorType.NETWORK) from exc
    except httpx.NetworkError as exc:
        raise AdapterError(f"Network error: {url} - {exc}", ErrorType.NETWORK) from exc
    except Exception as exc:
        raise AdapterError(f"Unexpected error: {url} - {exc}", ErrorType.UNKNOWN) from exc


async def safe_http_get(
    client: httpx.AsyncClient,
    url: str,
    **kwargs
) -> httpx.Response:
    """Safe HTTP GET with error handling."""
    response = await safe_http_request(client, "GET", url, **kwargs)
    
    # Handle HTTP status codes
    if response.status_code == 429:
        raise AdapterError(
            f"Rate limited: {url}",
            ErrorType.RATE_LIMIT,
            status_code=response.status_code
        )
    elif 500 <= response.status_code < 600:
        raise AdapterError(
            f"Server error: {url} - {response.status_code}",
            ErrorType.SERVER_ERROR,
            status_code=response.status_code
        )
    elif 400 <= response.status_code < 500:
        raise AdapterError(
            f"Client error: {url} - {response.status_code}",
            ErrorType.CLIENT_ERROR,
            status_code=response.status_code
        )
    
    return response


def log_error_metrics(error_info: ErrorInfo) -> None:
    """Log error metrics for monitoring."""
    # This could be extended to send to monitoring systems
    logger.info(
        f"ERROR_METRIC: {error_info.error_type.value} "
        f"adapter={error_info.adapter_name} "
        f"status={error_info.status_code} "
        f"retries={error_info.retry_count}"
    )
