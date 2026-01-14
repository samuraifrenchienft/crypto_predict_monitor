"""
Demo Integrated Main Monitoring Loop
Simplified version demonstrating the integrated architecture
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

logger = logging.getLogger("demo_integrated")

class DemoIntegratedMonitoringSystem:
    """Demo version of integrated monitoring system"""
    
    def __init__(self):
        self.is_running = False
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
        
        logger.info("🚀 DemoIntegratedMonitoringSystem initialized")

    async def start(self) -> None:
        """Start the demo integrated monitoring loop"""
        self.is_running = True
        logger.info("🚀 Starting demo integrated monitoring loop...")
        
        try:
            # Main monitoring loop
            await self._main_monitoring_loop()
            
        except KeyboardInterrupt:
            logger.info("🛑 Monitoring stopped by user")
        except Exception as e:
            logger.error(f"❌ Monitoring failed: {e}")
        finally:
            self.is_running = False

    async def _main_monitoring_loop(self) -> None:
        """Main polling loop for all data sources"""
        logger.info("🔄 Starting demo main monitoring loop...")
        
        loop_count = 0
        while self.is_running:
            try:
                loop_start = datetime.now(timezone.utc)
                loop_count += 1
                
                # FETCH PHASE - Simulate fetching from multiple sources
                logger.info(f"📊 Loop #{loop_count}: Fetching markets from all sources...")
                
                # Simulate Polymarket fetch
                pm_markets = await self._simulate_polymarket_fetch()
                
                # Simulate Azuro fetch from 4 chains
                azuro_markets = await self._simulate_azuro_fetch()
                
                # Combine all markets
                all_markets = pm_markets + azuro_markets
                self.stats['total_markets_monitored'] = len(all_markets)
                self.stats['last_poll_time'] = loop_start
                
                # DETECT PHASE - Simulate arbitrage detection
                opportunities = await self._simulate_arbitrage_detection(all_markets)
                self.stats['opportunities_detected'] += len(opportunities)
                
                # ALERT PHASE - Simulate sending alerts
                await self._process_opportunities(opportunities)
                
                # Simulate WebSocket updates
                await self._simulate_websocket_updates()
                
                # Log results
                loop_duration = (datetime.now(timezone.utc) - loop_start).total_seconds()
                logger.info(f"📊 Loop #{loop_count} completed in {loop_duration:.1f}s: "
                          f"{len(all_markets)} markets, {len(opportunities)} opportunities")
                
                # Show statistics every 3 loops
                if loop_count % 3 == 0:
                    await self._show_statistics()
                
                # Wait for next iteration
                await asyncio.sleep(self.poll_interval)
                
            except asyncio.CancelledError:
                logger.info("🛑 Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def _simulate_polymarket_fetch(self) -> List[Dict]:
        """Simulate fetching Polymarket markets"""
        await asyncio.sleep(1)  # Simulate API call
        
        return [
            {
                'market_id': 'polymarket:btc-2024',
                'source': 'polymarket',
                'chain': 'ethereum',
                'name': 'Bitcoin Price Above $100,000 by End of 2024',
                'category': 'crypto',
                'yes_price': 0.35,
                'no_price': 0.65,
                'spread': 0.0,
                'yes_liquidity': 50000,
                'no_liquidity': 75000,
                'total_liquidity': 125000,
                'volume_24h': 250000,
                'status': 'active',
                'expires_at': datetime.now(timezone.utc) + timedelta(days=30)
            },
            {
                'market_id': 'polymarket:trump-2024',
                'source': 'polymarket',
                'chain': 'ethereum',
                'name': 'Trump Wins 2024 Election',
                'category': 'politics',
                'yes_price': 0.42,
                'no_price': 0.58,
                'spread': 0.0,
                'yes_liquidity': 85000,
                'no_liquidity': 92000,
                'total_liquidity': 177000,
                'volume_24h': 450000,
                'status': 'active',
                'expires_at': datetime.now(timezone.utc) + timedelta(days=60)
            }
        ]

    async def _simulate_azuro_fetch(self) -> List[Dict]:
        """Simulate fetching Azuro markets from 4 chains"""
        await asyncio.sleep(2)  # Simulate API calls to multiple chains
        
        chains = ['polygon', 'gnosis', 'base', 'chiliz']
        all_markets = []
        
        for chain in chains:
            markets = [
                {
                    'market_id': f'azuro_{chain}:crypto-2024',
                    'source': f'azuro_{chain}',
                    'chain': chain,
                    'name': f'{chain.title()} Crypto Price Prediction 2024',
                    'category': 'crypto',
                    'yes_price': 0.38 + (hash(chain) % 10) * 0.02,
                    'no_price': 0.62 - (hash(chain) % 10) * 0.02,
                    'spread': 0.0,
                    'yes_liquidity': 30000 + (hash(chain) % 5) * 10000,
                    'no_liquidity': 35000 + (hash(chain) % 5) * 10000,
                    'total_liquidity': 65000 + (hash(chain) % 5) * 20000,
                    'volume_24h': 150000 + (hash(chain) % 3) * 50000,
                    'status': 'active',
                    'expires_at': datetime.now(timezone.utc) + timedelta(days=45)
                }
            ]
            all_markets.extend(markets)
        
        return all_markets

    async def _simulate_arbitrage_detection(self, markets: List[Dict]) -> List[Dict]:
        """Simulate arbitrage detection"""
        await asyncio.sleep(0.5)  # Simulate processing time
        
        opportunities = []
        
        # Simulate finding some opportunities
        for i, market in enumerate(markets):
            if i % 3 == 0:  # Every 3rd market is an opportunity
                opportunity = {
                    'market_id': market['market_id'],
                    'market_name': market['name'],
                    'efficiency_score': 6.5 + (i % 3) * 0.5,  # 6.5-8.0
                    'confidence_score': 7.0 + (i % 2) * 0.5,  # 7.0-8.0
                    'spread_percentage': market['spread'] * 100,
                    'yes_price': market['yes_price'],
                    'no_price': market['no_price'],
                    'yes_liquidity': market['yes_liquidity'],
                    'no_liquidity': market['no_liquidity'],
                    'reason': f"Simulated arbitrage opportunity #{i+1}"
                }
                opportunities.append(opportunity)
        
        return opportunities

    async def _process_opportunities(self, opportunities: List[Dict]) -> None:
        """Process detected opportunities and send alerts"""
        high_score_opportunities = [
            opp for opp in opportunities 
            if opp['efficiency_score'] >= self.min_opportunity_score
        ]
        
        for opp in high_score_opportunities:
            await self._send_alert(opp)

    async def _send_alert(self, opportunity: Dict) -> None:
        """Simulate sending alert"""
        await asyncio.sleep(0.1)  # Simulate API call
        
        self.stats['alerts_sent'] += 1
        
        logger.info(f"🚨 ALERT: {opportunity['market_name']}")
        logger.info(f"   Efficiency: {opportunity['efficiency_score']:.1f}/10")
        logger.info(f"   Confidence: {opportunity['confidence_score']:.1f}/10")
        logger.info(f"   Spread: {opportunity['spread_percentage']:.1f}%")
        logger.info(f"   Liquidity: ${opportunity['yes_liquidity'] + opportunity['no_liquidity']:,.0f}")

    async def _simulate_websocket_updates(self) -> None:
        """Simulate receiving WebSocket updates"""
        await asyncio.sleep(0.2)  # Simulate processing
        
        # Simulate 1-3 WebSocket updates per cycle
        num_updates = 1 + (hash(datetime.now().second) % 3)
        
        for i in range(num_updates):
            self.stats['websocket_updates'] += 1
            
            if self.stats['websocket_updates'] % 10 == 0:
                logger.info(f"📈 WebSocket update #{self.stats['websocket_updates']}: "
                          f"Real-time price update on azuro_polygon")

    async def _show_statistics(self) -> None:
        """Show current statistics"""
        uptime = datetime.now(timezone.utc) - self.stats['start_time']
        
        logger.info("📊 SYSTEM STATISTICS:")
        logger.info(f"  Uptime: {uptime.total_seconds() / 3600:.1f} hours")
        logger.info(f"  Markets Monitored: {self.stats['total_markets_monitored']}")
        logger.info(f"  Opportunities Detected: {self.stats['opportunities_detected']}")
        logger.info(f"  Alerts Sent: {self.stats['alerts_sent']}")
        logger.info(f"  WebSocket Updates: {self.stats['websocket_updates']}")

# Main entry point
async def main_monitoring_loop():
    """Enhanced monitoring: Polymarket + Azuro (4 chains) + Real-time"""
    logger.info("🚀 Starting Demo Multi-Source Market Monitoring")
    logger.info("📡 Sources: Polymarket + Azuro (polygon, gnosis, base, chiliz)")
    logger.info("🔔 Real-time WebSocket updates enabled")
    logger.info("🎯 Arbitrage detection with professional alerts")
    
    # Initialize demo system
    system = DemoIntegratedMonitoringSystem()
    
    try:
        await system.start()
        
    except KeyboardInterrupt:
        logger.info("🛑 Monitoring stopped by user")
    except Exception as e:
        logger.error(f"❌ Monitoring failed: {e}")
    finally:
        # Show final statistics
        uptime = datetime.now(timezone.utc) - system.stats['start_time']
        logger.info("📊 FINAL STATISTICS:")
        logger.info(f"  Total Uptime: {uptime.total_seconds() / 3600:.1f} hours")
        logger.info(f"  Markets Monitored: {system.stats['total_markets_monitored']}")
        logger.info(f"  Opportunities Detected: {system.stats['opportunities_detected']}")
        logger.info(f"  Alerts Sent: {system.stats['alerts_sent']}")
        logger.info(f"  WebSocket Updates: {system.stats['websocket_updates']}")
        logger.info("🎉 Demo completed successfully!")

if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run main loop
    asyncio.run(main_monitoring_loop())
