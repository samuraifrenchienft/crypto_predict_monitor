"""
Event Link Generator for Cross-Platform Market URLs
Generates correct market links for Polymarket, Manifold, Limitless, and Azuro
"""

import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class NormalizedMarket:
    """Normalized market data for URL generation"""
    source: str  # 'polymarket', 'manifold', 'limitless', 'azuro'
    market_id: str  # Platform-specific market ID
    chain: Optional[str] = None  # For Azuro (polygon, gnosis, base, etc.)
    slug: Optional[str] = None  # For Manifold market slugs
    image_url: Optional[str] = None  # Event image from market
    thumbnail_url: Optional[str] = None  # Backup image
    category: Optional[str] = None  # Market category for fallback images


class EventLinkGenerator:
    """Generate correct market links for each platform"""
    
    @staticmethod
    def generate_event_url(market: NormalizedMarket) -> str:
        """
        Generate correct URL based on market source/platform
        
        Args:
            market: NormalizedMarket object with platform details
            
        Returns:
            Full URL to event on the market platform
        """
        
        if market.source == 'polymarket':
            return EventLinkGenerator._polymarket_url(market)
        elif market.source == 'manifold':
            return EventLinkGenerator._manifold_url(market)
        elif market.source == 'limitless':
            return EventLinkGenerator._limitless_url(market)
        elif market.source.startswith('azuro'):
            return EventLinkGenerator._azuro_url(market)
        else:
            return '#'  # Fallback for unknown platforms
    
    @staticmethod
    def _polymarket_url(market: NormalizedMarket) -> str:
        """
        Polymarket URL format:
        https://polymarket.com/market/EVENT-ID
        or
        https://polymarket.com/event/EVENT-ID
        
        market.market_id should contain the event ID
        """
        # Clean the market ID - remove any prefixes or colons
        event_id = market.market_id.split(':')[-1] if ':' in market.market_id else market.market_id
        
        # Remove any URL prefixes if they exist
        event_id = re.sub(r'.*market/|.*event/', '', event_id)
        
        # Try both market and event URL formats
        if event_id and len(event_id) > 5:
            return f"https://polymarket.com/market/{event_id}"
        else:
            return f"https://polymarket.com"
    
    @staticmethod
    def _manifold_url(market: NormalizedMarket) -> str:
        """
        Manifold URL format:
        https://manifold.markets/CREATOR/MARKET-SLUG
        
        market.market_id contains the slug or full URL
        """
        # Extract slug from market_id
        slug = market.slug or market.market_id
        
        # If it's already a full URL, return as-is
        if slug.startswith('https://'):
            return slug
        
        # Clean the slug
        slug = slug.strip('/')
        
        # Remove any existing domain prefix
        slug = re.sub(r'.*manifold\.markets/', '', slug)
        
        if slug and len(slug) > 3:
            return f"https://manifold.markets/{slug}"
        else:
            return f"https://manifold.markets"
    
    @staticmethod
    def _limitless_url(market: NormalizedMarket) -> str:
        """
        Limitless URL format:
        https://limitless.exchange/market/MARKET-ID
        
        market.market_id contains the market ID
        """
        market_id = market.market_id.strip('/')
        
        # Remove any URL prefixes if they exist
        market_id = re.sub(r'.*limitless\.exchange/market/', '', market_id)
        
        if market_id and len(market_id) > 5:
            return f"https://limitless.exchange/market/{market_id}"
        else:
            return f"https://limitless.exchange"
    
    @staticmethod
    def _azuro_url(market: NormalizedMarket) -> str:
        """
        Azuro URL format depends on chain:
        https://gem.azuro.org/hub/market/MARKET-ID
        
        Add chain to URL for clarity
        """
        market_id = market.market_id.strip('/')
        chain = market.chain or 'polygon'
        
        # Remove any URL prefixes if they exist
        market_id = re.sub(r'.*gem\.azuro\.org/hub/market/', '', market_id)
        
        # Map chain names
        chain_map = {
            'polygon': 'polygon',
            'gnosis': 'gnosis', 
            'base': 'base',
            'chiliz': 'chiliz',
            'arbitrum': 'arbitrum',
            'optimism': 'optimism'
        }
        
        chain_name = chain_map.get(chain.lower(), chain.lower())
        
        if market_id and len(market_id) > 5:
            return f"https://gem.azuro.org/hub/market/{market_id}?chain={chain_name}"
        else:
            return f"https://gem.azuro.org"
    
    @staticmethod
    def create_from_opportunity(opportunity: dict) -> NormalizedMarket:
        """
        Create NormalizedMarket from opportunity dictionary
        
        Args:
            opportunity: Dictionary containing market data
            
        Returns:
            NormalizedMarket object
        """
        # Extract platform/source
        source = opportunity.get('source', opportunity.get('platform', 'unknown')).lower()
        
        # Extract market ID
        market_id = opportunity.get('market_id', opportunity.get('id', ''))
        
        # Extract chain for Azuro
        chain = opportunity.get('chain', opportunity.get('network', 'polygon'))
        
        # Extract slug for Manifold
        slug = opportunity.get('slug', opportunity.get('market_slug', ''))
        
        # Extract image URLs
        image_url = opportunity.get('image_url', opportunity.get('image', opportunity.get('thumbnail', None)))
        thumbnail_url = opportunity.get('thumbnail_url', opportunity.get('thumbnail', None))
        
        # Extract category for fallback images
        category = opportunity.get('category', opportunity.get('market_category', 'default'))
        
        return NormalizedMarket(
            source=source,
            market_id=market_id,
            chain=chain,
            slug=slug,
            image_url=image_url,
            thumbnail_url=thumbnail_url,
            category=category
        )
    
    @staticmethod
    def generate_url_from_opportunity(opportunity: dict) -> str:
        """
        Convenience method to generate URL directly from opportunity dict
        
        Args:
            opportunity: Dictionary containing market data
            
        Returns:
            Full URL to event on the market platform
        """
        market = EventLinkGenerator.create_from_opportunity(opportunity)
        return EventLinkGenerator.generate_event_url(market)


# Test cases for validation
def test_url_generation():
    """Test URL generation for different platforms"""
    
    # Test Polymarket
    polymarket_market = NormalizedMarket(
        source='polymarket',
        market_id='donald-trump-us-presidential-election-2024'
    )
    print(f"Polymarket: {EventLinkGenerator.generate_event_url(polymarket_market)}")
    
    # Test Manifold
    manifold_market = NormalizedMarket(
        source='manifold',
        market_id='will-trump-win-2024-election',
        slug='will-trump-win-2024-election'
    )
    print(f"Manifold: {EventLinkGenerator.generate_event_url(manifold_market)}")
    
    # Test Limitless
    limitless_market = NormalizedMarket(
        source='limitless',
        market_id='0x1234567890abcdef'
    )
    print(f"Limitless: {EventLinkGenerator.generate_event_url(limitless_market)}")
    
    # Test Azuro
    azuro_market = NormalizedMarket(
        source='azuro',
        market_id='0xabcdef1234567890',
        chain='polygon'
    )
    print(f"Azuro: {EventLinkGenerator.generate_event_url(azuro_market)}")


if __name__ == "__main__":
    test_url_generation()
