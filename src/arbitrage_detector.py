"""
Professional Arbitrage Detector
Integrates quality scoring with Discord alerts for top-tier opportunities
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from arbitrage_alerts import ArbitrageAlert, ArbitrageOpportunity, create_opportunity_from_data
from quality_scoring import QualityScorer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("arbitrage_detector")

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
    price_volatility: float = 0.0
    expires_at: datetime = None
    polymarket_link: str = ""
    analysis_link: str = ""
    market_source: str = "Polymarket"

class ArbitrageDetector:
    """Professional arbitrage opportunity detector"""
    
    def __init__(self, min_quality_threshold: float = 6.5):
        self.quality_scorer = QualityScorer()
        self.min_quality_threshold = min_quality_threshold
        self.alert_system = ArbitrageAlert()
        self.detected_opportunities: List[ArbitrageOpportunity] = []
        
    def calculate_spread_percentage(self, yes_price: float, no_price: float) -> float:
        """Calculate spread percentage"""
        # For binary markets: spread = |(yes_price + no_price) - 1.0|
        # But we want the inefficiency percentage
        theoretical_no = 1.0 - yes_price
        spread = abs(no_price - theoretical_no)
        return spread * 100  # Convert to percentage
    
    def calculate_liquidity_metrics(self, yes_bid: float, yes_ask: float, 
                                   no_bid: float, no_ask: float,
                                   yes_liquidity: float, no_liquidity: float) -> tuple:
        """Calculate refined liquidity metrics"""
        # Use bid-ask spread as liquidity quality indicator
        yes_spread = yes_ask - yes_bid
        no_spread = no_ask - no_bid
        
        # Adjust liquidity based on spread quality
        yes_liquidity_quality = yes_liquidity * (1.0 - yes_spread)
        no_liquidity_quality = no_liquidity * (1.0 - no_spread)
        
        return yes_liquidity_quality, no_liquidity_quality
    
    def detect_opportunity(self, market_data: MarketData) -> Optional[ArbitrageOpportunity]:
        """Detect if market data represents a quality arbitrage opportunity"""
        
        # Calculate refined metrics
        spread_percentage = self.calculate_spread_percentage(market_data.yes_price, market_data.no_price)
        yes_liquidity, no_liquidity = self.calculate_liquidity_metrics(
            market_data.yes_bid, market_data.yes_ask,
            market_data.no_bid, market_data.no_ask,
            market_data.yes_liquidity, market_data.no_liquidity
        )
        
        # Prepare data for quality scoring
        scoring_data = {
            "spread_percentage": spread_percentage,
            "yes_liquidity": yes_liquidity,
            "no_liquidity": no_liquidity,
            "volume_24h": market_data.volume_24h,
            "expires_at": market_data.expires_at,
            "price_volatility": market_data.price_volatility
        }
        
        # Calculate quality score
        quality_score = self.quality_scorer.calculate_market_confidence(scoring_data)
        confidence = self.quality_scorer.get_confidence_percentage(quality_score)
        
        # Check if meets minimum threshold
        if not self.quality_scorer.should_alert(quality_score, self.min_quality_threshold):
            return None
        
        # Calculate time window
        time_remaining = market_data.expires_at - datetime.utcnow()
        hours_remaining = time_remaining.total_seconds() / 3600
        time_window = f"Valid for ~{int(hours_remaining)} minutes (expires in {int(hours_remaining/60)} blocks)" if hours_remaining < 24 else f"Valid for ~{int(hours_remaining)} hours"
        
        # Create opportunity
        opportunity = ArbitrageOpportunity(
            market_name=market_data.market_name,
            opportunity_type="Arb Opportunity",
            quality_score=quality_score,
            spread_percentage=spread_percentage,
            confidence=confidence,
            yes_price=market_data.yes_price,
            yes_liquidity=yes_liquidity,
            no_price=market_data.no_price,
            no_liquidity=no_liquidity,
            time_window=time_window,
            polymarket_link=market_data.polymarket_link,
            analysis_link=market_data.analysis_link,
            filters_applied=self._get_filters_applied(spread_percentage, yes_liquidity, no_liquidity, market_data.volume_24h),
            expires_at=market_data.expires_at,
            market_source=market_data.market_source
        )
        
        return opportunity
    
    def _get_filters_applied(self, spread: float, yes_liq: float, no_liq: float, volume: float) -> str:
        """Generate filter description for opportunity - SPREAD-ONLY"""
        filters = []
        
        if spread >= 3.0:
            filters.append("Spread > 3% (EXCEPTIONAL)")
        elif spread >= 2.51:
            filters.append("Spread > 2.51% (EXCELLENT)")
        elif spread >= 2.01:
            filters.append("Spread > 2.01% (VERY GOOD)")
        elif spread >= 1.5:
            filters.append("Spread > 1.5% (GOOD)")
        elif spread >= 1.0:
            filters.append("Spread > 1% (FAIR)")
        else:
            filters.append("Spread detected")
        
        # NO LIQUIDITY OR VOLUME FILTERS - spread-only arbitrage
        
        return " | ".join(filters)
    
    async def analyze_markets(self, market_data_list: List[MarketData]) -> List[ArbitrageOpportunity]:
        """Analyze multiple markets for arbitrage opportunities"""
        opportunities = []
        
        for market_data in market_data_list:
            opportunity = self.detect_opportunity(market_data)
            if opportunity:
                opportunities.append(opportunity)
                logger.info(f"🎯 Quality opportunity detected: {opportunity.market_name} ({opportunity.quality_score:.1f}/10)")
        
        # Sort by quality score (highest first)
        opportunities.sort(key=lambda x: x.quality_score, reverse=True)
        
        self.detected_opportunities = opportunities
        return opportunities
    
    async def send_alerts(self, opportunities: List[ArbitrageOpportunity], detailed: bool = True) -> int:
        """Send Discord alerts for detected opportunities"""
        if not opportunities:
            logger.info("No quality opportunities to alert")
            return 0
        
        async with self.alert_system as alerter:
            success_count = await alerter.send_multiple_alerts(opportunities, detailed)
            return success_count
    
    async def detect_and_alert(self, market_data_list: List[MarketData], detailed: bool = True) -> Dict[str, Any]:
        """Complete detection and alert workflow"""
        logger.info(f"🔍 Analyzing {len(market_data_list)} markets for arbitrage opportunities...")
        
        # Detect opportunities
        opportunities = await self.analyze_markets(market_data_list)
        
        # Send alerts
        success_count = await self.send_alerts(opportunities, detailed)
        
        # Return summary
        summary = {
            "total_markets_analyzed": len(market_data_list),
            "opportunities_detected": len(opportunities),
            "alerts_sent": success_count,
            "opportunities": [
                {
                    "market": opp.market_name,
                    "quality_score": opp.quality_score,
                    "spread": opp.spread_percentage,
                    "confidence": opp.confidence
                }
                for opp in opportunities[:5]  # Top 5 opportunities
            ]
        }
        
        logger.info(f"✅ Analysis complete: {len(opportunities)} opportunities detected, {success_count} alerts sent")
        return summary

# Utility functions for creating test data
def create_test_market_data() -> List[MarketData]:
    """Create test market data for demonstration"""
    now = datetime.utcnow()
    
    test_markets = [
        # High-quality opportunity
        MarketData(
            market_id="bitcoin-election",
            market_name="Bitcoin Q4 Election Impact",
            yes_price=0.42,
            no_price=0.61,
            yes_bid=0.415,
            yes_ask=0.425,
            no_bid=0.605,
            no_ask=0.615,
            yes_liquidity=50000,
            no_liquidity=60000,
            volume_24h=1200000,
            spread_percentage=2.3,
            price_volatility=0.12,
            expires_at=now + timedelta(hours=45),
            polymarket_link="https://polymarket.com/market/bitcoin-q4-election-impact",
            analysis_link="https://api.example.com/analysis/bitcoin-q4"
        ),
        # Medium-quality opportunity
        MarketData(
            market_id="trump-indictment",
            market_name="Trump Indictment Before Election",
            yes_price=0.35,
            no_price=0.68,
            yes_bid=0.345,
            yes_ask=0.355,
            no_bid=0.675,
            no_ask=0.685,
            yes_liquidity=30000,
            no_liquidity=35000,
            volume_24h=600000,
            spread_percentage=1.8,
            price_volatility=0.08,
            expires_at=now + timedelta(hours=24),
            polymarket_link="https://polymarket.com/market/trump-indictment-election",
            analysis_link="https://api.example.com/analysis/trump-indictment"
        ),
        # Low-quality (below threshold)
        MarketData(
            market_id="biden-polls",
            market_name="Biden Approval Above 45%",
            yes_price=0.48,
            no_price=0.54,
            yes_bid=0.475,
            yes_ask=0.485,
            no_bid=0.535,
            no_ask=0.545,
            yes_liquidity=8000,
            no_liquidity=10000,
            volume_24h=80000,
            spread_percentage=0.8,
            price_volatility=0.03,
            expires_at=now + timedelta(hours=2),
            polymarket_link="https://polymarket.com/market/biden-approval-45",
            analysis_link="https://api.example.com/analysis/biden-polls"
        )
    ]
    
    return test_markets

# Example usage
async def run_arbitrage_detection_demo():
    """Run demonstration of arbitrage detection system"""
    detector = ArbitrageDetector(min_quality_threshold=6.5)
    
    # Get test market data
    market_data = create_test_market_data()
    
    # Run detection and alerting
    results = await detector.detect_and_alert(market_data, detailed=True)
    
    print("\n📊 Detection Summary:")
    print(f"  Markets Analyzed: {results['total_markets_analyzed']}")
    print(f"  Opportunities Detected: {results['opportunities_detected']}")
    print(f"  Alerts Sent: {results['alerts_sent']}")
    
    print("\n🎯 Top Opportunities:")
    for opp in results['opportunities']:
        print(f"  {opp['market']}: {opp['quality_score']:.1f}/10 ({opp['spread']:.1f}% spread)")

if __name__ == "__main__":
    asyncio.run(run_arbitrage_detection_demo())
