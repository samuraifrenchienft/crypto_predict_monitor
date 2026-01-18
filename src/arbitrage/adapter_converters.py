"""
Adapter Converters - Convert platform-specific market data to unified format
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from .complete_system import MarketData, Platform

logger = logging.getLogger(__name__)


def convert_polymarket_to_unified(markets) -> List[MarketData]:
    """Convert Polymarket adapter format to unified MarketData"""
    unified = []
    
    for market in markets:
        try:
            # Handle Market objects with Quote objects
            yes_price = 0.0
            no_price = 0.0
            yes_liquidity = 25000.0  # Default liquidity
            no_liquidity = 25000.0
            
            # Get quotes from Market object
            quotes = getattr(market, 'quotes', [])
            if not quotes and hasattr(market, 'outcomes'):
                # Extract from outcomes if no quotes
                for outcome in market.outcomes:
                    # Handle both Outcome and Quote objects
                    outcome_name = getattr(outcome, 'name', None)
                    outcome_id = getattr(outcome, 'outcome_id', None)
                    
                    # Try to get name from either attribute
                    if outcome_name:
                        name_str = str(outcome_name).upper()
                    elif outcome_id:
                        name_str = str(outcome_id).upper()
                    else:
                        continue
                    
                    if 'YES' in name_str:
                        yes_price = getattr(outcome, 'price', 0.0) or getattr(outcome, 'mid', 0.0) or 0.0
                    elif 'NO' in name_str:
                        no_price = getattr(outcome, 'price', 0.0) or getattr(outcome, 'mid', 0.0) or 0.0
            
            # Process Quote objects
            for quote in quotes:
                if hasattr(quote, 'outcome_id'):
                    outcome = str(quote.outcome_id).upper()
                    if 'YES' in outcome:
                        yes_price = getattr(quote, 'mid', 0.0) or 0.0
                        yes_liquidity = getattr(quote, 'liquidity', 25000.0) or 25000.0
                    elif 'NO' in outcome:
                        no_price = getattr(quote, 'mid', 0.0) or 0.0
                        no_liquidity = getattr(quote, 'liquidity', 25000.0) or 25000.0
            
            # Skip if no valid prices
            if yes_price == 0.0:
                continue
            
            # Infer NO price if missing
            if no_price == 0.0:
                no_price = 1.0 - yes_price
            
            # Parse expiration from Market object
            expires_at = getattr(market, 'end_date', None) or getattr(market, 'expires_at', None)
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except:
                    expires_at = datetime.utcnow() + timedelta(days=7)
            elif not isinstance(expires_at, datetime):
                expires_at = datetime.utcnow() + timedelta(days=7)
            
            # Get market attributes with fallbacks
            market_id = getattr(market, 'id', None) or getattr(market, 'market_id', 'unknown')
            title = getattr(market, 'title', None) or getattr(market, 'question', 'Unknown Market')
            description = getattr(market, 'description', '')
            volume = getattr(market, 'volume', 0.0) or 0.0
            image_url = getattr(market, 'image', None) or getattr(market, 'icon', None)
            
            unified_market = MarketData(
                platform=Platform.POLYMARKET,
                market_id=str(market_id),
                title=str(title),
                description=str(description),
                yes_price=yes_price,
                no_price=no_price,
                yes_liquidity=yes_liquidity,
                no_liquidity=no_liquidity,
                volume_24h=float(volume),
                expires_at=expires_at,
                image_url=str(image_url) if image_url else None
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


def convert_azuro_to_unified(markets) -> List[MarketData]:
    """Convert Azuro adapter format to unified MarketData"""
    unified = []
    
    for market in markets:
        try:
            # Handle Market objects with Quote objects
            yes_price = 0.0
            no_price = 0.0
            yes_liquidity = 25000.0
            no_liquidity = 25000.0
            
            # Get quotes from Market object
            quotes = getattr(market, 'quotes', [])
            if not quotes and hasattr(market, 'outcomes'):
                # Extract from outcomes if no quotes
                for outcome in market.outcomes:
                    # Handle both Outcome and Quote objects
                    outcome_name = getattr(outcome, 'name', None)
                    outcome_id = getattr(outcome, 'outcome_id', None)
                    
                    # Try to get name from either attribute
                    if outcome_name:
                        name_str = str(outcome_name).upper()
                    elif outcome_id:
                        name_str = str(outcome_id).upper()
                    else:
                        continue
                    
                    if 'YES' in name_str or 'HOME' in name_str or '1' in name_str:
                        yes_price = getattr(outcome, 'price', 0.0) or getattr(outcome, 'mid', 0.0) or 0.0
                    elif 'NO' in name_str or 'AWAY' in name_str or '2' in name_str:
                        no_price = getattr(outcome, 'price', 0.0) or getattr(outcome, 'mid', 0.0) or 0.0
            
            for quote in quotes:
                if hasattr(quote, 'outcome_id'):
                    outcome = str(quote.outcome_id).upper()
                    if 'YES' in outcome or 'HOME' in outcome or '1' in outcome:
                        yes_price = getattr(quote, 'mid', 0.0) or 0.0
                        yes_liquidity = getattr(quote, 'liquidity', 25000.0) or 25000.0
                    elif 'NO' in outcome or 'AWAY' in outcome or '2' in outcome:
                        no_price = getattr(quote, 'mid', 0.0) or 0.0
                        no_liquidity = getattr(quote, 'liquidity', 25000.0) or 25000.0
            
            # Skip if no valid prices
            if yes_price == 0.0:
                continue
            
            # Infer NO price if missing
            if no_price == 0.0:
                no_price = 1.0 - yes_price
            
            # Parse expiration from Market object
            expires_at = getattr(market, 'end_date', None) or getattr(market, 'startsAt', None) or getattr(market, 'expires_at', None)
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except:
                    expires_at = datetime.utcnow() + timedelta(days=7)
            elif not isinstance(expires_at, datetime):
                expires_at = datetime.utcnow() + timedelta(days=7)
            
            # Get market attributes with fallbacks
            market_id = getattr(market, 'id', None) or getattr(market, 'market_id', 'unknown')
            title = getattr(market, 'title', None) or getattr(market, 'question', 'Unknown Market')
            description = getattr(market, 'description', '')
            volume = getattr(market, 'volume', 0.0) or 0.0
            liquidity = getattr(market, 'liquidity', 0.0) or 0.0
            
            unified_market = MarketData(
                platform=Platform.AZURO,
                market_id=str(market_id),
                title=str(title),
                description=str(description),
                yes_price=yes_price,
                no_price=no_price,
                yes_liquidity=yes_liquidity if yes_liquidity > 0 else float(liquidity),
                no_liquidity=no_liquidity if no_liquidity > 0 else float(liquidity),
                volume_24h=float(volume),
                expires_at=expires_at,
                image_url=None
            )
            
            unified.append(unified_market)
            
        except Exception as e:
            logger.debug(f"Failed to convert Azuro market: {e}")
            continue
    
    return unified


def convert_limitless_to_unified(markets) -> List[MarketData]:
    """Convert Limitless adapter format to unified MarketData"""
    unified = []
    
    for market in markets:
        try:
            # Handle Market objects with Quote objects
            yes_price = 0.0
            no_price = 0.0
            yes_liquidity = 25000.0
            no_liquidity = 25000.0
            
            # Get quotes from Market object
            quotes = getattr(market, 'quotes', [])
            if not quotes and hasattr(market, 'outcomes'):
                # Extract from outcomes if no quotes
                for outcome in market.outcomes:
                    # Handle both Outcome and Quote objects
                    outcome_name = getattr(outcome, 'name', None)
                    outcome_id = getattr(outcome, 'outcome_id', None)
                    
                    # Try to get name from either attribute
                    if outcome_name:
                        name_str = str(outcome_name).upper()
                    elif outcome_id:
                        name_str = str(outcome_id).upper()
                    else:
                        continue
                    
                    if 'YES' in name_str:
                        yes_price = getattr(outcome, 'price', 0.0) or getattr(outcome, 'mid', 0.0) or 0.0
                    elif 'NO' in name_str:
                        no_price = getattr(outcome, 'price', 0.0) or getattr(outcome, 'mid', 0.0) or 0.0
            
            for quote in quotes:
                if hasattr(quote, 'outcome_id'):
                    outcome = str(quote.outcome_id).upper()
                    if 'YES' in outcome:
                        yes_price = getattr(quote, 'mid', 0.0) or 0.0
                        yes_liquidity = getattr(quote, 'liquidity', 25000.0) or 25000.0
                    elif 'NO' in outcome:
                        no_price = getattr(quote, 'mid', 0.0) or 0.0
                        no_liquidity = getattr(quote, 'liquidity', 25000.0) or 25000.0
            
            # Skip if no valid prices
            if yes_price == 0.0:
                continue
            
            # Infer NO price if missing
            if no_price == 0.0:
                no_price = 1.0 - yes_price
            
            # Parse expiration from Market object
            expires_at = getattr(market, 'end_date', None) or getattr(market, 'expires_at', None)
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                except:
                    expires_at = datetime.utcnow() + timedelta(days=7)
            elif not isinstance(expires_at, datetime):
                expires_at = datetime.utcnow() + timedelta(days=7)
            
            # Get market attributes with fallbacks
            market_id = getattr(market, 'id', None) or getattr(market, 'market_id', 'unknown')
            title = getattr(market, 'title', None) or getattr(market, 'question', 'Unknown Market')
            description = getattr(market, 'description', '')
            volume = getattr(market, 'volume', 0.0) or 0.0
            liquidity = getattr(market, 'liquidity', 0.0) or 0.0
            
            unified_market = MarketData(
                platform=Platform.LIMITLESS,
                market_id=str(market_id),
                title=str(title),
                description=str(description),
                yes_price=yes_price,
                no_price=no_price,
                yes_liquidity=yes_liquidity if yes_liquidity > 0 else float(liquidity),
                no_liquidity=no_liquidity if no_liquidity > 0 else float(liquidity),
                volume_24h=float(volume),
                expires_at=expires_at,
                image_url=None
            )
            
            unified.append(unified_market)
            
        except Exception as e:
            logger.debug(f"Failed to convert Limitless market: {e}")
            continue
    
    return unified
