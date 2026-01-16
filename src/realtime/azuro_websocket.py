"""
Azuro WebSocket Real-Time Listener
Real-time market updates via WebSocket for Azuro Protocol
"""

import asyncio
import json
import logging
import websockets
from datetime import datetime, timezone
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass
import backoff
from collections import deque
import time

logger = logging.getLogger("azuro_websocket")

@dataclass
class AzuroMarketUpdate:
    """Real-time market update from Azuro WebSocket"""
    type: str  # 'odds_update' | 'liquidity_update' | 'condition_update'
    chain: str  # 'polygon', 'gnosis', 'base', 'chiliz'
    condition_id: str
    game_id: str
    yes_price: float
    no_price: float
    yes_liquidity: float
    no_liquidity: float
    timestamp: datetime
    source_data: Dict[str, Any]

class AzuroWebSocketListener:
    """Real-time market updates via WebSocket"""
    
    # WebSocket URLs
    PRODUCTION_URL = 'wss://streams.onchainfeed.org/v1/streams/feed'
    DEVELOPMENT_URL = 'wss://dev-streams.onchainfeed.org/v1/streams/feed'
    
    # Supported chains
    SUPPORTED_CHAINS = ['polygon', 'gnosis', 'base', 'chiliz']
    
    # Connection settings
    MAX_RECONNECT_ATTEMPTS = 10
    INITIAL_RECONNECT_DELAY = 1.0  # seconds
    MAX_RECONNECT_DELAY = 60.0  # seconds
    PING_INTERVAL = 30  # seconds
    MESSAGE_TIMEOUT = 10  # seconds
    
    def __init__(self, production: bool = True, max_queue_size: int = 1000):
        self.production = production
        self.websocket_url = self.PRODUCTION_URL if production else self.DEVELOPMENT_URL
        self.max_queue_size = max_queue_size
        
        # Connection state
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.is_running = False
        self.reconnect_attempts = 0
        
        # Callbacks
        self.callbacks: List[Callable[[AzuroMarketUpdate], None]] = []
        
        # Message queue for high-frequency updates
        self.message_queue = deque(maxlen=max_queue_size)
        self.queue_processor_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'callbacks_triggered': 0,
            'connection_attempts': 0,
            'last_message_time': None,
            'last_callback_time': None
        }
        
        # Chain subscriptions
        self.subscribed_chains = set()
        
        logger.info(f"🔌 AzuroWebSocketListener initialized (production={production})")

    def register_callback(self, callback: Callable[[AzuroMarketUpdate], None]) -> None:
        """
        Register async callback for market updates
        
        Callback receives AzuroMarketUpdate with all market data
        """
        self.callbacks.append(callback)
        logger.info(f"📞 Registered callback (total: {len(self.callbacks)})")

    async def connect(self) -> None:
        """
        Connect to WebSocket with auto-reconnect
        Max 10 reconnection attempts with exponential backoff
        """
        if self.is_running:
            logger.warning("⚠️ WebSocket already running")
            return
        
        self.is_running = True
        logger.info(f"🚀 Starting Azuro WebSocket connection to {self.websocket_url}")
        
        # Start queue processor
        self.queue_processor_task = asyncio.create_task(self._process_message_queue())
        
        # Main connection loop
        while self.is_running and self.reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS:
            try:
                await self._connect_with_backoff()
                
                if self.is_connected:
                    # Reset reconnect attempts on successful connection
                    self.reconnect_attempts = 0
                    logger.info("✅ WebSocket connected successfully")
                    
                    # Subscribe to chains and start message loop
                    await self._subscribe_to_chains()
                    await self._message_loop()
                    
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"⚠️ WebSocket connection closed: {e}")
                self.is_connected = False
            except Exception as e:
                logger.error(f"❌ WebSocket error: {e}")
                self.is_connected = False
            
            # Reconnect logic
            if self.is_running:
                self.reconnect_attempts += 1
                if self.reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS:
                    delay = min(
                        self.INITIAL_RECONNECT_DELAY * (2 ** self.reconnect_attempts),
                        self.MAX_RECONNECT_DELAY
                    )
                    logger.info(f"🔄 Reconnecting in {delay:.1f}s (attempt {self.reconnect_attempts + 1}/{self.MAX_RECONNECT_ATTEMPTS})")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"❌ Max reconnection attempts reached. Giving up.")
                    break
        
        self.is_running = False
        logger.info("🔌 WebSocket connection loop ended")

    async def disconnect(self) -> None:
        """Gracefully disconnect from WebSocket"""
        logger.info("🛑 Disconnecting Azuro WebSocket...")
        
        self.is_running = False
        
        # Close WebSocket
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception as e:
                logger.warning(f"⚠️ Error closing WebSocket: {e}")
        
        self.is_connected = False
        self.websocket = None
        
        # Stop queue processor
        if self.queue_processor_task:
            self.queue_processor_task.cancel()
            try:
                await self.queue_processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("✅ Azuro WebSocket disconnected")

    @backoff.on_exception(
        backoff.expo,
        (websockets.exceptions.InvalidHandshake, websockets.exceptions.WebSocketException),
        max_tries=3,
        base=1,
        max_value=30
    )
    async def _connect_with_backoff(self) -> None:
        """Connect to WebSocket with exponential backoff"""
        self.stats['connection_attempts'] += 1
        
        extra_headers = {
            'User-Agent': 'AzuroWebSocketListener/1.0',
            'Origin': 'https://azuro.org'
        }
        
        self.websocket = await websockets.connect(
            self.websocket_url,
            extra_headers=extra_headers,
            ping_interval=self.PING_INTERVAL,
            ping_timeout=self.MESSAGE_TIMEOUT,
            close_timeout=self.MESSAGE_TIMEOUT
        )
        
        self.is_connected = True
        logger.info(f"🔗 Connected to Azuro WebSocket (attempt {self.stats['connection_attempts']})")

    async def _subscribe_to_chains(self) -> None:
        """Subscribe to each chain with filters"""
        if not self.is_connected or not self.websocket:
            raise RuntimeError("WebSocket not connected")
        
        logger.info("📡 Subscribing to Azuro chains...")
        
        for chain in self.SUPPORTED_CHAINS:
            try:
                # Subscribe to chain with filters
                subscribe_message = {
                    "action": "subscribe",
                    "channel": f"markets.{chain}",
                    "filters": {
                        "status": "active",
                        "liquidity_min": 40000,
                        "updates": ["odds", "liquidity"]
                    }
                }
                
                await self.websocket.send(json.dumps(subscribe_message))
                self.subscribed_chains.add(chain)
                logger.info(f"✅ Subscribed to {chain} markets")
                
                # Small delay between subscriptions
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ Failed to subscribe to {chain}: {e}")
        
        logger.info(f"📡 Subscribed to {len(self.subscribed_chains)} chains: {', '.join(self.subscribed_chains)}")

    async def _message_loop(self) -> None:
        """Main message processing loop"""
        logger.info("🔄 Starting message processing loop...")
        
        try:
            async for message in self.websocket:
                if not self.is_running:
                    break
                
                self.stats['messages_received'] += 1
                self.stats['last_message_time'] = datetime.now(timezone.utc)
                
                # Add to queue for processing
                try:
                    self.message_queue.append(message)
                except Exception as e:
                    logger.warning(f"⚠️ Message queue full, dropping message: {e}")
                
        except websockets.exceptions.ConnectionClosed:
            logger.info("📡 WebSocket connection closed in message loop")
        except Exception as e:
            logger.error(f"❌ Error in message loop: {e}")
        finally:
            self.is_connected = False

    async def _process_message_queue(self) -> None:
        """Process messages from queue in background"""
        logger.info("🔄 Starting message queue processor...")
        
        while self.is_running:
            try:
                # Get message from queue
                if self.message_queue:
                    message = self.message_queue.popleft()
                    await self._handle_message(message)
                else:
                    # No messages, wait briefly
                    await asyncio.sleep(0.01)
                    
            except asyncio.CancelledError:
                logger.info("📡 Message queue processor cancelled")
                break
            except Exception as e:
                logger.error(f"❌ Error processing message: {e}")
                await asyncio.sleep(1)  # Brief pause on error

    async def _handle_message(self, message: str) -> None:
        """Process incoming WebSocket messages"""
        try:
            # Parse JSON message
            data = json.loads(message)
            
            # Validate message structure
            if not isinstance(data, dict):
                logger.warning(f"⚠️ Invalid message format: {type(data)}")
                return
            
            # Extract update type
            update_type = data.get('type')
            if update_type not in ['odds_update', 'liquidity_update', 'condition_update']:
                logger.debug(f"📝 Ignoring message type: {update_type}")
                return
            
            # Extract chain information
            chain = data.get('chain', 'unknown')
            if chain not in self.SUPPORTED_CHAINS:
                logger.debug(f"📝 Ignoring unsupported chain: {chain}")
                return
            
            # Extract market data
            condition_id = data.get('condition_id')
            game_id = data.get('game_id')
            
            if not condition_id:
                logger.warning(f"⚠️ Missing condition_id in message")
                return
            
            # Extract prices and liquidity
            yes_price = float(data.get('yes_price', 0))
            no_price = float(data.get('no_price', 0))
            yes_liquidity = float(data.get('yes_liquidity', 0))
            no_liquidity = float(data.get('no_liquidity', 0))
            
            # Validate data
            if not (0 <= yes_price <= 1 and 0 <= no_price <= 1):
                logger.warning(f"⚠️ Invalid prices: yes={yes_price}, no={no_price}")
                return
            
            if yes_liquidity < 0 or no_liquidity < 0:
                logger.warning(f"⚠️ Invalid liquidity: yes={yes_liquidity}, no={no_liquidity}")
                return
            
            # Create market update object
            market_update = AzuroMarketUpdate(
                type=update_type,
                chain=chain,
                condition_id=condition_id,
                game_id=game_id or '',
                yes_price=yes_price,
                no_price=no_price,
                yes_liquidity=yes_liquidity,
                no_liquidity=no_liquidity,
                timestamp=datetime.now(timezone.utc),
                source_data=data
            )
            
            # Trigger callbacks
            await self._trigger_callbacks(market_update)
            
            self.stats['messages_processed'] += 1
            
            # Log update (debug level to avoid spam)
            logger.debug(f"📈 {update_type} on {chain}: {condition_id} (yes: {yes_price:.3f}, no: {no_price:.3f})")
            
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error: {e}")
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")

    async def _trigger_callbacks(self, market_update: AzuroMarketUpdate) -> None:
        """Call all registered callbacks with market update"""
        if not self.callbacks:
            return
        
        self.stats['callbacks_triggered'] += 1
        self.stats['last_callback_time'] = datetime.now(timezone.utc)
        
        # Trigger all callbacks concurrently
        tasks = []
        for callback in self.callbacks:
            try:
                task = asyncio.create_task(self._safe_callback(callback, market_update))
                tasks.append(task)
            except Exception as e:
                logger.error(f"❌ Error creating callback task: {e}")
        
        # Wait for all callbacks to complete (with timeout)
        if tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("⚠️ Callbacks took too long to complete")

    async def _safe_callback(self, callback: Callable[[AzuroMarketUpdate], None], 
                          market_update: AzuroMarketUpdate) -> None:
        """Safely execute callback with error handling"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(market_update)
            else:
                callback(market_update)
        except Exception as e:
            logger.error(f"❌ Callback error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket listener statistics"""
        return {
            **self.stats,
            'is_connected': self.is_connected,
            'is_running': self.is_running,
            'reconnect_attempts': self.reconnect_attempts,
            'subscribed_chains': list(self.subscribed_chains),
            'queue_size': len(self.message_queue),
            'callback_count': len(self.callbacks),
            'uptime_seconds': (time.time() - self.stats.get('connection_attempts', time.time())) if self.stats.get('connection_attempts') else 0
        }

# Test function
async def test_azuro_websocket():
    """Test the Azuro WebSocket listener"""
    print("🎯 Testing Azuro WebSocket Listener")
    print("=" * 50)
    
    # Create listener (use development URL for testing)
    listener = AzuroWebSocketListener(production=False)
    
    # Register test callback
    async def test_callback(update: AzuroMarketUpdate):
        print(f"📈 Update: {update.type} on {update.chain}")
        print(f"   Condition: {update.condition_id}")
        print(f"   Prices: YES={update.yes_price:.3f}, NO={update.no_price:.3f}")
        print(f"   Liquidity: YES=${update.yes_liquidity:,.0f}, NO=${update.no_liquidity:,.0f}")
        print(f"   Time: {update.timestamp}")
        print()
    
    listener.register_callback(test_callback)
    
    try:
        print("🔌 Connecting to WebSocket...")
        await listener.connect()
        
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")
    except Exception as e:
        print(f"❌ Test failed: {e}")
    finally:
        print("🔌 Disconnecting...")
        await listener.disconnect()
        
        # Show stats
        stats = listener.get_stats()
        print(f"\n📊 WebSocket Stats:")
        print(f"  Messages Received: {stats['messages_received']}")
        print(f"  Messages Processed: {stats['messages_processed']}")
        print(f"  Callbacks Triggered: {stats['callbacks_triggered']}")
        print(f"  Connection Attempts: {stats['connection_attempts']}")

if __name__ == "__main__":
    asyncio.run(test_azuro_websocket())
