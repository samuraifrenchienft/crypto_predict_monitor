"""
Complete Arbitrage Integration System
Connects opportunity detection, alert management, and professional Discord alerts
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from arbitrage.opportunity_detector_exact import ArbitrageDetector, ArbitrageOpportunity, Market
from arbitrage_alert_manager import ArbitrageAlertManager
from professional_alerts import ProfessionalArbitrageAlerts

logger = logging.getLogger("arbitrage_integration_complete")

class CompleteArbitrageIntegration:
    """Complete integration system for arbitrage detection and alerting"""
    
    def __init__(self):
        self.detector = ArbitrageDetector()
        self.alert_manager = ArbitrageAlertManager()
        self.discord_alerts = ProfessionalArbitrageAlerts()
        
        # Integration stats
        self.total_markets_processed = 0
        self.total_opportunities_detected = 0
        self.total_alerts_sent = 0
        self.total_discord_alerts_sent = 0
    
    async def process_markets(self, markets: List[Market], 
                            historical_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Complete market processing pipeline"""
        
        self.total_markets_processed += len(markets)
        
        logger.info(f"🔄 Starting complete arbitrage processing for {len(markets)} markets...")
        
        # Step 1: Detect opportunities using exact implementation
        opportunities = self.detector.detect_opportunities(markets)
        self.total_opportunities_detected += len(opportunities)
        
        if not opportunities:
            logger.info("📊 No quality opportunities detected")
            return self._create_result_dict(0, 0, 0, [])
        
        logger.info(f"🎯 Detected {len(opportunities)} quality opportunities")
        
        # Step 2: Filter and rank alerts using alert manager
        alerts = self.alert_manager.filter_and_rank_alerts(opportunities, historical_data)
        self.total_alerts_sent += len(alerts)
        
        if not alerts:
            logger.info("📢 No alerts passed priority filtering")
            return self._create_result_dict(len(opportunities), 0, 0, opportunities)
        
        logger.info(f"🚨 Generated {len(alerts)} prioritized alerts")
        
        # Step 3: Send professional Discord alerts
        discord_alerts_sent = await self._send_discord_alerts(alerts)
        self.total_discord_alerts_sent += discord_alerts_sent
        
        # Step 4: Create comprehensive results
        results = self._create_result_dict(len(opportunities), len(alerts), discord_alerts_sent, opportunities, alerts)
        
        logger.info(f"✅ Processing complete: {len(opportunities)} opportunities → {len(alerts)} alerts → {discord_alerts_sent} Discord messages")
        
        return results
    
    async def _send_discord_alerts(self, alerts: List) -> int:
        """Send alerts to Discord with professional formatting"""
        
        # Convert alerts to professional format
        professional_opps = []
        for alert in alerts:
            opp = alert.opportunity
            
            # Convert confidence score to 0-100 scale
            confidence_100 = opp.confidence_score * 10
            
            # Calculate time window
            time_remaining = opp.expires_at - datetime.utcnow()
            hours_remaining = time_remaining.total_seconds() / 3600
            
            if hours_remaining >= 24:
                time_window = f"Valid for ~{int(hours_remaining)} hours (expires in {int(hours_remaining/24)} days)"
            elif hours_remaining >= 1:
                time_window = f"Valid for ~{int(hours_remaining)} minutes (expires in {int(hours_remaining/60)} blocks)"
            else:
                time_window = f"Valid for ~{int(hours_remaining*60)} minutes (expires soon)"
            
            # Generate filters applied
            min_liquidity = min(opp.yes_liquidity, opp.no_liquidity)
            filters = []
            
            if opp.spread * 100 >= 3.0:
                filters.append("Spread > 3%")
            elif opp.spread * 100 >= 2.0:
                filters.append("Spread > 2%")
            else:
                filters.append("Spread > 1.5%")
            
            if min_liquidity >= 75000:
                filters.append("Liquidity > $75K")
            elif min_liquidity >= 50000:
                filters.append("Liquidity > $50K")
            else:
                filters.append("Liquidity > $40K")
            
            if opp.volume_24h >= 2000000:
                filters.append("Volume > $2M 24h")
            elif opp.volume_24h >= 1000000:
                filters.append("Volume > $1M 24h")
            else:
                filters.append("Volume > $500K 24h")
            
            filters_applied = " | ".join(filters)
            
            # Create professional opportunity
            from professional_alerts import ArbitrageOpportunity as ProfessionalOpportunity
            professional_opp = ProfessionalOpportunity(
                market_name=opp.market_name,
                market_id=opp.market_id,
                opportunity_type=f"Arb Opportunity ({alert.alert_type.replace('_', ' ').title()})",
                quality_score=opp.efficiency_score,
                confidence_score=confidence_100,
                spread_percentage=opp.spread * 100,
                yes_price=opp.yes_price,
                yes_liquidity=opp.yes_liquidity,
                no_price=opp.no_price,
                no_liquidity=opp.no_liquidity,
                time_window=time_window,
                polymarket_link=f"https://polymarket.com/market/{opp.market_id}",
                analysis_link=f"https://api.example.com/analysis/{opp.market_id}",
                filters_applied=filters_applied,
                expires_at=opp.expires_at
            )
            
            professional_opps.append(professional_opp)
        
        # Send Discord alerts
        async with self.discord_alerts as alerter:
            success_count = await alerter.send_multiple_alerts(professional_opps)
            
            logger.info(f"📢 Sent {success_count}/{len(professional_opps)} professional Discord alerts")
            
            return success_count
    
    def _create_result_dict(self, opportunities_count: int, alerts_count: int, 
                          discord_count: int, opportunities: List[ArbitrageOpportunity],
                          alerts: Optional[List] = None) -> Dict[str, Any]:
        """Create comprehensive results dictionary"""
        
        result = {
            "markets_processed": self.total_markets_processed,
            "opportunities_detected": opportunities_count,
            "alerts_generated": alerts_count,
            "discord_alerts_sent": discord_count,
            "opportunities": [],
            "alerts": [],
            "integration_stats": self.get_integration_stats()
        }
        
        # Add opportunity details
        for opp in opportunities:
            combined_score = (opp.efficiency_score + opp.confidence_score) / 2
            result["opportunities"].append({
                "market_name": opp.market_name,
                "market_id": opp.market_id,
                "efficiency_score": opp.efficiency_score,
                "confidence_score": opp.confidence_score,
                "combined_score": combined_score,
                "spread_percentage": opp.spread * 100,
                "liquidity": f"${min(opp.yes_liquidity, opp.no_liquidity):,.0f}",
                "volume_24h": f"${opp.volume_24h:,.0f}",
                "reason": opp.reason,
                "expires_at": opp.expires_at.isoformat()
            })
        
        # Add alert details if available
        if alerts:
            for alert in alerts:
                result["alerts"].append({
                    "market_name": alert.opportunity.market_name,
                    "alert_type": alert.alert_type,
                    "priority": alert.priority,
                    "severity": alert.severity,
                    "timestamp": alert.timestamp.isoformat(),
                    "reason": alert.reason,
                    "combined_score": (alert.opportunity.efficiency_score + alert.opportunity.confidence_score) / 2
                })
        
        return result
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get comprehensive integration statistics"""
        
        detector_stats = self.detector.get_detection_stats()
        alert_stats = self.alert_manager.get_alert_stats()
        
        return {
            "detector_stats": detector_stats,
            "alert_manager_stats": alert_stats,
            "integration_stats": {
                "total_markets_processed": self.total_markets_processed,
                "total_opportunities_detected": self.total_opportunities_detected,
                "total_alerts_sent": self.total_alerts_sent,
                "total_discord_alerts_sent": self.total_discord_alerts_sent,
                "opportunity_detection_rate": (self.total_opportunities_detected / max(self.total_markets_processed, 1)) * 100,
                "alert_conversion_rate": (self.total_alerts_sent / max(self.total_opportunities_detected, 1)) * 100,
                "discord_success_rate": (self.total_discord_alerts_sent / max(self.total_alerts_sent, 1)) * 100
            }
        }
    
    async def send_health_alert(self, message: str, level: str = "info") -> bool:
        """Send health alert to Discord"""
        async with self.discord_alerts as alerter:
            return await alerter.send_health_alert(message, level)

# Test data and demo functions
def create_test_markets() -> List[Market]:
    """Create test market data for demonstration"""
    now = datetime.utcnow()
    
    test_markets = [
        # Premium top-tier opportunity
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
        # Strong top-tier opportunity
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
        # Flash opportunity (high spread, closing fast)
        Market(
            id="crypto-regulation-flash",
            name="Crypto Regulation Flash Vote",
            yes_price=0.30,
            no_price=0.65,  # 5% spread
            yes_liquidity=45000,
            no_liquidity=50000,
            bid_ask_spread=0.0015,
            expiration=now + timedelta(minutes=45),  # Closes in 45 minutes
            price_change_24h=0.08,
            volume_24h=900000,
            time_to_expiration=timedelta(minutes=45),
            status='active'
        ),
        # Volume anomaly opportunity
        Market(
            id="volume-anomaly-market",
            name="Unusual Volume Activity",
            yes_price=0.48,
            no_price=0.49,
            yes_liquidity=42000,
            no_liquidity=48000,
            bid_ask_spread=0.0018,
            expiration=now + timedelta(hours=12),
            price_change_24h=0.12,
            volume_24h=3000000,  # Unusually high volume
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

def create_historical_data() -> Dict[str, Any]:
    """Create mock historical data for anomaly detection"""
    return {
        "volume-anomaly-market": {
            "volume_24h": 800000,  # Normal volume is 800K, current is 3M (3.75x increase)
            "liquidity": {"yes": 40000, "no": 45000}
        },
        "crypto-regulation-flash": {
            "volume_24h": 600000,  # Normal volume is 600K, current is 900K (1.5x increase)
            "liquidity": {"yes": 43000, "no": 48000}
        }
    }

# Demo function
async def run_complete_integration_demo():
    """Demonstrate the complete arbitrage integration system"""
    print("🎯 Complete Arbitrage Integration Demo")
    print("=" * 80)
    print("✅ Full pipeline: Detection → Alert Management → Discord Alerts")
    print("✅ Priority-based alert classification")
    print("✅ Professional Discord embeds with color coding")
    print()
    
    # Initialize integration
    integration = CompleteArbitrageIntegration()
    
    # Create test data
    markets = create_test_markets()
    historical_data = create_historical_data()
    
    print(f"📊 Processing {len(markets)} markets with historical data for anomaly detection...")
    
    # Run complete processing
    results = await integration.process_markets(markets, historical_data)
    
    # Display results
    print(f"\n🎯 Complete Integration Results:")
    print(f"  Markets Processed: {results['markets_processed']}")
    print(f"  Opportunities Detected: {results['opportunities_detected']}")
    print(f"  Alerts Generated: {results['alerts_generated']}")
    print(f"  Discord Alerts Sent: {results['discord_alerts_sent']}")
    
    if results['opportunities']:
        print(f"\n📈 Detected Opportunities:")
        for i, opp in enumerate(results['opportunities']):
            print(f"  {i+1}. {opp['market_name']}")
            print(f"     Combined Score: {opp['combined_score']:.1f}/10")
            print(f"     Spread: {opp['spread_percentage']:.1f}% | Liquidity: {opp['liquidity']}")
            print(f"     Volume: {opp['volume_24h']} | Reason: {opp['reason']}")
            print()
    
    if results['alerts']:
        print(f"\n🚨 Generated Alerts (Priority Order):")
        for i, alert in enumerate(results['alerts']):
            print(f"  {i+1}. {alert['market_name']}")
            print(f"     Type: {alert['alert_type']} (Priority: {alert['priority']})")
            print(f"     Severity: {alert['severity']}")
            print(f"     Combined Score: {alert['combined_score']:.1f}/10")
            print(f"     Reason: {alert['reason']}")
            print()
    
    # Show integration stats
    integration_stats = integration.get_integration_stats()
    stats = integration_stats['integration_stats']
    print(f"📊 Integration Statistics:")
    print(f"  Detection Rate: {stats['opportunity_detection_rate']:.1f}% of markets")
    print(f"  Alert Conversion Rate: {stats['alert_conversion_rate']:.1f}% of opportunities")
    print(f"  Discord Success Rate: {stats['discord_success_rate']:.1f}% of alerts")
    
    # Send health alert
    await integration.send_health_alert(
        f"✅ Complete integration demo completed!\n"
        f"📊 Processed {results['markets_processed']} markets\n"
        f"🎯 Found {results['opportunities_detected']} opportunities\n"
        f"🚨 Generated {results['alerts_generated']} prioritized alerts\n"
        f"📢 Sent {results['discord_alerts_sent']} professional Discord alerts\n"
        f"🎨 Color-coded alerts: 🟢 TRADE THIS | 🟡 GOOD OPPORTUNITY | 🟠 MONITOR/RESEARCH\n"
        f"⚡ Priority system: Top-tier > Flash > Volume Anomaly > Liquidity Change",
        "success"
    )
    
    print(f"\n🎯 Complete Integration Features:")
    print(f"  ✅ Exact arbitrage detection implementation")
    print(f"  ✅ Priority-based alert classification")
    print(f"  ✅ Quality score filtering (>= 6.0)")
    print(f"  ✅ Market cooldowns (30 minutes)")
    print(f"  ✅ Alert deduplication (5-minute window)")
    print(f"  ✅ Anomaly detection with historical data")
    print(f"  ✅ Professional Discord alerts with color coding")
    print(f"  ✅ Comprehensive statistics and monitoring")

if __name__ == "__main__":
    asyncio.run(run_complete_integration_demo())
