"""
Market Normalizer
Convert source-specific market data to unified format for arbitrage detection
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import re

logger = logging.getLogger("market_normalizer")

@dataclass
class NormalizedMarket:
    """Unified format for all market sources"""
    market_id: str           # 'polygon:0xabc123' or 'polymarket:xyz'
    source: str              # 'polymarket', 'azuro_polygon', 'azuro_gnosis', etc
    chain: str               # 'ethereum', 'polygon', 'gnosis', 'base', 'chiliz'
    
    name: str                # Market name
    category: str            # 'crypto', 'sports', 'event', 'politics'
    
    yes_price: float         # 0-1
    no_price: float          # 0-1
    spread: float            # 1 - (yes + no)
    
    yes_liquidity: float     # $ USD
    no_liquidity: float      # $ USD
    total_liquidity: float
    
    volume_24h: float
    status: str              # 'active', 'pending', 'resolved'
    expires_at: datetime
    
    source_data: Dict        # Raw data from source
    
    # Additional fields for arbitrage
    price_change_24h: float = 0.0
    bid_ask_spread: float = 0.001
    time_to_expiration: Optional[int] = None  # seconds

class MarketNormalizer:
    """Convert source-specific to unified format"""
    
    # Category mapping based on keywords
    CATEGORY_KEYWORDS = {
        'crypto': ['bitcoin', 'ethereum', 'btc', 'eth', 'crypto', 'blockchain', 'defi'],
        'sports': ['game', 'team', 'win', 'lose', 'score', 'match', 'season', 'player', 'coach'],
        'politics': ['election', 'president', 'vote', 'senate', 'congress', 'trump', 'biden'],
        'event': ['will', 'happen', 'when', 'reach', 'achieve', 'complete']
    }
    
    @staticmethod
    def _determine_category(market_name: str) -> str:
        """Determine market category from name"""
        name_lower = market_name.lower()
        
        for category, keywords in MarketNormalizer.CATEGORY_KEYWORDS.items():
            if any(keyword in name_lower for keyword in keywords):
                return category
        
        return 'event'  # Default category
    
    @staticmethod
    def _validate_prices(yes_price: float, no_price: float) -> bool:
        """Validate price ranges"""
        return (0 <= yes_price <= 1 and 
                0 <= no_price <= 1 and
                yes_price + no_price <= 1.1)  # Allow small rounding errors
    
    @staticmethod
    def _validate_liquidity(liquidity: float) -> bool:
        """Validate liquidity values"""
        return liquidity >= 0
    
    @staticmethod
    def _calculate_spread(yes_price: float, no_price: float) -> float:
        """Calculate spread from yes/no prices"""
        return max(0.0, 1.0 - (yes_price + no_price))
    
    @staticmethod
    def _parse_expires_at(expires_data: Any) -> datetime:
        """Parse expiration date from various formats"""
        if isinstance(expires_data, datetime):
            return expires_data
        elif isinstance(expires_data, str):
            try:
                # Try ISO format first
                return datetime.fromisoformat(expires_data.replace('Z', '+00:00'))
            except:
                # Try timestamp
                try:
                    timestamp = int(expires_data)
                    return datetime.fromtimestamp(timestamp, timezone.utc)
                except:
                    pass
        elif isinstance(expires_data, (int, float)):
            return datetime.fromtimestamp(expires_data, timezone.utc)
        
        # Default to 24 hours from now
        return datetime.now(timezone.utc) + timedelta(hours=24)
    
    @staticmethod
    async def normalize_polymarket(pm_market: Dict) -> NormalizedMarket:
        """Convert Polymarket market to unified format"""
        try:
            # Extract basic info
            market_id = f"polymarket:{pm_market.get('id', '')}"
            name = pm_market.get('title', pm_market.get('question', 'Unknown Market'))
            
            # Extract prices
            outcomes = pm_market.get('outcomes', [])
            if len(outcomes) >= 2:
                # Find YES and NO outcomes
                yes_outcome = None
                no_outcome = None
                
                for outcome in outcomes:
                    outcome_name = outcome.get('name', '').lower()
                    if 'yes' in outcome_name:
                        yes_outcome = outcome
                    elif 'no' in outcome_name:
                        no_outcome = outcome
                
                # Fallback to first two outcomes if YES/NO not found
                if not yes_outcome or not no_outcome:
                    yes_outcome = outcomes[0]
                    no_outcome = outcomes[1]
                
                yes_price = float(yes_outcome.get('price', 0.5))
                no_price = float(no_outcome.get('price', 0.5))
            else:
                # Use price data directly if available
                yes_price = float(pm_market.get('yes_price', 0.5))
                no_price = float(pm_market.get('no_price', 0.5))
            
            # Validate prices
            if not MarketNormalizer._validate_prices(yes_price, no_price):
                logger.warning(f"Invalid Polymarket prices: {yes_price}/{no_price}")
                yes_price = max(0.01, min(0.99, yes_price))
                no_price = max(0.01, min(0.99, no_price))
            
            # Extract liquidity
            yes_liquidity = float(pm_market.get('yes_liquidity', pm_market.get('liquidity', 0)))
            no_liquidity = float(pm_market.get('no_liquidity', pm_market.get('liquidity', 0)))
            
            # Extract volume
            volume_24h = float(pm_market.get('volume_24h', pm_market.get('volume', 0)))
            
            # Extract expiration
            expires_at = MarketNormalizer._parse_expires_at(
                pm_market.get('expires_at', pm_market.get('deadline'))
            )
            
            # Determine status
            status = pm_market.get('status', 'active')
            if status not in ['active', 'pending', 'resolved']:
                status = 'active'
            
            # Calculate spread
            spread = MarketNormalizer._calculate_spread(yes_price, no_price)
            
            # Determine category
            category = MarketNormalizer._determine_category(name)
            
            # Create normalized market
            normalized = NormalizedMarket(
                market_id=market_id,
                source='polymarket',
                chain='ethereum',  # Polymarket on Ethereum
                name=name,
                category=category,
                yes_price=yes_price,
                no_price=no_price,
                spread=spread,
                yes_liquidity=yes_liquidity,
                no_liquidity=no_liquidity,
                total_liquidity=yes_liquidity + no_liquidity,
                volume_24h=volume_24h,
                status=status,
                expires_at=expires_at,
                source_data=pm_market,
                price_change_24h=float(pm_market.get('price_change_24h', 0.0)),
                bid_ask_spread=float(pm_market.get('bid_ask_spread', 0.001)),
                time_to_expiration=int((expires_at - datetime.now(timezone.utc)).total_seconds()) if expires_at > datetime.now(timezone.utc) else None
            )
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing Polymarket market: {e}")
            raise

    @staticmethod
    async def normalize_azuro(azuro_market: Dict, chain: str) -> NormalizedMarket:
        """Convert Azuro market to unified format"""
        try:
            # Extract basic info
            condition_id = azuro_market.get('id', azuro_market.get('condition_id', ''))
            market_id = f"azuro_{chain}:{condition_id}"
            name = azuro_market.get('title', azuro_market.get('name', 'Unknown Market'))
            
            # Extract outcomes
            outcomes = azuro_market.get('outcomes', [])
            if len(outcomes) >= 2:
                # Find YES and NO outcomes
                yes_outcome = None
                no_outcome = None
                
                for outcome in outcomes:
                    outcome_name = outcome.get('title', outcome.get('name', '')).lower()
                    if 'yes' in outcome_name or outcome_name == '1':
                        yes_outcome = outcome
                    elif 'no' in outcome_name or outcome_name == '2':
                        no_outcome = outcome
                
                # Fallback to first two outcomes
                if not yes_outcome or not no_outcome:
                    yes_outcome = outcomes[0]
                    no_outcome = outcomes[1]
                
                yes_price = float(yes_outcome.get('probability', yes_outcome.get('price', 0.5)))
                no_price = float(no_outcome.get('probability', no_outcome.get('price', 0.5)))
            else:
                # Direct price extraction
                yes_price = float(azuro_market.get('yes_price', 0.5))
                no_price = float(azuro_market.get('no_price', 0.5))
            
            # Validate prices
            if not MarketNormalizer._validate_prices(yes_price, no_price):
                logger.warning(f"Invalid Azuro prices: {yes_price}/{no_price}")
                yes_price = max(0.01, min(0.99, yes_price))
                no_price = max(0.01, min(0.99, no_price))
            
            # Extract liquidity
            yes_liquidity = float(azuro_market.get('yes_liquidity', azuro_market.get('liquidity', 0)))
            no_liquidity = float(azuro_market.get('no_liquidity', azuro_market.get('liquidity', 0)))
            
            # Extract volume
            volume_24h = float(azuro_market.get('volume_24h', azuro_market.get('totalVolume', 0)))
            
            # Extract expiration
            expires_at = MarketNormalizer._parse_expires_at(
                azuro_market.get('expires_at', azuro_market.get('deadline'))
            )
            
            # Determine status
            status = azuro_market.get('status', 'active')
            if status not in ['active', 'pending', 'resolved']:
                status = 'active'
            
            # Calculate spread
            spread = MarketNormalizer._calculate_spread(yes_price, no_price)
            
            # Determine category
            category = MarketNormalizer._determine_category(name)
            
            # Create normalized market
            normalized = NormalizedMarket(
                market_id=market_id,
                source=f'azuro_{chain}',
                chain=chain,
                name=name,
                category=category,
                yes_price=yes_price,
                no_price=no_price,
                spread=spread,
                yes_liquidity=yes_liquidity,
                no_liquidity=no_liquidity,
                total_liquidity=yes_liquidity + no_liquidity,
                volume_24h=volume_24h,
                status=status,
                expires_at=expires_at,
                source_data=azuro_market,
                price_change_24h=float(azuro_market.get('price_change_24h', 0.0)),
                bid_ask_spread=float(azuro_market.get('bid_ask_spread', 0.001)),
                time_to_expiration=int((expires_at - datetime.now(timezone.utc)).total_seconds()) if expires_at > datetime.now(timezone.utc) else None
            )
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error normalizing Azuro market: {e}")
            raise

    @staticmethod
    async def normalize_batch(markets: List[Dict], source: str, chain: Optional[str] = None) -> List[NormalizedMarket]:
        """Batch normalize multiple markets"""
        normalized_markets = []
        
        logger.info(f"🔄 Normalizing {len(markets)} markets from {source}")
        
        for i, market in enumerate(markets):
            try:
                if source == 'polymarket':
                    normalized = await MarketNormalizer.normalize_polymarket(market)
                elif source.startswith('azuro'):
                    if not chain:
                        raise ValueError("Chain must be specified for Azuro markets")
                    normalized = await MarketNormalizer.normalize_azuro(market, chain)
                else:
                    logger.warning(f"Unknown source: {source}")
                    continue
                
                normalized_markets.append(normalized)
                
                # Log progress for large batches
                if (i + 1) % 100 == 0:
                    logger.info(f"📊 Normalized {i + 1}/{len(markets)} markets")
                    
            except Exception as e:
                logger.error(f"Error normalizing market {i}: {e}")
                continue
        
        logger.info(f"✅ Successfully normalized {len(normalized_markets)}/{len(markets)} markets from {source}")
        
        return normalized_markets

    @staticmethod
    def reverse_normalize(normalized_market: NormalizedMarket) -> Dict[str, Any]:
        """Convert normalized market back to source-specific format for trading"""
        if normalized_market.source == 'polymarket':
            return MarketNormalizer._reverse_polymarket(normalized_market)
        elif normalized_market.source.startswith('azuro'):
            return MarketNormalizer._reverse_azuro(normalized_market)
        else:
            raise ValueError(f"Unknown source for reverse normalization: {normalized_market.source}")

    @staticmethod
    def _reverse_polymarket(normalized_market: NormalizedMarket) -> Dict[str, Any]:
        """Convert normalized market back to Polymarket format"""
        return {
            'id': normalized_market.market_id.replace('polymarket:', ''),
            'title': normalized_market.name,
            'yes_price': normalized_market.yes_price,
            'no_price': normalized_market.no_price,
            'yes_liquidity': normalized_market.yes_liquidity,
            'no_liquidity': normalized_market.no_liquidity,
            'volume_24h': normalized_market.volume_24h,
            'status': normalized_market.status,
            'expires_at': normalized_market.expires_at.isoformat(),
            'price_change_24h': normalized_market.price_change_24h,
            'bid_ask_spread': normalized_market.bid_ask_spread
        }

    @staticmethod
    def _reverse_azuro(normalized_market: NormalizedMarket) -> Dict[str, Any]:
        """Convert normalized market back to Azuro format"""
        chain = normalized_market.source.replace('azuro_', '')
        
        return {
            'id': normalized_market.market_id.replace(f'azuro_{chain}:', ''),
            'condition_id': normalized_market.market_id.replace(f'azuro_{chain}:', ''),
            'title': normalized_market.name,
            'yes_price': normalized_market.yes_price,
            'no_price': normalized_market.no_price,
            'yes_liquidity': normalized_market.yes_liquidity,
            'no_liquidity': normalized_market.no_liquidity,
            'totalVolume': normalized_market.volume_24h,
            'status': normalized_market.status,
            'expires_at': normalized_market.expires_at.isoformat(),
            'chain': chain
        }

# Test function
async def test_market_normalizer():
    """Test the market normalizer with sample data"""
    print("🎯 Testing Market Normalizer")
    print("=" * 50)
    
    # Sample Polymarket data
    pm_market = {
        'id': 'polymarket-123',
        'title': 'Bitcoin Price Above $100,000 by End of 2024',
        'yes_price': 0.35,
        'no_price': 0.65,
        'yes_liquidity': 50000,
        'no_liquidity': 75000,
        'volume_24h': 125000,
        'status': 'active',
        'expires_at': '2024-12-31T23:59:59Z',
        'price_change_24h': 0.02,
        'bid_ask_spread': 0.001
    }
    
    # Sample Azuro data
    azuro_market = {
        'id': 'azuro-456',
        'title': 'US Presidential Election 2024 Winner',
        'yes_price': 0.48,
        'no_price': 0.52,
        'yes_liquidity': 85000,
        'no_liquidity': 92000,
        'totalVolume': 177000,
        'status': 'active',
        'expires_at': '2024-11-05T23:59:59Z'
    }
    
    try:
        # Test Polymarket normalization
        print("📊 Testing Polymarket normalization...")
        pm_normalized = await MarketNormalizer.normalize_polymarket(pm_market)
        print(f"✅ Polymarket normalized: {pm_normalized.name}")
        print(f"   Market ID: {pm_normalized.market_id}")
        print(f"   Category: {pm_normalized.category}")
        print(f"   Prices: YES={pm_normalized.yes_price:.3f}, NO={pm_normalized.no_price:.3f}")
        print(f"   Spread: {pm_normalized.spread:.3f}")
        print(f"   Liquidity: ${pm_normalized.total_liquidity:,.0f}")
        print()
        
        # Test Azuro normalization
        print("📊 Testing Azuro normalization...")
        azuro_normalized = await MarketNormalizer.normalize_azuro(azuro_market, 'polygon')
        print(f"✅ Azuro normalized: {azuro_normalized.name}")
        print(f"   Market ID: {azuro_normalized.market_id}")
        print(f"   Category: {azuro_normalized.category}")
        print(f"   Chain: {azuro_normalized.chain}")
        print(f"   Prices: YES={azuro_normalized.yes_price:.3f}, NO={azuro_normalized.no_price:.3f}")
        print(f"   Spread: {azuro_normalized.spread:.3f}")
        print(f"   Liquidity: ${azuro_normalized.total_liquidity:,.0f}")
        print()
        
        # Test batch normalization
        print("📊 Testing batch normalization...")
        batch_markets = [pm_market, azuro_market]
        
        # Normalize Polymarket batch
        pm_batch = await MarketNormalizer.normalize_batch([pm_market], 'polymarket')
        print(f"✅ Polymarket batch: {len(pm_batch)} markets")
        
        # Normalize Azuro batch
        azuro_batch = await MarketNormalizer.normalize_batch([azuro_market], 'azuro', 'polygon')
        print(f"✅ Azuro batch: {len(azuro_batch)} markets")
        
        # Test reverse normalization
        print()
        print("🔄 Testing reverse normalization...")
        pm_reverse = MarketNormalizer.reverse_normalize(pm_normalized)
        print(f"✅ Polymarket reverse: {pm_reverse['title']}")
        
        azuro_reverse = MarketNormalizer.reverse_normalize(azuro_normalized)
        print(f"✅ Azuro reverse: {azuro_reverse['title']}")
        
        print("\n🎉 All normalization tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_market_normalizer())
