"""
Tiered Arbitrage Filter - Spread-Only System
Pure spread percentage filtering with 6-tier categorization
No volume, no liquidity, just profit margin
"""

from typing import List, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class TierConfig:
    """Configuration for a single tier"""
    name: str
    min_spread: float
    emoji: str
    color: str
    priority: int  # 1 = highest priority
    action: str

class TieredArbitrageFilter:
    """Spread-only arbitrage filtering with tier system"""
    
    def __init__(self, min_spread: float = 0.015):
        """
        Initialize the tiered filter
        
        Args:
            min_spread: Minimum spread percentage (e.g., 0.015 for 1.5%)
        """
        self.min_spread = min_spread
        
        # Define tier system (spread-based only)
        self.tiers = {
            "exceptional": TierConfig(
                name="exceptional",
                min_spread=3.0,      # 3.0%+
                emoji="🔵",
                color="#0066ff",
                priority=1,
                action="IMMEDIATE ATTENTION REQUIRED"
            ),
            "excellent": TierConfig(
                name="excellent", 
                min_spread=2.51,     # 2.51-3.0%
                emoji="🟢",
                color="#00ff00",
                priority=2,
                action="ACT QUICKLY"
            ),
            "very_good": TierConfig(
                name="very_good",
                min_spread=2.01,     # 2.01-2.5%
                emoji="💛", 
                color="#ffff00",
                priority=3,
                action="STRONG YES"
            ),
            "good": TierConfig(
                name="good",
                min_spread=1.0,      # 1.0-2.0%
                emoji="🟠",
                color="#ffa500", 
                priority=4,
                action="YOUR STRATEGY"
            ),
            "fair": TierConfig(
                name="fair",
                min_spread=0.75,     # 0.75-1.0%
                emoji="⚪",
                color="#808080",
                priority=5,
                action="FILTERED OUT"
            ),
            "poor": TierConfig(
                name="poor",
                min_spread=0.0,      # <1.0%
                emoji="⚫",
                color="#808080",
                priority=6,
                action="FILTERED OUT"
            )
        }
        
        # Track statistics
        self.stats = {
            "total_processed": 0,
            "total_passed": 0,
            "total_filtered": 0,
            "tier_counts": {tier_name: 0 for tier_name in self.tiers.keys()}
        }
    
    def determine_tier(self, spread_percentage: float) -> str:
        """
        Determine tier based on spread percentage
        
        Args:
            spread_percentage: Spread as percentage (e.g., 2.5 for 2.5%)
            
        Returns:
            Tier name (e.g., "excellent", "very_good")
        """
        # Check tiers in order of highest to lowest spread
        for tier_name in ["exceptional", "excellent", "very_good", "good", "fair", "poor"]:
            if spread_percentage >= self.tiers[tier_name].min_spread:
                return tier_name
        return "poor"
    
    def calculate_quality_score(self, spread_percentage: float) -> float:
        """
        Calculate quality score based on spread percentage only
        Score: 0-10, where 10 = maximum quality
        
        Args:
            spread_percentage: Spread as percentage
            
        Returns:
            Quality score (0-10)
        """
        if spread_percentage >= 5.0:
            return 10.0  # Maximum score for 5%+ spreads
        
        # Linear scaling within tiers
        tier = self.determine_tier(spread_percentage)
        tier_config = self.tiers[tier]
        
        # Base score for each tier
        tier_bases = {
            "exceptional": 9.0,   # 3.0%+ starts at 9.0
            "excellent": 8.0,     # 2.51-3.0% starts at 8.0
            "very_good": 7.0,     # 2.01-2.5% starts at 7.0
            "good": 6.0,          # 1.5-2.0% starts at 6.0
            "fair": 5.0,          # 1.0-1.5% starts at 5.0
            "poor": 2.5           # <1.0% starts at 2.5
        }
        
        base_score = tier_bases[tier]
        
        # Add bonus within tier (max 1.0 point)
        if tier == "exceptional":
            # 3.0% = 9.0, 5.0% = 10.0 (linear)
            bonus = min((spread_percentage - 3.0) / 2.0, 1.0)
        elif tier == "excellent":
            # 2.51% = 8.0, 3.0% = 8.99
            bonus = (spread_percentage - 2.51) / 0.49 * 0.99
        elif tier == "very_good":
            # 2.01% = 7.0, 2.5% = 7.99
            bonus = (spread_percentage - 2.01) / 0.49 * 0.99
        elif tier == "good":
            # 1.5% = 6.0, 2.0% = 6.99
            bonus = (spread_percentage - 1.5) / 0.5 * 0.99
        elif tier == "fair":
            # 1.0% = 5.0, 1.5% = 5.99
            bonus = (spread_percentage - 1.0) / 0.5 * 0.99
        else:  # poor
            # 0% = 2.5, 1.0% = 4.99
            bonus = spread_percentage / 1.0 * 2.49
        
        return min(base_score + bonus, 10.0)
    
    def filter_and_tier_opportunities(self, opportunities: List[Dict[str, Any]], min_spread: float = None) -> List[Dict[str, Any]]:
        """
        Filter opportunities by minimum spread and add tier information
        
        Args:
            opportunities: List of arbitrage opportunities
            min_spread: Override minimum spread (uses instance default if None)
            
        Returns:
            Filtered and tiered opportunities
        """
        if min_spread is None:
            min_spread = self.min_spread
            
        logger.info(f"[TIERED FILTER] Starting filter with threshold {min_spread * 100:.1f}%")
        
        filtered_opportunities = []
        self.stats = {
            "total_processed": len(opportunities),
            "total_passed": 0,
            "total_filtered": 0,
            "tier_counts": {tier_name: 0 for tier_name in self.tiers.keys()}
        }
        
        for opp in opportunities:
            spread_pct = opp.get('spread_percentage', 0)
            
            # Determine tier
            tier = self.determine_tier(spread_pct)
            tier_config = self.tiers[tier]
            
            # Calculate quality score
            quality_score = self.calculate_quality_score(spread_pct)
            
            # Add tier information to opportunity
            opp_with_tier = opp.copy()
            opp_with_tier.update({
                'tier': tier,
                'tier_emoji': tier_config.emoji,
                'tier_color': tier_config.color,
                'tier_priority': tier_config.priority,
                'tier_action': tier_config.action,
                'quality_score': quality_score
            })
            
            # Filter based on minimum spread
            if spread_pct >= min_spread:
                filtered_opportunities.append(opp_with_tier)
                self.stats["total_passed"] += 1
                self.stats["tier_counts"][tier] += 1
                
                # Log passed opportunities
                logger.info(f"{tier_config.emoji} {tier.upper()}: {opp.get('normalized_title', 'Unknown')} - Spread: {spread_pct:.1f}% - Score: {quality_score:.1f}/10")
            else:
                self.stats["total_filtered"] += 1
                logger.info(f"❌ FILTERED: {opp.get('normalized_title', 'Unknown')} - Spread: {spread_pct:.1f}% < {min_spread * 100:.1f}%")
        
        # Log summary
        self._log_summary()
        
        return filtered_opportunities
    
    def _log_summary(self):
        """Log filtering summary"""
        logger.info("=" * 60)
        logger.info(f"TIER FILTER RESULTS (Threshold: {self.min_spread * 100:.1f}%)")
        logger.info("=" * 60)
        
        for tier_name in ["exceptional", "excellent", "very_good", "good"]:
            count = self.stats["tier_counts"][tier_name]
            tier_config = self.tiers[tier_name]
            if count > 0:
                spread_range = self._get_tier_range(tier_name)
                logger.info(f"{tier_config.emoji} {tier_name.upper()}: {count} ({spread_range})")
        
        logger.info("-" * 60)
        logger.info(f"✅ PASSED: {self.stats['total_passed']} opportunities")
        logger.info(f"❌ FILTERED: {self.stats['total_filtered']} opportunities")
        logger.info(f"📊 TOTAL: {self.stats['total_processed']} opportunities")
        logger.info("=" * 60)
    
    def _get_tier_range(self, tier_name: str) -> str:
        """Get spread range description for tier"""
        if tier_name == "exceptional":
            return "3.0%+"
        elif tier_name == "excellent":
            return "2.51-3.0%"
        elif tier_name == "very_good":
            return "2.01-2.5%"
        elif tier_name == "good":
            return "1.0-2.0%"
        elif tier_name == "fair":
            return "0.75-1.0%"
        else:
            return "<1.0%"
    
    def get_tier_breakdown(self) -> Dict[str, Any]:
        """
        Get detailed tier breakdown statistics
        
        Returns:
            Dictionary with tier statistics
        """
        total = self.stats["total_processed"]
        if total == 0:
            return {"summary": {"total_passed": 0, "total_filtered": 0}, "tiers": {}}
        
        tiers_data = {}
        for tier_name, tier_config in self.tiers.items():
            count = self.stats["tier_counts"][tier_name]
            percentage = (count / total) * 100 if total > 0 else 0
            
            tiers_data[tier_name] = {
                "count": count,
                "percentage": round(percentage, 1),
                "emoji": tier_config.emoji,
                "color": tier_config.color,
                "action": tier_config.action,
                "min_spread": tier_config.min_spread,
                "priority": tier_config.priority
            }
        
        return {
            "summary": {
                "total_passed": self.stats["total_passed"],
                "total_filtered": self.stats["total_filtered"],
                "total_processed": self.stats["total_processed"],
                "pass_rate": round((self.stats["total_passed"] / total) * 100, 1) if total > 0 else 0
            },
            "tiers": tiers_data
        }

# Global filter instance
_filter_instance = None

def get_filter(min_spread: float = 0.015) -> TieredArbitrageFilter:
    """Get or create filter instance"""
    global _filter_instance
    if _filter_instance is None or _filter_instance.min_spread != min_spread:
        _filter_instance = TieredArbitrageFilter(min_spread)
    return _filter_instance

def filter_and_tier_opportunities(opportunities: List[Dict[str, Any]], min_spread: float = 0.015) -> List[Dict[str, Any]]:
    """
    Convenience function to filter and tier opportunities
    
    Args:
        opportunities: List of arbitrage opportunities
        min_spread: Minimum spread percentage
        
    Returns:
        Filtered and tiered opportunities
    """
    filter_instance = get_filter(min_spread)
    return filter_instance.filter_and_tier_opportunities(opportunities, min_spread)

def get_tier_breakdown() -> Dict[str, Any]:
    """
    Get current tier breakdown statistics
    
    Returns:
        Dictionary with tier statistics
    """
    filter_instance = get_filter()
    return filter_instance.get_tier_breakdown()
