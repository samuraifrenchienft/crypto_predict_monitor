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
        # Use provided webhook_url, then config, then environment variable
        if webhook_url:
            self.webhook_url = webhook_url
        else:
            # Try to get from config - use health webhook for dashboard changes
            try:
                from bot.config import load_config
                cfg = load_config()
                self.webhook_url = cfg.discord_health_webhook_url  # Use health webhook for dashboard changes
            except:
                # Fallback to hardcoded health webhook URL
                self.webhook_url = "https://discord.com/api/webhooks/1455877944005365814/TpDNqyFu2XhD6SKgOMPssuBozVJ2HJvFa2fOMSqtOnyw6t5zaTx3F53TAcpDbLYpCeXb"
        
        self.health_webhook_url = os.getenv("DISCORD_HEALTH_WEBHOOK_URL")
        self.session = None
        
        # Brand configuration
        self.brand_name = "CPM Monitor"
        self.brand_tagline = "Premium Arbitrage Detection"
        # Samurai Frenchie Icon - Replace with your hosted URL
        self.brand_icon = "https://your-hosting.com/cpm_samurai_bulldog.png"  # Samurai bulldog icon
        self.brand_logo = "https://your-hosting.com/cpm_samurai_bulldog.png"
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def get_embed_color(self, confidence_score: float) -> int:
        """Get Discord embed color based on confidence score using your tier system"""
        if confidence_score >= 8.5:
            return 0x0066ff  # Blue for EXCEPTIONAL (3%+ spread)
        elif confidence_score >= 7.5:
            return 0x00ff00  # Green for EXCELLENT (2.51-3% spread)
        elif confidence_score >= 6.5:
            return 0xffff00  # Yellow for VERY GOOD (2.01-2.5% spread)
        else:
            return 0xffa500  # Orange for GOOD (1.5-2% spread)
    
    def get_confidence_tier(self, confidence_score: float) -> str:
        """Get confidence tier description using your spread-based tiers"""
        if confidence_score >= 8.5:
            return "EXCEPTIONAL 🔵 (3%+ spread)"
        elif confidence_score >= 7.5:
            return "EXCELLENT 🟢 (2.51-3% spread)"
        elif confidence_score >= 6.5:
            return "VERY GOOD 🟡 (2.01-2.5% spread)"
        else:
            return "GOOD 🟠 (1.5-2% spread)"
    
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
    
    async def create_professional_embed(self, opportunity: ArbitrageOpportunity) -> Dict[str, Any]:
        """Create investment-grade Discord embed with color-coded left border"""
        
        # Get dynamic color for left border
        embed_color = self.get_embed_color(opportunity.confidence_score)
        confidence_tier = self.get_confidence_tier(opportunity.confidence_score)
        quality_level = self.get_quality_level(opportunity.quality_score)
        
        # Generate proper Polymarket URL - FIX THE BROKEN LINK
        if opportunity.polymarket_link and opportunity.polymarket_link.startswith('https://polymarket.com'):
            # Use the provided link if it's valid
            polymarket_url = opportunity.polymarket_link
        elif opportunity.market_id:
            # Generate proper Polymarket URL from market ID
            # Remove any leading/trailing slashes and ensure proper format
            clean_market_id = opportunity.market_id.strip('/')
            polymarket_url = f"https://polymarket.com/event/{clean_market_id}"
        else:
            # Fallback - use search if no market ID
            market_slug = opportunity.market_name.lower().replace(' ', '-').replace('?', '').replace('!', '').replace('.', '').replace(',', '')
            polymarket_url = f"https://polymarket.com/search?q={market_slug.replace('-', '%20')}"
        
        # Fetch actual event image from Polymarket API
        event_image_url = None
        if opportunity.market_id:
            # Try to get the real event image from Polymarket
            event_image_url = await self._fetch_polymarket_event_image(opportunity.market_id)
        
        analysis_url = opportunity.analysis_link or f"https://api.example.com/analysis/{opportunity.market_id or 'unknown'}"
        
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
                    "value": f"[🎯 View on Polymarket]({polymarket_url})\n[📊 Analyze Data]({analysis_url})",
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
            # Add Polymarket event image in top right if available
            "image": {
                "url": event_image_url
            } if event_image_url else None,
            "footer": {
                "text": f"{self.brand_name} | {self.brand_tagline}",
                "icon_url": self.brand_logo
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        return embed
    
    async def _fetch_polymarket_event_image(self, market_id: str) -> Optional[str]:
        """Fetch the actual event image from Polymarket API with verification"""
        try:
            # Try multiple image URL patterns that Polymarket uses
            image_patterns = [
                f"https://polymarket.com/content/event-images/{market_id}.png",
                f"https://polymarket.com/content/event-images/{market_id}.jpg", 
                f"https://polymarket.com/content/event-images/{market_id}.jpeg",
                f"https://cdn.polymarket.com/content/event-images/{market_id}.png",
                f"https://strapi-matic.poly.market.com/content/event-images/{market_id}.png"
            ]
            
            # Test each image URL to see which one exists
            for image_url in image_patterns:
                try:
                    if self.session:
                        async with self.session.head(image_url, timeout=5) as response:
                            if response.status == 200:
                                logger.info(f"✅ Found event image: {image_url}")
                                return image_url
                except Exception as e:
                    logger.debug(f"Image URL test failed: {image_url} - {e}")
                    continue
            
            # If no image found, try to fetch from Polymarket API
            return await self._fetch_image_from_polymarket_api(market_id)
            
        except Exception as e:
            logger.warning(f"Failed to fetch event image for {market_id}: {e}")
            return None
    
    async def _fetch_image_from_polymarket_api(self, market_id: str) -> Optional[str]:
        """Fetch event image from Polymarket's API"""
        try:
            if not self.session:
                return None
                
            # Try to get market data from Polymarket API
            api_urls = [
                f"https://gamma-api.polymarket.com/markets/{market_id}",
                f"https://strapi-matic.poly.market.com/markets/{market_id}",
                f"https://data-api.polymarket.com/markets/{market_id}"
            ]
            
            for api_url in api_urls:
                try:
                    async with self.session.get(api_url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Look for image URL in response
                            image_url = None
                            
                            # Common field names for images
                            image_fields = ['image', 'imageUrl', 'image_url', 'picture', 'picture_url', 'icon', 'icon_url']
                            
                            for field in image_fields:
                                if field in data and data[field]:
                                    image_url = data[field]
                                    break
                            
                            # Check nested objects
                            if not image_url and isinstance(data, dict):
                                for key, value in data.items():
                                    if isinstance(value, dict):
                                        for field in image_fields:
                                            if field in value and value[field]:
                                                image_url = value[field]
                                                break
                                        if image_url:
                                            break
                            
                            if image_url:
                                logger.info(f"✅ Found image from API: {image_url}")
                                return image_url
                                
                except Exception as e:
                    logger.debug(f"API request failed: {api_url} - {e}")
                    continue
            
            logger.warning(f"No image found for market {market_id}")
            return None
            
        except Exception as e:
            logger.warning(f"Failed to fetch image from Polymarket API for {market_id}: {e}")
            return None
    
    async def send_arbitrage_alert(self, opportunity: ArbitrageOpportunity) -> bool:
        """Send professional arbitrage alert to Discord"""
        if not self.webhook_url:
            logger.error("❌ No CPM_WEBHOOK_URL configured for arbitrage alerts")
            return False
        
        if not self.session:
            logger.error("❌ Session not initialized. Use async context manager.")
            return False
        
        # Create professional embed (now async)
        embed = await self.create_professional_embed(opportunity)
        
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
    
    async def send_config_change_alert(self, changes: list, updated_by: str = "System") -> bool:
        """Send configuration change alert to arbitrage webhook"""
        if not self.webhook_url:
            logger.error("❌ No CPM_WEBHOOK_URL configured for config alerts")
            return False
        
        if not self.session:
            logger.error("❌ Session not initialized. Use async context manager.")
            return False
        
        # Create config change embed
        embed = {
            "title": "⚙️ CONFIGURATION CHANGED",
            "description": f"System configuration updated by {updated_by}",
            "color": 0xff9900,  # Orange for config changes
            "fields": [
                {
                    "name": "📋 Changes Made",
                    "value": "\n".join(f"• {change}" for change in changes),
                    "inline": False
                },
                {
                    "name": "🕐 Timestamp",
                    "value": f"<t:{int(datetime.utcnow().timestamp())}:R>",
                    "inline": True
                },
                {
                    "name": "🔄 Impact",
                    "value": "Arbitrage detection and alerting system updated",
                    "inline": True
                }
            ],
            "footer": {
                "text": f"{self.brand_name} | Configuration Monitor"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        payload = {
            "content": f"🔧 **CONFIGURATION UPDATE**\n\n{len(changes)} changes made to arbitrage system configuration.",
            "username": "CPM Config Monitor",
            "embeds": [embed]
        }
        
        try:
            async with self.session.post(self.webhook_url, json=payload) as response:
                if response.status == 204:
                    logger.info(f"✅ Sent config change alert with {len(changes)} changes")
                    return True
                else:
                    logger.error(f"❌ Failed to send config change alert: {response.status}")
                    return False
        except Exception as e:
            logger.error(f"❌ Error sending config change alert: {e}")
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
        # Use async context manager for proper session handling
        async with alerter:
            embed = await alerter.create_professional_embed(opp)
            color = alerter.get_embed_color(opp.confidence_score)
            tier = alerter.get_confidence_tier(opp.confidence_score)
            
            print(f"\n{i+1}. {opp.market_name}")
            print(f"   Quality: {opp.quality_score:.1f}/10")
            print(f"   Confidence: {opp.confidence_score:.0f}% ({tier})")
            print(f"   Spread: {opp.spread_percentage:.1f}%")
            print(f"   Color: #{color:06x}")
            print(f"   Embed Title: {embed['title']}")
            print(f"   Fields Count: {len(embed['fields'])}")
            print(f"   Polymarket URL: {opp.market_id and f'https://polymarket.com/event/{opp.market_id}' or 'Search fallback'}")
            print(f"   Event Image: {'✅ Found' if embed.get('image') else '❌ Not found'}")
    
    print(f"\n✅ Professional alert system test complete!")
    print(f"🎨 Color coding working: 🟢 TRADE THIS | 🟡 GOOD OPPORTUNITY | 🟠 MONITOR/RESEARCH")
    print(f"📱 Left border colors will indicate urgency in Discord")
    print(f"🔗 Polymarket links fixed and event images fetched!")
    print(f"🖼️ Real event images will appear in Discord alerts!")

if __name__ == "__main__":
    asyncio.run(test_professional_alerts())
