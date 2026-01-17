"""
Discord Alerts Module
Tier-based Discord webhook alerts for arbitrage opportunities
"""

import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, Any, List, Optional

from bot.models import ArbitrageOpportunity, AlertData, HealthStatus
from shared.logger import get_logger


class DiscordAlerts:
    """Tier-based Discord alert system"""
    
    def __init__(self, webhook_url: str, health_webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
        self.health_webhook_url = health_webhook_url
        self.logger = get_logger(__name__)
        
        # Tier colors for Discord embeds
        self.tier_colors = {
            'exceptional': 0x0066ff,  # Blue
            'excellent': 0x00ff00,    # Green
            'very_good': 0xffff00,    # Yellow
            'good': 0xffa500,        # Orange
            'fair': 0x808080,        # Gray
            'poor': 0x808080         # Gray
        }
    
    async def send_arbitrage_alert(self, opportunity: ArbitrageOpportunity) -> bool:
        """
        Send arbitrage opportunity alert
        
        Args:
            opportunity: Arbitrage opportunity to alert
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not opportunity.is_alertable():
            self.logger.debug(f"Skipping non-alertable opportunity: {opportunity.normalized_title}")
            return True
        
        try:
            embed = self._create_arbitrage_embed(opportunity)
            payload = {
                'embeds': [embed],
                'username': 'CPM Arbitrage Bot',
                'avatar_url': 'https://your-hosting.com/cpm_samurai_bulldog.png'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        self.logger.info(f"✅ Sent {opportunity.tier.value} alert: {opportunity.normalized_title}")
                        return True
                    else:
                        self.logger.error(f"❌ Failed to send alert: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Error sending arbitrage alert: {e}")
            return False
    
    async def send_batch_alerts(self, opportunities: List[ArbitrageOpportunity]) -> Dict[str, int]:
        """
        Send batch alerts for multiple opportunities
        
        Args:
            opportunities: List of arbitrage opportunities
            
        Returns:
            Results dictionary with success/failure counts
        """
        # Filter alertable opportunities
        alertable_opps = [opp for opp in opportunities if opp.is_alertable()]
        
        if not alertable_opps:
            self.logger.info("No alertable opportunities to send")
            return {'success': 0, 'failed': 0, 'skipped': len(opportunities)}
        
        self.logger.info(f"🚀 Sending batch alerts for {len(alertable_opps)} opportunities")
        
        # Send alerts concurrently
        tasks = [self.send_arbitrage_alert(opp) for opp in alertable_opps]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count results
        success_count = sum(1 for result in results if result is True)
        failed_count = len(results) - success_count
        skipped_count = len(opportunities) - len(alertable_opps)
        
        results_dict = {
            'success': success_count,
            'failed': failed_count,
            'skipped': skipped_count
        }
        
        self.logger.info(f"📊 Batch alert results: ✅ {success_count} sent, ❌ {failed_count} failed, ⏭️ {skipped_count} skipped")
        
        return results_dict
    
    async def send_health_alert(self, status: HealthStatus) -> bool:
        """
        Send health status alert
        
        Args:
            status: Health status to report
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.health_webhook_url:
            self.logger.warning("No health webhook URL configured")
            return False
        
        try:
            embed = self._create_health_embed(status)
            payload = {
                'embeds': [embed],
                'username': 'CPM Monitor',
                'avatar_url': 'https://your-hosting.com/cpm_samurai_bulldog.png'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.health_webhook_url, json=payload) as response:
                    if response.status == 204:
                        self.logger.info(f"✅ Sent health alert: {status.status}")
                        return True
                    else:
                        self.logger.error(f"❌ Failed to send health alert: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Error sending health alert: {e}")
            return False
    
    async def send_summary_report(self, summary_data: Dict[str, Any]) -> bool:
        """
        Send summary report alert
        
        Args:
            summary_data: Summary statistics
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            embed = self._create_summary_embed(summary_data)
            payload = {
                'embeds': [embed],
                'username': 'CPM Arbitrage Bot',
                'avatar_url': 'https://your-hosting.com/cpm_samurai_bulldog.png'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        self.logger.info("✅ Sent summary report")
                        return True
                    else:
                        self.logger.error(f"❌ Failed to send summary: {response.status}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"❌ Error sending summary: {e}")
            return False
    
    def _create_arbitrage_embed(self, opportunity: ArbitrageOpportunity) -> Dict[str, Any]:
        """Create Discord embed for arbitrage opportunity"""
        color = self.tier_colors.get(opportunity.tier.value, 0x808080)
        
        embed = {
            'title': f"{opportunity.tier_emoji} {opportunity.tier.value.upper()} Arbitrage Detected",
            'description': f"**{opportunity.normalized_title}**\n\n{opportunity.tier_action}",
            'color': color,
            'fields': [
                {
                    'name': '💰 Spread',
                    'value': f"**{opportunity.spread_percentage:.1f}%**",
                    'inline': True
                },
                {
                    'name': '⭐ Quality Score',
                    'value': f"**{opportunity.quality_score:.1f}/10**",
                    'inline': True
                },
                {
                    'name': '📊 Markets',
                    'value': f"{len(opportunity.markets)} platforms",
                    'inline': True
                }
            ],
            'footer': {
                'text': f"CPM Monitor | Tier: {opportunity.tier.value.upper()} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Add market details
        for i, market in enumerate(opportunity.markets[:5], 1):
            source = market.get('source', 'Unknown').upper()
            url = market.get('url', '')
            
            if url:
                embed['fields'].append({
                    'name': f"Market {i}: {source}",
                    'value': f"[View Market]({url})",
                    'inline': False
                })
            else:
                embed['fields'].append({
                    'name': f"Market {i}: {source}",
                    'value': "No link available",
                    'inline': False
                })
        
        return embed
    
    def _create_health_embed(self, status: HealthStatus) -> Dict[str, Any]:
        """Create Discord embed for health status"""
        # Color based on status
        status_colors = {
            'healthy': 0x00ff00,      # Green
            'ok': 0x00ff00,          # Green
            'info': 0x00ff00,         # Green
            'warning': 0xffff00,      # Yellow
            'error': 0xff0000,        # Red
            'critical': 0xff00ff      # Magenta
        }
        
        color = status_colors.get(status.status.lower(), 0x808080)
        
        embed = {
            'title': f"🔍 System Status: {status.status.upper()}",
            'description': status.message,
            'color': color,
            'fields': [],
            'footer': {
                'text': f"CPM Monitor | Health Alert | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Add details if provided
        for key, value in status.details.items():
            embed['fields'].append({
                'name': key.replace('_', ' ').title(),
                'value': str(value),
                'inline': True
            })
        
        return embed
    
    def _create_summary_embed(self, summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create Discord embed for summary report"""
        summary = summary_data.get('summary', {})
        tiers = summary_data.get('tiers', {})
        
        embed = {
            'title': '📊 Arbitrage Summary Report',
            'description': f"**Total Processed**: {summary.get('total_processed', 0)} opportunities\n**Pass Rate**: {summary.get('pass_rate', 0)}%",
            'color': 0x00ff00,  # Green for summary
            'fields': [],
            'footer': {
                'text': f"CPM Monitor | Summary Report | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            },
            'timestamp': datetime.now().isoformat()
        }
        
        # Add tier breakdown
        tier_emojis = {
            'exceptional': '🔵',
            'excellent': '🟢',
            'very_good': '💛',
            'good': '🟠'
        }
        
        for tier_name, emoji in tier_emojis.items():
            tier_data = tiers.get(tier_name, {})
            count = tier_data.get('count', 0)
            
            if count > 0:
                embed['fields'].append({
                    'name': f"{emoji} {tier_name.upper()}",
                    'value': f"Count: {count} | {tier_data.get('percentage', 0)}%",
                    'inline': True
                })
        
        # Add summary stats
        embed['fields'].extend([
            {
                'name': '✅ Passed',
                'value': str(summary.get('total_passed', 0)),
                'inline': True
            },
            {
                'name': '❌ Filtered',
                'value': str(summary.get('total_filtered', 0)),
                'inline': True
            }
        ])
        
        return embed


# Global alert instance
_alerts_instance = None


def get_discord_alerts(webhook_url: str, health_webhook_url: Optional[str] = None) -> DiscordAlerts:
    """Get or create Discord alerts instance"""
    global _alerts_instance
    if _alerts_instance is None or _alerts_instance.webhook_url != webhook_url:
        _alerts_instance = DiscordAlerts(webhook_url, health_webhook_url)
    return _alerts_instance
