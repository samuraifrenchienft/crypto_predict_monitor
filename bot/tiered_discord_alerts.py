"""
Tiered Discord Alerts - Spread-Only System
Color-coded Discord alerts based on arbitrage tiers
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class TieredDiscordAlerts:
    """Tiered Discord alert system with color-coded embeds"""
    
    def __init__(self, webhook_url: str):
        """
        Initialize tiered Discord alerts
        
        Args:
            webhook_url: Discord webhook URL for sending alerts
        """
        self.webhook_url = webhook_url
        
        # Tier colors and styling
        self.tier_colors = {
            "exceptional": 0x0066ff,  # Blue
            "excellent": 0x00ff00,    # Green
            "very_good": 0xffff00,    # Yellow
            "good": 0xffa500,        # Orange
            "fair": 0x808080,        # Gray
            "poor": 0x808080         # Gray
        }
        
        self.tier_emojis = {
            "exceptional": "🔵",
            "excellent": "🟢",
            "very_good": "💛",
            "good": "🟠",
            "fair": "⚪",
            "poor": "⚫"
        }
    
    async def send_alert(self, opportunity: Dict[str, Any]) -> bool:
        """
        Send tiered Discord alert for arbitrage opportunity
        
        Args:
            opportunity: Arbitrage opportunity with tier information
            
        Returns:
            True if alert sent successfully, False otherwise
        """
        try:
            tier = opportunity.get('tier', 'unknown')
            tier_emoji = opportunity.get('tier_emoji', '❓')
            tier_color = self.tier_colors.get(tier, 0x808080)
            tier_action = opportunity.get('tier_action', 'UNKNOWN')
            
            # Extract opportunity data
            title = opportunity.get('normalized_title', 'Unknown Opportunity')
            spread_pct = opportunity.get('spread_percentage', 0)
            quality_score = opportunity.get('quality_score', 0)
            markets = opportunity.get('markets', [])
            
            # Create Discord embed
            embed = {
                "title": f"{tier_emoji} {tier.upper()} Arbitrage Detected: {spread_pct:.1f}% spread",
                "description": f"**{title}**\n\n{tier_action}",
                "color": tier_color,
                "fields": [
                    {
                        "name": "💰 Spread",
                        "value": f"**{spread_pct:.1f}%**",
                        "inline": True
                    },
                    {
                        "name": "⭐ Quality Score",
                        "value": f"**{quality_score:.1f}/10**",
                        "inline": True
                    },
                    {
                        "name": "📊 Markets",
                        "value": f"{len(markets)} platforms",
                        "inline": True
                    }
                ],
                "footer": {
                    "text": f"CPM Monitor | Tier: {tier.upper()} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Add market details
            for i, market in enumerate(markets[:5], 1):  # Limit to 5 markets
                source = market.get('source', 'Unknown').upper()
                market_url = market.get('url', '')
                
                if market_url:
                    embed["fields"].append({
                        "name": f"Market {i}: {source}",
                        "value": f"[View Market]({market_url})",
                        "inline": False
                    })
                else:
                    embed["fields"].append({
                        "name": f"Market {i}: {source}",
                        "value": "No link available",
                        "inline": False
                    })
            
            # Create alert payload
            payload = {
                "embeds": [embed],
                "username": "CPM Arbitrage Bot",
                "avatar_url": "https://your-hosting.com/cpm_samurai_bulldog.png"
            }
            
            # Send alert
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        logger.info(f"✅ {tier.upper()} alert sent: {title}")
                        return True
                    else:
                        logger.error(f"❌ Failed to send {tier} alert: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Error sending {tier} alert: {e}")
            return False
    
    async def send_batch_alerts(self, opportunities: List[Dict[str, Any]], max_tier: int = 4) -> Dict[str, int]:
        """
        Send batch alerts for multiple opportunities
        
        Args:
            opportunities: List of arbitrage opportunities
            max_tier: Maximum tier priority to alert (1-4 = good or better)
            
        Returns:
            Dictionary with success/failure counts
        """
        results = {"success": 0, "failed": 0, "skipped": 0}
        
        # Filter by tier priority
        filtered_opps = [
            opp for opp in opportunities 
            if opp.get('tier_priority', 99) <= max_tier
        ]
        
        logger.info(f"🚀 Sending batch alerts for {len(filtered_opps)} opportunities (tier priority ≤ {max_tier})")
        
        # Send alerts concurrently
        tasks = []
        for opp in filtered_opps:
            task = self.send_alert(opp)
            tasks.append(task)
        
        # Wait for all alerts to complete
        if tasks:
            results_list = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results_list:
                if isinstance(result, Exception):
                    results["failed"] += 1
                elif result:
                    results["success"] += 1
                else:
                    results["failed"] += 1
        
        # Count skipped opportunities
        results["skipped"] = len(opportunities) - len(filtered_opps)
        
        logger.info(f"📊 Batch alert results: ✅ {results['success']} sent, ❌ {results['failed']} failed, ⏭️ {results['skipped']} skipped")
        
        return results
    
    async def send_summary_alert(self, tier_breakdown: Dict[str, Any]) -> bool:
        """
        Send summary alert with tier breakdown
        
        Args:
            tier_breakdown: Tier breakdown statistics
            
        Returns:
            True if alert sent successfully, False otherwise
        """
        try:
            summary = tier_breakdown.get('summary', {})
            tiers = tier_breakdown.get('tiers', {})
            
            # Create summary embed
            embed = {
                "title": "📊 Arbitrage Summary Report",
                "description": f"**Total Processed**: {summary.get('total_processed', 0)} opportunities\n**Pass Rate**: {summary.get('pass_rate', 0)}%",
                "color": 0x00ff00,  # Green for summary
                "fields": [],
                "footer": {
                    "text": f"CPM Monitor | Summary Report | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Add tier breakdown
            for tier_name in ["exceptional", "excellent", "very_good", "good"]:
                tier_data = tiers.get(tier_name, {})
                count = tier_data.get('count', 0)
                emoji = tier_data.get('emoji', '❓')
                
                if count > 0:
                    embed["fields"].append({
                        "name": f"{emoji} {tier_name.upper()}",
                        "value": f"Count: {count} | {tier_data.get('percentage', 0)}%",
                        "inline": True
                    })
            
            # Add summary stats
            embed["fields"].extend([
                {
                    "name": "✅ Passed",
                    "value": str(summary.get('total_passed', 0)),
                    "inline": True
                },
                {
                    "name": "❌ Filtered",
                    "value": str(summary.get('total_filtered', 0)),
                    "inline": True
                }
            ])
            
            # Create alert payload
            payload = {
                "embeds": [embed],
                "username": "CPM Arbitrage Bot",
                "avatar_url": "https://your-hosting.com/cpm_samurai_bulldog.png"
            }
            
            # Send alert
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        logger.info("✅ Summary alert sent successfully")
                        return True
                    else:
                        logger.error(f"❌ Failed to send summary alert: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Error sending summary alert: {e}")
            return False
    
    async def send_health_alert(self, status: str, message: str, details: Dict[str, Any] = None) -> bool:
        """
        Send health/system status alert
        
        Args:
            status: Status level (info, warning, error, critical)
            message: Alert message
            details: Additional details dictionary
            
        Returns:
            True if alert sent successfully, False otherwise
        """
        try:
            # Color based on status
            status_colors = {
                "info": 0x00ff00,      # Green
                "warning": 0xffff00,   # Yellow
                "error": 0xff0000,     # Red
                "critical": 0xff00ff   # Magenta
            }
            
            color = status_colors.get(status, 0x808080)
            
            # Create embed
            embed = {
                "title": f"🔍 System Status: {status.upper()}",
                "description": message,
                "color": color,
                "fields": [],
                "footer": {
                    "text": f"CPM Monitor | Health Alert | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                },
                "timestamp": datetime.now().isoformat()
            }
            
            # Add details if provided
            if details:
                for key, value in details.items():
                    embed["fields"].append({
                        "name": key.replace('_', ' ').title(),
                        "value": str(value),
                        "inline": True
                    })
            
            # Create alert payload
            payload = {
                "embeds": [embed],
                "username": "CPM Monitor",
                "avatar_url": "https://your-hosting.com/cpm_samurai_bulldog.png"
            }
            
            # Send alert
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        logger.info(f"✅ Health alert sent: {status}")
                        return True
                    else:
                        logger.error(f"❌ Failed to send health alert: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Error sending health alert: {e}")
            return False

# Global alert instance
_alert_instance = None

def get_alerter(webhook_url: str) -> TieredDiscordAlerts:
    """Get or create alert instance"""
    global _alert_instance
    if _alert_instance is None or _alert_instance.webhook_url != webhook_url:
        _alert_instance = TieredDiscordAlerts(webhook_url)
    return _alert_instance

async def send_tiered_alert(webhook_url: str, opportunity: Dict[str, Any]) -> bool:
    """
    Convenience function to send tiered alert
    
    Args:
        webhook_url: Discord webhook URL
        opportunity: Arbitrage opportunity with tier information
        
    Returns:
        True if alert sent successfully, False otherwise
    """
    alerter = get_alerter(webhook_url)
    return await alerter.send_alert(opportunity)

async def send_batch_alerts(webhook_url: str, opportunities: List[Dict[str, Any]], max_tier: int = 4) -> Dict[str, int]:
    """
    Convenience function to send batch alerts
    
    Args:
        webhook_url: Discord webhook URL
        opportunities: List of arbitrage opportunities
        max_tier: Maximum tier priority to alert
        
    Returns:
        Dictionary with success/failure counts
    """
    alerter = get_alerter(webhook_url)
    return await alerter.send_batch_alerts(opportunities, max_tier)
