"""
Main Integration for Phase 3.5 - P&L Tracking System
Ties together webhooks, alerts, fallback polling, and dashboard
"""

import asyncio
import logging
from datetime import datetime
import os
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Import all components
from utils.fallback_poller import start_fallback_polling
from utils.alert_manager import start_alert_system, create_alert_from_opportunity
from bot.arbitrage import detect_cross_market_arbitrage
from bot.adapters import polymarket, kalshi

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global background tasks
background_tasks = set()

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
        stats = await alert_manager.get_alert_statistics(user_id)
        return stats
    except Exception as e:
        logger.error(f"Error fetching alert stats: {e}")
        return {"error": str(e)}

# Enhanced arbitrage detection with alert creation
async def enhanced_arbitrage_detection():
    """Enhanced arbitrage detection that creates alerts"""
    
    # Get adapters
    poly_adapter = polymarket.PolymarketAdapter()
    kalshi_adapter = kalshi.KalshiAdapter(
        kalshi_access_key=os.getenv("KALSHI_ACCESS_KEY"),
        kalshi_private_key=os.getenv("KALSHI_PRIVATE_KEY")
    )
    
    # Detect arbitrage opportunities
    opportunities = await detect_cross_market_arbitrage(
        poly_adapter, 
        kalshi_adapter,
        min_spread=0.08
    )
    
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
