#!/usr/bin/env python3
"""
Render startup script for dashboard + arbitrage bot.
Handles database initialization, dashboard startup, and arbitrage bot.
"""

import logging
import os
import sys
import time
import threading
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize database tables and test connection"""
    try:
        from dashboard.db import test_connection, get_connection_info, engine
        from dashboard.models import Base
        
        logger.info("🔍 Testing database connection...")
        
        # Test connection
        if not test_connection():
            logger.error("❌ Database connection test failed")
            return False
        
        logger.info("✅ Database connection test passed")
        
        # Log connection info
        conn_info = get_connection_info()
        logger.info(f"📊 Database connection info: {conn_info}")
        
        # Create tables
        logger.info("🔧 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imports():
    """Test all critical imports"""
    try:
        logger.info("🔍 Testing imports...")
        
        # Test basic dependencies first
        try:
            import yaml
            logger.info("✅ yaml imported successfully")
        except ImportError as e:
            logger.error(f"❌ yaml import failed: {e}")
            return False
        
        try:
            import pydantic
            logger.info("✅ pydantic imported successfully")
        except ImportError as e:
            logger.error(f"❌ pydantic import failed: {e}")
            return False
        
        # Test dashboard app import
        import dashboard.app
        logger.info("✅ Dashboard app imported successfully")
        
        # Test database components
        from dashboard.db import get_session, test_connection
        logger.info("✅ Database components imported successfully")
        
        # Test models
        from dashboard.models import Base, User, Alert
        logger.info("✅ Models imported successfully")
        
        # Test logging
        from dashboard.db_logging import get_database_health
        logger.info("✅ Database logging imported successfully")
        
        # Test async database
        try:
            from dashboard.async_db import get_async_postgres_manager
            logger.info("✅ Async database imported successfully")
        except ImportError:
            logger.warning("⚠️  Async database module not available")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def start_arbitrage_bot():
    """Start the arbitrage bot in background thread"""
    try:
        logger.info("🤖 Starting arbitrage bot...")
        
        def run_arbitrage():
            try:
                import asyncio
                import sys
                from pathlib import Path
                sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
                
                from arbitrage_main import ProfessionalArbitrageSystem
                from arbitrage_detector import MarketData
                from dashboard.app import update_all_markets
                
                async def arbitrage_loop():
                    logger.info("🚀 Arbitrage bot started with real market data")
                    
                    # Initialize arbitrage system
                    system = ProfessionalArbitrageSystem()
                    if not await system.initialize():
                        logger.error("❌ Failed to initialize arbitrage system")
                        return
                    
                    # Send startup alert
                    await system.send_health_alert(
                        "🚀 ARBITRAGE BOT ONLINE - Real Market Monitoring\n"
                        "✅ Live data filtering active\n"
                        "✅ Discord alerts enabled\n"
                        "✅ Quality scoring system ready",
                        "success"
                    )
                    
                    # Main arbitrage monitoring loop
                    scan_count = 0
                    while True:
                        try:
                            scan_count += 1
                            logger.info(f"🔍 Scan #{scan_count}: Fetching live market data...")
                            
                            # Get real market data from dashboard
                            market_cache = {}
                            try:
                                from dashboard.app import cfg, adapters
                                from bot.rate_limit import RateLimitConfig
                                
                                # Update markets from all adapters
                                for adapter_name, adapter in adapters:
                                    logger.info(f"📊 Fetching {adapter_name} markets...")
                                    try:
                                        markets = adapter.fetch_markets()
                                        market_cache[adapter_name.lower()] = markets
                                        logger.info(f"✅ {adapter_name}: {len(markets)} markets")
                                    except Exception as e:
                                        logger.error(f"❌ {adapter_name} fetch failed: {e}")
                                        market_cache[adapter_name.lower()] = []
                                
                            except Exception as e:
                                logger.error(f"❌ Market data fetch failed: {e}")
                                market_cache = {}
                            
                            # Convert to MarketData objects for arbitrage detection
                            all_market_data = []
                            
                            for source, markets in market_cache.items():
                                for market in markets[:20]:  # Limit to top 20 per source for performance
                                    try:
                                        # Extract market data with your strategy filters
                                        market_data = MarketData(
                                            market_id=market.get('id', market.get('market_id', f'{source}-unknown')),
                                            market_name=market.get('question', market.get('title', 'Unknown Market')),
                                            yes_price=float(market.get('yes_price', market.get('price', 0))),
                                            no_price=float(market.get('no_price', 1 - float(market.get('yes_price', market.get('price', 0))))),
                                            yes_bid=float(market.get('yes_bid', market.get('yes_price', 0))),
                                            yes_ask=float(market.get('yes_ask', market.get('yes_price', 0))),
                                            no_bid=float(market.get('no_bid', market.get('no_price', 0))),
                                            no_ask=float(market.get('no_ask', market.get('no_price', 0))),
                                            yes_liquidity=float(market.get('yes_liquidity', market.get('liquidity', 25000))),
                                            no_liquidity=float(market.get('no_liquidity', market.get('liquidity', 25000))),
                                            volume_24h=float(market.get('volume_24h', market.get('volume', 100000))),
                                            spread_percentage=abs(float(market.get('spread', 0))),
                                            price_volatility=float(market.get('volatility', 0.1)),
                                            expires_at=market.get('ends_at', datetime.now() + timedelta(hours=24)),
                                            polymarket_link=market.get('url', market.get('polymarket_link', '')),
                                            analysis_link=market.get('analysis_link', ''),
                                            market_source=source.title()
                                        )
                                        
                                        # Apply your strategy filters
                                        if apply_strategy_filters(market_data):
                                            all_market_data.append(market_data)
                                            
                                    except Exception as e:
                                        logger.debug(f"Skipping invalid market data: {e}")
                                        continue
                            
                            logger.info(f"📊 {len(all_market_data)} markets passed strategy filters")
                            
                            # Run arbitrage detection and send Discord alerts
                            if all_market_data:
                                results = await system.run_full_scan_and_alert(all_market_data)
                                
                                # Log results
                                opp_count = results['scan_results']['opportunities_detected']
                                alert_count = results['alerts_sent']
                                
                                if opp_count > 0:
                                    logger.info(f"🎯 DETECTED {opp_count} arbitrage opportunities")
                                    logger.info(f"📢 Sent {alert_count} Discord alerts")
                                    
                                    # Log top opportunities
                                    for i, opp in enumerate(results['scan_results']['opportunities'][:3]):
                                        logger.info(f"  {i+1}. {opp.market_name} ({opp.quality_score:.1f}/10) - {opp.spread_percentage:.1f}% spread")
                                else:
                                    logger.info("📊 No quality arbitrage opportunities detected")
                            else:
                                logger.info("📊 No markets passed strategy filters")
                            
                            # Monitor system health
                            if scan_count % 10 == 0:  # Every 10 scans
                                health = await system.monitor_system_health()
                                logger.info(f"🏥 System health: {health['status']}")
                            
                            # Wait for next scan (5 minutes)
                            logger.info("⏳ Waiting 5 minutes for next scan...")
                            await asyncio.sleep(300)
                            
                        except Exception as e:
                            logger.error(f"❌ Arbitrage scan error: {e}")
                            import traceback
                            traceback.print_exc()
                            await asyncio.sleep(60)  # Wait 1 minute on error
                
                # Run the arbitrage loop
                asyncio.run(arbitrage_loop())
                
            except Exception as e:
                logger.error(f"❌ Arbitrage bot failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Start arbitrage bot in background thread
        arbitrage_thread = threading.Thread(target=run_arbitrage, daemon=True)
        arbitrage_thread.start()
        logger.info("✅ Arbitrage bot started in background")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to start arbitrage bot: {e}")
        return False

def apply_strategy_filters(market_data: MarketData) -> bool:
    """Apply your specific arbitrage strategy filters"""
    try:
        # Filter 1: Minimum spread requirements
        if market_data.spread_percentage < 1.0:  # Less than 1% spread
            return False
        
        # Filter 2: Minimum liquidity requirements
        min_liquidity = min(market_data.yes_liquidity, market_data.no_liquidity)
        if min_liquidity < 25000:  # Less than $25K liquidity
            return False
        
        # Filter 3: Minimum volume requirements
        if market_data.volume_24h < 100000:  # Less than $100K volume
            return False
        
        # Filter 4: Price range validation (avoid extreme prices)
        if market_data.yes_price < 0.1 or market_data.yes_price > 0.9:
            return False
        
        # Filter 5: Time window validation (avoid expired markets)
        if market_data.expires_at:
            time_remaining = market_data.expires_at - datetime.now()
            if time_remaining.total_seconds() < 1800:  # Less than 30 minutes remaining
                return False
        
        # Filter 6: Market name quality (avoid spam/markets we don't want)
        market_name_lower = market_data.market_name.lower()
        excluded_keywords = ['test', 'demo', 'spam', 'fake', 'mock']
        if any(keyword in market_name_lower for keyword in excluded_keywords):
            return False
        
        # Filter 7: Source-specific filters
        if market_data.market_source.lower() == 'manifold':
            # Manifold-specific filters
            if market_data.yes_liquidity < 10000:  # Lower liquidity threshold for Manifold
                return False
        
        # Filter 8: Volatility filter (avoid too volatile or too stable)
        if market_data.price_volatility > 0.5:  # Too volatile
            return False
        if market_data.price_volatility < 0.01:  # Too stable (possibly stale data)
            return False
        
        # Passed all filters
        return True
        
    except Exception as e:
        logger.debug(f"Strategy filter error: {e}")
        return False
                            
                        except Exception as e:
                            logger.error(f"❌ Arbitrage scan error: {e}")
                            await asyncio.sleep(60)  # Wait 1 minute on error
                
                # Run the arbitrage loop
                asyncio.run(arbitrage_loop())
                
            except Exception as e:
                logger.error(f"❌ Arbitrage bot failed: {e}")
                import traceback
                traceback.print_exc()
        
        # Start arbitrage bot in background thread
        arbitrage_thread = threading.Thread(target=run_arbitrage, daemon=True)
        arbitrage_thread.start()
        logger.info("✅ Arbitrage bot started in background")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to start arbitrage bot: {e}")
        return False


def start_application():
    """Start the Flask application with gunicorn"""
    try:
        logger.info("🚀 Starting application...")
        
        # Get port from environment
        port = int(os.environ.get("PORT", 5000))
        logger.info(f"📡 Starting on port {port}")
        
        # Import the app
        import dashboard.app
        
        # Start with gunicorn
        import subprocess
        cmd = [
            "gunicorn",
            "--bind", f"0.0.0.0:{port}",
            "--workers", "1",
            "--timeout", "120",
            "--access-logfile", "-",
            "--error-logfile", "-",
            "dashboard.app:app"
        ]
        
        logger.info(f"🎯 Running command: {' '.join(cmd)}")
        subprocess.run(cmd)
        
    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        sys.exit(1)


def main():
    """Main startup function"""
    logger.info("🎯 Render Dashboard + Arbitrage Bot Startup")
    logger.info("=" * 50)
    
    # Environment check
    logger.info("🌍 Environment check:")
    logger.info(f"   Python version: {sys.version}")
    logger.info(f"   Working directory: {os.getcwd()}")
    logger.info(f"   PORT: {os.environ.get('PORT', 'not set')}")
    logger.info(f"   DATABASE_URL set: {'yes' if os.environ.get('DATABASE_URL') else 'no'}")
    
    # Check Discord webhook URLs
    logger.info("📡 Discord webhook check:")
    discord_vars = ['DISCORD_WEBHOOK_URL', 'CPM_WEBHOOK_URL', 'DISCORD_HEALTH_WEBHOOK_URL']
    for var in discord_vars:
        value = os.environ.get(var)
        if value:
            logger.info(f"   {var}: ✅ SET")
        else:
            logger.warning(f"   {var}: ❌ NOT SET")
    
    # Test imports
    logger.info("\n📦 Testing imports...")
    if not test_imports():
        logger.error("❌ Import tests failed, exiting")
        sys.exit(1)
    
    # Initialize database
    logger.info("\n🗄️  Initializing database...")
    if not initialize_database():
        logger.error("❌ Database initialization failed, exiting")
        sys.exit(1)
    
    # Start arbitrage bot
    logger.info("\n🤖 Starting arbitrage bot...")
    if not start_arbitrage_bot():
        logger.warning("⚠️ Arbitrage bot failed to start, but continuing with dashboard")
    
    # Start dashboard
    logger.info("\n🚀 Starting dashboard...")
    start_application()


if __name__ == "__main__":
    main()
