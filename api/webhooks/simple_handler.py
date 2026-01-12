"""
Simple Webhook Handler with Alert Matching
A simplified version of the webhook processing system
"""

import os
import logging
import hmac
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import httpx
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

# Dataclasses
@dataclass
class AlertData:
    id: str
    user_id: str
    market: str
    ticker: str
    spread: float
    timestamp: datetime
    yes_price: float
    no_price: float

@dataclass
class TransactionData:
    hash: str
    from_address: str
    to_address: str
    value: float
    timestamp: datetime
    status: str

# Constants
ALCHEMY_WEBHOOK_SECRET = os.getenv("ALCHEMY_WEBHOOK_SECRET")
ALERT_MATCHING_WINDOW = timedelta(hours=2)

# Global state
recent_alerts_cache: Dict[str, List[AlertData]] = {}
leaderboard_update_queue: List[str] = []

# Helper Functions
async def calculate_pnl(execution: Dict[str, Any]) -> float:
    """Calculate P&L from execution data"""
    try:
        entry_price = execution.get("entry_price", 0)
        exit_price = execution.get("exit_price", 0)
        quantity = execution.get("quantity", 0)
        gas_cost = execution.get("gas_cost", 0)
        
        # Validate inputs
        if not all(isinstance(x, (int, float)) for x in [entry_price, exit_price, quantity]):
            logger.warning(f"Invalid P&L calculation inputs: entry={entry_price}, exit={exit_price}, quantity={quantity}")
            return 0.0
            
        pnl = (exit_price - entry_price) * quantity - gas_cost
        return pnl
    except Exception as e:
        logger.error(f"Error calculating P&L: {e}")
        return 0.0

def queue_leaderboard_update(user_id: str):
    """Queue a user for leaderboard update"""
    if user_id not in leaderboard_update_queue:
        leaderboard_update_queue.append(user_id)
        logger.info(f"Queued user {user_id} for leaderboard update")

async def get_recent_alerts(user_id: str, since: datetime) -> List[Dict[str, Any]]:
    """Get recent alerts for a user from database"""
    try:
        if not supabase:
            logger.warning("No Supabase client available")
            return []
            
        # Query recent alerts for user
        response = supabase.table("arbitrage_alerts").select("*").eq("user_id", user_id).gte("created_at", since.isoformat()).execute()
        
        if response.data:
            return response.data
        return []
    except Exception as e:
        logger.error(f"Error fetching recent alerts for user {user_id}: {e}")
        return []

async def match_transaction_to_alert(transaction: TransactionData, user_id: str) -> Optional[AlertData]:
    """Match a transaction to a recent arbitrage alert"""
    try:
        since = transaction.timestamp - ALERT_MATCHING_WINDOW
        alerts = await get_recent_alerts(user_id, since)
        
        if not alerts:
            logger.debug(f"No recent alerts found for user {user_id}")
            return None
        
        # Find best matching alert based on timestamp proximity
        best_match = None
        min_time_diff = float('inf')
        
        for alert in alerts:
            alert_time = alert.get("created_at")
            if isinstance(alert_time, str):
                alert_time = datetime.fromisoformat(alert_time.replace('Z', '+00:00'))
            
            time_diff = abs((transaction.timestamp - alert_time).total_seconds())
            
            # Match if within 5 minutes (300 seconds) and closer than current best
            if time_diff < 300 and time_diff < min_time_diff:
                best_match = AlertData(
                    id=alert.get("id"),
                    user_id=user_id,
                    market=alert.get("market"),
                    ticker=alert.get("ticker"),
                    spread=alert.get("spread", 0.0),
                    timestamp=alert_time,
                    yes_price=alert.get("yes_price", 0.0),
                    no_price=alert.get("no_price", 0.0)
                )
                min_time_diff = time_diff
                logger.debug(f"Found better match: time_diff={time_diff}, alert_id={alert.get('id')}")
        
        if best_match:
            logger.info(f"Matched transaction {transaction.hash[:10]} to alert {best_match.id}")
        else:
            logger.debug(f"No matching alert found for transaction {transaction.hash[:10]}")
            
        return best_match
    except Exception as e:
        logger.error(f"Error matching transaction to alert: {e}")
        return None

async def process_webhook_with_alert_matching(webhook_data: Dict[str, Any], webhook_id: str):
    """Process webhook with alert matching logic"""
    try:
        activities = webhook_data.get("activity", [])
        logger.info(f"Processing {len(activities)} activities from webhook {webhook_id}")
        
        for activity in activities:
            # Parse transaction data
            transaction = TransactionData(
                hash=activity.get("hash", ""),
                from_address=activity.get("fromAddress", ""),
                to_address=activity.get("toAddress", ""),
                value=float(activity.get("value", 0)),
                timestamp=datetime.fromtimestamp(int(activity.get("timestamp", 0))),
                status="pending"
            )
            
            # Match to recent alert
            matching_alert = await match_transaction_to_alert(transaction, transaction.from_address)
            
            if matching_alert:
                logger.info(f"Found matching alert {matching_alert.id} for transaction {transaction.hash[:10]}")
                
                # Store execution (simplified)
                await store_execution(transaction, matching_alert)
                
                # Queue for leaderboard update
                queue_leaderboard_update(transaction.from_address)
            else:
                logger.debug(f"No matching alert found for transaction {transaction.hash[:10]}")
                
    except Exception as e:
        logger.error(f"Error processing webhook {webhook_id}: {e}")

async def store_execution(transaction: TransactionData, alert: AlertData):
    """Store execution record in database"""
    try:
        if not supabase:
            logger.warning("No Supabase client available for storing execution")
            return
            
        execution_data = {
            "user_id": transaction.from_address,
            "alert_id": alert.id,
            "tx_hash": transaction.hash,
            "market": alert.market,
            "ticker": alert.ticker,
            "entry_price": alert.yes_price,  # Using yes_price as entry price
            "quantity": 1,  # Default quantity
            "gas_cost": 0.001,  # Default gas cost
            "status": "pending",
            "executed_at": transaction.timestamp.isoformat()
        }
        
        supabase.table("executions").insert(execution_data).execute()
        logger.info(f"Stored execution for transaction {transaction.hash[:10]}")
        
    except Exception as e:
        logger.error(f"Error storing execution: {e}")

async def process_webhook_data(webhook_data: Dict[str, Any]):
    """Process webhook data"""
    webhook_id = webhook_data.get("id", "unknown")
    await process_webhook_with_alert_matching(webhook_data, webhook_id)

# FastAPI app
app = FastAPI(title="Simple Webhook Handler")

@app.post("/webhook")
async def webhook_endpoint(request: Request, background_tasks: BackgroundTasks):
    """Webhook endpoint for receiving transaction data"""
    try:
        # Verify signature (simplified)
        signature = request.headers.get("X-Alchemy-Signature")
        if not signature:
            raise HTTPException(status_code=401, detail="Missing signature")
        
        # Parse webhook data
        webhook_data = await request.json()
        
        # Process in background
        background_tasks.add_task(process_webhook_data, webhook_data)
        
        return JSONResponse({"status": "received", "webhook_id": webhook_data.get("id", "unknown")})
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting simple webhook handler...")
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
