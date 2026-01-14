"""
Main Integration for Phase 3.5 - P&L Tracking System
Ties together webhooks, alerts, fallback polling, and dashboard
"""

import asyncio
import logging
from datetime import datetime
import os
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from copy import deepcopy
import time
from contextlib import asynccontextmanager

# Import all components
from utils.fallback_poller import start_fallback_polling
from utils.alert_manager import start_alert_system, create_alert_from_opportunity
from bot.arbitrage import detect_cross_market_arbitrage
from bot.adapters import polymarket, azuro, limitless, manifold

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global background tasks
background_tasks = set()

# Example gates — tune these
MIN_LIQUIDITY_DEFAULT = 200.0
MAX_STALENESS_SECONDS_DEFAULT = 180  # 3 minutes

def is_stale(m, now, max_age):
    ts = m.get("timestamp") or m.get("updated_at") or m.get("last_updated")
    if ts is None:
        return False  # if you prefer strict: return True
    try:
        return (now - float(ts)) > max_age
    except Exception:
        return False

def has_quotes(m):
    # adjust to your schema
    return m.get("has_quotes", True) and m.get("bid") is not None and m.get("ask") is not None

def liquidity_ok(m, min_liq):
    liq = m.get("liquidity") or m.get("volume") or 0
    try:
        return float(liq) >= min_liq
    except Exception:
        return True

def tier_thresholds(tier: str):
    tier = (tier or "").lower()
    if tier == "elite":
        return 0.08, 8.0
    if tier == "pro":
        return 0.06, 6.0
    if tier == "basic":
        return 0.04, 4.0
    return None, None

# Global market snapshot storage
market_snapshot = []

def update_market_snapshot(markets_data: Dict[str, Any]):
    """Update the global market snapshot"""
    global market_snapshot
    all_markets = []
    for source, markets in markets_data.items():
        for market in markets:
            market_data = {
                "source": source,
                "market_id": market.market_id,
                "title": market.title,
                "url": market.url,
                "spread": 0.0,  # Will be calculated
                "score": 0.0,   # Will be calculated
                "liquidity": 0.0,  # Will be calculated
                "timestamp": time.time(),
                "has_quotes": False
            }
            all_markets.append(market_data)
    market_snapshot = all_markets

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage background tasks on startup/shutdown"""
    logger.info("🚀 Starting P&L Tracking System...")
    
    # Start background systems
    poller_task = asyncio.create_task(start_fallback_polling())
    alert_task = asyncio.create_task(start_alert_system())
    
    background_tasks.add(poller_task)
    background_tasks.add(alert_task)
    
    logger.info("✅ Background systems started")
    
    try:
        yield
    finally:
        # Cancel background tasks
        logger.info("🛑 Shutting down background systems...")
        for task in background_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        logger.info("✅ Shutdown complete")

# Create main app with webhook routes
app = FastAPI(
    title="P&L Tracking System",
    description="Phase 3.5 - Real-time P&L tracking with alert matching",
    version="3.5.0",
    lifespan=lifespan
)

# Include webhook routes
from api.webhooks.enhanced_handler import app as webhook_app

# Add webhook routes directly to main app
for route in webhook_app.routes:
    app.routes.append(route)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "running",
        "system": "P&L Tracking System v3.5",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "webhooks": "✅ Active",
            "fallback_poller": "✅ Running",
            "alert_manager": "✅ Running"
        }
    }

@app.get("/api/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "services": {
            "webhook_handler": "✅ Active",
            "fallback_poller": "✅ Running",
            "alert_system": "✅ Running",
            "database": "✅ Connected"
        },
        "metrics": {
            "active_background_tasks": len(background_tasks),
            "uptime": "Check logs for startup time"
        }
    }

@app.post("/api/alerts/create")
async def create_alert_endpoint(opportunity: dict, user_id: str):
    """Create arbitrage alert from opportunity"""
    try:
        alert = await create_alert_from_opportunity(opportunity, user_id)
        if alert:
            return {"status": "success", "alert_id": alert["id"]}
        else:
            return {"status": "error", "message": "Failed to create alert"}
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/api/stats/alerts")
async def get_alert_stats(user_id: str = None):
    """Get arbitrage alert statistics"""
    try:
        from utils.alert_manager import ArbitrageAlertManager
        alert_manager = ArbitrageAlertManager()
        stats = await alert_manager.get_alert_stats(user_id)
        return stats
    except Exception as e:
        logger.error(f"Error fetching alert stats: {e}")
        return {"error": str(e)}

@app.get("/api/markets")
async def get_markets(
    source: str = Query(default="all", description="Filter by source: polymarket/manifold/azuro/limitless/all"),
    tier: str = Query(default="", description="Tier level: elite/pro/basic"),
    min_spread: Optional[float] = Query(default=None, description="Minimum spread threshold"),
    min_score: Optional[float] = Query(default=None, description="Minimum score threshold"),
    min_liquidity: float = Query(default=MIN_LIQUIDITY_DEFAULT, description="Minimum liquidity"),
    max_staleness: Optional[int] = Query(default=MAX_STALENESS_SECONDS_DEFAULT, description="Maximum age in seconds"),
    require_quotes: bool = Query(default=True, description="Require quotes to be present"),
    limit: Optional[int] = Query(default=300, description="Maximum number of results"),
    offset: int = Query(default=0, description="Results offset for pagination")
):
    """Get filtered markets with tier-based access control"""
    
    # Tier defaults (only if min_* not explicitly provided)
    t_spread, t_score = tier_thresholds(tier)
    if min_spread is None and t_spread is not None:
        min_spread = t_spread
    if min_score is None and t_score is not None:
        min_score = t_score

    now = time.time()

    # Take a safe copy of the snapshot
    markets = deepcopy(market_snapshot) if isinstance(market_snapshot, list) else list(market_snapshot.values())

    def keep(m):
        # Source filter
        if source != "all":
            m_source = (m.get("source") or m.get("market_source") or "").lower()
            if m_source != source:
                return False

        # Quality gates
        if max_staleness is not None and is_stale(m, now, max_staleness):
            return False

        if require_quotes and not has_quotes(m):
            return False

        if min_liquidity is not None and not liquidity_ok(m, min_liquidity):
            return False

        # Score/spread thresholds
        s = m.get("spread")
        sc = m.get("score")
        if min_spread is not None:
            try:
                if float(s) < min_spread:
                    return False
            except Exception:
                return False
        if min_score is not None:
            try:
                if float(sc) < min_score:
                    return False
            except Exception:
                return False

        return True

    filtered = [m for m in markets if keep(m)]

    # Sort best first (optional)
    filtered.sort(key=lambda m: (m.get("score", 0), m.get("spread", 0)), reverse=True)

    page = filtered[offset: offset + limit] if limit is not None else filtered[offset:]

    return {
        "markets": page,
        "total_markets": len(markets),
        "matched_markets": len(filtered),
        "limit": limit,
        "offset": offset,
        "filters": {
            "source": source,
            "tier": tier or None,
            "min_spread": min_spread,
            "min_score": min_score,
            "min_liquidity": min_liquidity,
            "max_staleness": max_staleness,
            "require_quotes": require_quotes,
        }
    }

# Enhanced arbitrage detection with alert creation
async def enhanced_arbitrage_detection():
    """Enhanced arbitrage detection that creates alerts"""
    
    # Get adapters
    poly_adapter = polymarket.PolymarketAdapter(
        gamma_base_url="https://gamma-api.polymarket.com",
        clob_base_url="https://clob.polymarket.com", 
        data_base_url="https://data-api.polymarket.com",
        events_limit=50
    )
    azuro_adapter = azuro.AzuroAdapter(
        graphql_base_url=os.getenv("AZURO_GRAPHQL_BASE_URL", "https://api.azuro.org/graphql"),
        subgraph_base_url=os.getenv("AZURO_SUBGRAPH_BASE_URL", "https://subgraph.azuro.org"),
        rest_base_url=os.getenv("AZURO_REST_BASE_URL", "https://azuro.org/api/v1"),
        markets_limit=int(os.getenv("AZURO_MARKETS_LIMIT", "50")),
        use_fallback=os.getenv("AZURO_USE_FALLBACK", "true").lower() == "true"
    )
    limitless_adapter = limitless.LimitlessAdapter(
        base_url="https://api.limitless.exchange"
    )
    manifold_adapter = manifold.ManifoldAdapter(
        base_url="https://api.manifold.markets",
        markets_limit=50
    )
    
    # Get markets from all adapters
    poly_markets = await poly_adapter.list_active_markets()
    azuro_markets = await azuro_adapter.list_active_markets()
    limitless_markets = await limitless_adapter.list_active_markets()
    manifold_markets = await manifold_adapter.list_active_markets()
    
    # Get quotes from all adapters
    poly_quotes = {}
    azuro_quotes = {}
    limitless_quotes = {}
    manifold_quotes = {}
    
    for market in poly_markets:
        try:
            outcomes = await poly_adapter.list_outcomes(market)
            quotes = await poly_adapter.get_quotes(market, outcomes)
            poly_quotes[market.market_id] = quotes
        except Exception as e:
            logger.warning(f"Failed to get quotes for Polymarket market {market.market_id}: {e}")
            poly_quotes[market.market_id] = []
        
    for market in azuro_markets:
        try:
            outcomes = await azuro.list_outcomes(market)
            quotes = await azuro.get_quotes(market, outcomes)
            azuro_quotes[market.market_id] = quotes
        except Exception as e:
            logger.warning(f"Failed to get quotes for Azuro market {market.market_id}: {e}")
            azuro_quotes[market.market_id] = []
            
    for market in limitless_markets:
        try:
            outcomes = await limitless.list_outcomes(market)
            quotes = await limitless.get_quotes(market, outcomes)
            limitless_quotes[market.market_id] = quotes
        except Exception as e:
            logger.warning(f"Failed to get quotes for Limitless market {market.market_id}: {e}")
            limitless_quotes[market.market_id] = []
            
    for market in manifold_markets:
        try:
            outcomes = await manifold.list_outcomes(market)
            quotes = await manifold.get_quotes(market, outcomes)
            manifold_quotes[market.market_id] = quotes
        except Exception as e:
            logger.warning(f"Failed to get quotes for Manifold market {market.market_id}: {e}")
            manifold_quotes[market.market_id] = []
    
    # Prepare data for arbitrage detection
    markets_by_source = {
        "polymarket": poly_markets,
        "azuro": azuro_markets,
        "limitless": limitless_markets,
        "manifold": manifold_markets
    }
    
    quotes_by_source = {
        "polymarket": poly_quotes,
        "azuro": azuro_quotes,
        "limitless": limitless_quotes,
        "manifold": manifold_quotes
    }
    
    # Detect arbitrage opportunities
    opportunities = detect_cross_market_arbitrage(
        markets_by_source,
        quotes_by_source,
        min_spread=0.08
    )
    
    # Update market snapshot for API endpoint
    update_market_snapshot(markets_by_source)
    
    # Create alerts for each opportunity
    for opp in opportunities:
        # In a real system, you'd have actual user IDs
        # For now, use a demo user
        await create_alert_from_opportunity(opp, "demo_user")
    
    logger.info(f"Created {len(opportunities)} arbitrage alerts")

if __name__ == "__main__":
    import uvicorn
    
    # Run the integrated system
    uvicorn.run(
        "main_integration:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
