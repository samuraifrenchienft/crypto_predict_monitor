"""
Quality Scoring System for Arbitrage Opportunities
Calculates investment-grade quality scores (0-10 scale)
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import math

class QualityScorer:
    """Investment-grade quality scoring for arbitrage opportunities"""
    
    def __init__(self):
        # Quality thresholds (configurable)
        self.spread_weights = {
            "excellent": 3.0,    # 3%+ spread
            "very_good": 2.0,    # 2-3% spread
            "good": 1.5,         # 1.5-2% spread
            "fair": 1.0,         # 1-1.5% spread
            "poor": 0.5          # <1% spread
        }
        
        self.liquidity_thresholds = {
            "excellent": 100000,  # $100K+
            "very_good": 50000,   # $50K-$100K
            "good": 25000,        # $25K-$50K
            "fair": 10000,        # $10K-$25K
            "poor": 0             # <$10K
        }
        
        self.volume_thresholds = {
            "excellent": 1000000, # $1M+ 24h volume
            "very_good": 500000,  # $500K-$1M
            "good": 250000,       # $250K-$500K
            "fair": 100000,       # $100K-$250K
            "poor": 0             # <$100K
        }
    
    def calculate_spread_score(self, spread_percentage: float) -> float:
        """Calculate spread quality score (0-3 points)"""
        if spread_percentage >= self.spread_weights["excellent"]:
            return 3.0
        elif spread_percentage >= self.spread_weights["very_good"]:
            return 2.5
        elif spread_percentage >= self.spread_weights["good"]:
            return 2.0
        elif spread_percentage >= self.spread_weights["fair"]:
            return 1.5
        elif spread_percentage >= self.spread_weights["poor"]:
            return 1.0
        else:
            return 0.5
    
    def calculate_liquidity_score(self, yes_liquidity: float, no_liquidity: float) -> float:
        """Calculate liquidity quality score (0-2 points)"""
        min_liquidity = min(yes_liquidity, no_liquidity)
        
        if min_liquidity >= self.liquidity_thresholds["excellent"]:
            return 2.0
        elif min_liquidity >= self.liquidity_thresholds["very_good"]:
            return 1.7
        elif min_liquidity >= self.liquidity_thresholds["good"]:
            return 1.4
        elif min_liquidity >= self.liquidity_thresholds["fair"]:
            return 1.0
        else:
            return 0.5
    
    def calculate_volume_score(self, volume_24h: float) -> float:
        """Calculate volume quality score (0-2 points)"""
        if volume_24h >= self.volume_thresholds["excellent"]:
            return 2.0
        elif volume_24h >= self.volume_thresholds["very_good"]:
            return 1.7
        elif volume_24h >= self.volume_thresholds["good"]:
            return 1.4
        elif volume_24h >= self.volume_thresholds["fair"]:
            return 1.0
        else:
            return 0.5
    
    def calculate_time_score(self, expires_at: datetime) -> float:
        """Calculate time window quality score (0-1.5 points)"""
        time_remaining = expires_at - datetime.utcnow()
        hours_remaining = time_remaining.total_seconds() / 3600
        
        if hours_remaining >= 24:      # 24+ hours
            return 1.5
        elif hours_remaining >= 12:    # 12-24 hours
            return 1.2
        elif hours_remaining >= 6:     # 6-12 hours
            return 1.0
        elif hours_remaining >= 2:     # 2-6 hours
            return 0.7
        elif hours_remaining >= 1:     # 1-2 hours
            return 0.4
        else:                          # <1 hour
            return 0.2
    
    def calculate_volatility_score(self, price_volatility: float) -> float:
        """Calculate volatility quality score (0-1.5 points)"""
        # Moderate volatility is good for arbitrage
        if 0.05 <= price_volatility <= 0.15:  # 5-15% volatility
            return 1.5
        elif 0.03 <= price_volatility <= 0.20:  # 3-20% volatility
            return 1.2
        elif 0.01 <= price_volatility <= 0.25:  # 1-25% volatility
            return 0.8
        else:  # Too low or too high volatility
            return 0.4
    
    def calculate_market_confidence(self, market_data: Dict[str, Any]) -> float:
        """Calculate market confidence score (0-10 scale)"""
        spread_score = self.calculate_spread_score(market_data.get("spread_percentage", 0))
        liquidity_score = self.calculate_liquidity_score(
            market_data.get("yes_liquidity", 0),
            market_data.get("no_liquidity", 0)
        )
        volume_score = self.calculate_volume_score(market_data.get("volume_24h", 0))
        time_score = self.calculate_time_score(market_data.get("expires_at", datetime.utcnow() + timedelta(hours=1)))
        
        # Total possible score: 8.5 points (removed volatility)
        total_score = (
            spread_score +      # 0-3 points
            liquidity_score +   # 0-2 points
            volume_score +      # 0-2 points
            time_score        # 0-1.5 points
        )
        
        return min(total_score, 8.5)  # Cap at 8.5 (reduced from 10.0)
    
    def get_confidence_percentage(self, quality_score: float) -> float:
        """Convert quality score to confidence percentage"""
        # Map 0-10 scale to 50-100% confidence range
        confidence = 50 + (quality_score / 10.0) * 50
        return min(confidence, 100.0)
    
    def get_quality_level(self, quality_score: float) -> str:
        """Get quality level description"""
        if quality_score >= 9.0:
            return "EXCEPTIONAL"
        elif quality_score >= 8.5:
            return "EXCELLENT"
        elif quality_score >= 7.5:
            return "VERY_GOOD"
        elif quality_score >= 6.5:
            return "GOOD"
        elif quality_score >= 5.0:
            return "FAIR"
        else:
            return "POOR"
    
    def should_alert(self, quality_score: float, min_threshold: float = 6.5) -> bool:
        """Determine if opportunity meets minimum quality threshold"""
        return quality_score >= min_threshold

# Example usage and testing
def test_quality_scoring():
    """Test the quality scoring system"""
    scorer = QualityScorer()
    
    # Test case 1: Excellent opportunity
    excellent_opportunity = {
        "spread_percentage": 3.2,
        "yes_liquidity": 75000,
        "no_liquidity": 80000,
        "volume_24h": 1200000,
        "expires_at": datetime.utcnow() + timedelta(hours=36),
        "price_volatility": 0.12
    }
    
    score = scorer.calculate_market_confidence(excellent_opportunity)
    confidence = scorer.get_confidence_percentage(score)
    level = scorer.get_quality_level(score)
    
    print(f"Excellent Opportunity:")
    print(f"  Quality Score: {score:.1f}/8.5")
    print(f"  Confidence: {confidence:.0f}%")
    print(f"  Level: {level}")
    print(f"  Should Alert: {scorer.should_alert(score)}")
    
    # Test case 2: Poor opportunity
    poor_opportunity = {
        "spread_percentage": 0.8,
        "yes_liquidity": 5000,
        "no_liquidity": 7000,
        "volume_24h": 50000,
        "expires_at": datetime.utcnow() + timedelta(minutes=30),
        "price_volatility": 0.02
    }
    
    score = scorer.calculate_market_confidence(poor_opportunity)
    confidence = scorer.get_confidence_percentage(score)
    level = scorer.get_quality_level(score)
    
    print(f"\nPoor Opportunity:")
    print(f"  Quality Score: {score:.1f}/8.5")
    print(f"  Confidence: {confidence:.0f}%")
    print(f"  Level: {level}")
    print(f"  Should Alert: {scorer.should_alert(score)}")

if __name__ == "__main__":
    test_quality_scoring()
