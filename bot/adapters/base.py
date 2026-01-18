"""
Base Adapter Class
Abstract base class for all platform adapters
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime

from bot.models import Market, Quote, Platform
from shared.logger import get_logger
from shared.http_client import AsyncHttpClient, SyncHttpClient


class BaseAdapter(ABC):
    """Abstract base class for platform adapters"""
    
    def __init__(self, platform: Platform, config: Dict[str, Any]):
        self.platform = platform
        self.config = config
        self.logger = get_logger(f"{__name__}.{platform.value}")
        
        # Initialize HTTP clients
        http_config = {
            'timeout': config.get('timeout', 30),
            'max_retries': config.get('retry_attempts', 3),
            'retry_delay': config.get('retry_delay', 1),
            'rate_limit': config.get('rate_limit', 100)
        }
        self.async_client = AsyncHttpClient(http_config)
        self.sync_client = SyncHttpClient(http_config)
    
    @abstractmethod
    async def fetch_markets(self) -> List[Market]:
        """
        Fetch all markets from the platform
        
        Returns:
            List of Market objects
        """
        pass
    
    @abstractmethod
    async def fetch_quotes(self, market_ids: List[str]) -> List[Quote]:
        """
        Fetch quotes for specific markets
        
        Args:
            market_ids: List of market IDs to fetch quotes for
            
        Returns:
            List of Quote objects
        """
        pass
    
    @abstractmethod
    def get_market_url(self, market_id: str) -> str:
        """
        Get platform-specific URL for a market
        
        Args:
            market_id: Market ID
            
        Returns:
            Market URL
        """
        pass
    
    @abstractmethod
    def normalize_market_title(self, title: str) -> str:
        """
        Normalize market title for cross-platform matching
        
        Args:
            title: Raw market title
            
        Returns:
            Normalized title
        """
        pass
    
    async def health_check(self) -> bool:
        """
        Check if the platform API is healthy
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to fetch a small number of markets as health check
            markets = await self.fetch_markets()
            return len(markets) > 0
        except Exception as e:
            self.logger.error(f"Health check failed for {self.platform.value}: {e}")
            return False
    
    def is_enabled(self) -> bool:
        """Check if this adapter is enabled"""
        return self.config.get('enabled', False)
    
    def get_rate_limit(self) -> int:
        """Get rate limit for this platform"""
        return self.config.get('rate_limit', 100)
    
    async def close(self):
        """Close HTTP clients"""
        await self.async_client.close()
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(platform={self.platform.value})"


class Adapter:
    """Simple adapter base class for adapters that don't use BaseAdapter"""
    name: str = "unknown"
    
    async def list_active_markets(self):
        raise NotImplementedError
    
    async def list_outcomes(self, market):
        raise NotImplementedError
    
    async def get_quotes(self, market, outcomes):
        raise NotImplementedError
