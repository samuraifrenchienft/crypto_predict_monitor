"""
Quality Scoring - Spread-Only System
Pure spread percentage quality scoring (0-10 scale)
No volume, no liquidity, just profit margin quality
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class SpreadOnlyQualityScorer:
    """Spread-only quality scoring system"""
    
    def __init__(self):
        """Initialize the quality scorer"""
        # Quality tiers based on spread percentage
        self.tiers = {
            "exceptional": {"min_spread": 3.0, "base_score": 9.0, "max_score": 10.0},
            "excellent": {"min_spread": 2.51, "base_score": 8.0, "max_score": 8.99},
            "very_good": {"min_spread": 2.01, "base_score": 7.0, "max_score": 7.99},
            "good": {"min_spread": 1.5, "base_score": 6.0, "max_score": 6.99},
            "fair": {"min_spread": 1.0, "base_score": 5.0, "max_score": 5.99},
            "poor": {"min_spread": 0.0, "base_score": 2.5, "max_score": 4.99}
        }
    
    def calculate_quality_score(self, spread_percentage: float) -> float:
        """
        Calculate quality score based on spread percentage only
        
        Args:
            spread_percentage: Spread as percentage (e.g., 2.5 for 2.5%)
            
        Returns:
            Quality score (0-10)
        """
        if spread_percentage >= 5.0:
            return 10.0  # Maximum score for 5%+ spreads
        
        # Determine tier
        tier = self._determine_tier(spread_percentage)
        tier_config = self.tiers[tier]
        
        # Calculate score within tier
        if tier == "exceptional":
            # 3.0% = 9.0, 5.0% = 10.0 (linear)
            score = 9.0 + min((spread_percentage - 3.0) / 2.0, 1.0)
        elif tier == "excellent":
            # 2.51% = 8.0, 3.0% = 8.99
            score = 8.0 + ((spread_percentage - 2.51) / 0.49) * 0.99
        elif tier == "very_good":
            # 2.01% = 7.0, 2.5% = 7.99
            score = 7.0 + ((spread_percentage - 2.01) / 0.49) * 0.99
        elif tier == "good":
            # 1.5% = 6.0, 2.0% = 6.99
            score = 6.0 + ((spread_percentage - 1.5) / 0.5) * 0.99
        elif tier == "fair":
            # 1.0% = 5.0, 1.5% = 5.99
            score = 5.0 + ((spread_percentage - 1.0) / 0.5) * 0.99
        else:  # poor
            # 0% = 2.5, 1.0% = 4.99
            score = 2.5 + (spread_percentage / 1.0) * 2.49
        
        return min(score, 10.0)
    
    def _determine_tier(self, spread_percentage: float) -> str:
        """Determine tier based on spread percentage"""
        if spread_percentage >= 3.0:
            return "exceptional"
        elif spread_percentage >= 2.51:
            return "excellent"
        elif spread_percentage >= 2.01:
            return "very_good"
        elif spread_percentage >= 1.5:
            return "good"
        elif spread_percentage >= 1.0:
            return "fair"
        else:
            return "poor"
    
    def get_score_breakdown(self, spread_percentage: float) -> Dict[str, Any]:
        """
        Get detailed score breakdown
        
        Args:
            spread_percentage: Spread as percentage
            
        Returns:
            Dictionary with score breakdown
        """
        quality_score = self.calculate_quality_score(spread_percentage)
        tier = self._determine_tier(spread_percentage)
        
        return {
            "spread_percentage": spread_percentage,
            "quality_score": round(quality_score, 2),
            "tier": tier,
            "grade": self._get_grade(quality_score),
            "recommendation": self._get_recommendation(tier),
            "score_components": {
                "spread_score": quality_score,
                "volume_score": 0,  # Disabled
                "liquidity_score": 0,  # Disabled
                "time_score": 0  # Disabled
            }
        }
    
    def _get_grade(self, score: float) -> str:
        """Get letter grade for score"""
        if score >= 9.5:
            return "A+"
        elif score >= 9.0:
            return "A"
        elif score >= 8.5:
            return "A-"
        elif score >= 8.0:
            return "B+"
        elif score >= 7.5:
            return "B"
        elif score >= 7.0:
            return "B-"
        elif score >= 6.5:
            return "C+"
        elif score >= 6.0:
            return "C"
        elif score >= 5.5:
            return "C-"
        elif score >= 5.0:
            return "D+"
        elif score >= 4.5:
            return "D"
        else:
            return "F"
    
    def _get_recommendation(self, tier: str) -> str:
        """Get recommendation based on tier"""
        recommendations = {
            "exceptional": "IMMEDIATE ACTION - Maximum profit opportunity",
            "excellent": "ACT QUICKLY - High profit opportunity",
            "very_good": "STRONG CONSIDERATION - Good profit opportunity",
            "good": "CONSIDER - Meets minimum strategy",
            "fair": "BELOW THRESHOLD - Consider passing",
            "poor": "AVOID - Low profit opportunity"
        }
        return recommendations.get(tier, "UNKNOWN")

# Global scorer instance
_scorer_instance = None

def get_scorer() -> SpreadOnlyQualityScorer:
    """Get or create scorer instance"""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = SpreadOnlyQualityScorer()
    return _scorer_instance

def calculate_quality_score(spread_percentage: float) -> float:
    """
    Convenience function to calculate quality score
    
    Args:
        spread_percentage: Spread as percentage
        
    Returns:
        Quality score (0-10)
    """
    scorer = get_scorer()
    return scorer.calculate_quality_score(spread_percentage)

def get_score_breakdown(spread_percentage: float) -> Dict[str, Any]:
    """
    Convenience function to get score breakdown
    
    Args:
        spread_percentage: Spread as percentage
        
    Returns:
        Dictionary with score breakdown
    """
    scorer = get_scorer()
    return scorer.get_score_breakdown(spread_percentage)
