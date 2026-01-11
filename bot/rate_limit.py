"""
Rate limiting utilities for API requests.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import httpx

from bot.errors import AdapterError, ErrorType


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 1.0  # Max requests per second
    requests_per_minute: int = 60    # Max requests per minute
    burst_size: int = 5              # Max burst requests
    retry_after: float = 60.0        # Seconds to wait when rate limited


class RateLimiter:
    """
    Token bucket rate limiter with per-adapter tracking.
    
    Uses a token bucket algorithm:
    - Tokens are added at a fixed rate
    - Each request consumes one token
    - Burst allows temporary higher rate
    """
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._tokens: Dict[str, float] = defaultdict(lambda: config.burst_size)
        self._last_update: Dict[str, float] = defaultdict(time.time)
        self._request_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=config.requests_per_minute))
        self._lock = asyncio.Lock()
    
    async def acquire(self, adapter_name: str) -> None:
        """
        Acquire a token for the given adapter.
        Blocks if rate limit would be exceeded.
        """
        while True:
            sleep_time: float | None = None
            async with self._lock:
                now = time.time()

                # Update tokens based on time elapsed
                self._update_tokens(adapter_name, now)

                # Remove old requests (older than 1 minute)
                minute_ago = now - 60
                while self._request_times[adapter_name] and self._request_times[adapter_name][0] < minute_ago:
                    self._request_times[adapter_name].popleft()

                # Per-minute limit
                if len(self._request_times[adapter_name]) >= self.config.requests_per_minute:
                    sleep_time = max(0.0, 60.0 - (now - self._request_times[adapter_name][0]))
                # Token bucket
                elif self._tokens[adapter_name] < 1.0:
                    tokens_needed = 1.0 - self._tokens[adapter_name]
                    sleep_time = max(0.0, tokens_needed / max(self.config.requests_per_second, 0.001))
                else:
                    # Consume token
                    self._tokens[adapter_name] -= 1.0
                    self._request_times[adapter_name].append(now)
                    return

            if sleep_time is not None and sleep_time > 0:
                await asyncio.sleep(sleep_time)
    
    def _update_tokens(self, adapter_name: str, now: float) -> None:
        """Update token count based on elapsed time."""
        last_update = self._last_update[adapter_name]
        elapsed = now - last_update
        
        if elapsed > 0:
            # Add tokens based on elapsed time
            tokens_to_add = elapsed * self.config.requests_per_second
            self._tokens[adapter_name] = min(
                self._tokens[adapter_name] + tokens_to_add,
                self.config.burst_size
            )
            self._last_update[adapter_name] = now
    
    async def get_status(self, adapter_name: str) -> Dict[str, float]:
        """Get current rate limit status for an adapter."""
        async with self._lock:
            now = time.time()
            self._update_tokens(adapter_name, now)
            
            recent_requests = len([
                t for t in self._request_times[adapter_name]
                if now - t < 60
            ])
            
            return {
                "available_tokens": self._tokens[adapter_name],
                "max_tokens": self.config.burst_size,
                "requests_last_minute": recent_requests,
                "max_requests_per_minute": self.config.requests_per_minute,
                "requests_per_second": self.config.requests_per_second
            }


class RateLimitedClient:
    """
    HTTP client with built-in rate limiting.
    Wraps httpx.AsyncClient with rate limiting per adapter.
    """
    
    def __init__(self, base_client: httpx.AsyncClient, rate_limiter: RateLimiter):
        self.client = base_client
        self.rate_limiter = rate_limiter
    
    async def get(self, adapter_name: str, url: str, **kwargs) -> httpx.Response:
        """Rate-limited GET request."""
        await self.rate_limiter.acquire(adapter_name)
        return await self.client.get(url, **kwargs)
    
    async def post(self, adapter_name: str, url: str, **kwargs) -> httpx.Response:
        """Rate-limited POST request."""
        await self.rate_limiter.acquire(adapter_name)
        return await self.client.post(url, **kwargs)
    
    async def request(self, adapter_name: str, method: str, url: str, **kwargs) -> httpx.Response:
        """Rate-limited generic request."""
        await self.rate_limiter.acquire(adapter_name)
        return await self.client.request(method, url, **kwargs)


# Default rate limit configurations per adapter
DEFAULT_RATE_LIMITS = {
    "manifold": RateLimitConfig(
        requests_per_second=2.0,
        requests_per_minute=120,
        burst_size=10,
        retry_after=30.0
    ),
    "kalshi": RateLimitConfig(
        requests_per_second=1.0,
        requests_per_minute=60,
        burst_size=5,
        retry_after=60.0
    ),
    "metaculus": RateLimitConfig(
        requests_per_second=1.5,
        requests_per_minute=90,
        burst_size=8,
        retry_after=45.0
    ),
    "polymarket": RateLimitConfig(
        requests_per_second=3.0,
        requests_per_minute=180,
        burst_size=15,
        retry_after=30.0
    ),
    "limitless": RateLimitConfig(
        requests_per_second=2.5,
        requests_per_minute=150,
        burst_size=12,
        retry_after=30.0
    )
}


# Global rate limiter instance
_global_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        # Create with default config (can be overridden)
        _global_rate_limiter = RateLimiter(RateLimitConfig(
            requests_per_second=2.0,
            requests_per_minute=120,
            burst_size=10,
            retry_after=30.0
        ))
    return _global_rate_limiter


def get_adapter_rate_limit(adapter_name: str) -> RateLimitConfig:
    """Get rate limit config for a specific adapter."""
    return DEFAULT_RATE_LIMITS.get(adapter_name, RateLimitConfig())


def create_rate_limited_client(
    adapter_name: str,
    timeout: float = 20.0,
    custom_config: Optional[RateLimitConfig] = None
) -> RateLimitedClient:
    """
    Create a rate-limited HTTP client for an adapter.
    
    Args:
        adapter_name: Name of the adapter
        timeout: Request timeout in seconds
        custom_config: Optional custom rate limit config
        
    Returns:
        RateLimitedClient instance
    """
    # Get rate limit config
    config = custom_config or get_adapter_rate_limit(adapter_name)
    
    # Create rate limiter for this adapter
    rate_limiter = RateLimiter(config)
    
    # Create HTTP client
    http_client = httpx.AsyncClient(timeout=timeout)
    
    # Wrap with rate limiting
    return RateLimitedClient(http_client, rate_limiter)


class RateLimitMiddleware:
    """
    Middleware for handling rate limit responses from APIs.
    Automatically retries with appropriate delays.
    """
    
    @staticmethod
    async def handle_response(
        response: httpx.Response,
        adapter_name: str,
        attempt: int = 1,
        max_attempts: int = 3
    ) -> httpx.Response:
        """
        Handle HTTP response, retrying on rate limits.
        
        Args:
            response: HTTP response to check
            adapter_name: Name of the adapter for logging
            attempt: Current attempt number
            max_attempts: Maximum retry attempts
            
        Returns:
            Final response (possibly after retries)
            
        Raises:
            AdapterError: If rate limit persists after max attempts
        """
        if response.status_code != 429:
            return response
        
        # Extract retry-after header if present
        retry_after = response.headers.get("retry-after")
        if retry_after:
            try:
                retry_seconds = float(retry_after)
            except ValueError:
                retry_seconds = 60.0  # Default
        else:
            # Use default retry time for this adapter
            config = get_adapter_rate_limit(adapter_name)
            retry_seconds = config.retry_after
        
        if attempt >= max_attempts:
            raise AdapterError(
                f"Rate limit persisted after {max_attempts} attempts for {adapter_name}",
                ErrorType.RATE_LIMIT,
                adapter_name=adapter_name,
                status_code=429
            )
        
        # Wait and retry (in a real implementation, this would need the original request)
        await asyncio.sleep(retry_seconds)
        
        # Note: In practice, this would need to re-execute the original request
        # This is a simplified version showing the concept
        raise AdapterError(
            f"Rate limited by {adapter_name} API. "
            f"Retry after {retry_seconds}s (attempt {attempt}/{max_attempts})",
            ErrorType.RATE_LIMIT,
            adapter_name=adapter_name,
            status_code=429
        )
