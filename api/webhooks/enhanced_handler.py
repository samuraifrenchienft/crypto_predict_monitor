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
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv('.env')

# Debug: Check if environment variables are loaded
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

if not supabase_url:
    print("WARNING: SUPABASE_URL not found in .env")
if not supabase_key:
    print("WARNING: SUPABASE_SERVICE_KEY not found in .env")

# Initialize Supabase client only if credentials are available
supabase = None
if supabase_url and supabase_key:
    supabase = create_client(supabase_url, supabase_key)
    print("Supabase client initialized successfully")
else:
    print("Running without Supabase database connection")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
_alert_cache: Dict[str, List[Dict[str, Any]]] = {}
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

async def get_recent_alerts(user_id: str, since: datetime) -> List[Dict[str, Any]]:
    """Get recent alerts for a user from cache or database"""
    # Check cache first
    cache_key = f"alerts_{user_id}"
    if cache_key in _alert_cache:
        cached_alerts = _alert_cache[cache_key]
        recent_cached = [alert for alert in cached_alerts if datetime.fromisoformat(alert["created_at"]) >= since]
        if recent_cached:
            return recent_cached
    
    # Query database for recent alerts if supabase is available
    if supabase:
        try:
            result = supabase.table("arbitrage_alerts").select("*").eq("user_id", user_id).gte("created_at", since.isoformat()).execute()
            
            alerts = []
            for alert in result.data:
                alerts.append({
                    "id": alert["id"],
                    "market": alert["market"],
                    "ticker": alert["ticker"],
                    "spread": alert["spread"],
                    "yes_price": alert["yes_price"],
                    "no_price": alert["no_price"],
                    "created_at": alert["created_at"],
                    "status": alert["status"],
                    "alert_spread": alert["spread"]
                })
            return alerts
        except Exception as e:
            logger.error(f"Error fetching alerts from database: {e}")
    
    return []

async def match_transaction_to_alert(transaction: TransactionData, user_id: str = None) -> Optional[AlertData]:
    """Match a transaction to a recent arbitrage alert"""
    try:
        if user_id is None:
            user_id = transaction.from_address
            
        # Get recent alerts for this user
        since = transaction.timestamp - ALERT_MATCHING_WINDOW
        recent_alerts = await get_recent_alerts(user_id, since)
        
        if not recent_alerts:
            logger.debug(f"No recent alerts found for user {user_id}")
            return None
        
        # Find best matching alert based on timestamp proximity and market match
        best_match = None
        min_time_diff = timedelta.max
        
        for alert in recent_alerts:
            # Convert alert timestamp to datetime if it's a string
            alert_time = alert.get("created_at")
            if isinstance(alert_time, str):
                alert_time = datetime.fromisoformat(alert_time.replace('Z', '+00:00'))
            
            time_diff = abs(transaction.timestamp - alert_time)
            
            # Check if within matching window and closer than current best
            if time_diff < ALERT_MATCHING_WINDOW and time_diff < min_time_diff:
                # Additional matching criteria
                if is_market_match(transaction, alert):
                    best_match = alert
                    min_time_diff = time_diff
                    logger.debug(f"Found better match: time_diff={time_diff}, alert_id={alert.id}")
        
        if best_match:
            logger.info(f"Matched transaction {transaction.hash[:10]} to alert {best_match.id}")
        else:
            logger.debug(f"No matching alert found for transaction {transaction.hash[:10]}")
            
        return best_match
    except Exception as e:
        logger.error(f"Error matching transaction to alert: {e}")
        return None

def is_market_match(transaction: TransactionData, alert: AlertData) -> bool:
    """Check if transaction matches the alert's market"""
    # Check if transaction involves the correct market contract
    if alert.market == "polymarket":
        return transaction.to_address.lower() in [addr.lower() for addr in POLYMARKET_ADDRESSES]
    elif alert.market == "azuro":
        return True  # Azuro transactions would have different detection logic
    
    return False

async def get_trade_details_from_tx(market: str, tx_hash: str, user_address: str) -> Dict[str, Any]:
    """Extract trade details from transaction"""
    try:
        if market == "polymarket":
            return await get_polymarket_trade_details(tx_hash, user_address)
        elif market == "azuro":
            return await get_azuro_trade_details(tx_hash, user_address)
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

async def get_azuro_trade_details(tx_hash: str, user_address: str) -> Dict[str, Any]:
    """Fetch trade details from Azuro"""
    # Implementation would parse Azuro transaction data
    return {
        "market_ticker": "AZUROMARKET123",
        "side": "yes",
        "entry_price": 0.65,
        "quantity": 100,
        "gas_cost": 0.001
    }

async def calculate_pnl(execution: Dict[str, Any]) -> float:
    """Calculate P&L from execution data"""
    try:
        entry_price = execution.get("entry_price", 0)
        exit_price = execution.get("exit_price", 0)
        quantity = execution.get("quantity", 0)
        gas_cost = execution.get("gas_cost", 0)
        
        # For binary options: P&L = (exit_price - entry_price) * quantity - gas_cost
        pnl = (exit_price - entry_price) * quantity - gas_cost
        
        # Validate calculation
        if not isinstance(entry_price, (int, float)) or not isinstance(exit_price, (int, float)):
            logger.warning(f"Invalid price data: entry={entry_price}, exit={exit_price}")
            return 0.0
            
        if not isinstance(quantity, (int, float)) or quantity <= 0:
            logger.warning(f"Invalid quantity: {quantity}")
            return 0.0
            
        return pnl
    except Exception as e:
        logger.error(f"Error calculating P&L: {e}")
        return 0.0

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
        if supabase:
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
        
        if supabase:
            result = supabase.table("executions").insert(execution_data).execute()
            
            if result.data:
                logger.info(f"Opened new position for user {user_id}")
                return result.data[0]
    
    return {}

async def get_open_position(user_id: str, market: str, ticker: str, side: str) -> Optional[Dict[str, Any]]:
    """Get open position for user, market, and side"""
    # Validate user_id parameter
    if not user_id or user_id == "user" or user_id.lower() == "user":
        logger.error(f"Invalid user_id parameter: {user_id}")
        return None
        
    if supabase:
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
            # Validate user_id parameter
            if not user_id or user_id == "user" or user_id.lower() == "user":
                logger.error(f"Invalid user_id in leaderboard update: {user_id}")
                continue
                
            if supabase:
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
        if supabase:
            supabase.table("webhook_logs").insert({
                "webhook_id": webhook_id,
                "transaction_data": webhook_data,
                "status": "received"
            }).execute()
        
        # Process webhook in background
        background_tasks.add_task(process_webhook_data, webhook_data)
        
        return JSONResponse({"status": "received", "webhook_id": webhook_id})
        
    except Exception as e:
        logger.error(f"Error processing webhook {webhook_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def process_webhook_data(webhook_data: Dict[str, Any]):
    """Process webhook data (legacy function)"""
    await process_webhook_with_alert_matching(webhook_data, webhook_data.get("id", "unknown"))

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
                value=float(activity.get("value", 0)),
                status="pending"  # Default status
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
        if supabase:
            supabase.table("webhook_logs").update({
                "status": "processed"
            }).eq("webhook_id", webhook_id).execute()
        
    except Exception as e:
        logger.error(f"Error processing webhook {webhook_id}: {e}")
        
        # Mark webhook as error
        if supabase:
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
        if supabase:
            result = supabase.table("leaderboard").select("*").order("total_pnl", desc=True).limit(limit).execute()
            return result.data
        else:
            # Return demo data if no database connection
            return [
                {"user_id": "demo_user_1", "total_pnl": 500.00, "updated_at": datetime.utcnow().isoformat()},
                {"user_id": "demo_user_2", "total_pnl": 350.00, "updated_at": datetime.utcnow().isoformat()},
                {"user_id": "demo_user_3", "total_pnl": 200.00, "updated_at": datetime.utcnow().isoformat()}
            ]
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
