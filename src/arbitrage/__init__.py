"""
Cross-Platform Arbitrage Detection Package
"""

from .complete_system import (
    Platform,
    MarketData,
    MatchedMarketPair,
    CrossPlatformArb,
    PlatformFeeCalculator,
    ContractMatcher,
    CrossPlatformArbitrageDetector,
    CompleteArbitrageSystem,
)

__all__ = [
    'Platform',
    'MarketData',
    'MatchedMarketPair',
    'CrossPlatformArb',
    'PlatformFeeCalculator',
    'ContractMatcher',
    'CrossPlatformArbitrageDetector',
    'CompleteArbitrageSystem',
]
