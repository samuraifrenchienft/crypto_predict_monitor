"""
Fallback Polling System for Missed Transactions
Polls Alchemy Transfers API every 5 minutes as backup to webhooks
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging
import asyncio
import json
import os
import httpx
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class FallbackPoller:
    """Fallback polling system for missed transactions"""
    
    def __init__(self):
        load_dotenv('.env')
        self.alchemy_api_key = os.getenv("ALCHEMY_API_KEY")
        
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if supabase_url and supabase_key:
            self.supabase: Client = create_client(supabase_url, supabase_key)
            print("FallbackPoller: Supabase client initialized")
        else:
            self.supabase = None
            print("FallbackPoller: Running without Supabase database connection")
            
        self.polling_interval = timedelta(minutes=5)
        self.lookback_window = timedelta(hours=2)
        self.base_url = "https://eth-mainnet.g.alchemy.com/v2"
        
        # Market addresses
        self.market_addresses = {
            "polymarket": [
                "0x4bF53B9B888197B09A09e6dC3fea0837eBBdF5aB",
                "0x8b6f69c4297e3461e1c0d3643e639c444c4af642",
            ],
            "kalshi": [
                # Add Kalshi addresses
            ]
        }
    
    async def start_polling(self):
        """Start the background polling task"""
        logger.info("Starting fallback polling system")
        
        while True:
            try:
                await self.poll_for_missed_transactions()
                await asyncio.sleep(self.polling_interval.total_seconds())
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def poll_for_missed_transactions(self):
        """Poll for transactions that might have been missed by webhooks"""
        logger.info("Running fallback poll for missed transactions")
        
        # Get time window to check
        since = datetime.utcnow() - self.lookback_window
        
        # Get all users with recent alerts
        users_with_alerts = await self.get_users_with_recent_alerts(since)
        
        if not users_with_alerts:
            logger.info("No users with recent alerts to check")
            return
        
        # Check each user for missed transactions
        for user_id in users_with_alerts:
            await self.check_user_for_missed_transactions(user_id, since)
    
    async def get_users_with_recent_alerts(self, since: datetime) -> List[str]:
        """Get users who have received alerts in the time window"""
        if not self.supabase:
            return []
            
        try:
            result = self.supabase.table("arbitrage_alerts").select("user_id").gte("created_at", since.isoformat()).execute()
            
            # Extract unique user IDs
            user_ids = list(set(alert["user_id"] for alert in result.data))
            return user_ids
        except Exception as e:
            logger.error(f"Error fetching users with alerts: {e}")
            return []
    
    async def check_user_for_missed_transactions(self, user_id: str, since: datetime):
        """Check a specific user for missed transactions"""
        try:
            # Get transactions from Alchemy
            transactions = await self.get_user_transactions(user_id, since)
            
            if not transactions:
                return
            
            # Check each transaction
            for tx in transactions:
                await self.process_missed_transaction(user_id, tx)
                
        except Exception as e:
            logger.error(f"Error checking user {user_id} for missed transactions: {e}")
    
    async def get_user_transactions(self, user_address: str, since: datetime) -> List[Dict]:
        """Get transactions for a user address from Alchemy"""
        try:
            # Convert to Unix timestamp
            from_timestamp = int(since.timestamp())
            to_timestamp = int(datetime.utcnow().timestamp())
            
            # Build request for Alchemy Transfers API
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "alchemy_getAssetTransfers",
                "params": [
                    {
                        "fromBlock": f"0x{from_timestamp:x}",
                        "toBlock": "latest",
                        "fromAddress": user_address,
                        "category": [
                            "external",
                            "internal",
                            "erc20",
                            "erc721",
                            "erc1155"
                        ],
                        "maxCount": "0x3e8",  # 1000 transactions max
                        "order": "desc"
                    }
                ]
            }
            
            headers = {"Content-Type": "application/json"}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{self.alchemy_api_key}",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    transfers = data.get("result", {}).get("transfers", [])
                    
                    # Filter for market transactions
                    market_transfers = []
                    for transfer in transfers:
                        if self.is_market_transaction(transfer):
                            market_transfers.append(transfer)
                    
                    return market_transfers
                else:
                    logger.error(f"Alchemy API error: {response.status_code} - {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching transactions from Alchemy: {e}")
            return []
    
    def is_market_transaction(self, transfer: Dict) -> bool:
        """Check if transaction is related to supported markets"""
        to_address = transfer.get("to", "").lower()
        
        # Check against known market addresses
        for market, addresses in self.market_addresses.items():
            if to_address in [addr.lower() for addr in addresses]:
                return True
        
        return False
    
    async def process_missed_transaction(self, user_id: str, transfer: Dict):
        """Process a transaction that was missed by webhooks"""
        tx_hash = transfer.get("hash")
        timestamp = datetime.fromtimestamp(int(transfer.get("timeStamp", 0)))
        
        # Check if already processed
        if await self.is_transaction_processed(tx_hash):
            return
        
        logger.info(f"Processing missed transaction {tx_hash} for user {user_id}")
        
        # Try to match to alert
        matching_alert = await self.match_transaction_to_alert(user_id, transfer, timestamp)
        
        if matching_alert:
            # Get trade details
            trade_details = await self.extract_trade_details(transfer, matching_alert)
            
            if trade_details:
                # Store execution
                from api.webhooks.enhanced_handler import store_execution_with_alert, AlertData
                
                alert_data = AlertData(
                    id=matching_alert["id"],
                    user_id=matching_alert["user_id"],
                    market=matching_alert["market"],
                    ticker=matching_alert["ticker"],
                    spread=matching_alert["spread"],
                    timestamp=datetime.fromisoformat(matching_alert["created_at"])
                )
                
                await store_execution_with_alert(
                    user_id,
                    alert_data,
                    trade_details,
                    tx_hash,
                    timestamp
                )
                
    async def match_transaction_to_alert(self, user_id: str, transfer: Dict, timestamp: datetime) -> Optional[Dict]:
        """Match transaction to recent alert"""
        if not self.supabase:
            return None
            
        try:
            # Get alerts within 2 hours of transaction
            since = timestamp - timedelta(hours=2)
            until = timestamp + timedelta(hours=2)
            
            result = self.supabase.table("arbitrage_alerts").select("*").eq("user_id", user_id).gte("created_at", since.isoformat()).lte("created_at", until.isoformat()).eq("status", "active").execute()
            
            if not result.data:
                return None
            
            # Find best match based on timestamp proximity and market
            best_match = None
            min_time_diff = timedelta.max
            
            for alert in result.data:
                alert_time = datetime.fromisoformat(alert["created_at"])
                time_diff = abs(timestamp - alert_time)
                
                # Check market match
                if self.is_market_match_for_alert(transfer, alert):
                    if time_diff < min_time_diff and time_diff < timedelta(hours=2):
                        best_match = alert
                        min_time_diff = time_diff
            
            return best_match
            
        except Exception as e:
            logger.error(f"Error matching transaction to alert: {e}")
            return None
    
    def is_market_match_for_alert(self, transfer: Dict, alert: Dict) -> bool:
        """Check if transaction matches the alert's market"""
        market = alert.get("market")
        to_address = transfer.get("to", "").lower()
        
        if market == "polymarket":
            return to_address in [addr.lower() for addr in self.market_addresses["polymarket"]]
        elif market == "kalshi":
            return to_address in [addr.lower() for addr in self.market_addresses["kalshi"]]
        
        return False
    
    async def extract_trade_details(self, transfer: Dict, alert: Dict) -> Dict[str, Any]:
        """Extract trade details from transaction"""
        # This would parse the transaction to extract trade details
        # For now, return basic structure
        
        return {
            "market_ticker": alert.get("ticker"),
            "side": "yes",  # Would extract from transaction data
            "entry_price": alert.get("yes_price", 0.5),
            "quantity": 100,  # Would extract from transaction
            "gas_cost": float(transfer.get("gasUsed", 0)) * float(transfer.get("gasPrice", 0)) / 1e18
        }

# Singleton instance
fallback_poller = FallbackPoller()

async def start_fallback_polling():
    """Start the fallback polling system"""
    await fallback_poller.start_polling()
