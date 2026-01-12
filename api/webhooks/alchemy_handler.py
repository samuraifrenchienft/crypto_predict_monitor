"""
Alchemy Webhook Handler for Real-Time Trade Execution Tracking
Receives webhook notifications when users execute trades on Polymarket/Kalshi
"""

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import hmac
import hashlib
import json
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
from supabase import create_client, Client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

# Alchemy webhook secret (set in environment)
ALCHEMY_WEBHOOK_SECRET = os.getenv("ALCHEMY_WEBHOOK_SECRET")

# Market detection patterns
POLYMETRIC_ADDRESS = "0x4bF53B9B888197B09A09e6dC3fea0837eBBdF5aB"  # CTF Exchange
KALSHI_ADDRESS = "0x0000000000000000000000000000000000000000"  # Update with actual

app = FastAPI(title="Trade Execution Webhook API")

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

async def detect_market_from_transaction(tx_data: Dict[str, Any]) -> Optional[str]:
    """Detect which market the transaction belongs to"""
    # Check if transaction involves known market addresses
    if tx_data.get("to", "").lower() == POLYMETRIC_ADDRESS.lower():
        return "polymarket"
    elif tx_data.get("to", "").lower() == KALSHI_ADDRESS.lower():
        return "kalshi"
    
    # Could also check transaction input data for market-specific patterns
    input_data = tx_data.get("input", "")
    if "0x" in input_data:  # Contains function call data
        # Add logic to parse function selector and detect market
        pass
    
    return None

async def get_trade_details(market: str, tx_hash: str, user_address: str) -> Dict[str, Any]:
    """Fetch trade details from market API using transaction hash"""
    try:
        if market == "polymarket":
            return await get_polymarket_trade_details(tx_hash, user_address)
        elif market == "kalshi":
            return await get_kalshi_trade_details(tx_hash, user_address)
    except Exception as e:
        logger.error(f"Error fetching trade details: {e}")
        return {}

async def get_polymarket_trade_details(tx_hash: str, user_address: str) -> Dict[str, Any]:
    """Fetch trade details from Polymarket API"""
    # Implementation would call Polymarket's API or GraphQL
    # For now, return placeholder structure
    return {
        "market_ticker": "placeholder-market",
        "side": "yes",  # or "no"
        "price": 0.65,
        "quantity": 100,
        "gas_cost": 0.001
    }

async def get_kalshi_trade_details(tx_hash: str, user_address: str) -> Dict[str, Any]:
    """Fetch trade details from Kalshi API"""
    # Implementation would call Kalshi's API
    # For now, return placeholder structure
    return {
        "market_ticker": "KXMARKET123",
        "side": "yes",  # or "no"
        "price": 0.65,
        "quantity": 100,
        "gas_cost": 0.001
    }

async def store_execution(user_id: str, market: str, trade_details: Dict[str, Any], tx_hash: str, timestamp: datetime):
    """Store execution in database"""
    execution_data = {
        "user_id": user_id,
        "market": market,
        "market_ticker": trade_details.get("market_ticker"),
        "side": trade_details.get("side"),
        "entry_price": trade_details.get("price"),
        "quantity": trade_details.get("quantity", 1),
        "entry_tx_hash": tx_hash,
        "gas_cost": trade_details.get("gas_cost", 0),
        "entry_timestamp": timestamp,
        "status": "open"
    }
    
    try:
        result = supabase.table("executions").insert(execution_data).execute()
        logger.info(f"Stored execution for user {user_id}: {result.data}")
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error storing execution: {e}")
        raise

async def check_for_exit_position(user_id: str, market: str, side: str, market_ticker: str):
    """Check if user has an open position to close"""
    try:
        result = supabase.table("executions").select("*").eq("user_id", user_id).eq("market", market).eq("market_ticker", market_ticker).eq("side", side).eq("status", "open").execute()
        
        if result.data and len(result.data) > 0:
            # Return the oldest open position
            return result.data[0]
    except Exception as e:
        logger.error(f"Error checking for exit position: {e}")
    
    return None

async def close_position(execution_id: str, exit_price: float, exit_tx_hash: str, exit_timestamp: datetime):
    """Update execution with exit details"""
    try:
        result = supabase.table("executions").update({
            "exit_price": exit_price,
            "exit_tx_hash": exit_tx_hash,
            "exit_timestamp": exit_timestamp,
            "status": "closed"
        }).eq("id", execution_id).execute()
        
        logger.info(f"Closed position {execution_id}")
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise

@app.post("/api/webhooks/wallet-activity")
async def wallet_activity_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Alchemy wallet activity webhook"""
    
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
    user_address = webhook_data.get("activity", [{}])[0].get("fromAddress", "unknown")
    
    try:
        supabase.table("webhook_logs").insert({
            "user_id": user_address,
            "webhook_id": webhook_id,
            "transaction_data": webhook_data,
            "status": "received"
        }).execute()
    except Exception as e:
        logger.error(f"Error logging webhook: {e}")
    
    # Process in background
    background_tasks.add_task(process_webhook, webhook_data, webhook_id, user_address)
    
    return JSONResponse({"status": "received"})

async def process_webhook(webhook_data: Dict[str, Any], webhook_id: str, user_address: str):
    """Process webhook data in background"""
    try:
        activities = webhook_data.get("activity", [])
        
        for activity in activities:
            # Detect which market
            market = await detect_market_from_transaction(activity)
            if not market:
                logger.info(f"Transaction not from supported market: {activity.get('hash')}")
                continue
            
            # Get trade details
            tx_hash = activity.get("hash")
            timestamp = datetime.fromtimestamp(int(activity.get("timestamp", 0)))
            
            trade_details = await get_trade_details(market, tx_hash, user_address)
            if not trade_details:
                logger.warning(f"Could not fetch trade details for {tx_hash}")
                continue
            
            # Check if this is an entry or exit
            open_position = await check_for_exit_position(
                user_address, 
                market, 
                trade_details.get("side"),
                trade_details.get("market_ticker")
            )
            
            if open_position:
                # This is an exit - close the position
                await close_position(
                    open_position["id"],
                    trade_details.get("price"),
                    tx_hash,
                    timestamp
                )
                logger.info(f"Closed position for user {user_address}")
            else:
                # This is a new entry
                await store_execution(user_address, market, trade_details, tx_hash, timestamp)
                logger.info(f"Opened new position for user {user_address}")
        
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

@app.get("/api/executions/{user_id}")
async def get_user_executions(user_id: str, market: Optional[str] = None, status: Optional[str] = None):
    """Get user's execution history"""
    try:
        query = supabase.table("executions").select("*").eq("user_id", user_id)
        
        if market:
            query = query.eq("market", market)
        if status:
            query = query.eq("status", status)
        
        result = query.order("entry_timestamp", desc=True).execute()
        return result.data
    except Exception as e:
        logger.error(f"Error fetching executions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/pnl/{user_id}")
async def get_user_pnl(user_id: str):
    """Get user's P&L summary"""
    try:
        result = supabase.table("user_pnl_summary").select("*").eq("user_id", user_id).execute()
        return result.data
    except Exception as e:
        logger.error(f"Error fetching P&L: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/webhooks/create/{user_id}")
async def create_user_webhook(user_id: str, wallet_address: str):
    """Create Alchemy webhook for user wallet"""
    # This would call Alchemy's API to create a webhook
    # For now, return placeholder
    return {
        "webhook_id": f"webhook_{user_id}_{wallet_address}",
        "status": "created"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
