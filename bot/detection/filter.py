"""
Tiered Filter Module
Spread-only arbitrage opportunity filtering and tiering
"""

from typing import List, Dict, Any
from datetime import datetime, timezone

from bot.models import ArbitrageOpportunity, Tier
from shared.logger import get_logger


class TieredFilter:
    """Spread-only tiered arbitrage filter"""
    
    def __init__(self, tier_configs: Dict[str, Any]):
        self.tier_configs = tier_configs
        self.logger = get_logger(__name__)
        self._reset_stats()
    
    def filter_and_tier_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        min_spread: float = 0.015
    ) -> List[ArbitrageOpportunity]:
        """
        Filter and tier arbitrage opportunities based on spread
        
        Args:
            opportunities: Raw arbitrage opportunities
            min_spread: Minimum spread percentage
            
        Returns:
            List of tiered arbitrage opportunities
        """
        self._reset_stats()
        
        filtered_opportunities = []
        
        for opp in opportunities:
            spread_pct = opp.get('spread_percentage', 0)
            
            # Update stats
            self.stats['total_processed'] += 1
            
            # Apply minimum spread filter
            if spread_pct < min_spread:
                self.stats['total_filtered'] += 1
                continue
            
            # Determine tier
            tier_info = self._determine_tier(spread_pct)
            
            # Create arbitrage opportunity object
            arbitrage_opp = ArbitrageOpportunity(
                normalized_title=opp.get('normalized_title', ''),
                markets=opp.get('markets', []),
                spread_percentage=spread_pct,
                tier=tier_info['tier'],
                tier_emoji=tier_info['emoji'],
                tier_color=tier_info['color'],
                tier_action=tier_info['action'],
                tier_priority=tier_info['priority'],
                quality_score=self._calculate_quality_score(spread_pct),
                created_at=opp.get('created_at', datetime.now(timezone.utc))
            )
            
            filtered_opportunities.append(arbitrage_opp)
            
            # Update tier stats
            tier_name = tier_info['tier'].value
            if tier_name not in self.stats['tiers']:
                self.stats['tiers'][tier_name] = {
                    'count': 0,
                    'emoji': tier_info['emoji'],
                    'percentage': 0.0
                }
            self.stats['tiers'][tier_name]['count'] += 1
            self.stats['total_passed'] += 1
        
        # Calculate percentages
        if self.stats['total_processed'] > 0:
            for tier_data in self.stats['tiers'].values():
                tier_data['percentage'] = (tier_data['count'] / self.stats['total_processed']) * 100
        
        # Calculate pass rate
        if self.stats['total_processed'] > 0:
            self.stats['pass_rate'] = (self.stats['total_passed'] / self.stats['total_processed']) * 100
        
        self.logger.info(f"Filtered {self.stats['total_passed']}/{self.stats['total_processed']} opportunities ({self.stats['pass_rate']:.1f}% pass rate)")
        
        return filtered_opportunities
    
    def _determine_tier(self, spread_pct: float) -> Dict[str, Any]:
        """Determine tier based on spread percentage"""
        # Sort tiers by min_spread descending to find the highest applicable tier
        sorted_tiers = sorted(
            self.tier_configs.items(),
            key=lambda x: x[1]['min_spread'],
            reverse=True
        )
        
        for tier_name, tier_config in sorted_tiers:
            if spread_pct >= tier_config['min_spread']:
                from bot.models import Tier
                return {
                    'tier': Tier(tier_name),
                    'emoji': tier_config['emoji'],
                    'color': tier_config['color'],
                    'action': tier_config['action'],
                    'priority': tier_config['priority']
                }
        
        # Default to poor tier
        return {
            'tier': Tier.POOR,
            'emoji': '⚫',
            'color': '#808080',
            'action': 'FILTERED OUT',
            'priority': 6
        }
    
    def _calculate_quality_score(self, spread_pct: float) -> float:
        """
        Calculate quality score based purely on spread percentage
        
        Args:
            spread_pct: Spread percentage
            
        Returns:
            Quality score (0-10)
        """
        # Spread-only quality scoring
        if spread_pct >= 3.0:
            return 9.5 + (spread_pct - 3.0) * 0.5  # 9.5-10.0
        elif spread_pct >= 2.5:
            return 8.5 + (spread_pct - 2.5) * 2.0  # 8.5-9.5
        elif spread_pct >= 2.0:
            return 7.0 + (spread_pct - 2.0) * 3.0  # 7.0-8.5
        elif spread_pct >= 1.5:
            return 5.0 + (spread_pct - 1.5) * 4.0  # 5.0-7.0
        elif spread_pct >= 1.0:
            return 2.5 + (spread_pct - 1.0) * 5.0  # 2.5-5.0
        else:
            return spread_pct * 2.5  # 0-2.5
    
    def _reset_stats(self):
        """Reset filtering statistics"""
        self.stats = {
            'total_processed': 0,
            'total_passed': 0,
            'total_filtered': 0,
            'pass_rate': 0.0,
            'tiers': {}
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get filtering statistics"""
        return {
            'summary': {
                'total_processed': self.stats['total_processed'],
                'total_passed': self.stats['total_passed'],
                'total_filtered': self.stats['total_filtered'],
                'pass_rate': round(self.stats['pass_rate'], 1)
            },
            'tiers': self.stats['tiers']
        }
    
    def get_alertable_opportunities(self, opportunities: List[ArbitrageOpportunity]) -> List[ArbitrageOpportunity]:
        """Get opportunities that should trigger alerts"""
        return [opp for opp in opportunities if opp.is_alertable()]
    
    def get_opportunities_by_tier(self, opportunities: List[ArbitrageOpportunity], tier: Tier) -> List[ArbitrageOpportunity]:
        """Get opportunities filtered by specific tier"""
        return [opp for opp in opportunities if opp.tier == tier]
