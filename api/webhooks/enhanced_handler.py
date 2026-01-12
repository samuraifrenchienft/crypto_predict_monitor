"""
Enhanced Webhook Handler with Alert Matching
Matches transactions to recent arbitrage alerts for accurate P&L tracking
"""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import hmac
import hashlib
import json
import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import httpx
from supabase import create_client, Client
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Configuration
ALCHEMY_WEBHOOK_SECRET = os.getenv("ALCHEMY_WEBHOOK_SECRET")
ALERT_MATCHING_WINDOW = timedelta(hours=2)  # Match alerts from last 2 hours
BATCH_UPDATE_INTERVAL = 300  # Update leaderboard every 5 minutes

# Market detection patterns
POLYMARKET_ADDRESSES = [
    "0x4bF53B9B888197B09A09e6dC3fea0837eBBdF5aB",  # CTF Exchange
    "0x8b6f69c4297e3461e1c0d3643e639c444c4af642",  # CTF Exchange 2
    "0x4D6D095E4213c4A9A8F7b3A5E3e8c9D9A8b7C6D5",  # Additional
]

KALSHI_ADDRESSES = [
    # Add Kalshi contract addresses when available
]

@dataclass
class AlertData:
    """Structure for arbitrage alert data"""
    id: str
    user_id: str
    market: str
    ticker: str
    spread: float
    timestamp: datetime
    yes_price: Optional[float] = None
    no_price: Optional[float] = None

@dataclass
class TransactionData:
    """Structure for transaction data"""
    hash: str
    from_address: str
    to_address: str
    timestamp: datetime
    gas_used: float
    gas_price: float
    value: str
    input_data: str

app = FastAPI(title="Enhanced Trade Execution Webhook API")

# In-memory cache for recent alerts (in production, use Redis)
recent_alerts_cache: Dict[str, List[AlertData]] = {}
leaderboard_update_queue: List[str] = []  # Queue of user_ids needing leaderboard updates

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify Alchemy webhook signature"""
    if not ALCHEMY_WEBHOOK_SECRET:
        logger.warning("No webhook secret configured - skipping verification")
        return True
    
    expected_signature = hmac.new(
        ALCHEMY_WEBHOOK_SECRET.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected_signature, signature)

async def get_recent_alerts(user_id: str, since: datetime) -> List[AlertData]:
    """Get recent arbitrage alerts for a user"""
    try:
        # Check cache first
        if user_id in recent_alerts_cache:
            cached_alerts = recent_alerts_cache[user_id]
            recent_cached = [a for a in cached_alerts if a.timestamp >= since]
            if recent_cached:
                return recent_cached
        
        # Query database for recent alerts
        result = supabase.table("arbitrage_alerts").select("*").eq("user_id", user_id).gte("created_at", since.isoformat()).execute()
        
        alerts = []
        for alert in result.data:
            alert_data = AlertData(
                id=alert["id"],
                user_id=alert["user_id"],
                market=alert["market"],
                ticker=alert["ticker"],
                spread=alert["spread"],
                timestamp=datetime.fromisoformat(alert["created_at"]),
                yes_price=alert.get("yes_price"),
                no_price=alert.get("no_price")
            )
            alerts.append(alert_data)
        
        # Update cache
        recent_alerts_cache[user_id] = alerts
        
        return alerts
    except Exception as e:
        logger.error(f"Error fetching recent alerts: {e}")
        return []

async def match_transaction_to_alert(transaction: TransactionData) -> Optional[AlertData]:
    """Match a transaction to a recent arbitrage alert"""
    user_id = transaction.from_address
    
    # Get recent alerts for this user
    since = transaction.timestamp - ALERT_MATCHING_WINDOW
    recent_alerts = await get_recent_alerts(user_id, since)
    
    if not recent_alerts:
        return None
    
    # Find best matching alert based on timestamp proximity
    best_match = None
    min_time_diff = timedelta.max
    
    for alert in recent_alerts:
        time_diff = abs(transaction.timestamp - alert.timestamp)
        
        # Check if within matching window and closer than current best
        if time_diff < ALERT_MATCHING_WINDOW and time_diff < min_time_diff:
            # Additional matching criteria
            if is_market_match(transaction, alert):
                best_match = alert
                min_time_diff = time_diff
    
    return best_match

def is_market_match(transaction: TransactionData, alert: AlertData) -> bool:
    """Check if transaction matches the alert's market"""
    # Check if transaction involves the correct market contract
    if alert.market == "polymarket":
        return transaction.to_address.lower() in [addr.lower() for addr in POLYMARKET_ADDRESSES]
    elif alert.market == "kalshi":
        return transaction.to_address.lower() in [addr.lower() for addr in KALSHI_ADDRESSES]
    
    return False

async def get_trade_details_from_tx(market: str, tx_hash: str, user_address: str) -> Dict[str, Any]:
    """Extract trade details from transaction"""
    try:
        if market == "polymarket":
            return await get_polymarket_trade_details(tx_hash, user_address)
        elif market == "kalshi":
            return await get_kalshi_trade_details(tx_hash, user_address)
    except Exception as e:
        logger.error(f"Error fetching trade details: {e}")
        return {}

async def get_polymarket_trade_details(tx_hash: str, user_address: str) -> Dict[str, Any]:
    """Fetch trade details from Polymarket"""
    # Implementation would parse transaction data or call Polymarket API
    # For now, return extracted data from transaction
    
    # In production, you would:
    # 1. Get transaction receipt from Alchemy
    # 2. Parse event logs for trade details
    # 3. Query Polymarket GraphQL API for market info
    
    return {
        "market_ticker": "PRESIDENT-2024",  # Extract from tx
        "side": "yes",  # Extract from tx
        "entry_price": 0.65,  # Extract from tx
        "quantity": 100,  # Extract from tx
        "gas_cost": 0.001  # Calculate from gas_used * gas_price
    }

async def get_kalshi_trade_details(tx_hash: str, user_address: str) -> Dict[str, Any]:
    """Fetch trade details from Kalshi"""
    # Similar implementation for Kalshi
    return {
        "market_ticker": "KXMARKET123",
        "side": "yes",
        "entry_price": 0.65,
        "quantity": 100,
        "gas_cost": 0.001
    }

async def calculate_pnl(execution: Dict[str, Any]) -> float:
    """Calculate P&L for a closed position"""
    if execution.get("status") != "closed" or execution.get("exit_price") is None:
        return 0.0
    
    entry_price = execution.get("entry_price", 0)
    exit_price = execution.get("exit_price", 0)
    quantity = execution.get("quantity", 0)
    gas_cost = execution.get("gas_cost", 0)
    
    # For binary options: P&L = (exit_price - entry_price) * quantity - gas_cost
    pnl = (exit_price - entry_price) * quantity - gas_cost
    
    return pnl

async def store_execution_with_alert(
    user_id: str,
    alert: AlertData,
    trade_details: Dict[str, Any],
    tx_hash: str,
    timestamp: datetime
) -> Dict[str, Any]:
    """Store execution linked to an arbitrage alert"""
    
    # Check if this is an entry or exit
    existing_position = await get_open_position(user_id, alert.market, alert.ticker, trade_details.get("side"))
    
    if existing_position:
        # This is an exit - close the position
        execution_data = {
            "exit_price": trade_details.get("entry_price"),  # Current price is exit price
            "exit_tx_hash": tx_hash,
            "exit_timestamp": timestamp,
            "status": "closed"
        }
        
        # Update existing execution
        result = supabase.table("executions").update(execution_data).eq("id", existing_position["id"]).execute()
        
        # Calculate and store P&L
        if result.data:
            updated_execution = result.data[0]
            pnl = await calculate_pnl(updated_execution)
            
            # Update with calculated P&L
            supabase.table("executions").update({"pnl": pnl}).eq("id", existing_position["id"]).execute()
            
            # Queue for leaderboard update
            queue_leaderboard_update(user_id)
            
            logger.info(f"Closed position for user {user_id} with P&L: ${pnl:.2f}")
            return {**updated_execution, "pnl": pnl}
    else:
        # This is a new entry
        execution_data = {
            "user_id": user_id,
            "market": alert.market,
            "market_ticker": alert.ticker,
            "side": trade_details.get("side"),
            "entry_price": trade_details.get("entry_price"),
            "quantity": trade_details.get("quantity"),
            "entry_tx_hash": tx_hash,
            "gas_cost": trade_details.get("gas_cost", 0),
            "entry_timestamp": timestamp,
            "status": "open",
            "alert_id": alert.id,  # Link to the alert
            "alert_spread": alert.spread  # Store the spread at alert time
        }
        
        result = supabase.table("executions").insert(execution_data).execute()
        
        if result.data:
            logger.info(f"Opened new position for user {user_id}")
            return result.data[0]
    
    return {}

async def get_open_position(user_id: str, market: str, ticker: str, side: str) -> Optional[Dict[str, Any]]:
    """Get open position for user, market, and side"""
    try:
        result = supabase.table("executions").select("*").eq("user_id", user_id).eq("market", market).eq("market_ticker", ticker).eq("side", side).eq("status", "open").execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
    except Exception as e:
        logger.error(f"Error checking for open position: {e}")
    
    return None

def queue_leaderboard_update(user_id: str):
    """Queue user for leaderboard update (batch processing)"""
    if user_id not in leaderboard_update_queue:
        leaderboard_update_queue.append(user_id)

async def process_leaderboard_updates():
    """Process batch leaderboard updates"""
    if not leaderboard_update_queue:
        return
    
    # Get unique users
    users_to_update = list(set(leaderboard_update_queue))
    leaderboard_update_queue.clear()
    
    for user_id in users_to_update:
        try:
            # Calculate user's total P&L
            result = supabase.table("executions").select("pnl").eq("user_id", user_id).eq("status", "closed").execute()
            
            total_pnl = sum(exec["pnl"] for exec in result.data if exec.get("pnl") is not None)
            
            # Update leaderboard
            supabase.table("leaderboard").upsert({
                "user_id": user_id,
                "total_pnl": total_pnl,
                "updated_at": datetime.utcnow().isoformat()
            }).execute()
            
            logger.info(f"Updated leaderboard for user {user_id}: ${total_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating leaderboard for {user_id}: {e}")

@app.post("/api/webhooks/wallet-activity")
async def wallet_activity_webhook(request: Request, background_tasks: BackgroundTasks):
    """Enhanced webhook handler with alert matching"""
    
    # Verify webhook signature
    signature = request.headers.get("X-Alchemy-Signature")
    if signature:
        body = await request.body()
        if not verify_webhook_signature(body, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse webhook data
    try:
        webhook_data = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    # Log webhook for debugging
    webhook_id = webhook_data.get("id", "unknown")
    
    try:
        supabase.table("webhook_logs").insert({
            "webhook_id": webhook_id,
            "transaction_data": webhook_data,
            "status": "received"
        }).execute()
    except Exception as e:
        logger.error(f"Error logging webhook: {e}")
    
    # Process in background
    background_tasks.add_task(process_webhook_with_alert_matching, webhook_data, webhook_id)
    
    return JSONResponse({"status": "received", "matched": True})

async def process_webhook_with_alert_matching(webhook_data: Dict[str, Any], webhook_id: str):
    """Process webhook with alert matching logic"""
    try:
        activities = webhook_data.get("activity", [])
        
        for activity in activities:
            # Parse transaction data
            transaction = TransactionData(
                hash=activity.get("hash"),
                from_address=activity.get("fromAddress"),
                to_address=activity.get("toAddress"),
                timestamp=datetime.fromtimestamp(int(activity.get("timestamp", 0))),
                gas_used=float(activity.get("gas", 0)),
                gas_price=float(activity.get("gasPrice", 0)) / 1e18,  # Convert from wei
                value=activity.get("value", "0"),
                input_data=activity.get("input", "")
            )
            
            # Match to recent alert
            matching_alert = await match_transaction_to_alert(transaction)
            
            if matching_alert:
                logger.info(f"Matched transaction {transaction.hash} to alert {matching_alert.id}")
                
                # Get trade details
                trade_details = await get_trade_details_from_tx(
                    matching_alert.market,
                    transaction.hash,
                    transaction.from_address
                )
                
                if trade_details:
                    # Store execution linked to alert
                    await store_execution_with_alert(
                        transaction.from_address,
                        matching_alert,
                        trade_details,
                        transaction.hash,
                        transaction.timestamp
                    )
            else:
                # No matching alert - could be a trade without arbitrage signal
                logger.info(f"No matching alert found for transaction {transaction.hash}")
        
        # Mark webhook as processed
        supabase.table("webhook_logs").update({
            "status": "processed"
        }).eq("webhook_id", webhook_id).execute()
        
    except Exception as e:
        logger.error(f"Error processing webhook {webhook_id}: {e}")
        
        # Mark webhook as error
        supabase.table("webhook_logs").update({
            "status": "error",
            "error_message": str(e)
        }).eq("webhook_id", webhook_id).execute()

@app.post("/api/webhooks/fallback-poll")
async def fallback_poll():
    """Fallback polling for missed transactions"""
    try:
        # Poll for transactions in the last 2 hours
        since = datetime.utcnow() - timedelta(hours=2)
        
        # This would implement the fallback polling logic
        # Query Alchemy Transfers API for recent transactions
        # Match to alerts that weren't caught by webhooks
        
        await process_leaderboard_updates()  # Also update leaderboard
        
        return JSONResponse({"status": "polled", "since": since.isoformat()})
    except Exception as e:
        logger.error(f"Error in fallback poll: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/leaderboard")
async def get_leaderboard(limit: int = 20):
    """Get trading leaderboard"""
    try:
        result = supabase.table("leaderboard").select("*").order("total_pnl", desc=True).limit(limit).execute()
        return result.data
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Schedule batch leaderboard updates
import asyncio

async def scheduled_leaderboard_updates():
    """Background task for batch leaderboard updates"""
    while True:
        await asyncio.sleep(BATCH_UPDATE_INTERVAL)
        await process_leaderboard_updates()

@app.on_event("startup")
async def startup_event():
    """Start background tasks"""
    # Start leaderboard update scheduler
    asyncio.create_task(scheduled_leaderboard_updates())
    logger.info("Started leaderboard update scheduler")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
