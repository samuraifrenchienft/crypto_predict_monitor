"""
Cross-Market Arbitrage Detector
Find best cross-platform opportunities by combining contract matching + fee calculations
Enhances existing arbitrage detector with cross-market capabilities
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import asyncio
from datetime import datetime, timezone

# Add path for imports
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'fetchers'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.dirname(__file__))

from market_normalizer import NormalizedMarket
from contract_matcher import ContractMatcher, MatchedMarketPair
from cross_market_fee_calculator import CrossMarketFeeCalculator, ArbProfitability

logger = logging.getLogger("cross_market_detector")

@dataclass
class CrossMarketArbitrageOpportunity:
    """Best cross-market arb for an event"""
    event_name: str
    yes_market: NormalizedMarket
    no_market: NormalizedMarket
    yes_platform: str
    no_platform: str
    yes_price: float
    no_price: float
    profitability: ArbProfitability
    confidence_score: float  # Contract matching score
    roi_percent: float
    net_profit: float
    execution_difficulty: str  # 'easy', 'moderate', 'hard'
    
    # Additional analysis fields (calculated in __post_init__)
    total_liquidity: float = 0.0
    risk_score: float = 0.5  # 0-1 based on various factors
    time_to_expiration: Optional[int] = None  # seconds
    platform_combo: str = ""  # "polymarket+manifold" etc
    
    def __post_init__(self):
        """Calculate derived fields"""
        self.total_liquidity = self.yes_market.total_liquidity + self.no_market.total_liquidity
        self.platform_combo = f"{self.yes_platform}+{self.no_platform}"
        
        # Calculate risk score based on various factors
        liquidity_risk = 1.0 - min(self.total_liquidity / 200000, 1.0)  # Higher risk for low liquidity
        confidence_risk = 1.0 - self.confidence_score  # Higher risk for lower confidence
        execution_risk = {'easy': 0.1, 'moderate': 0.3, 'hard': 0.6}.get(self.execution_difficulty, 0.5)
        
        self.risk_score = (liquidity_risk + confidence_risk + execution_risk) / 3
        
        # Calculate time to expiration
        if self.yes_market.expires_at:
            self.time_to_expiration = int((self.yes_market.expires_at - datetime.now(timezone.utc)).total_seconds())
        else:
            self.time_to_expiration = None

class CrossMarketArbitrageDetector:
    """
    Find BEST cross-market arbitrage opportunities
    
    This ENHANCES the existing arbitrage detector by:
    1. Finding same events across platforms
    2. Checking profitability after ALL costs
    3. Ranking by ROI and confidence
    4. Filtering for execution viability
    """
    
    def __init__(self, min_roi_percent: float = 0.25):
        self.contract_matcher = ContractMatcher()
        self.fee_calculator = CrossMarketFeeCalculator()
        self.min_roi_percent = min_roi_percent
        
        # Statistics tracking
        self.stats = {
            'total_markets_analyzed': 0,
            'matched_pairs_found': 0,
            'opportunities_detected': 0,
            'profitable_opportunities': 0,
            'average_roi': 0.0,
            'best_roi': 0.0,
            'platform_combos': {}
        }
        
        logger.info(f"🔍 CrossMarketArbitrageDetector initialized (min_roi={min_roi_percent}%)")

    async def find_best_cross_market_arbs(
        self,
        markets: List[NormalizedMarket],
        limit: int = 50
    ) -> List[CrossMarketArbitrageOpportunity]:
        """
        Find top cross-market arbitrage opportunities
        
        Algorithm:
        1. Match markets across platforms (same event)
        2. Check all YES/NO combinations
        3. Calculate actual profit (with fees)
        4. Filter by minimum ROI
        5. Rank by ROI and confidence
        6. Return top N opportunities
        """
        
        start_time = datetime.now(timezone.utc)
        self.stats['total_markets_analyzed'] = len(markets)
        
        logger.info(f"🔍 Analyzing {len(markets)} markets for cross-market arbitrage...")
        
        opportunities = []
        
        # STEP 1: Find matched market pairs
        matched_pairs = await self.contract_matcher.find_all_matched_pairs(markets)
        self.stats['matched_pairs_found'] = len(matched_pairs)
        
        logger.info(f"📊 Found {len(matched_pairs)} matched market pairs")
        
        # STEP 2: Check all YES/NO combinations
        for pair in matched_pairs:
            market_a = pair.market_a
            market_b = pair.market_b
            
            logger.debug(f"🔍 Analyzing pair: {market_a.source} + {market_b.source}")
            
            # Try all 4 combinations:
            # 1. BUY YES on A, NO on B
            arb_1 = self._check_arb_combination(
                market_a, market_b, buy_yes_on='a',
                match_confidence=pair.match_score
            )
            
            # 2. BUY YES on B, NO on A
            arb_2 = self._check_arb_combination(
                market_a, market_b, buy_yes_on='b',
                match_confidence=pair.match_score
            )
            
            # Add viable opportunities
            for arb in [arb_1, arb_2]:
                if arb and arb.profitability.is_profitable:
                    opportunities.append(arb)
                    logger.debug(f"✅ Found profitable arb: {arb.platform_combo} @ {arb.roi_percent:.2f}% ROI")
        
        # STEP 3: Sort by ROI (best first)
        opportunities.sort(key=lambda x: x.roi_percent, reverse=True)
        
        # STEP 4: Filter by minimum ROI
        viable_opportunities = [opp for opp in opportunities if opp.roi_percent >= self.min_roi_percent]
        
        # STEP 5: Return top N
        top_opportunities = viable_opportunities[:limit]
        
        # Update statistics
        self._update_statistics(opportunities, viable_opportunities)
        
        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(f"🎯 Found {len(opportunities)} total, {len(viable_opportunities)} viable cross-market arbs "
                   f"in {duration:.1f}s, returning top {len(top_opportunities)}")
        
        return top_opportunities
    
    def _check_arb_combination(
        self,
        market_a: NormalizedMarket,
        market_b: NormalizedMarket,
        buy_yes_on: str,  # 'a' or 'b'
        match_confidence: float
    ) -> Optional[CrossMarketArbitrageOpportunity]:
        """Check if specific YES/NO combination is profitable"""
        
        # Determine which market to buy YES from, NO from
        if buy_yes_on == 'a':
            yes_market = market_a
            no_market = market_b
        else:
            yes_market = market_b
            no_market = market_a
        
        # Calculate profitability
        profitability = self.fee_calculator.calculate_cross_market_profit(
            yes_platform=yes_market.source,
            yes_price=yes_market.yes_price,
            yes_liquidity=yes_market.yes_liquidity,
            no_platform=no_market.source,
            no_price=no_market.no_price,
            no_liquidity=no_market.no_liquidity,
            position_size_usd=1000  # Standard sizing
        )
        
        if not profitability.is_profitable:
            return None
        
        # Calculate execution difficulty
        execution_difficulty = self._estimate_execution_difficulty(
            yes_market, no_market
        )
        
        opp = CrossMarketArbitrageOpportunity(
            event_name=yes_market.name,
            yes_market=yes_market,
            no_market=no_market,
            yes_platform=yes_market.source,
            no_platform=no_market.source,
            yes_price=yes_market.yes_price,
            no_price=no_market.no_price,
            profitability=profitability,
            confidence_score=match_confidence,
            roi_percent=profitability.roi_percent,
            net_profit=profitability.net_profit,
            execution_difficulty=execution_difficulty
        )
        
        return opp
    
    @staticmethod
    def _estimate_execution_difficulty(market_a: NormalizedMarket, market_b: NormalizedMarket) -> str:
        """
        Estimate how hard it is to execute this arb
        
        Factors:
        - Liquidity on each leg
        - Platform availability
        - Settlement speed
        - Geographic availability
        """
        
        avg_liquidity = (market_a.total_liquidity + market_b.total_liquidity) / 2
        
        if avg_liquidity > 100000:
            return 'easy'      # Deep liquidity = fast execution
        elif avg_liquidity > 20000:
            return 'moderate'  # Moderate liquidity = some slippage
        else:
            return 'hard'      # Shallow = slippage + timing risk
    
    def _update_statistics(
        self, 
        all_opportunities: List[CrossMarketArbitrageOpportunity],
        viable_opportunities: List[CrossMarketArbitrageOpportunity]
    ) -> None:
        """Update detection statistics"""
        self.stats['opportunities_detected'] = len(all_opportunities)
        self.stats['profitable_opportunities'] = len(viable_opportunities)
        
        if viable_opportunities:
            rois = [opp.roi_percent for opp in viable_opportunities]
            self.stats['average_roi'] = sum(rois) / len(rois)
            self.stats['best_roi'] = max(rois)
            
            # Track platform combinations
            for opp in viable_opportunities:
                combo = opp.platform_combo
                if combo not in self.stats['platform_combos']:
                    self.stats['platform_combos'][combo] = 0
                self.stats['platform_combos'][combo] += 1
    
    def get_statistics(self) -> Dict[str, any]:
        """Get detection statistics"""
        return self.stats.copy()
    
    def analyze_platform_performance(self) -> Dict[str, Dict[str, any]]:
        """Analyze performance by platform combination"""
        platform_stats = {}
        
        for combo, count in self.stats['platform_combos'].items():
            platforms = combo.split('+')
            platform_stats[combo] = {
                'count': count,
                'platforms': platforms,
                'success_rate': count / max(self.stats['matched_pairs_found'], 1)
            }
        
        return platform_stats
    
    def get_top_opportunities_summary(
        self, 
        opportunities: List[CrossMarketArbitrageOpportunity],
        limit: int = 10
    ) -> Dict[str, any]:
        """Get summary of top opportunities"""
        if not opportunities:
            return {
                'count': 0,
                'average_roi': 0.0,
                'best_roi': 0.0,
                'platform_distribution': {},
                'difficulty_distribution': {'easy': 0, 'moderate': 0, 'hard': 0}
            }
        
        top_opps = opportunities[:limit]
        
        # Calculate metrics
        rois = [opp.roi_percent for opp in top_opps]
        platform_dist = {}
        difficulty_dist = {'easy': 0, 'moderate': 0, 'hard': 0}
        
        for opp in top_opps:
            # Platform distribution
            combo = opp.platform_combo
            platform_dist[combo] = platform_dist.get(combo, 0) + 1
            
            # Difficulty distribution
            difficulty_dist[opp.execution_difficulty] += 1
        
        return {
            'count': len(top_opps),
            'average_roi': sum(rois) / len(rois),
            'best_roi': max(rois),
            'platform_distribution': platform_dist,
            'difficulty_distribution': difficulty_dist
        }

# Test function
async def test_cross_market_detector():
    """Test the cross-market arbitrage detector"""
    print("🔍 Testing Cross-Market Arbitrage Detector")
    print("=" * 60)
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create detector
    detector = CrossMarketArbitrageDetector(min_roi_percent=0.1)  # Lower threshold for testing
    
    # Create sample markets (same as contract matcher test)
    from datetime import datetime, timezone
    
    markets = [
        # Perfect match - should create arbitrage opportunities
        NormalizedMarket(
            market_id="polymarket:btc-2024",
            source="polymarket",
            chain="ethereum",
            name="Bitcoin price above $100,000 by end of 2024",
            category="crypto",
            yes_price=0.35,  # Very low price - creates arbitrage
            no_price=0.68,
            spread=0.03,
            yes_liquidity=80000,
            no_liquidity=95000,
            total_liquidity=175000,
            volume_24h=350000,
            status="active",
            expires_at=datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            source_data={'description': 'Will Bitcoin price exceed $100,000 by end of 2024 according to Coinbase data'}
        ),
        # Same event on different platform - different prices
        NormalizedMarket(
            market_id="manifold:btc-2024",
            source="manifold",
            chain="ethereum",
            name="Bitcoin price above $100,000 by end of 2024",
            category="crypto",
            yes_price=0.45,  # Higher price - creates arbitrage
            no_price=0.58,
            spread=0.03,
            yes_liquidity=60000,
            no_liquidity=75000,
            total_liquidity=135000,
            volume_24h=280000,
            status="active",
            expires_at=datetime(2024, 12, 31, 23, 59, 30, tzinfo=timezone.utc),
            source_data={'description': 'Will Bitcoin price exceed $100,000 by end of 2024 according to Coinbase data'}
        ),
        # Third platform with even better prices
        NormalizedMarket(
            market_id="limitless:btc-2024",
            source="limitless",
            chain="ethereum",
            name="Bitcoin price above $100,000 by end of 2024",
            category="crypto",
            yes_price=0.40,
            no_price=0.55,  # Very low NO price - creates arbitrage
            spread=0.05,
            yes_liquidity=70000,
            no_liquidity=85000,
            total_liquidity=155000,
            volume_24h=310000,
            status="active",
            expires_at=datetime(2024, 12, 31, 23, 59, 45, tzinfo=timezone.utc),
            source_data={'description': 'Will Bitcoin price exceed $100,000 by end of 2024 according to Coinbase data'}
        ),
        # Different event - should not match
        NormalizedMarket(
            market_id="polymarket:eth-2024",
            source="polymarket",
            chain="ethereum",
            name="Ethereum price above $5,000 by end of 2024",
            category="crypto",
            yes_price=0.35,
            no_price=0.68,
            spread=0.03,
            yes_liquidity=40000,
            no_liquidity=60000,
            total_liquidity=100000,
            volume_24h=200000,
            status="active",
            expires_at=datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
            source_data={'description': 'Will Ethereum price exceed $5,000 by end of 2024 according to CoinGecko data'}
        )
    ]
    
    try:
        print(f"📊 Analyzing {len(markets)} markets...")
        
        # Find cross-market arbitrage opportunities
        opportunities = await detector.find_best_cross_market_arbs(markets, limit=10)
        
        print(f"\n🎯 RESULTS:")
        print(f"  Opportunities Found: {len(opportunities)}")
        
        if opportunities:
            print(f"\n📈 TOP OPPORTUNITIES:")
            for i, opp in enumerate(opportunities[:5], 1):
                print(f"\n{i}. {opp.platform_combo.upper()}")
                print(f"   Event: {opp.event_name}")
                print(f"   YES: {opp.yes_platform} @ ${opp.yes_price:.4f}")
                print(f"   NO:  {opp.no_platform} @ ${opp.no_price:.4f}")
                print(f"   ROI: {opp.roi_percent:.2f}%")
                print(f"   Net Profit: ${opp.net_profit:.4f}")
                print(f"   Confidence: {opp.confidence_score*100:.0f}%")
                print(f"   Execution: {opp.execution_difficulty}")
                print(f"   Total Liquidity: ${opp.total_liquidity:,.0f}")
                print(f"   Risk Score: {opp.risk_score:.2f}")
            
            # Show statistics
            stats = detector.get_statistics()
            print(f"\n📊 DETECTION STATISTICS:")
            print(f"  Markets Analyzed: {stats['total_markets_analyzed']}")
            print(f"  Matched Pairs: {stats['matched_pairs_found']}")
            print(f"  Opportunities Detected: {stats['opportunities_detected']}")
            print(f"  Profitable Opportunities: {stats['profitable_opportunities']}")
            print(f"  Average ROI: {stats['average_roi']:.2f}%")
            print(f"  Best ROI: {stats['best_roi']:.2f}%")
            
            # Platform performance
            platform_perf = detector.analyze_platform_performance()
            print(f"\n🏢 PLATFORM PERFORMANCE:")
            for combo, perf in platform_perf.items():
                print(f"  {combo}: {perf['count']} opportunities ({perf['success_rate']*100:.1f}% success rate)")
            
            # Top opportunities summary
            summary = detector.get_top_opportunities_summary(opportunities)
            print(f"\n📈 TOP OPPORTUNITIES SUMMARY:")
            print(f"  Count: {summary['count']}")
            print(f"  Average ROI: {summary['average_roi']:.2f}%")
            print(f"  Best ROI: {summary['best_roi']:.2f}%")
            print(f"  Platform Distribution: {summary['platform_distribution']}")
            print(f"  Difficulty Distribution: {summary['difficulty_distribution']}")
        
        else:
            print("❌ No profitable cross-market opportunities found")
        
        print(f"\n🎉 Cross-Market Detector Test Completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cross_market_detector())
