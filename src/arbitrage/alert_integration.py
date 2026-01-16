"""
Integration between ArbitrageDetector and Discord Alerts
Connects opportunity detection with professional Discord alerting
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from opportunity_detector import ArbitrageDetector, ArbitrageOpportunity, Market
from arbitrage_alerts import ArbitrageAlert, ArbitrageOpportunity as DiscordOpportunity

logger = logging.getLogger("arbitrage_integration")

class ArbitrageAlertIntegration:
    """Integrates detection with Discord alerting"""
    
    def __init__(self, min_efficiency: float = 6.5, min_confidence: float = 6.5):
        self.detector = ArbitrageDetector(min_efficiency, min_confidence)
        self.alert_system = ArbitrageAlert()
        self.alerts_sent = 0
        self.opportunities_detected = 0
        
    def convert_to_discord_format(self, opportunity: ArbitrageOpportunity) -> DiscordOpportunity:
        """Convert detector opportunity to Discord alert format"""
        # Calculate quality level and color
        combined_score = (opportunity.efficiency_score + opportunity.confidence_score) / 2
        
        # Generate time window
        time_remaining = opportunity.expires_at - datetime.utcnow()
        hours_remaining = time_remaining.total_seconds() / 3600
        if hours_remaining >= 24:
            time_window = f"Valid for ~{int(hours_remaining)} hours (expires in {int(hours_remaining/24)} days)"
        else:
            time_window = f"Valid for ~{int(hours_remaining)} minutes (expires in {int(hours_remaining/60)} blocks)"
        
        # Generate filters applied
        min_liquidity = min(opportunity.yes_liquidity, opportunity.no_liquidity)
        filters = []
        
        if opportunity.spread * 100 >= 3.0:
            filters.append("Spread > 3%")
        elif opportunity.spread * 100 >= 2.0:
            filters.append("Spread > 2%")
        else:
            filters.append("Spread > 1%")
            
        if min_liquidity >= 75000:
            filters.append("Liquidity > $75K")
        elif min_liquidity >= 50000:
            filters.append("Liquidity > $50K")
        else:
            filters.append("Liquidity > $40K")
            
        if opportunity.volume_24h >= 2000000:
            filters.append("Volume > $2M 24h")
        elif opportunity.volume_24h >= 1000000:
            filters.append("Volume > $1M 24h")
        else:
            filters.append("Volume > $500K 24h")
        
        filters_applied = " | ".join(filters)
        
        return DiscordOpportunity(
            market_name=opportunity.market_name,
            opportunity_type="Arb Opportunity",
            quality_score=combined_score,
            spread_percentage=opportunity.spread * 100,
            confidence=opportunity.confidence_score * 10,  # Convert to 0-100 scale
            yes_price=opportunity.yes_price,
            yes_liquidity=opportunity.yes_liquidity,
            no_price=opportunity.no_price,
            no_liquidity=opportunity.no_liquidity,
            time_window=time_window,
            polymarket_link=f"https://polymarket.com/market/{opportunity.market_id}",
            analysis_link=f"https://api.example.com/analysis/{opportunity.market_id}",
            filters_applied=filters_applied,
            expires_at=opportunity.expires_at,
            market_source="Polymarket"
        )
    
    async def detect_and_alert(self, markets: List[Market], detailed: bool = True) -> Dict[str, Any]:
        """Detect opportunities and send Discord alerts"""
        logger.info(f"🔄 Starting detection and alert workflow for {len(markets)} markets...")
        
        # Detect opportunities
        opportunities = self.detector.detect_opportunities(markets)
        self.opportunities_detected += len(opportunities)
        
        if not opportunities:
            logger.info("📊 No quality opportunities detected")
            return {
                "opportunities_detected": 0,
                "alerts_sent": 0,
                "opportunities": []
            }
        
        # Convert to Discord format
        discord_opportunities = [
            self.convert_to_discord_format(opp) 
            for opp in opportunities
        ]
        
        # Send Discord alerts
        logger.info(f"📢 Sending {len(discord_opportunities)} Discord alerts...")
        
        async with self.alert_system as alerter:
            success_count = await alerter.send_multiple_alerts(discord_opportunities, detailed)
            self.alerts_sent += success_count
            
            logger.info(f"✅ Sent {success_count}/{len(discord_opportunities)} Discord alerts successfully")
        
        # Return results
        return {
            "opportunities_detected": len(opportunities),
            "alerts_sent": success_count,
            "opportunities": [
                {
                    "market_name": opp.market_name,
                    "market_id": opp.market_id,
                    "efficiency_score": opp.efficiency_score,
                    "confidence_score": opp.confidence_score,
                    "combined_score": (opp.efficiency_score + opp.confidence_score) / 2,
                    "spread_percentage": opp.spread * 100,
                    "liquidity": f"${min(opp.yes_liquidity, opp.no_liquidity):,.0f}",
                    "volume_24h": f"${opp.volume_24h:,.0f}",
                    "reason": opp.reason
                }
                for opp in opportunities
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

# Demo function
async def run_integration_demo():
    """Demonstrate the integration system"""
    print("🎯 Arbitrage Detection & Alert Integration Demo")
    print("=" * 60)
    
    # Initialize integration
    integration = ArbitrageAlertIntegration(min_efficiency=6.5, min_confidence=6.5)
    
    # Create test markets (using the same test data as detector)
    from opportunity_detector import create_test_markets
    markets = create_test_markets()
    
    print(f"📊 Processing {len(markets)} markets through detection and alert pipeline...")
    
    # Run detection and alerting
    results = await integration.detect_and_alert(markets, detailed=True)
    
    # Display results
    print(f"\n🎯 Integration Results:")
    print(f"  Opportunities Detected: {results['opportunities_detected']}")
    print(f"  Discord Alerts Sent: {results['alerts_sent']}")
    
    if results['opportunities']:
        print(f"\n📈 Top Opportunities:")
        for i, opp in enumerate(results['opportunities'][:3]):
            print(f"  {i+1}. {opp['market_name']}")
            print(f"     Combined Score: {opp['combined_score']:.1f}/10")
            print(f"     Efficiency: {opp['efficiency_score']:.1f}/10 | Confidence: {opp['confidence_score']:.1f}/10")
            print(f"     Spread: {opp['spread_percentage']:.1f}% | Liquidity: {opp['liquidity']}")
            print(f"     Volume: {opp['volume_24h']} | Reason: {opp['reason']}")
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
        f"✅ Integration demo completed successfully!\n"
        f"📊 Processed {len(markets)} markets\n"
        f"🎯 Found {results['opportunities_detected']} opportunities\n"
        f"📢 Sent {results['alerts_sent']} Discord alerts",
        "success"
    )

if __name__ == "__main__":
    asyncio.run(run_integration_demo())
