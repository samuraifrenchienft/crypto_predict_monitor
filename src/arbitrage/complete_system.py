# src/arbitrage/complete_system.py
# Complete Cross-Platform Arbitrage Detection System
# Integrates: Contract Matching + Fee Calculation + Profit Detection

import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

class Platform(Enum):
    """Supported prediction market platforms"""
    POLYMARKET = "polymarket"
    MANIFOLD = "manifold"
    LIMITLESS = "limitless"
    AZURO = "azuro"

@dataclass
class MarketData:
    """Unified market data format"""
    platform: Platform
    market_id: str
    title: str
    description: str
    yes_price: float  # 0-1
    no_price: float   # 0-1
    yes_liquidity: float
    no_liquidity: float
    volume_24h: float
    expires_at: datetime
    image_url: Optional[str] = None

@dataclass
class MatchedMarketPair:
    """Two markets confirmed as same event"""
    market_a: MarketData
    market_b: MarketData
    match_score: float  # 0-1 confidence
    normalized_title: str

@dataclass
class CrossPlatformArb:
    """Cross-platform arbitrage opportunity"""
    matched_pair: MatchedMarketPair
    
    # Buy side
    buy_platform: Platform
    buy_price: float
    buy_liquidity: float
    
    # Sell side
    sell_platform: Platform
    sell_price: float
    sell_liquidity: float
    
    # Calculations
    spread_percent: float  # Raw spread before fees
    platform_fees: float   # Combined fee cost
    slippage_estimate: float
    net_profit: float      # Profit after ALL costs
    roi_percent: float     # Return on investment
    is_viable: bool        # Above minimum threshold

# ============================================================================
# PART 1: PLATFORM FEE CALCULATOR
# ============================================================================

class PlatformFeeCalculator:
    """Calculate real fees per platform"""
    
    # Platform-specific taker fees (when buying)
    TAKER_FEES = {
        Platform.POLYMARKET: 0.02,    # 2%
        Platform.MANIFOLD: 0.02,      # 2%
        Platform.LIMITLESS: 0.015,    # 1.5%
        Platform.AZURO: 0.025,        # 2.5%
    }
    
    # Slippage by liquidity depth
    SLIPPAGE_MODEL = {
        'deep': 0.005,      # >$100K liquidity = 0.5% slippage
        'moderate': 0.010,  # $20K-$100K = 1% slippage
        'shallow': 0.025,   # <$20K = 2.5% slippage
    }
    
    MIN_VIABLE_PROFIT = 0.005  # 0.5% minimum profit threshold
    
    @staticmethod
    def calculate_arb_profit(
        buy_platform: Platform,
        buy_price: float,
        buy_liquidity: float,
        sell_platform: Platform,
        sell_price: float,
        sell_liquidity: float,
        position_size: float = 1000.0
    ) -> Tuple[float, float, float, float]:
        """
        Calculate actual profit after ALL costs
        
        Returns: (net_profit, roi_percent, total_fees, slippage)
        """
        
        # 1. TAKER FEES (buying on both sides)
        buy_fee = buy_price * PlatformFeeCalculator.TAKER_FEES[buy_platform]
        sell_fee = sell_price * PlatformFeeCalculator.TAKER_FEES[sell_platform]
        total_fees = buy_fee + sell_fee
        
        # 2. SLIPPAGE (estimated by liquidity)
        buy_slippage = buy_price * PlatformFeeCalculator._estimate_slippage(buy_liquidity)
        sell_slippage = sell_price * PlatformFeeCalculator._estimate_slippage(sell_liquidity)
        total_slippage = buy_slippage + sell_slippage
        
        # 3. TOTAL COST
        gross_spread = sell_price - buy_price
        total_cost = total_fees + total_slippage
        net_profit = gross_spread - total_cost
        
        # 4. ROI (return on investment)
        roi_percent = (net_profit / buy_price) * 100 if buy_price > 0 else 0
        
        return net_profit, roi_percent, total_fees, total_slippage
    
    @staticmethod
    def _estimate_slippage(liquidity: float) -> float:
        """Estimate slippage based on order book depth"""
        if liquidity > 100000:
            return PlatformFeeCalculator.SLIPPAGE_MODEL['deep']
        elif liquidity > 20000:
            return PlatformFeeCalculator.SLIPPAGE_MODEL['moderate']
        else:
            return PlatformFeeCalculator.SLIPPAGE_MODEL['shallow']

# ============================================================================
# PART 2: CONTRACT MATCHER (from comprehensive_matcher.py)
# ============================================================================

class ContractMatcher:
    """Match same events across platforms"""
    
    def __init__(self):
        self.min_match_score = 0.85  # Require 85%+ confidence
        
        # Noise words to remove
        self.noise_words = {
            'will', 'is', 'the', 'a', 'an', 'be', 'or', 'and',
            'by', 'in', 'on', 'at', 'to', 'for', 'of', 'if',
            'prediction', 'market', 'yes', 'no', 'resolved',
        }
        
        # Category keywords
        self.crypto_keywords = ['bitcoin', 'ethereum', 'btc', 'eth', 'crypto', 'price']
        self.sports_keywords = ['football', 'basketball', 'game', 'win', 'score', 'nfl']
        self.politics_keywords = ['election', 'vote', 'president', 'senate', 'congress']
    
    async def find_matched_pairs(
        self,
        markets: List[MarketData]
    ) -> List[MatchedMarketPair]:
        """Find all same events across platforms"""
        
        matched_pairs = []
        
        # Group by normalized title
        groups = self._group_by_normalized_title(markets)
        
        # Find pairs within groups
        for normalized_title, market_list in groups.items():
            
            if len(market_list) < 2:
                continue  # Need at least 2 platforms
            
            # Check all pairs
            for i, market_a in enumerate(market_list):
                for market_b in market_list[i+1:]:
                    
                    score = self._calculate_match_score(market_a, market_b)
                    
                    if score >= self.min_match_score:
                        pair = MatchedMarketPair(
                            market_a=market_a,
                            market_b=market_b,
                            match_score=score,
                            normalized_title=normalized_title
                        )
                        matched_pairs.append(pair)
                        logger.info(f"Matched: {market_a.platform.value} + {market_b.platform.value} ({normalized_title}) - Score: {score:.2f}")
        
        return matched_pairs
    
    def _calculate_match_score(self, market_a: MarketData, market_b: MarketData) -> float:
        """Score how confident we are these are the same event (0-1)"""
        
        from difflib import SequenceMatcher
        
        normalized_a = self._normalize_title(market_a.title)
        normalized_b = self._normalize_title(market_b.title)
        
        # Title similarity (0-1)
        title_ratio = SequenceMatcher(None, normalized_a, normalized_b).ratio()
        
        # Category match (0-1)
        cat_a = self._classify_category(market_a.title)
        cat_b = self._classify_category(market_b.title)
        category_match = 1.0 if cat_a == cat_b else 0.5
        
        # Combined score
        score = (title_ratio * 0.7) + (category_match * 0.3)
        
        return score
    
    def _normalize_title(self, title: str) -> str:
        """Normalize market title for comparison"""
        
        title = title.lower()
        
        # Remove noise words
        words = [w for w in title.split() if w not in self.noise_words]
        normalized = ' '.join(words)
        
        # Common replacements
        replacements = {
            'bitcoin': 'btc', 'ethereum': 'eth', 'eoy': 'end',
            '>': 'above', '<': 'below', '>=': 'above_equal',
        }
        
        for old, new in replacements.items():
            normalized = normalized.replace(old, new)
        
        return normalized.strip()
    
    def _classify_category(self, title: str) -> str:
        """Classify market category"""
        
        title_lower = title.lower()
        
        if any(kw in title_lower for kw in self.crypto_keywords):
            return 'crypto'
        elif any(kw in title_lower for kw in self.sports_keywords):
            return 'sports'
        elif any(kw in title_lower for kw in self.politics_keywords):
            return 'politics'
        else:
            return 'other'
    
    def _group_by_normalized_title(self, markets: List[MarketData]) -> Dict[str, List[MarketData]]:
        """Group markets by normalized title"""
        
        groups = {}
        
        for market in markets:
            normalized = self._normalize_title(market.title)
            
            if normalized not in groups:
                groups[normalized] = []
            
            groups[normalized].append(market)
        
        return groups

# ============================================================================
# PART 3: CROSS-PLATFORM ARBITRAGE DETECTOR
# ============================================================================

class CrossPlatformArbitrageDetector:
    """Find cross-platform arbitrage opportunities"""
    
    def __init__(self):
        self.matcher = ContractMatcher()
        self.fee_calc = PlatformFeeCalculator()
    
    async def detect_all_arbitrage(
        self,
        markets: List[MarketData],
        min_roi: float = 0.5  # 0.5% minimum ROI
    ) -> List[CrossPlatformArb]:
        """
        Find ALL cross-platform arbitrage opportunities
        
        Algorithm:
        1. Match same events across platforms
        2. For each match, check all BUY/SELL combinations
        3. Calculate profit after fees
        4. Filter by ROI threshold
        5. Sort by profitability
        """
        
        opportunities = []
        
        # STEP 1: Match events across platforms
        matched_pairs = await self.matcher.find_matched_pairs(markets)
        logger.info(f"Found {len(matched_pairs)} matched market pairs")
        
        # STEP 2: Check all combinations
        for pair in matched_pairs:
            
            # Try both: Buy A → Sell B, and Buy B → Sell A
            arb_1 = self._check_arb_opportunity(
                pair, pair.market_a, pair.market_b, min_roi
            )
            arb_2 = self._check_arb_opportunity(
                pair, pair.market_b, pair.market_a, min_roi
            )
            
            if arb_1 and arb_1.is_viable:
                opportunities.append(arb_1)
            if arb_2 and arb_2.is_viable:
                opportunities.append(arb_2)
        
        # STEP 3: Sort by profitability
        opportunities.sort(key=lambda x: x.roi_percent, reverse=True)
        
        logger.info(f"Found {len(opportunities)} viable arbitrage opportunities")
        
        return opportunities
    
    def _check_arb_opportunity(
        self,
        pair: MatchedMarketPair,
        buy_market: MarketData,
        sell_market: MarketData,
        min_roi: float
    ) -> Optional[CrossPlatformArb]:
        """Check if specific BUY/SELL combination is profitable"""
        
        # Calculate profit
        net_profit, roi, fees, slippage = self.fee_calc.calculate_arb_profit(
            buy_platform=buy_market.platform,
            buy_price=buy_market.yes_price,
            buy_liquidity=buy_market.yes_liquidity,
            sell_platform=sell_market.platform,
            sell_price=sell_market.yes_price,
            sell_liquidity=sell_market.yes_liquidity
        )
        
        # Check viability
        is_viable = (
            net_profit > 0 and
            roi >= min_roi and
            buy_market.yes_liquidity >= 20000 and  # Min liquidity
            sell_market.yes_liquidity >= 20000
        )
        
        if not is_viable:
            return None
        
        spread_percent = (sell_market.yes_price - buy_market.yes_price) * 100
        
        arb = CrossPlatformArb(
            matched_pair=pair,
            buy_platform=buy_market.platform,
            buy_price=buy_market.yes_price,
            buy_liquidity=buy_market.yes_liquidity,
            sell_platform=sell_market.platform,
            sell_price=sell_market.yes_price,
            sell_liquidity=sell_market.yes_liquidity,
            spread_percent=spread_percent,
            platform_fees=fees,
            slippage_estimate=slippage,
            net_profit=net_profit,
            roi_percent=roi,
            is_viable=True
        )
        
        logger.info(
            f"Arb Found: Buy {buy_market.platform.value} YES ${buy_market.yes_price:.4f} → "
            f"Sell {sell_market.platform.value} YES ${sell_market.yes_price:.4f} = "
            f"${net_profit:.4f} profit ({roi:.2f}% ROI)"
        )
        
        return arb

# ============================================================================
# PART 4: INTEGRATION INTO MAIN LOOP
# ============================================================================

class CompleteArbitrageSystem:
    """Production-ready complete arbitrage system"""
    
    def __init__(self):
        self.detector = CrossPlatformArbitrageDetector()
    
    async def run_complete_scan(
        self,
        markets: List[MarketData],
        min_roi: float = 0.5
    ) -> List[CrossPlatformArb]:
        """
        Run complete arbitrage scan
        
        Returns: List of viable opportunities sorted by ROI
        """
        
        logger.info(f"Starting arbitrage scan on {len(markets)} markets")
        
        # Find cross-platform arbitrage
        opportunities = await self.detector.detect_all_arbitrage(
            markets, min_roi=min_roi
        )
        
        return opportunities
