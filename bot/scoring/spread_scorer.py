"""
Spread Scorer Module
Pure spread-based quality scoring for arbitrage opportunities
"""

from typing import Dict, Any
from bot.models import Tier
from shared.logger import get_logger


class SpreadScorer:
    """Spread-only quality scorer for arbitrage opportunities"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def calculate_score(self, spread_percentage: float) -> float:
        """
        Calculate quality score based purely on spread percentage
        
        Args:
            spread_percentage: Spread percentage (e.g., 2.5 for 2.5%)
            
        Returns:
            Quality score (0.0 to 10.0)
        """
        # Spread-only scoring algorithm
        if spread_percentage >= 3.0:
            # Exceptional: 9.5-10.0
            return 9.5 + min((spread_percentage - 3.0) * 0.5, 0.5)
        elif spread_percentage >= 2.5:
            # Excellent: 8.5-9.5
            return 8.5 + (spread_percentage - 2.5) * 2.0
        elif spread_percentage >= 2.0:
            # Very Good: 7.0-8.5
            return 7.0 + (spread_percentage - 2.0) * 3.0
        elif spread_percentage >= 1.5:
            # Good: 5.0-7.0 (user's strategy threshold)
            return 5.0 + (spread_percentage - 1.5) * 4.0
        elif spread_percentage >= 1.0:
            # Fair: 2.5-5.0
            return 2.5 + (spread_percentage - 1.0) * 5.0
        else:
            # Poor: 0.0-2.5
            return spread_percentage * 2.5
    
    def get_tier_from_score(self, score: float) -> Tier:
        """
        Get tier from quality score
        
        Args:
            score: Quality score (0-10)
            
        Returns:
            Tier enum value
        """
        if score >= 9.5:
            return Tier.EXCEPTIONAL
        elif score >= 8.5:
            return Tier.EXCELLENT
        elif score >= 7.0:
            return Tier.VERY_GOOD
        elif score >= 5.0:
            return Tier.GOOD
        elif score >= 2.5:
            return Tier.FAIR
        else:
            return Tier.POOR
    
    def get_grade_from_score(self, score: float) -> str:
        """
        Get letter grade from quality score
        
        Args:
            score: Quality score (0-10)
            
        Returns:
            Letter grade (A+, A, B+, B, C, F)
        """
        if score >= 9.5:
            return "A+"
        elif score >= 8.5:
            return "A"
        elif score >= 7.0:
            return "B+"
        elif score >= 5.0:
            return "B"
        elif score >= 2.5:
            return "C"
        else:
            return "F"
    
    def get_score_breakdown(self, spread_percentage: float) -> Dict[str, Any]:
        """
        Get complete score breakdown for a spread
        
        Args:
            spread_percentage: Spread percentage
            
        Returns:
            Detailed score breakdown
        """
        score = self.calculate_score(spread_percentage)
        tier = self.get_tier_from_score(score)
        grade = self.get_grade_from_score(score)
        
        return {
            'spread_percentage': spread_percentage,
            'quality_score': round(score, 1),
            'tier': tier.value,
            'grade': grade,
            'is_alertable': tier.value in ['exceptional', 'excellent', 'very_good', 'good'],
            'score_breakdown': {
                'base_score': score,
                'tier_threshold': self._get_tier_threshold(tier),
                'next_tier_score': self._get_next_tier_score(spread_percentage)
            }
        }
    
    def _get_tier_threshold(self, tier: Tier) -> float:
        """Get minimum spread percentage for a tier"""
        thresholds = {
            Tier.EXCEPTIONAL: 3.0,
            Tier.EXCELLENT: 2.5,
            Tier.VERY_GOOD: 2.0,
            Tier.GOOD: 1.5,
            Tier.FAIR: 1.0,
            Tier.POOR: 0.0
        }
        return thresholds.get(tier, 0.0)
    
    def _get_next_tier_score(self, current_spread: float) -> Dict[str, Any]:
        """Get information about next tier"""
        if current_spread >= 3.0:
            return {'tier': 'MAX', 'spread_needed': 0.0, 'score_gain': 0.0}
        elif current_spread >= 2.5:
            return {'tier': 'exceptional', 'spread_needed': 3.0 - current_spread, 'score_gain': 10.0 - self.calculate_score(current_spread)}
        elif current_spread >= 2.0:
            return {'tier': 'excellent', 'spread_needed': 2.5 - current_spread, 'score_gain': 8.5 - self.calculate_score(current_spread)}
        elif current_spread >= 1.5:
            return {'tier': 'very_good', 'spread_needed': 2.0 - current_spread, 'score_gain': 7.0 - self.calculate_score(current_spread)}
        elif current_spread >= 1.0:
            return {'tier': 'good', 'spread_needed': 1.5 - current_spread, 'score_gain': 5.0 - self.calculate_score(current_spread)}
        else:
            return {'tier': 'fair', 'spread_needed': 1.0 - current_spread, 'score_gain': 2.5 - self.calculate_score(current_spread)}
    
    def validate_score(self, score: float) -> bool:
        """
        Validate that a score is within acceptable range
        
        Args:
            score: Score to validate
            
        Returns:
            True if valid, False otherwise
        """
        return 0.0 <= score <= 10.0
    
    def get_score_distribution(self, scores: list) -> Dict[str, Any]:
        """
        Get distribution statistics for a list of scores
        
        Args:
            scores: List of quality scores
            
        Returns:
            Score distribution statistics
        """
        if not scores:
            return {
                'count': 0,
                'mean': 0.0,
                'median': 0.0,
                'min': 0.0,
                'max': 0.0,
                'tier_distribution': {}
            }
        
        import statistics
        
        # Basic statistics
        distribution = {
            'count': len(scores),
            'mean': round(statistics.mean(scores), 1),
            'median': round(statistics.median(scores), 1),
            'min': round(min(scores), 1),
            'max': round(max(scores), 1)
        }
        
        # Tier distribution
        tier_counts = {}
        for score in scores:
            tier = self.get_tier_from_score(score).value
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        distribution['tier_distribution'] = tier_counts
        
        return distribution
