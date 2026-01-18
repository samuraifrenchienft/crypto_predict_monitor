"""
Professional Arbitrage System - Cross-Platform Integration
Complete arbitrage detection with contract matching and fee calculation
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Add src/arbitrage to path
sys.path.insert(0, str(Path(__file__).parent / 'arbitrage'))

from arbitrage.complete_system import CompleteArbitrageSystem, MarketData as UnifiedMarketData
from arbitrage.adapter_converters import (
    convert_polymarket_to_unified,
    convert_azuro_to_unified,
    convert_limitless_to_unified
)
from arbitrage.discord_alerts import send_multiple_arbitrage_alerts
from arbitrage_alerts import ArbitrageAlert

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("arbitrage_main")

class ProfessionalArbitrageSystem:
    """Cross-platform arbitrage system orchestrator"""
    
    def __init__(self):
        self.arb_system = CompleteArbitrageSystem()
        self.alert_system = ArbitrageAlert()
        
        # System state
        self.last_scan_time: Optional[datetime] = None
        self.total_opportunities_detected = 0
        self.total_alerts_sent = 0
        self.scan_count = 0
        
        # Configuration
        self.min_roi = 0.5  # 0.5% minimum ROI after fees
        
    async def initialize(self) -> bool:
        """Initialize the cross-platform arbitrage system"""
        logger.info("🚀 Initializing Cross-Platform Arbitrage System...")
        
        # Check environment variables
        required_env_vars = ["CPM_WEBHOOK_URL"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing environment variables: {missing_vars}")
            return False
        
        logger.info("✅ System initialized successfully")
        return True
    
    async def scan_markets(self, unified_markets: List[UnifiedMarketData]) -> Dict[str, Any]:
        """Scan markets for cross-platform arbitrage opportunities"""
        self.scan_count += 1
        self.last_scan_time = datetime.utcnow()
        
        logger.info(f"🔍 Scan #{self.scan_count}: Analyzing {len(unified_markets)} markets across platforms")
        
        # Detect cross-platform arbitrage
        opportunities = await self.arb_system.run_complete_scan(
            unified_markets,
            min_roi=self.min_roi
        )
        
        # Update counters
        self.total_opportunities_detected += len(opportunities)
        
        # Log results
        if opportunities:
            logger.info(f"🎯 Found {len(opportunities)} cross-platform arbitrage opportunities")
            for i, opp in enumerate(opportunities[:3]):  # Log top 3
                logger.info(
                    f"  {i+1}. {opp.matched_pair.normalized_title[:50]} - "
                    f"Buy {opp.buy_platform.value} @ ${opp.buy_price:.4f} → "
                    f"Sell {opp.sell_platform.value} @ ${opp.sell_price:.4f} = "
                    f"{opp.roi_percent:.2f}% ROI"
                )
        else:
            logger.info("📊 No viable cross-platform arbitrage detected")
        
        return {
            "scan_id": self.scan_count,
            "scan_time": self.last_scan_time.isoformat(),
            "markets_analyzed": len(unified_markets),
            "opportunities_detected": len(opportunities),
            "opportunities": opportunities
        }
    
    async def send_alerts(self, opportunities: List) -> int:
        """Send Discord alerts for cross-platform arbitrage opportunities"""
        if not opportunities:
            return 0
        
        logger.info(f"📢 Sending {len(opportunities)} cross-platform arbitrage alerts...")
        
        # Send using new cross-platform alert system
        success_count = await send_multiple_arbitrage_alerts(opportunities, max_alerts=10)
        self.total_alerts_sent += success_count
        
        logger.info(f"✅ Sent {success_count}/{len(opportunities)} alerts successfully")
        return success_count
    
    async def run_full_scan_and_alert(self, unified_markets: List[UnifiedMarketData]) -> Dict[str, Any]:
        """Complete cross-platform arbitrage scan and alert workflow"""
        logger.info("🔄 Starting cross-platform arbitrage scan...")
        
        # Scan for cross-platform arbitrage
        scan_results = await self.scan_markets(unified_markets)
        opportunities = scan_results["opportunities"]
        
        # Send alerts
        alerts_sent = 0
        if opportunities:
            alerts_sent = await self.send_alerts(opportunities)
        
        # Return comprehensive results
        results = {
            "scan_results": scan_results,
            "alerts_sent": alerts_sent,
            "system_stats": {
                "total_scans": self.scan_count,
                "total_opportunities": self.total_opportunities_detected,
                "total_alerts": self.total_alerts_sent,
                "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None
            }
        }
        
        logger.info(f"✅ Cross-platform scan complete: {len(opportunities)} opportunities, {alerts_sent} alerts")
        return results
    
    async def send_health_alert(self, message: str, level: str = "info") -> bool:
        """Send health alert to separate webhook"""
        async with self.alert_system as alerter:
            return await alerter.send_health_alert(message, level)
    
    async def monitor_system_health(self) -> Dict[str, Any]:
        """Monitor system health and send alerts if needed"""
        now = datetime.utcnow()
        
        health_status = {
            "timestamp": now.isoformat(),
            "system_uptime": now.isoformat(),  # Would calculate from start time
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "scan_count": self.scan_count,
            "total_opportunities": self.total_opportunities_detected,
            "total_alerts": self.total_alerts_sent,
            "status": "healthy"
        }
        
        # Check for issues
        issues = []
        
        # Check if last scan was too long ago
        if self.last_scan_time:
            time_since_last_scan = now - self.last_scan_time
            if time_since_last_scan > timedelta(hours=1):
                issues.append(f"No scan in {time_since_last_scan.total_seconds()/3600:.1f} hours")
                health_status["status"] = "warning"
        
        # Check if no opportunities detected recently
        if self.scan_count > 10 and self.total_opportunities_detected == 0:
            issues.append("No opportunities detected in 10+ scans")
            health_status["status"] = "warning"
        
        # Send health alert if issues
        if issues:
            message = f"⚠️ System Health Issues:\n" + "\n".join(f"• {issue}" for issue in issues)
            await self.send_health_alert(message, "warning")
        
        return health_status
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get current system statistics"""
        return {
            "scan_count": self.scan_count,
            "total_opportunities_detected": self.total_opportunities_detected,
            "total_alerts_sent": self.total_alerts_sent,
            "last_scan_time": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "config": {
                "min_quality_threshold": self.config.MIN_QUALITY_THRESHOLD,
                "min_spread_percentage": self.config.MIN_SPREAD_PERCENTAGE,
                "min_liquidity_usd": self.config.MIN_LIQUIDITY_USD,
                "detailed_alerts": self.config.DETAILED_ALERTS
            }
        }

# Demo and testing functions
async def run_professional_demo():
    """Run demonstration of the professional arbitrage system"""
    print("🎯 Professional Arbitrage System Demo")
    print("=" * 50)
    
    # Initialize system
    system = ProfessionalArbitrageSystem()
    
    if not await system.initialize():
        print("❌ System initialization failed")
        return
    
    # Get test market data
    market_data = create_test_market_data()
    
    # Run full workflow
    results = await system.run_full_scan_and_alert(market_data)
    
    # Display results
    print("\n📊 Results Summary:")
    print(f"  Markets Analyzed: {results['scan_results']['markets_analyzed']}")
    print(f"  Opportunities Detected: {results['scan_results']['opportunities_detected']}")
    print(f"  Alerts Sent: {results['alerts_sent']}")
    
    print("\n🎯 Top Opportunities:")
    for i, opp in enumerate(results['scan_results']['opportunities'][:3]):
        level = system.config.get_quality_level(opp.quality_score)
        print(f"  {i+1}. {opp.market_name}")
        print(f"     Quality: {opp.quality_score:.1f}/10 ({level})")
        print(f"     Spread: {opp.spread_percentage:.1f}%")
        print(f"     Confidence: {opp.confidence:.0f}%")
    
    print("\n📈 System Statistics:")
    stats = system.get_system_stats()
    for key, value in stats.items():
        if key != 'config':
            print(f"  {key}: {value}")
    
    # Monitor health
    health = await system.monitor_system_health()
    print(f"\n🏥 System Health: {health['status']}")

async def run_continuous_monitoring(interval_minutes: int = 5, max_scans: int = 10):
    """Run continuous monitoring with real market data from adapters"""
    logger.info(f"🔄 Starting continuous monitoring (every {interval_minutes} minutes, max {max_scans} scans)")
    
    system = ProfessionalArbitrageSystem()
    
    if not await system.initialize():
        logger.error("❌ System initialization failed")
        return
    
    # Send startup alert
    await system.send_health_alert(
        "🚀 CROSS-PLATFORM ARBITRAGE BOT ONLINE\n"
        "✅ Contract matching enabled\n"
        "✅ Fee calculation active\n"
        "✅ Discord alerts enabled\n"
        "✅ Multi-platform scanning ready",
        "success"
    )
    
    for scan_num in range(max_scans):
        try:
            logger.info(f"\n📍 Scan {scan_num + 1}/{max_scans}")
            
            # Fetch real market data from all platforms
            unified_markets = []
            try:
                sys.path.insert(0, str(Path(__file__).parent.parent))
                
                from bot.adapters.polymarket import PolymarketAdapter
                from bot.adapters.azuro import AzuroAdapter
                from bot.adapters.limitless import LimitlessAdapter
                from bot.config import Config
                
                config = Config.load()
                
                # POLYMARKET
                try:
                    logger.info("📊 Fetching Polymarket markets...")
                    poly_adapter = PolymarketAdapter(
                        gamma_base_url=config.get_platform_config("polymarket", "gamma_base_url"),
                        clob_base_url=config.get_platform_config("polymarket", "clob_base_url"),
                        data_base_url=config.get_platform_config("polymarket", "data_base_url"),
                        events_limit=50
                    )
                    poly_markets = poly_adapter.fetch_markets()
                    poly_unified = convert_polymarket_to_unified(poly_markets)
                    unified_markets.extend(poly_unified)
                    logger.info(f"✅ Polymarket: {len(poly_unified)} markets converted")
                except Exception as e:
                    logger.error(f"❌ Polymarket fetch failed: {e}")
                
                # AZURO
                try:
                    logger.info("📊 Fetching Azuro markets...")
                    azuro_adapter = AzuroAdapter(markets_limit=50)
                    azuro_markets = azuro_adapter.fetch_markets()
                    azuro_unified = convert_azuro_to_unified(azuro_markets)
                    unified_markets.extend(azuro_unified)
                    logger.info(f"✅ Azuro: {len(azuro_unified)} markets converted")
                except Exception as e:
                    logger.error(f"❌ Azuro fetch failed: {e}")
                
                # LIMITLESS
                try:
                    logger.info("📊 Fetching Limitless markets...")
                    limitless_adapter = LimitlessAdapter(markets_limit=50)
                    limitless_markets = limitless_adapter.fetch_markets()
                    limitless_unified = convert_limitless_to_unified(limitless_markets)
                    unified_markets.extend(limitless_unified)
                    logger.info(f"✅ Limitless: {len(limitless_unified)} markets converted")
                except Exception as e:
                    logger.error(f"❌ Limitless fetch failed: {e}")
                
                logger.info(f"📊 Total unified markets: {len(unified_markets)} across all platforms")
                
            except Exception as e:
                logger.error(f"❌ Market data fetch failed: {e}")
                import traceback
                traceback.print_exc()
                unified_markets = []
            
            # Run cross-platform arbitrage scan
            if unified_markets:
                results = await system.run_full_scan_and_alert(unified_markets)
                
                opp_count = results['scan_results']['opportunities_detected']
                alert_count = results['alerts_sent']
                
                if opp_count > 0:
                    logger.info(f"🎯 DETECTED {opp_count} cross-platform arbitrage opportunities")
                    logger.info(f"📢 Sent {alert_count} Discord alerts")
                else:
                    logger.info("📊 No viable cross-platform arbitrage detected this scan")
            else:
                logger.warning("⚠️ No market data available for scan")
            
            # Monitor health
            if scan_num % 10 == 0:
                health = await system.monitor_system_health()
                logger.info(f"🏥 System health: {health['status']}")
            
            # Wait for next scan
            if scan_num < max_scans - 1:
                logger.info(f"⏳ Waiting {interval_minutes} minutes for next scan...")
                await asyncio.sleep(interval_minutes * 60)
                
        except Exception as e:
            logger.error(f"❌ Scan error: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(60)  # Wait 1 minute on error
    
    logger.info("✅ Continuous monitoring complete")

if __name__ == "__main__":
    # Check if running in production (Render) or demo mode
    if os.getenv("RENDER") or os.getenv("ENVIRONMENT") == "production":
        # Production: Run continuous monitoring indefinitely
        asyncio.run(run_continuous_monitoring(interval_minutes=5, max_scans=1000000))
    else:
        # Demo mode: Run single scan
        asyncio.run(run_professional_demo())
