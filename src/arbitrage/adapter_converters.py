"""
Adapter Converters - Convert platform-specific market data to unified format
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from .complete_system import MarketData, Platform

logger = logging.getLogger(__name__)


def convert_polymarket_to_unified(markets: List[Dict[str, Any]]) -> List[MarketData]:
    """Convert Polymarket adapter format to unified MarketData"""
    unified = []
    
    for market in markets:
        try:
            # Extract YES/NO prices from quotes
            yes_price = 0.0
            no_price = 0.0
            yes_liquidity = 0.0
            no_liquidity = 0.0
            
            quotes = market.get('quotes', [])
            for quote in quotes:
                outcome = str(quote.get('outcome_id', '')).upper()
                if 'YES' in outcome:
                    yes_price = quote.get('mid', 0.0)
                    yes_liquidity = quote.get('liquidity', 0.0)
                elif 'NO' in outcome:
                    no_price = quote.get('mid', 0.0)
                    no_liquidity = quote.get('liquidity', 0.0)
            
            # Skip if no valid prices
            if yes_price == 0.0:
                continue
            
            # Infer NO price if missing
            if no_price == 0.0:
                no_price = 1.0 - yes_price
            
            # Parse expiration
            expires_at = market.get('end_date')
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except:
                    expires_at = datetime.utcnow() + timedelta(days=7)
            elif not isinstance(expires_at, datetime):
                expires_at = datetime.utcnow() + timedelta(days=7)
            
            unified_market = MarketData(
                platform=Platform.POLYMARKET,
                market_id=market.get('id', market.get('market_id', 'unknown')),
                title=market.get('title', market.get('question', 'Unknown Market')),
                description=market.get('description', ''),
                yes_price=yes_price,
                no_price=no_price,
                yes_liquidity=yes_liquidity,
                no_liquidity=no_liquidity,
                volume_24h=float(market.get('volume', 0.0)),
                expires_at=expires_at,
                image_url=market.get('image', market.get('icon', None))
            )
            
            unified.append(unified_market)
            
        except Exception as e:
            logger.debug(f"Failed to convert Polymarket market: {e}")
            continue
    
    return unified


def convert_manifold_to_unified(markets: List[Dict[str, Any]]) -> List[MarketData]:
    """Convert Manifold adapter format to unified MarketData"""
    unified = []
    
    for market in markets:
        try:
            # Extract YES/NO prices
            yes_price = 0.0
            no_price = 0.0
            yes_liquidity = 0.0
            no_liquidity = 0.0
            
            quotes = market.get('quotes', [])
            for quote in quotes:
                outcome = str(quote.get('outcome_id', '')).upper()
                if 'YES' in outcome:
                    yes_price = quote.get('mid', 0.0)
                    yes_liquidity = quote.get('liquidity', 0.0)
                elif 'NO' in outcome:
                    no_price = quote.get('mid', 0.0)
                    no_liquidity = quote.get('liquidity', 0.0)
            
            # Skip if no valid prices
            if yes_price == 0.0:
                continue
            
            # Infer NO price if missing
            if no_price == 0.0:
                no_price = 1.0 - yes_price
            
            # Parse expiration
            expires_at = market.get('end_date', market.get('closeTime'))
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except:
                    expires_at = datetime.utcnow() + timedelta(days=7)
            elif not isinstance(expires_at, datetime):
                expires_at = datetime.utcnow() + timedelta(days=7)
            
            unified_market = MarketData(
                platform=Platform.MANIFOLD,
                market_id=market.get('id', 'unknown'),
                title=market.get('title', market.get('question', 'Unknown Market')),
                description=market.get('description', ''),
                yes_price=yes_price,
                no_price=no_price,
                yes_liquidity=yes_liquidity if yes_liquidity > 0 else float(market.get('liquidity', 0.0)),
                no_liquidity=no_liquidity if no_liquidity > 0 else float(market.get('liquidity', 0.0)),
                volume_24h=float(market.get('volume', 0.0)),
                expires_at=expires_at,
                image_url=None
            )
            
            unified.append(unified_market)
            
        except Exception as e:
            logger.debug(f"Failed to convert Manifold market: {e}")
            continue
    
    return unified


def convert_azuro_to_unified(markets: List[Dict[str, Any]]) -> List[MarketData]:
    """Convert Azuro adapter format to unified MarketData"""
    unified = []
    
    for market in markets:
        try:
            # Extract YES/NO prices
            yes_price = 0.0
            no_price = 0.0
            yes_liquidity = 0.0
            no_liquidity = 0.0
            
            quotes = market.get('quotes', [])
            for quote in quotes:
                outcome = str(quote.get('outcome_id', '')).upper()
                if 'YES' in outcome or 'HOME' in outcome or '1' in outcome:
                    yes_price = quote.get('mid', 0.0)
                    yes_liquidity = quote.get('liquidity', 0.0)
                elif 'NO' in outcome or 'AWAY' in outcome or '2' in outcome:
                    no_price = quote.get('mid', 0.0)
                    no_liquidity = quote.get('liquidity', 0.0)
            
            # Skip if no valid prices
            if yes_price == 0.0:
                continue
            
            # Infer NO price if missing
            if no_price == 0.0:
                no_price = 1.0 - yes_price
            
            # Parse expiration
            expires_at = market.get('end_date', market.get('startsAt'))
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except:
                    expires_at = datetime.utcnow() + timedelta(days=7)
            elif not isinstance(expires_at, datetime):
                expires_at = datetime.utcnow() + timedelta(days=7)
            
            unified_market = MarketData(
                platform=Platform.AZURO,
                market_id=market.get('id', 'unknown'),
                title=market.get('title', market.get('question', 'Unknown Market')),
                description=market.get('description', ''),
                yes_price=yes_price,
                no_price=no_price,
                yes_liquidity=yes_liquidity if yes_liquidity > 0 else float(market.get('liquidity', 0.0)),
                no_liquidity=no_liquidity if no_liquidity > 0 else float(market.get('liquidity', 0.0)),
                volume_24h=float(market.get('volume', 0.0)),
                expires_at=expires_at,
                image_url=None
            )
            
            unified.append(unified_market)
            
        except Exception as e:
            logger.debug(f"Failed to convert Azuro market: {e}")
            continue
    
    return unified


def convert_limitless_to_unified(markets: List[Dict[str, Any]]) -> List[MarketData]:
    """Convert Limitless adapter format to unified MarketData"""
    unified = []
    
    for market in markets:
        try:
            # Extract YES/NO prices
            yes_price = 0.0
            no_price = 0.0
            yes_liquidity = 0.0
            no_liquidity = 0.0
            
            quotes = market.get('quotes', [])
            for quote in quotes:
                outcome = str(quote.get('outcome_id', '')).upper()
                if 'YES' in outcome:
                    yes_price = quote.get('mid', 0.0)
                    yes_liquidity = quote.get('liquidity', 0.0)
                elif 'NO' in outcome:
                    no_price = quote.get('mid', 0.0)
                    no_liquidity = quote.get('liquidity', 0.0)
            
            # Skip if no valid prices
            if yes_price == 0.0:
                continue
            
            # Infer NO price if missing
            if no_price == 0.0:
                no_price = 1.0 - yes_price
            
            # Parse expiration
            expires_at = market.get('end_date')
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except:
                    expires_at = datetime.utcnow() + timedelta(days=7)
            elif not isinstance(expires_at, datetime):
                expires_at = datetime.utcnow() + timedelta(days=7)
            
            unified_market = MarketData(
                platform=Platform.LIMITLESS,
                market_id=market.get('id', 'unknown'),
                title=market.get('title', market.get('question', 'Unknown Market')),
                description=market.get('description', ''),
                yes_price=yes_price,
                no_price=no_price,
                yes_liquidity=yes_liquidity if yes_liquidity > 0 else float(market.get('liquidity', 0.0)),
                no_liquidity=no_liquidity if no_liquidity > 0 else float(market.get('liquidity', 0.0)),
                volume_24h=float(market.get('volume', 0.0)),
                expires_at=expires_at,
                image_url=None
            )
            
            unified.append(unified_market)
            
        except Exception as e:
            logger.debug(f"Failed to convert Limitless market: {e}")
            continue
    
    return unified
