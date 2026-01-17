"""
Shared HTTP Client Module
Robust HTTP client with retry logic and rate limiting
"""

import asyncio
import time
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
import aiohttp
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shared.logger import get_logger


@dataclass
class HttpClientConfig:
    """Configuration for HTTP client"""
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit: int = 100  # requests per minute
    circuit_breaker_threshold: int = 5
    circuit_breaker_timeout: int = 60


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int, timeout: int):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.logger = get_logger(__name__)
    
    def call_allowed(self) -> bool:
        """Check if call is allowed based on circuit breaker state"""
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - self.last_failure_time > self.timeout:
                self.state = "HALF_OPEN"
                self.logger.info("Circuit breaker moving to HALF_OPEN state")
                return True
            return False
        else:  # HALF_OPEN
            return True
    
    def record_success(self):
        """Record a successful call"""
        if self.state == "HALF_OPEN":
            self.state = "CLOSED"
            self.failure_count = 0
            self.logger.info("Circuit breaker moving to CLOSED state")
    
    def record_failure(self):
        """Record a failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            self.logger.warning(f"Circuit breaker OPENED after {self.failure_count} failures")


class RateLimiter:
    """Simple rate limiter implementation"""
    
    def __init__(self, requests_per_minute: int):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.logger = get_logger(__name__)
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        if len(self.requests) >= self.requests_per_minute:
            # Calculate wait time
            oldest_request = min(self.requests)
            wait_time = 60 - (now - oldest_request)
            if wait_time > 0:
                self.logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
                time.sleep(wait_time)
        
        self.requests.append(now)


class AsyncHttpClient:
    """Async HTTP client with retry logic and circuit breaker"""
    
    def __init__(self, config: HttpClientConfig):
        self.config = config
        self.circuit_breaker = CircuitBreaker(
            config.circuit_breaker_threshold,
            config.circuit_breaker_timeout
        )
        self.rate_limiter = RateLimiter(config.rate_limit)
        self.logger = get_logger(__name__)
        self._session = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Close the HTTP session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    async def get(self, url: str, headers: Optional[Dict[str, str]] = None, 
                  params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make GET request with retry logic
        
        Args:
            url: Request URL
            headers: Request headers
            params: Query parameters
            
        Returns:
            Response JSON data
            
        Raises:
            Exception: If all retries fail
        """
        if not self.circuit_breaker.call_allowed():
            raise Exception("Circuit breaker is OPEN")
        
        self.rate_limiter.wait_if_needed()
        
        session = await self.get_session()
        
        for attempt in range(self.config.max_retries + 1):
            try:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        self.circuit_breaker.record_success()
                        return await response.json()
                    else:
                        error_msg = f"HTTP {response.status}: {await response.text()}"
                        if attempt == self.config.max_retries:
                            raise Exception(error_msg)
                        self.logger.warning(f"Request failed (attempt {attempt + 1}): {error_msg}")
                        
            except Exception as e:
                if attempt == self.config.max_retries:
                    self.circuit_breaker.record_failure()
                    raise
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.config.max_retries:
                    await asyncio.sleep(self.config.retry_delay * (2 ** attempt))
        
        raise Exception("Max retries exceeded")


class SyncHttpClient:
    """Synchronous HTTP client with retry logic and circuit breaker"""
    
    def __init__(self, config: HttpClientConfig):
        self.config = config
        self.circuit_breaker = CircuitBreaker(
            config.circuit_breaker_threshold,
            config.circuit_breaker_timeout
        )
        self.rate_limiter = RateLimiter(config.rate_limit)
        self.logger = get_logger(__name__)
        self._session = None
    
    def get_session(self) -> requests.Session:
        """Get or create requests session"""
        if self._session is None:
            self._session = requests.Session()
            
            # Setup retry strategy
            retry_strategy = Retry(
                total=self.config.max_retries,
                backoff_factor=self.config.retry_delay,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            
            adapter = HTTPAdapter(max_retries=retry_strategy)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
        
        return self._session
    
    def get(self, url: str, headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make GET request with retry logic
        
        Args:
            url: Request URL
            headers: Request headers
            params: Query parameters
            
        Returns:
            Response JSON data
            
        Raises:
            Exception: If all retries fail
        """
        if not self.circuit_breaker.call_allowed():
            raise Exception("Circuit breaker is OPEN")
        
        self.rate_limiter.wait_if_needed()
        
        session = self.get_session()
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = session.get(
                    url, 
                    headers=headers, 
                    params=params, 
                    timeout=self.config.timeout
                )
                
                if response.status_code == 200:
                    self.circuit_breaker.record_success()
                    return response.json()
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    if attempt == self.config.max_retries:
                        raise Exception(error_msg)
                    self.logger.warning(f"Request failed (attempt {attempt + 1}): {error_msg}")
                    
            except Exception as e:
                if attempt == self.config.max_retries:
                    self.circuit_breaker.record_failure()
                    raise
                self.logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
                if attempt < self.config.max_retries:
                    time.sleep(self.config.retry_delay * (2 ** attempt))
        
        raise Exception("Max retries exceeded")


# Default client instances
default_async_client = None
default_sync_client = None


def get_async_client(config: Optional[HttpClientConfig] = None) -> AsyncHttpClient:
    """Get default async HTTP client"""
    global default_async_client
    if default_async_client is None:
        default_async_client = AsyncHttpClient(config or HttpClientConfig())
    return default_async_client


def get_sync_client(config: Optional[HttpClientConfig] = None) -> SyncHttpClient:
    """Get default sync HTTP client"""
    global default_sync_client
    if default_sync_client is None:
        default_sync_client = SyncHttpClient(config or HttpClientConfig())
    return default_sync_client


async def close_all_clients():
    """Close all HTTP clients"""
    global default_async_client
    if default_async_client:
        await default_async_client.close()
