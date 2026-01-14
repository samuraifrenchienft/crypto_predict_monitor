"""
Professional Arbitrage Opportunity Detector
Implements investment-grade arbitrage detection with quality scoring
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional
import logging

logger = logging.getLogger("arbitrage_detector")

@dataclass
class Market:
    """Market data structure for detection"""
    id: str
    name: str
    yes_price: float
    no_price: float
    yes_liquidity: float
    no_liquidity: float
    bid_ask_spread: float
    expiration: datetime
    price_change_24h: float
    volume_24h: float
    time_to_expiration: timedelta
    status: str

@dataclass
class MarketData:
    """Raw market data structure"""
    market_id: str
    market_name: str
    yes_price: float = 0.0
    no_price: float = 0.0
    yes_bid: float = 0.0
    yes_ask: float = 0.0
    no_bid: float = 0.0
    no_ask: float = 0.0
    yes_liquidity: float = 0.0
    no_liquidity: float = 0.0
    volume_24h: float = 0.0
    spread_percentage: float = 0.0
    expires_at: datetime = None
    polymarket_link: str = ""
    analysis_link: str = ""
    market_source: str = "Polymarket"

@dataclass
class ArbitrageOpportunity:
    """Professional arbitrage opportunity structure"""
    market_id: str
    market_name: str
    yes_price: float
    no_price: float
    yes_liquidity: float
    no_liquidity: float
    spread: float  # (1 - (yes + no))
    efficiency_score: float  # 0-10
    confidence_score: float  # 0-10
    reason: str  # Why it's an arb opportunity
    expires_at: datetime
    movement_24h: float  # % change in last 24h
    volume_24h: float

class ArbitrageDetector:
    """Professional arbitrage opportunity detector"""
    
    def __init__(self, min_efficiency: float = 6.0, min_confidence: float = 6.0):
        self.min_efficiency = min_efficiency
        self.min_confidence = min_confidence
        self.detection_count = 0
        
    def detect_opportunities(self, markets: List[Market]) -> List[ArbitrageOpportunity]:
        """
        Find top-tier arbitrage opportunities
        
        Scoring criteria:
        1. Spread (wider = better opportunity)
        2. Liquidity (higher = safer trade)
        3. Volume momentum (increasing = better)
        4. Price movement pattern (stable = less risky)
        5. Bid-ask alignment (predictable = better)
        """
        self.detection_count += 1
        opportunities = []
        
        logger.info(f"🔍 Detection #{self.detection_count}: Analyzing {len(markets)} markets")
        
        for market in markets:
            if not self._passes_filters(market):
                continue
            
            efficiency_score = self._calculate_efficiency(market)
            confidence_score = self._calculate_confidence(market)
            
            if efficiency_score >= self.min_efficiency and confidence_score >= self.min_confidence:
                opp = ArbitrageOpportunity(
                    market_id=market.id,
                    market_name=market.name,
                    yes_price=market.yes_price,
                    no_price=market.no_price,
                    yes_liquidity=market.yes_liquidity,
                    no_liquidity=market.no_liquidity,
                    spread=1.0 - (market.yes_price + market.no_price),
                    efficiency_score=efficiency_score,
                    confidence_score=confidence_score,
                    reason=self._generate_reason(market, efficiency_score),
                    expires_at=market.expiration,
                    movement_24h=market.price_change_24h,
                    volume_24h=market.volume_24h
                )
                opportunities.append(opp)
                logger.debug(f"🎯 Found opportunity: {market.name} ({efficiency_score:.1f}/{confidence_score:.1f})")
        
        # Sort by combined score (efficiency + confidence)
        opportunities.sort(
            key=lambda x: (x.efficiency_score + x.confidence_score) / 2,
            reverse=True
        )
        
        # Return top 20
        top_opportunities = opportunities[:20]
        
        logger.info(f"✅ Found {len(top_opportunities)} quality opportunities (top {len(top_opportunities)}/20)")
        
        # Log top 5 for visibility
        for i, opp in enumerate(top_opportunities[:5]):
            combined_score = (opp.efficiency_score + opp.confidence_score) / 2
            logger.info(f"  {i+1}. {opp.market_name}: {combined_score:.1f}/10 ({opp.reason})")
        
        return top_opportunities
    
    def _passes_filters(self, market: Market) -> bool:
        """Pre-filter to avoid low-quality markets"""
        passes = (
            market.yes_liquidity > 40000 and
            market.no_liquidity > 40000 and
            market.volume_24h > 500000 and
            (1.0 - (market.yes_price + market.no_price)) > 0.01 and  # >1% spread
            market.time_to_expiration > timedelta(days=1) and
            market.status == 'active'
        )
        
        if not passes:
            logger.debug(f"❌ Filtered {market.name}: "
                        f"Liq: ${market.yes_liquidity:,.0f}/${market.no_liquidity:,.0f}, "
                        f"Vol: ${market.volume_24h:,.0f}, "
                        f"Spread: {(1.0 - (market.yes_price + market.no_price))*100:.2f}%, "
                        f"Time: {market.time_to_expiration.days}d, "
                        f"Status: {market.status}")
        
        return passes
    
    def _calculate_efficiency(self, market: Market) -> float:
        """
        Score opportunity based on spread and liquidity
        Higher spread + high liquidity = better opportunity
        """
        spread = 1.0 - (market.yes_price + market.no_price)
        spread_score = min(spread * 100 * 5, 10)  # Convert % to 0-10 scale
        
        min_liquidity = min(market.yes_liquidity, market.no_liquidity)
        liquidity_score = min((min_liquidity / 100000) * 10, 10)  # Scale by $100K
        
        return (spread_score * 0.6) + (liquidity_score * 0.4)
    
    def _calculate_confidence(self, market: Market) -> float:
        """
        Score opportunity based on stability and volume
        """
        # Price stability (small 24h movement = stable = confident)
        movement = abs(market.price_change_24h)
        stability_score = max(10 - (movement * 10), 0)  # Penalize volatility
        
        # Volume confidence (high volume = many traders = efficient)
        volume_score = min((market.volume_24h / 5000000) * 10, 10)  # Scale by $5M
        
        # Bid-ask spread tightness (at order book level)
        bid_ask_score = 10 if market.bid_ask_spread < 0.001 else 7
        
        return (stability_score * 0.5) + (volume_score * 0.3) + (bid_ask_score * 0.2)
    
    def _generate_reason(self, market: Market, score: float) -> str:
        """Generate human-readable reason for alert"""
        spread_pct = (1.0 - (market.yes_price + market.no_price)) * 100
        
        if score >= 8.5:
            reason = f"Premium inefficiency detected: {spread_pct:.2f}% spread with deep liquidity"
        elif score >= 7.0:
            reason = f"Strong arb signal: {spread_pct:.2f}% spread + {market.volume_24h/1e6:.1f}M volume"
        else:
            reason = f"Opportunity: {spread_pct:.2f}% spread in {market.name}"
        
        return reason
    
    def get_detection_stats(self) -> dict:
        """Get detection statistics"""
        return {
            "detection_count": self.detection_count,
            "min_efficiency_threshold": self.min_efficiency,
            "min_confidence_threshold": self.min_confidence
        }

# Utility functions for creating test data
def create_test_markets() -> List[Market]:
    """Create test market data for demonstration"""
    now = datetime.utcnow()
    
    test_markets = [
        # Premium opportunity
        Market(
            id="bitcoin-election-2024",
            name="Bitcoin Q4 2024 Election Impact",
            yes_price=0.42,
            no_price=0.55,  # Changed to make yes+no < 1.0
            yes_liquidity=75000,
            no_liquidity=85000,
            bid_ask_spread=0.0008,
            expiration=now + timedelta(days=15),
            price_change_24h=0.02,
            volume_24h=2500000,
            time_to_expiration=timedelta(days=15),
            status='active'
        ),
        # Strong opportunity
        Market(
            id="trump-indictment-q4",
            name="Trump Indictment Before Q4 2024",
            yes_price=0.35,
            no_price=0.60,  # Changed to make yes+no < 1.0
            yes_liquidity=55000,
            no_liquidity=60000,
            bid_ask_spread=0.0012,
            expiration=now + timedelta(days=30),
            price_change_24h=0.05,
            volume_24h=1800000,
            time_to_expiration=timedelta(days=30),
            status='active'
        ),
        # Medium opportunity
        Market(
            id="biden-polls-december",
            name="Biden Approval Above 45% in December",
            yes_price=0.48,
            no_price=0.49,  # Changed to make yes+no < 1.0
            yes_liquidity=45000,
            no_liquidity=50000,
            bid_ask_spread=0.0015,
            expiration=now + timedelta(days=20),
            price_change_24h=0.08,
            volume_24h=900000,
            time_to_expiration=timedelta(days=20),
            status='active'
        ),
        # Below threshold (filtered out)
        Market(
            id="low-quality-market",
            name="Low Volume Test Market",
            yes_price=0.49,
            no_price=0.48,  # Changed to make yes+no < 1.0
            yes_liquidity=15000,  # Below threshold
            no_liquidity=20000,  # Below threshold
            bid_ask_spread=0.002,
            expiration=now + timedelta(days=10),
            price_change_24h=0.15,
            volume_24h=200000,  # Below threshold
            time_to_expiration=timedelta(days=10),
            status='active'
        ),
        # Poor spread (filtered out)
        Market(
            id="tight-spread-market",
            name="Efficient Market Test",
            yes_price=0.495,
            no_price=0.502,  # Changed to make yes+no < 1.0
            yes_liquidity=60000,
            no_liquidity=65000,
            bid_ask_spread=0.0005,
            expiration=now + timedelta(days=25),
            price_change_24h=0.01,
            volume_24h=800000,
            time_to_expiration=timedelta(days=25),
            status='active'
        )
    ]
    
    return test_markets

# Example usage and testing
def run_opportunity_detection_demo():
    """Run demonstration of opportunity detection"""
    print("🎯 Professional Arbitrage Opportunity Detection Demo")
    print("=" * 60)
    
    # Enable debug logging
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    
    # Initialize detector
    detector = ArbitrageDetector(min_efficiency=6.0, min_confidence=6.0)
    
    # Get test markets
    markets = create_test_markets()
    print(f"📊 Analyzing {len(markets)} test markets...")
    
    # Debug: Check each market
    for market in markets:
        spread = (1.0 - (market.yes_price + market.no_price)) * 100
        print(f"🔍 {market.name}: YES=${market.yes_price:.3f}, NO=${market.no_price:.3f}, Spread={spread:.2f}%")
        print(f"   Liquidity: ${market.yes_liquidity:,.0f}/${market.no_liquidity:,.0f}, Volume: ${market.volume_24h:,.0f}")
        passes = detector._passes_filters(market)
        print(f"   Passes filter: {passes}")
        if passes:
            eff_score = detector._calculate_efficiency(market)
            conf_score = detector._calculate_confidence(market)
            print(f"   Scores: Efficiency={eff_score:.1f}, Confidence={conf_score:.1f}")
        print()
    
    # Detect opportunities
    opportunities = detector.detect_opportunities(markets)
    
    # Display results
    print(f"\n🎯 Found {len(opportunities)} quality opportunities:")
    print("-" * 60)
    
    for i, opp in enumerate(opportunities):
        combined_score = (opp.efficiency_score + opp.confidence_score) / 2
        spread_pct = opp.spread * 100
        
        print(f"{i+1}. {opp.market_name}")
        print(f"   Market ID: {opp.market_id}")
        print(f"   YES/NO Prices: ${opp.yes_price:.3f} / ${opp.no_price:.3f}")
        print(f"   Spread: {spread_pct:.2f}%")
        print(f"   Liquidity: ${opp.yes_liquidity:,.0f} / ${opp.no_liquidity:,.0f}")
        print(f"   Efficiency: {opp.efficiency_score:.1f}/10")
        print(f"   Confidence: {opp.confidence_score:.1f}/10")
        print(f"   Combined: {combined_score:.1f}/10")
        print(f"   Volume 24h: ${opp.volume_24h:,.0f}")
        print(f"   Movement 24h: {opp.movement_24h:+.1f}%")
        print(f"   Expires: {opp.expires_at.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Reason: {opp.reason}")
        print()
    
    # Show detection stats
    stats = detector.get_detection_stats()
    print(f"📈 Detection Statistics:")
    print(f"   Total Detections: {stats['detection_count']}")
    print(f"   Efficiency Threshold: {stats['min_efficiency_threshold']}")
    print(f"   Confidence Threshold: {stats['min_confidence_threshold']}")

if __name__ == "__main__":
    run_opportunity_detection_demo()
