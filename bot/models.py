"""
Bot Data Models
Clean, minimal data models for spread-only arbitrage system
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

class Platform(Enum):
    """Supported prediction market platforms"""
    POLYMARKET = "polymarket"
    AZURO = "azuro"
    MANIFOLD = "manifold"
    LIMITLESS = "limitless"

class Tier(Enum):
    """Arbitrage opportunity tiers based on spread"""
    EXCEPTIONAL = "exceptional"
    EXCELLENT = "excellent"
    VERY_GOOD = "very_good"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"

@dataclass
class Quote:
    """Market quote with bid/ask prices"""
    market_id: str
    platform: Platform
    bid: float
    ask: float
    mid: float
    spread: float
    timestamp: datetime
    volume: Optional[float] = None  # Kept for compatibility but not used
    
    def __post_init__(self):
        """Calculate mid price and spread if not provided"""
        if self.mid is None and self.bid is not None and self.ask is not None:
            self.mid = (self.bid + self.ask) / 2
        if self.spread is None and self.bid is not None and self.ask is not None:
            self.spread = self.ask - self.bid

@dataclass
class Market:
    """Prediction market information"""
    market_id: str
    platform: Platform
    title: str
    description: str
    url: str
    category: str
    end_time: Optional[datetime]
    created_time: datetime
    is_active: bool = True
    
    def get_normalized_title(self) -> str:
        """Get normalized title for cross-platform matching"""
        return self.title.lower().strip()
    
    def get_platform_url(self) -> str:
        """Get platform-specific URL"""
        if self.platform == Platform.POLYMARKET:
            return f"https://polymarket.com/event/{self.market_id}"
        elif self.platform == Platform.AZURO:
            return f"https://bookmaker.xyz?utm_source=arbitrage_bot&utm_medium=referral"
        elif self.platform == Platform.MANIFOLD:
            return f"https://manifold.markets/{self.market_id}"
        elif self.platform == Platform.LIMITLESS:
            return f"https://limitless.exchange/events/{self.market_id}"
        return self.url

@dataclass
class ArbitrageOpportunity:
    """Arbitrage opportunity with tier information"""
    normalized_title: str
    markets: List[Dict[str, Any]]
    spread_percentage: float
    tier: Tier
    tier_emoji: str
    tier_color: str
    tier_action: str
    tier_priority: int
    quality_score: float
    created_at: datetime
    
    def get_best_spread(self) -> float:
        """Get the best spread percentage"""
        return self.spread_percentage
    
    def is_alertable(self) -> bool:
        """Check if this opportunity should trigger alerts"""
        return self.tier_priority <= 4  # GOOD tier and above
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "normalized_title": self.normalized_title,
            "markets": self.markets,
            "spread_percentage": round(self.spread_percentage, 2),
            "tier": self.tier.value,
            "tier_emoji": self.tier_emoji,
            "tier_color": self.tier_color,
            "tier_action": self.tier_action,
            "tier_priority": self.tier_priority,
            "quality_score": round(self.quality_score, 1),
            "created_at": self.created_at.isoformat(),
            "is_alertable": self.is_alertable()
        }

@dataclass
class TierConfig:
    """Configuration for a tier"""
    name: str
    min_spread: float
    emoji: str
    color: str
    action: str
    priority: int
    alert: bool
    
    def get_tier_enum(self) -> Tier:
        """Get Tier enum value"""
        return Tier(self.name)

@dataclass
class PlatformConfig:
    """Configuration for a platform adapter"""
    platform: Platform
    enabled: bool
    base_url: str
    rate_limit: int
    timeout: int
    retry_attempts: int
    retry_delay: int

@dataclass
class AlertData:
    """Data for Discord alerts"""
    opportunity: ArbitrageOpportunity
    webhook_url: str
    timestamp: datetime
    
    def get_embed_color(self) -> int:
        """Get Discord embed color from tier color"""
        color_hex = self.opportunity.tier_color.lstrip('#')
        return int(color_hex, 16) if color_hex else 0x808080
    
    def get_title(self) -> str:
        """Get alert title"""
        return f"{self.opportunity.tier_emoji} {self.opportunity.tier.value.upper()} Arbitrage: {self.opportunity.spread_percentage:.1f}% spread"

@dataclass
class HealthStatus:
    """System health status"""
    status: str
    message: str
    timestamp: datetime
    details: Dict[str, Any]
    
    def is_healthy(self) -> bool:
        """Check if system is healthy"""
        return self.status.lower() in ["healthy", "ok", "info"]
