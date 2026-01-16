"""
Event Image Extractor for Discord Alert Thumbnails
Extracts event images from market data with platform-specific fallbacks
"""

import re
from typing import Optional
from .event_link_generator import NormalizedMarket


class EventImageExtractor:
    """Extract event images from market data"""
    
    @staticmethod
    def extract_image_url(market: NormalizedMarket) -> Optional[str]:
        """
        Extract image URL from market source
        
        Args:
            market: NormalizedMarket object with platform details
            
        Returns:
            Full URL to event image or None
        """
        
        if market.source == 'polymarket':
            return EventImageExtractor._polymarket_image(market)
        
        elif market.source == 'manifold':
            return EventImageExtractor._manifold_image(market)
        
        elif market.source == 'limitless':
            return EventImageExtractor._limitless_image(market)
        
        elif market.source.startswith('azuro'):
            return EventImageExtractor._azuro_image(market)
        
        return None
    
    @staticmethod
    def _polymarket_image(market: NormalizedMarket) -> Optional[str]:
        """
        Polymarket image extraction
        
        Polymarket markets usually have high-quality event images
        """
        # Try primary image URL first
        if market.image_url and EventImageExtractor._is_valid_image_url(market.image_url):
            return market.image_url
        
        # Try thumbnail URL as backup
        if market.thumbnail_url and EventImageExtractor._is_valid_image_url(market.thumbnail_url):
            return market.thumbnail_url
        
        # Polymarket fallback - use their logo
        return "https://polymarket.com/_next/static/media/logo.6e5b8c8e.svg"
    
    @staticmethod
    def _manifold_image(market: NormalizedMarket) -> Optional[str]:
        """
        Manifold image extraction
        
        Manifold markets have built-in images or use platform defaults
        """
        # Try primary image URL first
        if market.image_url and EventImageExtractor._is_valid_image_url(market.image_url):
            return market.image_url
        
        # Try thumbnail URL as backup
        if market.thumbnail_url and EventImageExtractor._is_valid_image_url(market.thumbnail_url):
            return market.thumbnail_url
        
        # Manifold fallback - use their logo
        return "https://manifold.markets/logo.png"
    
    @staticmethod
    def _limitless_image(market: NormalizedMarket) -> Optional[str]:
        """
        Limitless image extraction
        
        Limitless markets may have images or use platform defaults
        """
        # Try primary image URL first
        if market.image_url and EventImageExtractor._is_valid_image_url(market.image_url):
            return market.image_url
        
        # Try thumbnail URL as backup
        if market.thumbnail_url and EventImageExtractor._is_valid_image_url(market.thumbnail_url):
            return market.thumbnail_url
        
        # Limitless fallback - use their logo
        return "https://limitless.exchange/logo.png"
    
    @staticmethod
    def _azuro_image(market: NormalizedMarket) -> Optional[str]:
        """
        Azuro image extraction
        
        Azuro might not have event images - use chain logos or category fallbacks
        """
        # Try primary image URL first
        if market.image_url and EventImageExtractor._is_valid_image_url(market.image_url):
            return market.image_url
        
        # Try thumbnail URL as backup
        if market.thumbnail_url and EventImageExtractor._is_valid_image_url(market.thumbnail_url):
            return market.thumbnail_url
        
        # Fallback to chain logo
        chain = market.chain or 'polygon'
        chain_logos = {
            'polygon': 'https://cryptologos.cc/logos/polygon-matic-logo.png',
            'gnosis': 'https://cryptologos.cc/logos/gnosis-gno-logo.png',
            'base': 'https://cryptologos.cc/logos/base-logo.png',
            'chiliz': 'https://cryptologos.cc/logos/chiliz-chz-logo.png',
            'arbitrum': 'https://cryptologos.cc/logos/arbitrum-arb-logo.png',
            'optimism': 'https://cryptologos.cc/logos/optimism-op-logo.png',
        }
        
        return chain_logos.get(chain.lower())
    
    @staticmethod
    def get_fallback_image(market_category: str) -> str:
        """
        Get fallback image based on market category
        
        Args:
            market_category: 'crypto', 'sports', 'politics', 'event', etc.
        
        Returns:
            URL to fallback image
        """
        
        fallback_images = {
            'crypto': 'https://cryptologos.cc/logos/bitcoin-btc-logo.png',
            'sports': 'https://via.placeholder.com/200x200/4CAF50/FFFFFF?text=SPORTS',
            'politics': 'https://via.placeholder.com/200x200/2196F3/FFFFFF?text=POLITICS',
            'election': 'https://via.placeholder.com/200x200/2196F3/FFFFFF?text=ELECTION',
            'finance': 'https://via.placeholder.com/200x200/FF9800/FFFFFF?text=FINANCE',
            'entertainment': 'https://via.placeholder.com/200x200/9C27B0/FFFFFF?text=ENTERTAINMENT',
            'technology': 'https://via.placeholder.com/200x200/607D8B/FFFFFF?text=TECHNOLOGY',
            'event': 'https://via.placeholder.com/200x200/795548/FFFFFF?text=EVENT',
            'default': 'https://via.placeholder.com/200x200/9E9E9E/FFFFFF?text=PREDICTION+MARKET',
        }
        
        return fallback_images.get(market_category.lower(), fallback_images['default'])
    
    @staticmethod
    def get_thumbnail_with_fallback(market: NormalizedMarket) -> str:
        """
        Get thumbnail URL with fallback logic
        
        Args:
            market: NormalizedMarket object
            
        Returns:
            URL to thumbnail image (always returns something)
        """
        # Try to extract image from market
        image_url = EventImageExtractor.extract_image_url(market)
        
        if image_url:
            return image_url
        
        # Use category-based fallback
        category = market.category or 'default'
        return EventImageExtractor.get_fallback_image(category)
    
    @staticmethod
    def _is_valid_image_url(url: str) -> bool:
        """
        Check if URL is a valid image URL
        
        Args:
            url: URL to check
            
        Returns:
            True if valid image URL
        """
        if not url or not isinstance(url, str):
            return False
        
        # Check if it looks like an image URL
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
        url_lower = url.lower()
        
        # Check for image extensions
        for ext in image_extensions:
            if url_lower.endswith(ext):
                return True
        
        # Check for common image hosting patterns
        image_patterns = [
            'i.imgur.com',
            'images.unsplash.com',
            'cdn.pixabay.com',
            'cryptologos.cc',
            'via.placeholder.com',
            'polymarket.com',
            'manifold.markets',
            'limitless.exchange',
            'gem.azuro.org'
        ]
        
        for pattern in image_patterns:
            if pattern in url_lower:
                return True
        
        return False
    
    @staticmethod
    def create_from_opportunity(opportunity: dict) -> str:
        """
        Convenience method to get thumbnail URL directly from opportunity dict
        
        Args:
            opportunity: Dictionary containing market data
            
        Returns:
            URL to thumbnail image (always returns something)
        """
        from .event_link_generator import EventLinkGenerator
        
        market = EventLinkGenerator.create_from_opportunity(opportunity)
        return EventImageExtractor.get_thumbnail_with_fallback(market)


# Test cases for validation
def test_image_extraction():
    """Test image extraction for different platforms"""
    
    # Test Polymarket
    polymarket_market = NormalizedMarket(
        source='polymarket',
        market_id='donald-trump-election',
        image_url='https://polymarket.com/images/trump.jpg',
        category='politics'
    )
    print(f"Polymarket: {EventImageExtractor.get_thumbnail_with_fallback(polymarket_market)}")
    
    # Test Manifold
    manifold_market = NormalizedMarket(
        source='manifold',
        market_id='will-biden-win',
        category='politics'
    )
    print(f"Manifold: {EventImageExtractor.get_thumbnail_with_fallback(manifold_market)}")
    
    # Test Azuro
    azuro_market = NormalizedMarket(
        source='azuro',
        market_id='0x123456',
        chain='polygon',
        category='crypto'
    )
    print(f"Azuro: {EventImageExtractor.get_thumbnail_with_fallback(azuro_market)}")
    
    # Test fallback
    unknown_market = NormalizedMarket(
        source='unknown',
        market_id='test',
        category='sports'
    )
    print(f"Unknown: {EventImageExtractor.get_thumbnail_with_fallback(unknown_market)}")


if __name__ == "__main__":
    test_image_extraction()
