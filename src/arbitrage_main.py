"""
Professional Arbitrage System - Main Integration
Ties together quality scoring, detection, and Discord alerts
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from arbitrage_detector import ArbitrageDetector, MarketData, create_test_market_data
from arbitrage_alerts import ArbitrageAlert
from quality_scoring import QualityScorer
from arbitrage_config import ArbitrageConfig, validate_arbitrage_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("arbitrage_main")

class ProfessionalArbitrageSystem:
    """Main arbitrage system orchestrator"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config = ArbitrageConfig()
        self.detector = ArbitrageDetector(min_quality_threshold=self.config.MIN_QUALITY_THRESHOLD)
        self.quality_scorer = QualityScorer()
        self.alert_system = ArbitrageAlert()
        
        # System state
        self.last_scan_time: Optional[datetime] = None
        self.total_opportunities_detected = 0
        self.total_alerts_sent = 0
        self.scan_count = 0
        
    async def initialize(self) -> bool:
        """Initialize the arbitrage system"""
        logger.info("🚀 Initializing Professional Arbitrage System...")
        
        # Validate configuration
        if not validate_arbitrage_config():
            logger.error("❌ Configuration validation failed")
            return False
        
        # Check environment variables
        required_env_vars = ["CPM_WEBHOOK_URL"]
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        
        if missing_vars:
            logger.error(f"❌ Missing environment variables: {missing_vars}")
            return False
        
        logger.info("✅ System initialized successfully")
        return True
    
    async def scan_markets(self, market_data: List[MarketData]) -> Dict[str, Any]:
        """Scan markets for arbitrage opportunities"""
        self.scan_count += 1
        self.last_scan_time = datetime.utcnow()
        
        logger.info(f"🔍 Scan #{self.scan_count}: Analyzing {len(market_data)} markets")
        
        # Detect opportunities
        opportunities = await self.detector.analyze_markets(market_data)
        
        # Update counters
        self.total_opportunities_detected += len(opportunities)
        
        # Log results
        if opportunities:
            logger.info(f"🎯 Found {len(opportunities)} quality opportunities")
            for i, opp in enumerate(opportunities[:3]):  # Log top 3
                level = self.config.get_quality_level(opp.quality_score)
                logger.info(f"  {i+1}. {opp.market_name} ({opp.quality_score:.1f}/10) - {level}")
        else:
            logger.info("📊 No quality opportunities detected in this scan")
        
        return {
            "scan_id": self.scan_count,
            "scan_time": self.last_scan_time.isoformat(),
            "markets_analyzed": len(market_data),
            "opportunities_detected": len(opportunities),
            "opportunities": opportunities
        }
    
    async def send_alerts(self, opportunities: List[MarketData], detailed: bool = True) -> int:
        """Send Discord alerts for opportunities"""
        if not opportunities:
            return 0
        
        logger.info(f"📢 Sending {len(opportunities)} Discord alerts...")
        
        async with self.alert_system as alerter:
            success_count = await alerter.send_multiple_alerts(opportunities, detailed)
            self.total_alerts_sent += success_count
            
            logger.info(f"✅ Sent {success_count}/{len(opportunities)} alerts successfully")
            return success_count
    
    async def run_full_scan_and_alert(self, market_data: List[MarketData]) -> Dict[str, Any]:
        """Complete scan and alert workflow"""
        logger.info("🔄 Starting full scan and alert workflow...")
        
        # Scan markets
        scan_results = await self.scan_markets(market_data)
        opportunities = scan_results["opportunities"]
        
        # Send alerts
        alerts_sent = 0
        if opportunities:
            alerts_sent = await self.send_alerts(opportunities, detailed=self.config.DETAILED_ALERTS)
        
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
        
        logger.info(f"✅ Full workflow complete: {len(opportunities)} opportunities, {alerts_sent} alerts")
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
    """Run continuous monitoring with specified interval"""
    print(f"🔄 Starting continuous monitoring (every {interval_minutes} minutes, max {max_scans} scans)")
    
    system = ProfessionalArbitrageSystem()
    
    if not await system.initialize():
        return
    
    for scan_num in range(max_scans):
        print(f"\n📍 Scan {scan_num + 1}/{max_scans}")
        
        # Get fresh market data (in real implementation, this would fetch from APIs)
        market_data = create_test_market_data()
        
        # Run scan
        results = await system.run_full_scan_and_alert(market_data)
        
        # Monitor health
        health = await system.monitor_system_health()
        
        # Wait for next scan
        if scan_num < max_scans - 1:
            print(f"⏳ Waiting {interval_minutes} minutes for next scan...")
            await asyncio.sleep(interval_minutes * 60)
    
    print("✅ Continuous monitoring complete")

if __name__ == "__main__":
    # Check if running in production (Render) or demo mode
    if os.getenv("RENDER") or os.getenv("ENVIRONMENT") == "production":
        # Production: Run continuous monitoring indefinitely
        asyncio.run(run_continuous_monitoring(interval_minutes=5, max_scans=1000000))
    else:
        # Demo mode: Run single scan
        asyncio.run(run_professional_demo())
