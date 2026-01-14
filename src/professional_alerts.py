"""
Professional Discord Alert System
Investment-grade arbitrage opportunity alerts with color-coded embeds
"""

import os
import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

logger = logging.getLogger("professional_alerts")

@dataclass
class ArbitrageOpportunity:
    """Professional arbitrage opportunity data structure"""
    market_name: str
    market_id: str
    opportunity_type: str = "Arb Opportunity"
    quality_score: float = 8.7
    confidence_score: float = 92.0
    spread_percentage: float = 2.3
    yes_price: float = 0.42
    yes_liquidity: float = 50000
    no_price: float = 0.61
    no_liquidity: float = 60000
    time_window: str = "Valid for ~45 minutes (expires in 3 blocks)"
    polymarket_link: str = ""
    analysis_link: str = ""
    filters_applied: str = "Spread > 2% | Liquidity > $40K | Volume > $500K 24h"
    expires_at: Optional[datetime] = None

class ProfessionalArbitrageAlerts:
    """Professional Discord alert system with investment-grade embeds"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("CPM_WEBHOOK_URL")
        self.health_webhook_url = os.getenv("DISCORD_HEALTH_WEBHOOK_URL")
        self.session = None
        
        # Brand configuration
        self.brand_name = "CPM Monitor"
        self.brand_tagline = "Premium Arbitrage Detection"
        self.brand_icon = "https://i.imgur.com/7GkUJvA.png"
        self.brand_logo = "https://i.imgur.com/7GkUJvA.png"
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def get_embed_color(self, confidence_score: float) -> int:
        """Return hex color based on confidence score"""
        if confidence_score >= 8.5:
            return 0x00FF64  # Green for HIGH confidence (TRADE THIS)
        elif confidence_score >= 6.5:
            return 0xFFFF00  # Yellow for MEDIUM confidence (GOOD OPPORTUNITY)
        else:
            return 0xFF8800  # Orange for LOW confidence (MONITOR/RESEARCH)
    
    def get_confidence_tier(self, confidence_score: float) -> str:
        """Get confidence tier description"""
        if confidence_score >= 8.5:
            return "HIGH 🟢 (TRADE THIS)"
        elif confidence_score >= 6.5:
            return "MEDIUM 🟡 (GOOD OPPORTUNITY)"
        else:
            return "LOW 🟠 (MONITOR/RESEARCH)"
    
    def get_quality_level(self, quality_score: float) -> str:
        """Get quality level description"""
        if quality_score >= 9.0:
            return "EXCEPTIONAL"
        elif quality_score >= 8.5:
            return "HIGH"
        elif quality_score >= 7.5:
            return "VERY_GOOD"
        elif quality_score >= 6.5:
            return "GOOD"
        elif quality_score >= 5.0:
            return "FAIR"
        else:
            return "POOR"
    
    def create_professional_embed(self, opportunity: ArbitrageOpportunity) -> Dict[str, Any]:
        """Create investment-grade Discord embed with color-coded left border"""
        
        # Get dynamic color for left border
        embed_color = self.get_embed_color(opportunity.confidence_score)
        confidence_tier = self.get_confidence_tier(opportunity.confidence_score)
        quality_level = self.get_quality_level(opportunity.quality_score)
        
        # Generate Polymarket and analysis links
        polymarket_url = opportunity.polymarket_link or f"https://polymarket.com/market/{opportunity.market_id}"
        analysis_url = opportunity.analysis_link or f"https://api.example.com/analysis/{opportunity.market_id}"
        
        # Format prices with liquidity (right-aligned formatting)
        yes_price_formatted = f"${opportunity.yes_price:.3f} | Liquidity: ${opportunity.yes_liquidity:,.0f}"
        no_price_formatted = f"${opportunity.no_price:.3f} | Liquidity: ${opportunity.no_liquidity:,.0f}"
        
        # Format spread with significance indicator
        spread_significance = ""
        if opportunity.spread_percentage >= 3.0:
            spread_significance = " (HIGHLY significant)"
        elif opportunity.spread_percentage >= 2.0:
            spread_significance = " (significant)"
        elif opportunity.spread_percentage >= 1.5:
            spread_significance = " (moderate)"
        
        spread_formatted = f"{opportunity.spread_percentage:.1f}%{spread_significance}"
        
        # Create professional embed
        embed = {
            "title": "🔥 ARBITRAGE OPPORTUNITY DETECTED",
            "color": embed_color,  # Dynamic color for LEFT BORDER
            "fields": [
                {
                    "name": "📊 Market",
                    "value": opportunity.market_name,
                    "inline": False
                },
                {
                    "name": "🎯 Type",
                    "value": opportunity.opportunity_type,
                    "inline": True
                },
                {
                    "name": "⚡ Quality Score",
                    "value": f"{opportunity.quality_score:.1f}/10 ({quality_level})",
                    "inline": True
                },
                {
                    "name": "💰 Spread/Inefficiency",
                    "value": spread_formatted,
                    "inline": True
                },
                {
                    "name": "📈 Confidence",
                    "value": f"{opportunity.confidence_score:.0f}% ({confidence_tier})",
                    "inline": True
                },
                {
                    "name": "🔹 YES Price",
                    "value": yes_price_formatted,
                    "inline": True
                },
                {
                    "name": "🔹 NO Price",
                    "value": no_price_formatted,
                    "inline": True
                },
                {
                    "name": "⏰ Time Window",
                    "value": opportunity.time_window,
                    "inline": False
                },
                {
                    "name": "🔗 Action",
                    "value": f"[View on Polymarket]({polymarket_url})\n[Analyze Data]({analysis_url})",
                    "inline": False
                },
                {
                    "name": "⚙️ Filters Applied",
                    "value": opportunity.filters_applied,
                    "inline": False
                },
                {
                    "name": "🎨 Confidence Tier",
                    "value": f"{confidence_tier} - Border color indicates action level",
                    "inline": False
                }
            ],
            "thumbnail": {
                "url": self.brand_icon
            },
            "footer": {
                "text": f"{self.brand_name} | {self.brand_tagline}",
                "icon_url": self.brand_logo
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return embed
    
    async def send_arbitrage_alert(self, opportunity: ArbitrageOpportunity) -> bool:
        """Send professional arbitrage alert to Discord"""
        if not self.webhook_url:
            logger.error("❌ No CPM_WEBHOOK_URL configured for arbitrage alerts")
            return False
        
        if not self.session:
            logger.error("❌ Session not initialized. Use async context manager.")
            return False
        
        # Create professional embed
        embed = self.create_professional_embed(opportunity)
        
        # Prepare Discord webhook payload
        payload = {
            "username": "CPM Arbitrage Alerts",
            "avatar_url": self.brand_logo,
            "embeds": [embed]
        }
        
        try:
            async with self.session.post(self.webhook_url, json=payload) as response:
                if response.status == 204:
                    logger.info(f"✅ Sent arbitrage alert: {opportunity.market_name}")
                    return True
                else:
                    logger.error(f"❌ Failed to send alert: {response.status} - {await response.text()}")
                    return False
        except Exception as e:
            logger.error(f"❌ Error sending arbitrage alert: {e}")
            return False
    
    async def send_multiple_alerts(self, opportunities: List[ArbitrageOpportunity]) -> int:
        """Send multiple arbitrage alerts with rate limiting"""
        success_count = 0
        
        for i, opportunity in enumerate(opportunities):
            logger.info(f"📢 Sending alert {i+1}/{len(opportunities)}: {opportunity.market_name}")
            
            success = await self.send_arbitrage_alert(opportunity)
            if success:
                success_count += 1
            
            # Rate limiting: wait 1 second between alerts
            if i < len(opportunities) - 1:
                await asyncio.sleep(1)
        
        logger.info(f"✅ Sent {success_count}/{len(opportunities)} arbitrage alerts successfully")
        return success_count
    
    async def send_health_alert(self, message: str, level: str = "info") -> bool:
        """Send health alert to separate webhook"""
        if not self.health_webhook_url:
            logger.error("❌ No DISCORD_HEALTH_WEBHOOK_URL configured")
            return False
        
        if not self.session:
            logger.error("❌ Session not initialized. Use async context manager.")
            return False
        
        # Color based on level
        colors = {
            "success": 0x00ff64,
            "info": 0x0099ff,
            "warning": 0xffff00,
            "error": 0xff0000
        }
        
        embed = {
            "title": f"🏥 System Health Alert",
            "color": colors.get(level, 0x0099ff),
            "description": message,
            "footer": {
                "text": f"{self.brand_name} | Health Monitor",
                "icon_url": self.brand_logo
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        payload = {
            "username": "CPM Health Monitor",
            "avatar_url": self.brand_logo,
            "embeds": [embed]
        }
        
        try:
            async with self.session.post(self.health_webhook_url, json=payload) as response:
                if response.status == 204:
                    logger.info(f"✅ Sent health alert: {level}")
                    return True
                else:
                    logger.error(f"❌ Failed to send health alert: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Error sending health alert: {e}")
            return False

# Example usage and testing
async def test_professional_alerts():
    """Test the professional alert system"""
    print("🎯 Professional Discord Alerts Test")
    print("=" * 50)
    
    # Create test opportunities with different confidence levels
    opportunities = [
        ArbitrageOpportunity(
            market_name="Bitcoin Q4 2024 Election Impact",
            market_id="bitcoin-election-2024",
            quality_score=8.7,
            confidence_score=92.0,
            spread_percentage=2.3,
            yes_price=0.42,
            yes_liquidity=50000,
            no_price=0.61,
            no_liquidity=60000,
            polymarket_link="https://polymarket.com/market/bitcoin-q4-election-impact",
            analysis_link="https://api.example.com/analysis/bitcoin-q4"
        ),
        ArbitrageOpportunity(
            market_name="Trump Indictment Before Q4 2024",
            market_id="trump-indictment-q4",
            quality_score=7.2,
            confidence_score=75.0,
            spread_percentage=1.8,
            yes_price=0.35,
            yes_liquidity=45000,
            no_price=0.60,
            no_liquidity=55000,
            polymarket_link="https://polymarket.com/market/trump-indictment-q4",
            analysis_link="https://api.example.com/analysis/trump-indictment"
        ),
        ArbitrageOpportunity(
            market_name="Biden Approval Above 45% in December",
            market_id="biden-polls-december",
            quality_score=6.0,
            confidence_score=58.0,
            spread_percentage=1.2,
            yes_price=0.48,
            yes_liquidity=40000,
            no_price=0.49,
            no_liquidity=45000,
            polymarket_link="https://polymarket.com/market/biden-polls-december",
            analysis_link="https://api.example.com/analysis/biden-polls"
        )
    ]
    
    # Test embed creation (without sending)
    alerter = ProfessionalArbitrageAlerts()
    
    print("📊 Testing Embed Creation:")
    for i, opp in enumerate(opportunities):
        embed = alerter.create_professional_embed(opp)
        color = alerter.get_embed_color(opp.confidence_score)
        tier = alerter.get_confidence_tier(opp.confidence_score)
        
        print(f"\n{i+1}. {opp.market_name}")
        print(f"   Quality: {opp.quality_score:.1f}/10")
        print(f"   Confidence: {opp.confidence_score:.0f}% ({tier})")
        print(f"   Spread: {opp.spread_percentage:.1f}%")
        print(f"   Color: #{color:06x}")
        print(f"   Embed Title: {embed['title']}")
        print(f"   Fields Count: {len(embed['fields'])}")
    
    print(f"\n✅ Professional alert system test complete!")
    print(f"🎨 Color coding working: 🟢 TRADE THIS | 🟡 GOOD OPPORTUNITY | 🟠 MONITOR/RESEARCH")
    print(f"📱 Left border colors will indicate urgency in Discord")

if __name__ == "__main__":
    asyncio.run(test_professional_alerts())
