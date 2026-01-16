"""
Arbitrage System Configuration
Professional settings for arbitrage detection and alerting
"""

from datetime import timedelta
from typing import Dict, Any

class ArbitrageConfig:
    """Configuration for professional arbitrage system"""
    
    # Quality thresholds
    MIN_QUALITY_THRESHOLD = 6.5  # Minimum quality score to consider (0-10 scale)
    HIGH_QUALITY_THRESHOLD = 8.5  # High confidence threshold
    MEDIUM_QUALITY_THRESHOLD = 6.5  # Medium confidence threshold
    
    # Market filters (matching updated config.yaml)
    MIN_SPREAD_PERCENTAGE = 0.015  # From updated config.yaml thresholds.min_spread (1.5%)
    # Remove arbitrary liquidity and volume requirements - user didn't specify these
    
    # Alert settings
    MAX_ALERTS_PER_BATCH = 5  # Maximum alerts to send in one batch
    ALERT_RATE_LIMIT_SECONDS = 1  # Seconds between alerts
    DETAILED_ALERTS = True  # Send detailed embeds by default
    
    # Color coding for quality levels
    QUALITY_COLORS = {
        "exceptional": 0x0066ff,  # Blue (#0066ff) - 3%+ spread
        "excellent": 0x00ff00,    # Green (#00ff00) - 2.51-3% spread
        "very_good": 0xffff00,    # Yellow (#ffff00) - 2.01-2.5% spread
        "good": 0xffa500,        # Orange (#ffa500) - 1.5-2% spread
        "fair": 0x808080,         # Gray
        "poor": 0x808080          # Gray
    }
    
    # Quality score ranges
    QUALITY_RANGES = {
        "exceptional": (9.0, 10.0),
        "excellent": (8.5, 9.0),
        "very_good": (7.5, 8.5),
        "good": (6.5, 7.5),
        "fair": (5.0, 6.5),
        "poor": (0.0, 5.0)
    }
    
    # Discord webhook URLs (set via environment variables)
    DISCORD_WEBHOOKS = {
        "arbitrage": "CPM_WEBHOOK_URL",  # For arbitrage alerts
        "health": "DISCORD_HEALTH_WEBHOOK_URL"  # For health alerts only
    }
    
    # Time windows
    DEFAULT_TIME_WINDOW_HOURS = 24
    MIN_TIME_WINDOW_MINUTES = 30
    MAX_TIME_WINDOW_HOURS = 168  # 1 week
    
    # Market sources
    SUPPORTED_MARKETS = [
        "Polymarket",
        "Manifold", 
        "Limitless",
        "Kalshi"
    ]
    
    # Scoring weights (total must sum to 8.5)
    SCORING_WEIGHTS = {
        "spread": 3.0,        # 35.3% of total score
        "liquidity": 2.0,     # 23.5% of total score
        "volume": 2.0,        # 23.5% of total score
        "time": 1.5,          # 17.6% of total score
        # Removed "volatility": 1.5 (was 17.6%)
    }
    
    # Liquidity thresholds
    LIQUIDITY_THRESHOLDS = {
        "excellent": 100000,  # $100K+
        "very_good": 50000,   # $50K-$100K
        "good": 25000,        # $25K-$50K
        "fair": 10000,        # $10K-$25K
        "poor": 0             # <$10K
    }
    
    # Volume thresholds
    VOLUME_THRESHOLDS = {
        "excellent": 1000000, # $1M+ 24h volume
        "very_good": 500000,  # $500K-$1M
        "good": 250000,       # $250K-$500K
        "fair": 100000,       # $100K-$250K
        "poor": 0             # <$100K
    }
    
    # Spread thresholds (matching user's strategy)
    SPREAD_THRESHOLDS = {
        "exceptional": 3.0,     # 3%+ spread - Blue
        "excellent": 2.51,      # 2.51-3% spread - Green
        "very_good": 2.01,      # 2.01-2.5% spread - Yellow
        "good": 1.5,            # 1.5-2% spread - Orange
        "fair": 1.0,            # 1-1.5% spread
        "poor": 0.5             # <1% spread
    }
    
    # Branding
    BRAND_NAME = "CPM Monitor"
    BRAND_TAGLINE = "Premium Arbitrage Detection"
    BRAND_ICON = "https://i.imgur.com/7GkUJvA.png"
    BRAND_LOGO = "https://i.imgur.com/7GkUJvA.png"
    
    # Alert templates
    ALERT_TEMPLATES = {
        "title": "🔥 ARBITRAGE OPPORTUNITY DETECTED",
        "footer_text": f"{BRAND_NAME} | {BRAND_TAGLINE}",
        "username": "CPM Arbitrage Alerts",
        "health_username": "CPM Health Monitor"
    }
    
    @classmethod
    def get_quality_level(cls, score: float) -> str:
        """Get quality level from score"""
        for level, (min_score, max_score) in cls.QUALITY_RANGES.items():
            if min_score <= score < max_score:
                return level
        return "poor"
    
    @classmethod
    def get_color(cls, score: float) -> int:
        """Get Discord color for quality score"""
        level = cls.get_quality_level(score)
        return cls.QUALITY_COLORS.get(level, cls.QUALITY_COLORS["poor"])
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate configuration settings"""
        issues = []
        
        # Check scoring weights sum to 8.5
        total_weight = sum(cls.SCORING_WEIGHTS.values())
        if abs(total_weight - 8.5) > 0.1:
            issues.append(f"Scoring weights sum to {total_weight}, should be 8.5")
        
        # Check thresholds are logical
        if cls.MIN_QUALITY_THRESHOLD > cls.HIGH_QUALITY_THRESHOLD:
            issues.append("MIN_QUALITY_THRESHOLD should be <= HIGH_QUALITY_THRESHOLD")
        
        # Check time windows
        if cls.MIN_TIME_WINDOW_MINUTES >= cls.MAX_TIME_WINDOW_HOURS * 60:
            issues.append("MIN_TIME_WINDOW should be < MAX_TIME_WINDOW")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "config": {
                "min_quality": cls.MIN_QUALITY_THRESHOLD,
                "high_quality": cls.HIGH_QUALITY_THRESHOLD,
                "min_spread": cls.MIN_SPREAD_PERCENTAGE,
                "min_liquidity": cls.MIN_LIQUIDITY_USD,
                "max_alerts_per_batch": cls.MAX_ALERTS_PER_BATCH
            }
        }

# Global configuration instance
config = ArbitrageConfig()

# Configuration validation
def validate_arbitrage_config():
    """Validate arbitrage configuration"""
    validation_result = config.validate_config()
    
    if not validation_result["valid"]:
        print("⚠️ Configuration Issues Found:")
        for issue in validation_result["issues"]:
            print(f"  - {issue}")
        return False
    
    print("✅ Arbitrage configuration is valid")
    return True

if __name__ == "__main__":
    validate_arbitrage_config()
