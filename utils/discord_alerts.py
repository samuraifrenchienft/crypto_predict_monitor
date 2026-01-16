"""
Discord Alert Embeds for Arbitrage Opportunities
Creates rich Discord embeds with color coding based on profit margin
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

@dataclass
class AlertData:
    """Data structure for arbitrage alert"""
    market_question: str
    yes_bid: float
    yes_ask: float
    no_bid: float
    no_ask: float
    spread: float
    est_profit: float
    profit_margin: float
    market_link: str
    expires_at: datetime
    liquidity: str
    market_source: str
    image_url: Optional[str] = None  # Event image URL
    category: Optional[str] = None  # Market category for fallback images

class DiscordAlerter:
    """Handles Discord alert embeds for arbitrage opportunities"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("DISCORD_WEBHOOK_URL")
        self.health_webhook_url = os.getenv("DISCORD_HEALTH_WEBHOOK_URL")  # For health alerts
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def get_platform_thumbnail(self, market_source: str) -> str:
        """Get platform-specific thumbnail image"""
        thumbnails = {
            'polymarket': 'https://polymarket.com/favicon.ico',
            'manifold': 'https://manifold.markets/favicon.ico',
            'limitless': 'https://limitless.exchange/favicon.ico',
            'azuro': 'https://gem.azuro.org/favicon.ico',
            'default': 'https://your-hosting.com/cpm_samurai_bulldog.png'
        }
        return thumbnails.get(market_source.lower(), thumbnails['default'])
    
    def get_color_by_margin(self, profit_margin: float) -> int:
        """Get Discord embed color based on profit margin"""
        if profit_margin >= 2.0:  # 2% or more - Green
            return 0x00FF00  # Green
        elif profit_margin >= 1.0:  # 1-2% - Yellow  
            return 0xFFFF00  # Yellow
        else:  # Less than 1% - Red
            return 0xFF0000  # Red
    
    def get_rating_emoji(self, profit_margin: float) -> str:
        """Get rating emoji based on profit margin"""
        if profit_margin >= 5.0:
            return "🎯🎯🎯🎯🎯"  # Excellent
        elif profit_margin >= 3.0:
            return "🎯🎯🎯🎯"    # Great
        elif profit_margin >= 2.0:
            return "🎯🎯🎯"      # Very Good
        elif profit_margin >= 1.0:
            return "🎯🎯"        # Good
        else:
            return "🎯"          # Fair
    
    def get_profit_emoji(self, profit_margin: float) -> str:
        """Get profit emoji based on margin"""
        if profit_margin >= 2.0:
            return "💰💰💰"  # High profit
        elif profit_margin >= 1.0:
            return "💰💰"     # Medium profit
        else:
            return "💰"         # Low profit
    
    def get_spread_emoji(self, spread: float) -> str:
        """Get spread emoji"""
        if spread >= 0.10:
            return "⚡⚡⚡"  # High spread
        elif spread >= 0.05:
            return "⚡⚡"     # Medium spread
        else:
            return "⚡"         # Low spread
    
    def create_detailed_embed(self, alert_data: AlertData) -> Dict[str, Any]:
        """Create detailed Discord embed"""
        color = self.get_color_by_margin(alert_data.profit_margin)
        rating = self.get_rating_emoji(alert_data.profit_margin)
        profit_emoji = self.get_profit_emoji(alert_data.profit_margin)
        spread_emoji = self.get_spread_emoji(alert_data.spread)
        
        # Format prices
        yes_mid = (alert_data.yes_bid + alert_data.yes_ask) / 2
        no_mid = (alert_data.no_bid + alert_data.no_ask) / 2
        
        # Make event name clickable
        clickable_event = f"[{alert_data.market_question}]({alert_data.market_link})"
        
        # Get event image using EventImageExtractor
        from .event_image_extractor import EventImageExtractor
        event_thumbnail = EventImageExtractor.get_fallback_image('default')
        
        # Try to extract image from additional data if available
        if hasattr(alert_data, 'image_url') and alert_data.image_url:
            event_thumbnail = alert_data.image_url
        elif hasattr(alert_data, 'category') and alert_data.category:
            event_thumbnail = EventImageExtractor.get_fallback_image(alert_data.category)
        
        embed = {
            "title": f"{rating} Arbitrage Opportunity",
            "description": f"**{clickable_event}**",
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "thumbnail": {
                "url": event_thumbnail,
                "height": 200,
                "width": 200
            },
            "fields": [
                {
                    "name": "🎯 Rating",
                    "value": f"{rating} ({alert_data.profit_margin:.2f}% margin)",
                    "inline": True
                },
                {
                    "name": "📊 Platform",
                    "value": f"[{alert_data.market_source.upper()}]({alert_data.market_link})",
                    "inline": True
                },
                {
                    "name": "⏰ Expires",
                    "value": f"<t:{int(alert_data.expires_at.timestamp())}:R>",
                    "inline": True
                },
                {
                    "name": f"{spread_emoji} Spread",
                    "value": f"**{alert_data.spread:.3f}** {'✓' if alert_data.spread > 0 else '✗'}",
                    "inline": False
                },
                {
                    "name": "💹 YES Market",
                    "value": f"```yaml\nBid: ${alert_data.yes_bid:.3f}\nAsk: ${alert_data.yes_ask:.3f}\nMid: ${yes_mid:.3f}```",
                    "inline": True
                },
                {
                    "name": "📉 NO Market",
                    "value": f"```yaml\nBid: ${alert_data.no_bid:.3f}\nAsk: ${alert_data.no_ask:.3f}\nMid: ${no_mid:.3f}```",
                    "inline": True
                },
                {
                    "name": f"{profit_emoji} Est. Profit",
                    "value": f"**${alert_data.est_profit:.2f}** ({alert_data.profit_margin:.2f}%)",
                    "inline": False
                },
                {
                    "name": "💎 Liquidity",
                    "value": alert_data.liquidity,
                    "inline": True
                },
                {
                    "name": "⚖️ Quick Actions",
                    "value": f"[🔗 Trade on {alert_data.market_source}]({alert_data.market_link})",
                    "inline": True
                }
            ],
            "footer": {
                "text": f"⚡ Arbitrage Alert System • Click event name or trade button to execute",
                "icon_url": "https://your-hosting.com/cpm_samurai_bulldog.png"  # Samurai bulldog icon
            }
        }
        
        return embed
    
    def create_compact_embed(self, alert_data: AlertData) -> Dict[str, Any]:
        """Create compact Discord embed"""
        color = self.get_color_by_margin(alert_data.profit_margin)
        rating = self.get_rating_emoji(alert_data.profit_margin)
        
        embed = {
            "title": f"{rating} {alert_data.market_question[:80]}{'...' if len(alert_data.market_question) > 80 else ''}",
            "description": f"**{alert_data.profit_margin:.2f}%** margin • **${alert_data.est_profit:.2f}** est. profit",
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "fields": [
                {
                    "name": "📊 Market",
                    "value": f"[{alert_data.market_source}]({alert_data.market_link})",
                    "inline": True
                },
                {
                    "name": "💰 Spread",
                    "value": f"**{alert_data.spread:.3f}**",
                    "inline": True
                },
                {
                    "name": "⏰ Expires",
                    "value": f"<t:{int(alert_data.expires_at.timestamp())}:R>",
                    "inline": True
                },
                {
                    "name": "💹 YES",
                    "value": f"${alert_data.yes_bid:.3f}/${alert_data.yes_ask:.3f}",
                    "inline": True
                },
                {
                    "name": "📉 NO",
                    "value": f"${alert_data.no_bid:.3f}/${alert_data.no_ask:.3f}",
                    "inline": True
                },
                {
                    "name": "💎 Liquidity",
                    "value": alert_data.liquidity,
                    "inline": True
                }
            ],
            "footer": {
                "text": f"⚡ Arbitrage Alert • {alert_data.market_source.upper()}",
                "icon_url": "https://your-hosting.com/cpm_samurai_bulldog.png"
            }
        }
        
        return embed
    
    async def send_alert(self, alert_data: AlertData, detailed: bool = True) -> bool:
        """Send Discord alert"""
        if not self.webhook_url:
            print("❌ No Discord webhook URL configured")
            return False
            
        try:
            embed = self.create_detailed_embed(alert_data) if detailed else self.create_compact_embed(alert_data)
            
            # Create action buttons
            components = [
                {
                    "type": 1,  # Action Row
                    "components": [
                        {
                            "type": 2,  # Button
                            "style": 5,  # Link style
                            "label": "🔗 Trade Now",
                            "url": alert_data.market_link
                        },
                        {
                            "type": 2,  # Button
                            "style": 5,  # Link style
                            "label": f"📊 {alert_data.market_source.upper()}",
                            "url": alert_data.market_link
                        }
                    ]
                }
            ]
            
            payload = {
                "embeds": [embed],
                "components": components,
                "username": "Arbitrage Alerts",
                "avatar_url": "https://your-hosting.com/cpm_samurai_bulldog.png"
            }
            
            async with self.session.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 204:
                    print(f"✅ Discord alert sent successfully for {alert_data.market_source}")
                    return True
                else:
                    print(f"❌ Failed to send Discord alert: {response.status} - {await response.text()}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error sending Discord alert: {e}")
            return False
    
    async def send_multiple_alerts(self, alerts: list[AlertData], detailed: bool = True) -> int:
        """Send multiple Discord alerts"""
        success_count = 0
        
        for alert in alerts:
            if await self.send_alert(alert, detailed):
                success_count += 1
            # Add small delay to avoid rate limiting
            await asyncio.sleep(1)
        
        print(f"✅ Sent {success_count}/{len(alerts)} Discord alerts successfully")
        return success_count
    
    async def send_health_alert(self, message: str, level: str = "info") -> bool:
        """Send health alert to Discord health webhook"""
        if not self.health_webhook_url:
            print("❌ No Discord health webhook URL configured")
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
                    "text": f"⚡ Crypto Prediction Monitor • {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
                    "icon_url": "https://your-hosting.com/cpm_samurai_bulldog.png"
                }
            }
            
            payload = {
                "embeds": [embed],
                "username": "Health Monitor",
                "avatar_url": "https://your-hosting.com/cpm_samurai_bulldog.png"
            }
            
            async with self.session.post(
                self.health_webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 204:
                    print(f"✅ Health alert sent successfully: {level.upper()}")
                    return True
                else:
                    print(f"❌ Failed to send health alert: {response.status} - {await response.text()}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error sending health alert: {e}")
            return False

# Utility functions
def create_alert_from_opportunity(opportunity: Dict[str, Any]) -> AlertData:
    """Create AlertData from opportunity dictionary"""
    
    # Generate proper market link using EventLinkGenerator
    from .event_link_generator import EventLinkGenerator
    market_link = EventLinkGenerator.generate_url_from_opportunity(opportunity)
    
    # Extract image and category data
    image_url = opportunity.get("image_url", opportunity.get("image", None))
    category = opportunity.get("category", opportunity.get("market_category", "default"))
    
    return AlertData(
        market_question=opportunity.get("question", "Unknown Market"),
        yes_bid=opportunity.get("yes_bid", opportunity.get("yes_price", 0.0)),
        yes_ask=opportunity.get("yes_ask", 0.0),
        no_bid=opportunity.get("no_bid", opportunity.get("no_price", 0.0)),
        no_ask=opportunity.get("no_ask", 0.0),
        spread=opportunity.get("spread", 0.0),
        est_profit=opportunity.get("profit_est", opportunity.get("est_profit", 0.0)),
        profit_margin=opportunity.get("profit_margin", 0.0),
        market_link=market_link,
        expires_at=datetime.fromisoformat(opportunity.get("expires_at", datetime.utcnow().isoformat())),
        liquidity=opportunity.get("liquidity", opportunity.get("volume", "Unknown")),
        market_source=opportunity.get("source", opportunity.get("platform", "unknown")),
        image_url=image_url,
        category=category
    )

# Example usage
async def send_example_alert():
    """Send an example Discord alert"""
    async with DiscordAlerter() as alerter:
        example_alert = AlertData(
            market_question="Will Donald Trump win the 2024 US Presidential Election?",
            yes_bid=0.45,
            yes_ask=0.47,
            no_bid=0.53,
            no_ask=0.55,
            spread=0.08,
            est_profit=8.00,
            profit_margin=1.6,
            market_link="https://polymarket.com/market/donald-trump-us-presidential-election-2024",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            liquidity="High",
            market_source="polymarket"
        )
        
        await alerter.send_alert(example_alert, detailed=True)

if __name__ == "__main__":
    asyncio.run(send_example_alert())
