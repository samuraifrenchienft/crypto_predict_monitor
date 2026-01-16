"""
Integrated Main Monitoring Loop
Enhanced monitoring: Polymarket + Azuro (4 chains) + Real-time WebSocket
"""

import asyncio
import logging
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bot'))
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'arbitrage'))

# Import existing components
from opportunity_detector import ArbitrageDetector, Market
from arbitrage_alert_manager import ArbitrageAlertManager
from professional_alerts import ProfessionalArbitrageAlerts

# Import new components
from realtime.azuro_websocket import AzuroWebSocketListener, AzuroMarketUpdate
from fetchers.market_normalizer import MarketNormalizer, NormalizedMarket
from simple_live_verification import verify_live_data

logger = logging.getLogger("main_integrated")

class IntegratedMonitoringSystem:
    """Integrated monitoring system with multiple data sources and real-time updates"""
    
    def __init__(self):
        self.is_running = False
        
        # Core components
        self.arbitrage_detector = ArbitrageDetector()
        self.alert_manager = ArbitrageAlertManager()
        self.discord_alerts = ProfessionalArbitrageAlerts()
        
        # Azuro components
        self.azuro_websocket: Optional[AzuroWebSocketListener] = None
        
        # Statistics
        self.stats = {
            'start_time': datetime.now(timezone.utc),
            'total_markets_monitored': 0,
            'opportunities_detected': 0,
            'alerts_sent': 0,
            'websocket_updates': 0,
            'last_poll_time': None,
            'last_websocket_update': None
        }
        
        # Configuration
        self.poll_interval = 30  # seconds
        self.min_opportunity_score = 6.0
        
        logger.info("🚀 IntegratedMonitoringSystem initialized")

    async def initialize(self) -> bool:
        """Initialize all components"""
        try:
            logger.info("🔧 Initializing integrated monitoring system...")
            
            # Initialize Azuro WebSocket
            self.azuro_websocket = AzuroWebSocketListener(production=True)
            
            # Register real-time callback
            self.azuro_websocket.register_callback(self._on_websocket_update)
            
            logger.info("✅ All components initialized")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize: {e}")
            return False

    async def start(self) -> None:
        """Start the integrated monitoring loop"""
        if not await self.initialize():
            raise RuntimeError("Failed to initialize components")
        
        self.is_running = True
        logger.info("🚀 Starting integrated monitoring loop...")
        
        # Start WebSocket in background
        ws_task = asyncio.create_task(self._run_websocket())
        
        try:
            # Main monitoring loop
            await self._main_monitoring_loop()
            
        finally:
            # Cleanup
            self.is_running = False
            if self.azuro_websocket:
                await self.azuro_websocket.disconnect()
            ws_task.cancel()
            
            try:
                await ws_task
            except asyncio.CancelledError:
                pass

    async def _run_websocket(self) -> None:
        """Run WebSocket listener in background"""
        try:
            await self.azuro_websocket.connect()
        except Exception as e:
            logger.error(f"❌ WebSocket error: {e}")

    async def _on_websocket_update(self, update: AzuroMarketUpdate) -> None:
        """Handle real-time WebSocket updates"""
        try:
            self.stats['websocket_updates'] += 1
            self.stats['last_websocket_update'] = datetime.now(timezone.utc)
            
            logger.debug(f"📈 WebSocket update: {update.type} on {update.chain}")
            
            # Convert to NormalizedMarket
            normalized_market = self._convert_websocket_update(update)
            
            # Run arbitrage detection on single market
            opportunities = await self._detect_single_market_opportunities(normalized_market)
            
            # Send alerts for high-scoring opportunities
            for opp in opportunities:
                if opp.efficiency_score >= self.min_opportunity_score:
                    await self._send_alert(opp)
            
        except Exception as e:
            logger.error(f"❌ Error handling WebSocket update: {e}")

    def _convert_websocket_update(self, update: AzuroMarketUpdate) -> NormalizedMarket:
        """Convert WebSocket update to NormalizedMarket"""
        return NormalizedMarket(
            market_id=f"azuro_{update.chain}:{update.condition_id}",
            source=f'azuro_{update.chain}',
            chain=update.chain,
            name=f"Real-time Market {update.condition_id}",
            category='event',
            yes_price=update.yes_price,
            no_price=update.no_price,
            spread=1.0 - (update.yes_price + update.no_price),
            yes_liquidity=update.yes_liquidity,
            no_liquidity=update.no_liquidity,
            total_liquidity=update.yes_liquidity + update.no_liquidity,
            volume_24h=0.0,  # Not available in WebSocket updates
            status='active',
            expires_at=update.timestamp + timedelta(hours=24),
            source_data=update.source_data,
            price_change_24h=0.0,
            bid_ask_spread=0.001,
            time_to_expiration=86400  # 24 hours
        )

    async def _main_monitoring_loop(self) -> None:
        """Main polling loop for all data sources"""
        logger.info("🔄 Starting main monitoring loop...")
        
        while self.is_running:
            try:
                loop_start = datetime.now(timezone.utc)
                
                # FETCH PHASE
                all_markets = []
                
                # 1. Fetch Polymarket markets
                pm_markets = await self._fetch_polymarket_markets()
                all_markets.extend(pm_markets)
                
                # 2. Fetch Azuro markets (all chains)
                azuro_markets = await self._fetch_azuro_markets()
                all_markets.extend(azuro_markets)
                
                # Update statistics
                self.stats['total_markets_monitored'] = len(all_markets)
                self.stats['last_poll_time'] = loop_start
                
                # DETECT PHASE
                opportunities = await self._detect_opportunities(all_markets)
                
                # ALERT PHASE
                await self._process_opportunities(opportunities)
                
                # Log results
                loop_duration = (datetime.now(timezone.utc) - loop_start).total_seconds()
                logger.info(f"📊 Loop completed in {loop_duration:.1f}s: "
                          f"{len(all_markets)} markets, {len(opportunities)} opportunities")
                
                # Wait for next iteration
                await asyncio.sleep(self.poll_interval)
                
            except asyncio.CancelledError:
                logger.info("🛑 Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def _fetch_polymarket_markets(self) -> List[NormalizedMarket]:
        """Fetch and normalize Polymarket markets"""
        try:
            # Import Polymarket adapter
            from adapters.polymarket import PolymarketAdapter
            
            # Create adapter with production URLs
            adapter = PolymarketAdapter(
                gamma_base_url="https://gamma-api.polymarket.com",
                clob_base_url="https://clob.polymarket.com",
                data_base_url="https://data-api.polymarket.com",
                events_limit=50
            )
            
            # Fetch markets
            markets = await adapter.list_active_markets()
            
            # Convert to dict format for normalizer
            market_dicts = []
            for market in markets:
                # Get outcomes and quotes
                outcomes = await adapter.list_outcomes(market)
                quotes = await adapter.get_quotes(market, outcomes)
                
                market_dict = {
                    'id': market.market_id,
                    'title': market.title,
                    'status': 'active',
                    'outcomes': []
                }
                
                # Add outcome data
                for outcome in outcomes:
                    outcome_dict = {
                        'name': outcome.name,
                        'outcome_id': outcome.outcome_id
                    }
                    
                    # Find corresponding quote
                    for quote in quotes:
                        if quote.outcome_id == outcome.outcome_id:
                            outcome_dict['price'] = quote.mid if quote.mid else (quote.bid + quote.ask) / 2
                            outcome_dict['liquidity'] = quote.bid_size or quote.ask_size or 0
                            break
                    
                    market_dict['outcomes'].append(outcome_dict)
                
                # Extract first outcome prices for compatibility
                if len(market_dict['outcomes']) >= 2:
                    market_dict['yes_price'] = market_dict['outcomes'][0]['price']
                    market_dict['no_price'] = market_dict['outcomes'][1]['price']
                    market_dict['yes_liquidity'] = market_dict['outcomes'][0]['liquidity']
                    market_dict['no_liquidity'] = market_dict['outcomes'][1]['liquidity']
                
                market_dicts.append(market_dict)
            
            # Normalize markets
            normalized_markets = await MarketNormalizer.normalize_batch(market_dicts, 'polymarket')
            
            await adapter.close()
            
            logger.info(f"📊 Fetched {len(normalized_markets)} Polymarket markets")
            return normalized_markets
            
        except Exception as e:
            logger.error(f"❌ Error fetching Polymarket markets: {e}")
            return []

    async def _fetch_azuro_markets(self) -> List[NormalizedMarket]:
        """Fetch and normalize Azuro markets from all chains"""
        all_azuro_markets = []
        
        try:
            # Import Azuro adapter
            from adapters.azuro import AzuroAdapter
            
            # Create adapter
            adapter = AzuroAdapter(
                graphql_base_url="https://api.azuro.org/graphql",
                subgraph_base_url="https://subgraph.azuro.org",
                rest_base_url="https://azuro.org/api/v1",
                markets_limit=50,
                use_fallback=True
            )
            
            # Fetch markets (fallback data)
            markets = await adapter.list_active_markets()
            
            # Convert to dict format
            market_dicts = []
            for market in markets:
                outcomes = await adapter.list_outcomes(market)
                quotes = await adapter.get_quotes(market, outcomes)
                
                market_dict = {
                    'id': market.market_id,
                    'title': market.title,
                    'status': 'active',
                    'outcomes': []
                }
                
                for outcome in outcomes:
                    outcome_dict = {
                        'name': outcome.name,
                        'outcome_id': outcome.outcome_id
                    }
                    
                    for quote in quotes:
                        if quote.outcome_id == outcome.outcome_id:
                            outcome_dict['probability'] = quote.mid if quote.mid else (quote.bid + quote.ask) / 2
                            outcome_dict['liquidity'] = quote.bid_size or quote.ask_size or 0
                            break
                    
                    market_dict['outcomes'].append(outcome_dict)
                
                # Extract prices for compatibility
                if len(market_dict['outcomes']) >= 2:
                    market_dict['yes_price'] = market_dict['outcomes'][0]['probability']
                    market_dict['no_price'] = market_dict['outcomes'][1]['probability']
                    market_dict['yes_liquidity'] = market_dict['outcomes'][0]['liquidity']
                    market_dict['no_liquidity'] = market_dict['outcomes'][1]['liquidity']
                
                market_dicts.append(market_dict)
            
            # Normalize for each chain (using fallback chain)
            normalized_markets = await MarketNormalizer.normalize_batch(market_dicts, 'azuro', 'polygon')
            all_azuro_markets.extend(normalized_markets)
            
            await adapter.close()
            
            logger.info(f"📊 Fetched {len(all_azuro_markets)} Azuro markets")
            return all_azuro_markets
            
        except Exception as e:
            logger.error(f"❌ Error fetching Azuro markets: {e}")
            return []

    async def _detect_opportunities(self, markets: List[NormalizedMarket]) -> List[Any]:
        """Detect arbitrage opportunities across all markets"""
        try:
            # Convert NormalizedMarket to Market format for detector
            detector_markets = []
            for normalized in markets:
                # Create Market object
                market = Market(
                    id=normalized.market_id,
                    name=normalized.name,
                    yes_price=normalized.yes_price,
                    no_price=normalized.no_price,
                    yes_liquidity=normalized.yes_liquidity,
                    no_liquidity=normalized.no_liquidity,
                    bid_ask_spread=normalized.bid_ask_spread,
                    expiration=normalized.expires_at,
                    price_change_24h=normalized.price_change_24h,
                    volume_24h=normalized.volume_24h,
                    time_to_expiration=timedelta(seconds=normalized.time_to_expiration or 86400),
                    status=normalized.status
                )
                detector_markets.append(market)
            
            # Detect opportunities
            opportunities = self.arbitrage_detector.detect_opportunities(detector_markets)
            
            self.stats['opportunities_detected'] += len(opportunities)
            
            logger.info(f"🎯 Detected {len(opportunities)} opportunities")
            return opportunities
            
        except Exception as e:
            logger.error(f"❌ Error detecting opportunities: {e}")
            return []

    async def _detect_single_market_opportunities(self, market: NormalizedMarket) -> List[Any]:
        """Detect opportunities for a single market (WebSocket updates)"""
        try:
            # Convert to Market format
            detector_market = Market(
                id=market.market_id,
                name=market.name,
                yes_price=market.yes_price,
                no_price=market.no_price,
                yes_liquidity=market.yes_liquidity,
                no_liquidity=market.no_liquidity,
                bid_ask_spread=market.bid_ask_spread,
                expiration=market.expires_at,
                price_change_24h=market.price_change_24h,
                volume_24h=market.volume_24h,
                time_to_expiration=timedelta(seconds=market.time_to_expiration or 86400),
                status=market.status
            )
            
            # Detect opportunities
            opportunities = self.arbitrage_detector.detect_opportunities([detector_market])
            
            return opportunities
            
        except Exception as e:
            logger.error(f"❌ Error detecting single market opportunities: {e}")
            return []

    async def _process_opportunities(self, opportunities: List[Any]) -> None:
        """Process detected opportunities and send alerts"""
        try:
            # Filter by minimum score
            high_score_opportunities = [
                opp for opp in opportunities 
                if opp.efficiency_score >= self.min_opportunity_score
            ]
            
            # Send alerts
            for opp in high_score_opportunities:
                await self._send_alert(opp)
            
            logger.info(f"📢 Sent alerts for {len(high_score_opportunities)} high-score opportunities")
            
        except Exception as e:
            logger.error(f"❌ Error processing opportunities: {e}")

    async def _send_alert(self, opportunity: Any) -> None:
        """Send alert for opportunity"""
        try:
            # Convert to professional alert format
            from professional_alerts import ArbitrageOpportunity as ProfessionalOpportunity
            
            professional_opp = ProfessionalOpportunity(
                market_name=opportunity.market_name,
                market_id=opportunity.market_id,
                opportunity_type="Arbitrage Opportunity",
                quality_score=opportunity.efficiency_score,
                confidence_score=opportunity.confidence_score * 10,  # Convert to 0-100 scale
                spread_percentage=opportunity.spread * 100,
                yes_price=opportunity.yes_price,
                yes_liquidity=opportunity.yes_liquidity,
                no_price=opportunity.no_price,
                no_liquidity=opportunity.no_liquidity,
                time_window=f"Valid for ~24 hours",
                polymarket_link=f"https://polymarket.com/market/{opportunity.market_id}",
                analysis_link=f"https://api.example.com/analysis/{opportunity.market_id}",
                filters_applied="Quality score >= 6.0",
                expires_at=opportunity.expires_at
            )
            
            # Send Discord alert
            async with self.discord_alerts as alerter:
                success = await alerter.send_multiple_alerts([professional_opp])
                if success > 0:
                    self.stats['alerts_sent'] += 1
            
        except Exception as e:
            logger.error(f"❌ Error sending alert: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        uptime = datetime.now(timezone.utc) - self.stats['start_time']
        
        stats = self.stats.copy()
        stats['uptime_seconds'] = uptime.total_seconds()
        stats['uptime_hours'] = uptime.total_seconds() / 3600
        
        if self.azuro_websocket:
            ws_stats = self.azuro_websocket.get_stats()
            stats['websocket'] = ws_stats
        
        return stats

# Main entry point
async def main_monitoring_loop():
    """Enhanced monitoring: Polymarket + Azuro (4 chains) + Real-time"""
    logger.info("🚀 Starting Multi-Source Market Monitoring")
    
    # Verify live data first
    logger.info("🔍 Verifying all data sources are live...")
    is_live = await verify_live_data()
    
    if not is_live:
        logger.error("🚨 NOT ALL SOURCES ARE LIVE - ABORTING")
        return
    
    logger.info("✅ All sources verified as live")
    
    # Initialize integrated system
    system = IntegratedMonitoringSystem()
    
    try:
        await system.start()
        
    except KeyboardInterrupt:
        logger.info("🛑 Monitoring stopped by user")
    except Exception as e:
        logger.error(f"❌ Monitoring failed: {e}")
    finally:
        # Show final statistics
        stats = system.get_stats()
        logger.info("📊 Final Statistics:")
        logger.info(f"  Uptime: {stats['uptime_hours']:.1f} hours")
        logger.info(f"  Markets Monitored: {stats['total_markets_monitored']}")
        logger.info(f"  Opportunities Detected: {stats['opportunities_detected']}")
        logger.info(f"  Alerts Sent: {stats['alerts_sent']}")
        logger.info(f"  WebSocket Updates: {stats['websocket_updates']}")

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run main loop
    asyncio.run(main_monitoring_loop())
