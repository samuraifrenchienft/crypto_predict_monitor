"""
Arbitrage Detection & Professional Alerts Integration
Connects opportunity detection with investment-grade Discord alerts
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from professional_alerts import ProfessionalArbitrageAlerts, ArbitrageOpportunity
from arbitrage.opportunity_detector import ArbitrageDetector, Market

logger = logging.getLogger("arbitrage_integration")

class ArbitrageIntegration:
    """Integration between detection and professional Discord alerts"""
    
    def __init__(self, min_efficiency: float = 6.5, min_confidence: float = 6.5):
        self.detector = ArbitrageDetector(min_efficiency, min_confidence)
        self.alert_system = ProfessionalArbitrageAlerts()
        self.alerts_sent = 0
        self.opportunities_detected = 0
    
    def convert_detector_to_professional(self, detector_opp) -> ArbitrageOpportunity:
        """Convert detector opportunity to professional alert format"""
        
        # Calculate time window
        time_remaining = detector_opp.expires_at - datetime.utcnow()
        hours_remaining = time_remaining.total_seconds() / 3600
        
        if hours_remaining >= 24:
            time_window = f"Valid for ~{int(hours_remaining)} hours (expires in {int(hours_remaining/24)} days)"
        elif hours_remaining >= 1:
            time_window = f"Valid for ~{int(hours_remaining)} minutes (expires in {int(hours_remaining/60)} blocks)"
        else:
            time_window = f"Valid for ~{int(hours_remaining*60)} minutes (expires soon)"
        
        # Generate filters applied
        min_liquidity = min(detector_opp.yes_liquidity, detector_opp.no_liquidity)
        filters = []
        
        if detector_opp.spread * 100 >= 3.0:
            filters.append("Spread > 3%")
        elif detector_opp.spread * 100 >= 2.0:
            filters.append("Spread > 2%")
        else:
            filters.append("Spread > 1.5%")
        
        if min_liquidity >= 75000:
            filters.append("Liquidity > $75K")
        elif min_liquidity >= 50000:
            filters.append("Liquidity > $50K")
        else:
            filters.append("Liquidity > $40K")
        
        if detector_opp.volume_24h >= 2000000:
            filters.append("Volume > $2M 24h")
        elif detector_opp.volume_24h >= 1000000:
            filters.append("Volume > $1M 24h")
        else:
            filters.append("Volume > $500K 24h")
        
        filters_applied = " | ".join(filters)
        
        # Convert confidence score to 0-100 scale
        confidence_100 = detector_opp.confidence_score * 10
        
        return ArbitrageOpportunity(
            market_name=detector_opp.market_name,
            market_id=detector_opp.market_id,
            opportunity_type="Arb Opportunity",
            quality_score=detector_opp.efficiency_score,  # Use efficiency as quality
            confidence_score=confidence_100,
            spread_percentage=detector_opp.spread * 100,
            yes_price=detector_opp.yes_price,
            yes_liquidity=detector_opp.yes_liquidity,
            no_price=detector_opp.no_price,
            no_liquidity=detector_opp.no_liquidity,
            time_window=time_window,
            polymarket_link=f"https://polymarket.com/market/{detector_opp.market_id}",
            analysis_link=f"https://api.example.com/analysis/{detector_opp.market_id}",
            filters_applied=filters_applied,
            expires_at=detector_opp.expires_at
        )
    
    async def detect_and_alert(self, markets: List[Market]) -> Dict[str, Any]:
        """Complete detection and alert workflow"""
        logger.info(f"🔄 Starting professional arbitrage detection for {len(markets)} markets...")
        
        # Detect opportunities
        detector_opps = self.detector.detect_opportunities(markets)
        self.opportunities_detected += len(detector_opps)
        
        if not detector_opps:
            logger.info("📊 No quality opportunities detected")
            return {
                "opportunities_detected": 0,
                "alerts_sent": 0,
                "opportunities": []
            }
        
        # Convert to professional format
        professional_opps = [
            self.convert_detector_to_professional(opp) 
            for opp in detector_opps
        ]
        
        # Send professional Discord alerts
        logger.info(f"📢 Sending {len(professional_opps)} professional Discord alerts...")
        
        async with self.alert_system as alerter:
            success_count = await alerter.send_multiple_alerts(professional_opps)
            self.alerts_sent += success_count
            
            logger.info(f"✅ Sent {success_count}/{len(professional_opps)} professional Discord alerts successfully")
        
        # Return comprehensive results
        return {
            "opportunities_detected": len(detector_opps),
            "alerts_sent": success_count,
            "opportunities": [
                {
                    "market_name": opp.market_name,
                    "market_id": opp.market_id,
                    "quality_score": opp.quality_score,
                    "confidence_score": opp.confidence_score,
                    "spread_percentage": opp.spread_percentage,
                    "confidence_tier": alerter.get_confidence_tier(opp.confidence_score),
                    "color_code": f"#{alerter.get_embed_color(opp.confidence_score):06x}",
                    "liquidity": f"${min(opp.yes_liquidity, opp.no_liquidity):,.0f}",
                    "volume_24h": f"${detector_opp.volume_24h:,.0f}",
                    "reason": detector_opp.reason,
                    "time_window": opp.time_window
                }
                for opp, detector_opp in zip(professional_opps, detector_opps)
            ]
        }
    
    async def send_health_alert(self, message: str, level: str = "info") -> bool:
        """Send health alert to Discord"""
        async with self.alert_system as alerter:
            return await alerter.send_health_alert(message, level)
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration statistics"""
        detector_stats = self.detector.get_detection_stats()
        
        return {
            "detector_stats": detector_stats,
            "integration_stats": {
                "opportunities_detected": self.opportunities_detected,
                "alerts_sent": self.alerts_sent,
                "alert_success_rate": (self.alerts_sent / max(self.opportunities_detected, 1)) * 100
            }
        }

# Test data and demo
def create_test_markets() -> List[Market]:
    """Create test market data for demonstration"""
    now = datetime.utcnow()
    
    test_markets = [
        # Premium opportunity (will get GREEN border)
        Market(
            id="bitcoin-election-2024",
            name="Bitcoin Q4 2024 Election Impact",
            yes_price=0.42,
            no_price=0.55,
            yes_liquidity=75000,
            no_liquidity=85000,
            bid_ask_spread=0.0008,
            expiration=now + timedelta(hours=36),
            price_change_24h=0.02,
            volume_24h=2500000,
            time_to_expiration=timedelta(hours=36),
            status='active'
        ),
        # Strong opportunity (will get GREEN border)
        Market(
            id="trump-indictment-q4",
            name="Trump Indictment Before Q4 2024",
            yes_price=0.35,
            no_price=0.60,
            yes_liquidity=55000,
            no_liquidity=60000,
            bid_ask_spread=0.0012,
            expiration=now + timedelta(days=2),
            price_change_24h=0.05,
            volume_24h=1800000,
            time_to_expiration=timedelta(days=2),
            status='active'
        ),
        # Medium opportunity (will get YELLOW border)
        Market(
            id="biden-polls-december",
            name="Biden Approval Above 45% in December",
            yes_price=0.48,
            no_price=0.49,
            yes_liquidity=45000,
            no_liquidity=50000,
            bid_ask_spread=0.0015,
            expiration=now + timedelta(hours=18),
            price_change_24h=0.08,
            volume_24h=900000,
            time_to_expiration=timedelta(hours=18),
            status='active'
        ),
        # Lower confidence opportunity (will get BLUE border)
        Market(
            id="crypto-regulation-q1",
            name="Crypto Regulation Q1 2024",
            yes_price=0.38,
            no_price=0.59,
            yes_liquidity=42000,
            no_liquidity=48000,
            bid_ask_spread=0.0018,
            expiration=now + timedelta(hours=12),
            price_change_24h=0.12,
            volume_24h=750000,
            time_to_expiration=timedelta(hours=12),
            status='active'
        ),
        # Below threshold (filtered out)
        Market(
            id="low-quality-market",
            name="Low Volume Test Market",
            yes_price=0.49,
            no_price=0.48,
            yes_liquidity=15000,  # Below threshold
            no_liquidity=20000,  # Below threshold
            bid_ask_spread=0.002,
            expiration=now + timedelta(hours=6),
            price_change_24h=0.15,
            volume_24h=200000,  # Below threshold
            time_to_expiration=timedelta(hours=6),
            status='active'
        )
    ]
    
    return test_markets

# Demo function
async def run_professional_integration_demo():
    """Demonstrate the professional integration system"""
    print("🎯 Professional Arbitrage Integration Demo")
    print("=" * 60)
    
    # Initialize integration
    integration = ArbitrageIntegration(min_efficiency=6.5, min_confidence=6.5)
    
    # Create test markets
    markets = create_test_markets()
    print(f"📊 Processing {len(markets)} markets through professional detection and alert pipeline...")
    
    # Run detection and alerting
    results = await integration.detect_and_alert(markets)
    
    # Display results
    print(f"\n🎯 Professional Integration Results:")
    print(f"  Opportunities Detected: {results['opportunities_detected']}")
    print(f"  Discord Alerts Sent: {results['alerts_sent']}")
    
    if results['opportunities']:
        print(f"\n📈 Professional Opportunities with Color Coding:")
        for i, opp in enumerate(results['opportunities']):
            print(f"  {i+1}. {opp['market_name']}")
            print(f"     Quality: {opp['quality_score']:.1f}/10")
            print(f"     Confidence: {opp['confidence_score']:.0f}% ({opp['confidence_tier']})")
            print(f"     Color: {opp['color_code']} (LEFT BORDER)")
            print(f"     Spread: {opp['spread_percentage']:.1f}% | Liquidity: {opp['liquidity']}")
            print(f"     Volume: {opp['volume_24h']} | Time: {opp['time_window']}")
            print(f"     Reason: {opp['reason']}")
            print()
    
    # Show integration stats
    stats = integration.get_integration_stats()
    print(f"📊 Integration Statistics:")
    print(f"  Total Detections: {stats['detector_stats']['detection_count']}")
    print(f"  Opportunities Found: {stats['integration_stats']['opportunities_detected']}")
    print(f"  Alerts Sent: {stats['integration_stats']['alerts_sent']}")
    print(f"  Alert Success Rate: {stats['integration_stats']['alert_success_rate']:.1f}%")
    
    # Send health alert
    await integration.send_health_alert(
        f"✅ Professional integration demo completed!\n"
        f"📊 Processed {len(markets)} markets\n"
        f"🎯 Found {results['opportunities_detected']} opportunities\n"
        f"📢 Sent {results['alerts_sent']} professional Discord alerts\n"
        f"🎨 Color-coded alerts: 🟢 HIGH | 🟡 MEDIUM | 🔵 LOWER",
        "success"
    )
    
    print(f"\n🎨 Professional Discord Alert Features:")
    print(f"  ✅ Color-coded LEFT BORDERS for visual scanning")
    print(f"  ✅ Investment-grade embed layout")
    print(f"  ✅ Actionable intelligence with links")
    print(f"  ✅ Professional branding and formatting")
    print(f"  ✅ Rate limiting and error handling")

if __name__ == "__main__":
    asyncio.run(run_professional_integration_demo())
