"""
Arbitrage Detection Module
Core arbitrage opportunity detection logic
"""

from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone, timedelta

from bot.models import Market, Quote, ArbitrageOpportunity, Tier
from shared.logger import get_logger
from shared.utils import normalize_text, calculate_spread_percentage


class ArbitrageDetector:
    """Core arbitrage detection engine"""
    
    def __init__(self, min_spread: float = 0.015):
        self.min_spread = min_spread
        self.logger = get_logger(__name__)
    
    def detect_opportunities(
        self,
        markets_by_source: Dict[str, List[Market]],
        quotes_by_source: Dict[str, Dict[str, List[Quote]]],
        prioritize_new: bool = True,
        new_event_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Detect arbitrage opportunities across platforms
        
        Args:
            markets_by_source: Markets grouped by platform
            quotes_by_source: Quotes grouped by platform and market
            prioritize_new: Whether to prioritize new events
            new_event_hours: Hours to consider events as "new"
            
        Returns:
            List of arbitrage opportunities
        """
        # Group markets by normalized title
        market_groups = self._group_by_normalized_title(markets_by_source)
        
        opportunities = []
        for normalized_title, markets in market_groups.items():
            if len(markets) < 2:
                continue  # Need at least 2 platforms for arbitrage
            
            # Find best arbitrage for this group
            opportunity = self._find_best_arbitrage(
                normalized_title, markets, quotes_by_source, prioritize_new, new_event_hours
            )
            
            if opportunity:
                opportunities.append(opportunity)
        
        # Sort by spread percentage (best first)
        opportunities.sort(key=lambda x: x.get('spread_percentage', 0), reverse=True)
        
        self.logger.info(f"Detected {len(opportunities)} arbitrage opportunities")
        return opportunities
    
    def _group_by_normalized_title(self, markets_by_source: Dict[str, List[Market]]) -> Dict[str, List[Tuple[str, Market]]]:
        """Group markets by normalized title"""
        groups = {}
        
        for source, markets in markets_by_source.items():
            for market in markets:
                normalized = normalize_text(market.title)
                if normalized not in groups:
                    groups[normalized] = []
                groups[normalized].append((source, market))
        
        return groups
    
    def _find_best_arbitrage(
        self,
        normalized_title: str,
        markets: List[Tuple[str, Market]],
        quotes_by_source: Dict[str, Dict[str, List[Quote]]],
        prioritize_new: bool,
        new_event_hours: int
    ) -> Dict[str, Any]:
        """Find the best arbitrage opportunity for a group of markets"""
        best_opportunity = None
        best_spread = 0.0
        
        # Try all combinations of markets
        for i in range(len(markets)):
            for j in range(i + 1, len(markets)):
                source1, market1 = markets[i]
                source2, market2 = markets[j]
                
                # Get quotes for both markets
                quotes1 = quotes_by_source.get(source1, {}).get(market1.market_id, [])
                quotes2 = quotes_by_source.get(source2, {}).get(market2.market_id, [])
                
                if not quotes1 or not quotes2:
                    continue
                
                # Use latest quotes
                quote1 = quotes1[0]
                quote2 = quotes2[0]
                
                # Calculate arbitrage spread
                spread_pct = self._calculate_arbitrage_spread(quote1, quote2)
                
                if spread_pct > best_spread and spread_pct >= self.min_spread:
                    best_spread = spread_pct
                    best_opportunity = {
                        'normalized_title': normalized_title,
                        'markets': [
                            {
                                'source': source1,
                                'market_id': market1.market_id,
                                'title': market1.title,
                                'url': market1.get_platform_url(),
                                'bid': quote1.bid,
                                'ask': quote1.ask,
                                'mid': quote1.mid
                            },
                            {
                                'source': source2,
                                'market_id': market2.market_id,
                                'title': market2.title,
                                'url': market2.get_platform_url(),
                                'bid': quote2.bid,
                                'ask': quote2.ask,
                                'mid': quote2.mid
                            }
                        ],
                        'spread_percentage': spread_pct,
                        'spread': spread_pct / 100,
                        'priority': self._calculate_priority(market1, market2, prioritize_new, new_event_hours),
                        'created_at': datetime.now(timezone.utc)
                    }
        
        return best_opportunity
    
    def _calculate_arbitrage_spread(self, quote1: Quote, quote2: Quote) -> float:
        """Calculate arbitrage spread between two quotes"""
        # Find the best bid and ask across both markets
        best_bid = max(quote1.bid, quote2.bid)
        best_ask = min(quote1.ask, quote2.ask)
        
        if best_bid >= best_ask:
            return 0.0  # No arbitrage opportunity
        
        # Calculate spread percentage
        mid_price = (best_bid + best_ask) / 2
        spread = best_ask - best_bid
        spread_percentage = (spread / mid_price) * 100
        
        return spread_percentage
    
    def _calculate_priority(
        self,
        market1: Market,
        market2: Market,
        prioritize_new: bool,
        new_event_hours: int
    ) -> str:
        """Calculate priority level for an opportunity"""
        if not prioritize_new:
            return "normal"
        
        now = datetime.now(timezone.utc)
        cutoff_time = now - timedelta(hours=new_event_hours)
        
        # Check if either market is new
        market1_new = market1.created_time and market1.created_time > cutoff_time
        market2_new = market2.created_time and market2.created_time > cutoff_time
        
        if market1_new or market2_new:
            return "high"
        
        return "normal"
    
    def calculate_confidence_score(self, opportunity: Dict[str, Any]) -> float:
        """
        Calculate confidence score for an arbitrage opportunity
        
        Args:
            opportunity: Arbitrage opportunity data
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.5  # Base confidence
        
        # Boost for higher spreads
        spread_pct = opportunity.get('spread_percentage', 0)
        if spread_pct >= 3.0:
            confidence += 0.3
        elif spread_pct >= 2.0:
            confidence += 0.2
        elif spread_pct >= 1.5:
            confidence += 0.1
        
        # Boost for high priority
        if opportunity.get('priority') == 'high':
            confidence += 0.1
        
        # Boost for multiple markets (always 2 in current implementation)
        markets = opportunity.get('markets', [])
        if len(markets) >= 2:
            confidence += 0.1
        
        return min(confidence, 1.0)
