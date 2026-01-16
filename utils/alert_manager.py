"""
Arbitrage Alert Generation System
Creates alerts when arbitrage opportunities are detected
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import asyncio
import json
import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Import Discord alert system
try:
    from .discord_alerts import DiscordAlerter, AlertData, create_alert_from_opportunity
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    print("Discord alerts not available - install required dependencies")

logger = logging.getLogger(__name__)

class ArbitrageAlertManager:
    """Manages arbitrage alerts for P&L tracking"""
    
    def __init__(self):
        load_dotenv('.env')
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if supabase_url and supabase_key:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            print("AlertManager: Supabase client initialized")
        else:
            self.supabase = None
            print("AlertManager: Running without Supabase database connection")
            
        self.alert_window = timedelta(hours=2)  # Alerts expire after 2 hours
        
        # Initialize Discord alerter if available
        self.discord_alerter = None
        if DISCORD_AVAILABLE and os.getenv("DISCORD_WEBHOOK_URL"):
            self.discord_alerter = DiscordAlerter()
            print("AlertManager: Discord alerter initialized")
        else:
            print("AlertManager: Discord alerts not configured")
    
    async def create_alert(
        self,
        user_id: str,
        market: str,
        ticker: str,
        spread: float,
        yes_price: float = None,
        no_price: float = None,
        market_data: Dict = None,
        confidence: float = 1.0
    ) -> Dict[str, Any]:
        """Create a new arbitrage alert"""
        if not self.supabase:
            logger.info(f"Creating demo alert for user {user_id} (no database)")
            return {
                "id": f"demo_{datetime.utcnow().timestamp()}",
                "user_id": user_id,
                "market": market,
                "ticker": ticker,
                "spread": spread,
                "yes_price": yes_price,
                "no_price": no_price,
                "status": "active",
                "created_at": datetime.utcnow().isoformat()
            }
            
        try:
            alert_data = {
                "user_id": user_id,
                "market": market,
                "ticker": ticker,
                "spread": spread,
                "yes_price": yes_price,
                "no_price": no_price,
                "market_data": market_data or {},
                "confidence_score": confidence,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + self.alert_window).isoformat(),
                "status": "active"
            }
            
            result = self.supabase.table("arbitrage_alerts").insert(alert_data).execute()
            
            if result.data:
                alert = result.data[0]
                logger.info(f"Created arbitrage alert {alert['id']} for user {user_id}")
                return alert
            else:
                logger.error("Failed to create alert")
                return {}
                
        except Exception as e:
            logger.error(f"Error creating arbitrage alert: {e}")
            return {}
    
    async def get_active_alerts(self, user_id: str = None) -> List[Dict]:
        """Get active arbitrage alerts"""
        if not self.supabase:
            return []
            
        try:
            query = self.supabase.table("arbitrage_alerts").select("*").eq("status", "active")
            
            if user_id:
                query = query.eq("user_id", user_id)
            
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"Error fetching active alerts: {e}")
            return []
    
    async def get_alerts_for_transaction(self, user_id: str, timestamp: datetime) -> List[Dict]:
        """Get alerts that would match a transaction at given timestamp"""
        if not self.supabase:
            return []
            
        try:
            # Look for alerts within 2 hours of timestamp
            since = timestamp - timedelta(hours=2)
            until = timestamp + timedelta(hours=2)
            
            result = self.supabase.table("arbitrage_alerts").select("*").eq("user_id", user_id).gte("created_at", since.isoformat()).lte("created_at", until.isoformat()).eq("status", "active").execute()
            
            return result.data
        except Exception as e:
            logger.error(f"Error fetching alerts for transaction: {e}")
            return []
    
    async def mark_alert_executed(self, alert_id: str, execution_id: str):
        """Mark an alert as executed"""
        try:
            result = self.supabase.table("arbitrage_alerts").update({
                "status": "executed",
                "execution_id": execution_id,
                "executed_at": datetime.utcnow().isoformat()
            }).eq("id", alert_id).execute()
            
            if result.data:
                logger.info(f"Marked alert {alert_id} as executed")
            return result.data
        except Exception as e:
            logger.error(f"Error marking alert as executed: {e}")
            return {}
    
    async def cleanup_expired_alerts(self):
        """Clean up expired alerts"""
        try:
            # Mark expired alerts
            result = self.supabase.table("arbitrage_alerts").update({
                "status": "expired"
            }).eq("status", "active").lt("expires_at", datetime.utcnow().isoformat()).execute()
            
            expired_count = len(result.data) if result.data else 0
            if expired_count > 0:
                logger.info(f"Marked {expired_count} alerts as expired")
            
            # Delete old alerts (older than 7 days)
            delete_result = self.supabase.table("arbitrage_alerts").delete().lt("created_at", (datetime.utcnow() - timedelta(days=7)).isoformat()).execute()
            
            deleted_count = len(delete_result.data) if delete_result.data else 0
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old alerts")
                
        except Exception as e:
            logger.error(f"Error cleaning up alerts: {e}")
    
    async def get_alert_statistics(self, user_id: str = None) -> Dict[str, Any]:
        """Get statistics about arbitrage alerts"""
        try:
            # Base query
            query = self.supabase.table("arbitrage_alerts").select("*")
            if user_id:
                query = query.eq("user_id", user_id)
            
            result = query.execute()
            alerts = result.data
            
            if not alerts:
                return {}
            
            # Calculate statistics
            total_alerts = len(alerts)
            active_alerts = len([a for a in alerts if a["status"] == "active"])
            executed_alerts = len([a for a in alerts if a["status"] == "executed"])
            expired_alerts = len([a for a in alerts if a["status"] == "expired"])
            
            # Calculate execution rate
            execution_rate = (executed_alerts / total_alerts * 100) if total_alerts > 0 else 0
            
            # Average spread
            avg_spread = sum(a["spread"] for a in alerts) / total_alerts if total_alerts > 0 else 0
            
            # Alerts by market
            by_market = {}
            for alert in alerts:
                market = alert["market"]
                if market not in by_market:
                    by_market[market] = {"total": 0, "executed": 0}
                by_market[market]["total"] += 1
                if alert["status"] == "executed":
                    by_market[market]["executed"] += 1
            
            return {
                "total_alerts": total_alerts,
                "active_alerts": active_alerts,
                "executed_alerts": executed_alerts,
                "expired_alerts": expired_alerts,
                "execution_rate": round(execution_rate, 2),
                "avg_spread": round(avg_spread, 4),
                "by_market": by_market
            }
            
        except Exception as e:
            logger.error(f"Error calculating alert statistics: {e}")
            return {}

# Integration with arbitrage detection
async def create_alert_from_opportunity(
    opportunity: Dict[str, Any],
    user_id: str
) -> Optional[Dict[str, Any]]:
    """Create an alert from an arbitrage opportunity"""
    
    alert_manager = ArbitrageAlertManager()
    
    # Extract opportunity data
    market1 = opportunity.get("market1", {})
    market2 = opportunity.get("market2", {})
    
    # Determine which market to use for the alert
    # Use the market with higher volume or better liquidity
    primary_market = market1.get("source", "unknown")
    ticker = market1.get("ticker", "unknown")
    
    # Calculate spread
    mid1 = market1.get("mid")
    mid2 = market2.get("mid")
    
    if mid1 is None or mid2 is None:
        return None
    
    spread = abs(mid1 - mid2)
    
    # Get prices
    yes_price = market1.get("bid") if market1.get("outcome_id", "").endswith("YES") else market1.get("ask")
    no_price = market2.get("bid") if market2.get("outcome_id", "").endswith("NO") else market2.get("ask")
    
    # Create the alert
    alert = await alert_manager.create_alert(
        user_id=user_id,
        market=primary_market,
        ticker=ticker,
        spread=spread,
        yes_price=yes_price,
        no_price=no_price,
        market_data={
            "opportunity": opportunity,
            "detected_at": datetime.utcnow().isoformat(),
            "market1": market1,
            "market2": market2
        },
        confidence=opportunity.get("confidence", 1.0)
    )
    
    return alert

    async def send_discord_alert(self, opportunity: Dict[str, Any], detailed: bool = True) -> bool:
        """Send Discord alert for arbitrage opportunity"""
        if not self.discord_alerter:
            logger.info("Discord alerter not available")
            return False
            
        try:
            # Convert opportunity to AlertData
            alert_data = create_alert_from_opportunity(opportunity)
            
            # Send to Discord
            success = await self.discord_alerter.send_alert(alert_data, detailed)
            
            if success:
                logger.info(f"Discord alert sent for {opportunity.get('source', 'unknown')} opportunity")
            else:
                logger.error(f"Failed to send Discord alert for {opportunity.get('source', 'unknown')} opportunity")
                
            return success
        except Exception as e:
            logger.error(f"Error sending Discord alert: {e}")
            return False
    
    async def send_discord_alerts_batch(self, opportunities: List[Dict[str, Any]], detailed: bool = True) -> int:
        """Send multiple Discord alerts in batch"""
        if not self.discord_alerter:
            logger.info("Discord alerter not available for batch alerts")
            return 0
            
        try:
            # Convert opportunities to AlertData objects
            alerts = []
            for opp in opportunities:
                try:
                    alert_data = create_alert_from_opportunity(opp)
                    alerts.append(alert_data)
                except Exception as e:
                    logger.error(f"Error converting opportunity to alert data: {e}")
                    continue
            
            # Send batch alerts
            success_count = await self.discord_alerter.send_multiple_alerts(alerts, detailed)
            
            logger.info(f"Sent {success_count}/{len(opportunities)} Discord alerts in batch")
            return success_count
            
        except Exception as e:
            logger.error(f"Error sending Discord alerts batch: {e}")
            return 0

# Background task for alert cleanup
async def alert_cleanup_task():
    """Background task to clean up expired alerts"""
    alert_manager = ArbitrageAlertManager()
    
    while True:
        try:
            await alert_manager.cleanup_expired_alerts()
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error(f"Error in alert cleanup task: {e}")
            await asyncio.sleep(300)  # Wait 5 minutes on error

# Start background tasks
async def start_alert_system():
    """Start the alert system background tasks"""
    logger.info("Starting arbitrage alert system")
    asyncio.create_task(alert_cleanup_task())
