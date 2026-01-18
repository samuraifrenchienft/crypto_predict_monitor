"""
Discord Alert Formatting for Cross-Platform Arbitrage
"""

import os
import logging
from typing import List
from datetime import datetime

from .complete_system import CrossPlatformArb

logger = logging.getLogger(__name__)


async def send_arbitrage_discord_alert(opportunity: CrossPlatformArb) -> bool:
    """Send Discord alert for cross-platform arbitrage opportunity"""
    
    webhook_url = os.getenv("CPM_WEBHOOK_URL")
    if not webhook_url:
        logger.warning("CPM_WEBHOOK_URL not set - skipping alert")
        return False
    
    try:
        import aiohttp
        
        # Build professional embed
        embed = {
            "title": f"🎯 CROSS-PLATFORM ARBITRAGE DETECTED",
            "description": f"**{opportunity.matched_pair.normalized_title}**",
            "color": _get_color_by_roi(opportunity.roi_percent),
            "fields": [
                {
                    "name": "💰 Net Profit",
                    "value": f"**${opportunity.net_profit:.4f}** ({opportunity.roi_percent:.2f}% ROI)",
                    "inline": True
                },
                {
                    "name": "📊 Raw Spread",
                    "value": f"**{opportunity.spread_percent:.2f}%**",
                    "inline": True
                },
                {
                    "name": "🎯 Match Score",
                    "value": f"**{opportunity.matched_pair.match_score:.0%}**",
                    "inline": True
                },
                {
                    "name": "🛒 BUY Side",
                    "value": (
                        f"Platform: **{opportunity.buy_platform.value.title()}**\n"
                        f"Price: **${opportunity.buy_price:.4f}**\n"
                        f"Liquidity: **${opportunity.buy_liquidity:,.0f}**"
                    ),
                    "inline": True
                },
                {
                    "name": "💸 SELL Side",
                    "value": (
                        f"Platform: **{opportunity.sell_platform.value.title()}**\n"
                        f"Price: **${opportunity.sell_price:.4f}**\n"
                        f"Liquidity: **${opportunity.sell_liquidity:,.0f}**"
                    ),
                    "inline": True
                },
                {
                    "name": "💵 Costs",
                    "value": (
                        f"Platform Fees: **${opportunity.platform_fees:.4f}**\n"
                        f"Slippage Est: **${opportunity.slippage_estimate:.4f}**"
                    ),
                    "inline": True
                },
                {
                    "name": "📈 Strategy",
                    "value": (
                        f"1. Buy YES on **{opportunity.buy_platform.value.title()}** @ ${opportunity.buy_price:.4f}\n"
                        f"2. Sell YES on **{opportunity.sell_platform.value.title()}** @ ${opportunity.sell_price:.4f}\n"
                        f"3. Profit: **${opportunity.net_profit:.4f}** after fees"
                    ),
                    "inline": False
                },
                {
                    "name": "🔗 Market A",
                    "value": f"**{opportunity.matched_pair.market_a.title[:100]}**",
                    "inline": False
                },
                {
                    "name": "🔗 Market B",
                    "value": f"**{opportunity.matched_pair.market_b.title[:100]}**",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"CPM Cross-Platform Arbitrage • {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        payload = {
            "embeds": [embed],
            "username": "CPM Arbitrage Bot"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status == 204:
                    logger.info(f"✅ Alert sent: {opportunity.matched_pair.normalized_title} ({opportunity.roi_percent:.2f}% ROI)")
                    return True
                else:
                    logger.error(f"❌ Discord webhook failed: {response.status}")
                    return False
                    
    except Exception as e:
        logger.error(f"❌ Error sending arbitrage alert: {e}")
        return False


def _get_color_by_roi(roi_percent: float) -> int:
    """Get embed color based on ROI"""
    if roi_percent >= 5.0:
        return 0x0066ff  # Blue - Exceptional (5%+)
    elif roi_percent >= 3.0:
        return 0x00ff00  # Green - Excellent (3-5%)
    elif roi_percent >= 2.0:
        return 0xffff00  # Yellow - Very Good (2-3%)
    elif roi_percent >= 1.0:
        return 0xffa500  # Orange - Good (1-2%)
    else:
        return 0x808080  # Gray - Fair (<1%)


async def send_multiple_arbitrage_alerts(opportunities: List[CrossPlatformArb], max_alerts: int = 5) -> int:
    """Send multiple arbitrage alerts (rate limited)"""
    
    import asyncio
    
    sent_count = 0
    
    for i, opp in enumerate(opportunities[:max_alerts]):
        success = await send_arbitrage_discord_alert(opp)
        if success:
            sent_count += 1
        
        # Rate limit: 1 alert per 2 seconds
        if i < len(opportunities[:max_alerts]) - 1:
            await asyncio.sleep(2)
    
    return sent_count
