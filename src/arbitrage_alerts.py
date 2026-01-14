"""
Professional Discord Arbitrage Alerts
Investment-grade Discord embeds for top-tier arbitrage opportunities
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

@dataclass
class ArbitrageOpportunity:
    """Data structure for professional arbitrage opportunity"""
    market_name: str
    opportunity_type: str = "Arb Opportunity"
    quality_score: float = 7.0
    spread_percentage: float = 0.0
    confidence: float = 85.0
    yes_price: float = 0.0
    yes_liquidity: float = 0.0
    no_price: float = 0.0
    no_liquidity: float = 0.0
    time_window: str = "Valid for ~45 minutes"
    polymarket_link: str = ""
    analysis_link: str = ""
    filters_applied: str = "Spread > 2% | Liquidity > $40K | Volume > $500K 24h"
    expires_at: datetime = None
    market_source: str = "Polymarket"

class ArbitrageAlert:
    """Professional Discord embed builder for arbitrage opportunities"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("CPM_WEBHOOK_URL")  # Arbitrage alerts webhook
        self.health_webhook_url = os.getenv("DISCORD_HEALTH_WEBHOOK_URL")  # Health alerts only
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_color_by_confidence(self, quality_score: float) -> int:
        """Get Discord embed color based on quality score"""
        if quality_score >= 8.5:  # High confidence - Green
            return 0x00ff64  # Green (#00ff64)
        elif quality_score >= 6.5:  # Medium confidence - Yellow
            return 0xffff00  # Yellow (#ffff00)
        elif quality_score >= 5.0:  # Lower confidence but notable - Blue
            return 0x0001ff  # Blue (#0001ff)
        else:  # Low confidence - Gray
            return 0x808080  # Gray
    
    def get_quality_emoji(self, quality_score: float) -> str:
        """Get quality emoji based on score"""
        if quality_score >= 9.0:
            return "🔥🔥🔥"  # Exceptional
        elif quality_score >= 8.5:
            return "🔥🔥"  # Excellent
        elif quality_score >= 7.5:
            return "🔥"  # Very Good
        elif quality_score >= 6.5:
            return "⚡"  # Good
        else:
            return "📊"  # Fair
    
    def create_professional_embed(self, opportunity: ArbitrageOpportunity) -> Dict[str, Any]:
        """Create investment-grade Discord embed"""
        color = self.get_color_by_confidence(opportunity.quality_score)
        quality_emoji = self.get_quality_emoji(opportunity.quality_score)
        
        # Format quality score display
        quality_level = "HIGH" if opportunity.quality_score >= 8.5 else "MEDIUM" if opportunity.quality_score >= 6.5 else "LOW"
        
        embed = {
            "title": f"🔥 ARBITRAGE OPPORTUNITY DETECTED",
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
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
                    "value": f"{opportunity.spread_percentage:.1f}% ({opportunity.spread_percentage*100:.0f}bps from 1% = significant)",
                    "inline": True
                },
                {
                    "name": "📈 Confidence",
                    "value": f"{opportunity.confidence:.0f}% (based on volume & movement)",
                    "inline": True
                },
                {
                    "name": "🔹 YES Price",
                    "value": f"${opportunity.yes_price:.2f} | Liquidity: ${opportunity.yes_liquidity:,.0f}",
                    "inline": True
                },
                {
                    "name": "🔹 NO Price",
                    "value": f"${opportunity.no_price:.2f} | Liquidity: ${opportunity.no_liquidity:,.0f}",
                    "inline": True
                },
                {
                    "name": "⏰ Time Window",
                    "value": opportunity.time_window,
                    "inline": False
                },
                {
                    "name": "🔗 Action",
                    "value": f"[View on {opportunity.market_source}]({opportunity.polymarket_link})\n[Analyze Data]({opportunity.analysis_link})",
                    "inline": False
                },
                {
                    "name": "⚙️ Filters Applied",
                    "value": opportunity.filters_applied,
                    "inline": False
                }
            ],
            "thumbnail": {
                "url": "https://i.imgur.com/7GkUJvA.png"  # Replace with your brand icon
            },
            "footer": {
                "text": "CPM Monitor | Premium Arbitrage Detection",
                "icon_url": "https://i.imgur.com/7GkUJvA.png"  # Replace with your logo
            }
        }
        
        return embed
    
    def create_compact_embed(self, opportunity: ArbitrageOpportunity) -> Dict[str, Any]:
        """Create compact version for quick scanning"""
        color = self.get_color_by_confidence(opportunity.quality_score)
        quality_emoji = self.get_quality_emoji(opportunity.quality_score)
        
        embed = {
            "title": f"{quality_emoji} {opportunity.market_name[:60]}{'...' if len(opportunity.market_name) > 60 else ''}",
            "description": f"**{opportunity.spread_percentage:.1f}%** spread • **{opportunity.quality_score:.1f}/10** quality • **{opportunity.confidence:.0f}%** confidence",
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "💰 Prices",
                    "value": f"YES: ${opportunity.yes_price:.2f} | NO: ${opportunity.no_price:.2f}",
                    "inline": True
                },
                {
                    "name": "💎 Liquidity",
                    "value": f"${opportunity.yes_liquidity:,.0f} | ${opportunity.no_liquidity:,.0f}",
                    "inline": True
                },
                {
                    "name": "⏰ Window",
                    "value": opportunity.time_window,
                    "inline": True
                },
                {
                    "name": "🔗 Trade",
                    "value": f"[{opportunity.market_source}]({opportunity.polymarket_link})",
                    "inline": True
                }
            ],
            "footer": {
                "text": f"CPM Monitor | {opportunity.market_source}",
                "icon_url": "https://i.imgur.com/7GkUJvA.png"
            }
        }
        
        return embed
    
    async def send_arbitrage_alert(self, opportunity: ArbitrageOpportunity, detailed: bool = True) -> bool:
        """Send professional arbitrage alert"""
        if not self.webhook_url:
            print("❌ No CPM_WEBHOOK_URL configured for arbitrage alerts")
            return False
            
        try:
            embed = self.create_professional_embed(opportunity) if detailed else self.create_compact_embed(opportunity)
            
            payload = {
                "embeds": [embed],
                "username": "CPM Arbitrage Alerts",
                "avatar_url": "https://i.imgur.com/7GkUJvA.png"
            }
            
            async with self.session.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 204:
                    print(f"✅ Professional arbitrage alert sent: {opportunity.market_name}")
                    return True
                else:
                    print(f"❌ Failed to send arbitrage alert: {response.status} - {await response.text()}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error sending arbitrage alert: {e}")
            return False
    
    async def send_multiple_alerts(self, opportunities: List[ArbitrageOpportunity], detailed: bool = True) -> int:
        """Send multiple arbitrage alerts with rate limiting"""
        success_count = 0
        
        for i, opportunity in enumerate(opportunities):
            if await self.send_arbitrage_alert(opportunity, detailed):
                success_count += 1
            
            # Rate limiting: 1 second between alerts
            if i < len(opportunities) - 1:
                await asyncio.sleep(1)
        
        print(f"✅ Sent {success_count}/{len(opportunities)} arbitrage alerts successfully")
        return success_count
    
    async def send_health_alert(self, message: str, level: str = "info") -> bool:
        """Send health alert to separate health webhook"""
        if not self.health_webhook_url:
            print("❌ No DISCORD_HEALTH_WEBHOOK_URL configured")
            return False
            
        try:
            # Color code based on level
            colors = {
                "info": 0x00FFFF,    # Cyan
                "warning": 0xFFFF00,  # Yellow
                "error": 0xFF0000,    # Red
                "success": 0x00FF00    # Green
            }
            
            color = colors.get(level, 0x00FFFF)
            
            embed = {
                "title": f"🚨 System Health Alert",
                "description": message,
                "color": color,
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": f"CPM Monitor Health • {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    "icon_url": "https://i.imgur.com/7GkUJvA.png"
                }
            }
            
            payload = {
                "embeds": [embed],
                "username": "CPM Health Monitor",
                "avatar_url": "https://i.imgur.com/7GkUJvA.png"
            }
            
            async with self.session.post(
                self.health_webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 204:
                    print(f"✅ Health alert sent: {level.upper()}")
                    return True
                else:
                    print(f"❌ Failed to send health alert: {response.status} - {await response.text()}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error sending health alert: {e}")
            return False

# Utility functions
def create_opportunity_from_data(data: Dict[str, Any]) -> ArbitrageOpportunity:
    """Create ArbitrageOpportunity from raw data"""
    return ArbitrageOpportunity(
        market_name=data.get("market_name", "Unknown Market"),
        opportunity_type=data.get("opportunity_type", "Arb Opportunity"),
        quality_score=data.get("quality_score", 7.0),
        spread_percentage=data.get("spread_percentage", 0.0),
        confidence=data.get("confidence", 85.0),
        yes_price=data.get("yes_price", 0.0),
        yes_liquidity=data.get("yes_liquidity", 0.0),
        no_price=data.get("no_price", 0.0),
        no_liquidity=data.get("no_liquidity", 0.0),
        time_window=data.get("time_window", "Valid for ~45 minutes"),
        polymarket_link=data.get("polymarket_link", ""),
        analysis_link=data.get("analysis_link", ""),
        filters_applied=data.get("filters_applied", "Spread > 2% | Liquidity > $40K | Volume > $500K 24h"),
        expires_at=datetime.fromisoformat(data.get("expires_at", datetime.utcnow().isoformat())),
        market_source=data.get("market_source", "Polymarket")
    )

# Example usage
async def send_professional_example():
    """Send example professional arbitrage alert"""
    async with ArbitrageAlert() as alerter:
        example_opportunity = ArbitrageOpportunity(
            market_name="Bitcoin Q4 Election Impact",
            opportunity_type="Arb Opportunity",
            quality_score=8.7,
            spread_percentage=2.3,
            confidence=92.0,
            yes_price=0.42,
            yes_liquidity=50000.0,
            no_price=0.61,
            no_liquidity=60000.0,
            time_window="Valid for ~45 minutes (expires in 3 blocks)",
            polymarket_link="https://polymarket.com/market/bitcoin-q4-election-impact",
            analysis_link="https://api.example.com/analysis/bitcoin-q4",
            filters_applied="Spread > 2% | Liquidity > $40K | Volume > $500K 24h",
            expires_at=datetime.utcnow() + timedelta(minutes=45),
            market_source="Polymarket"
        )
        
        await alerter.send_arbitrage_alert(example_opportunity, detailed=True)

if __name__ == "__main__":
    asyncio.run(send_professional_example())
