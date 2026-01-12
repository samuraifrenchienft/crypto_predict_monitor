from __future__ import annotations

from typing import Iterable, Optional, Dict, Tuple, Awaitable, List
from urllib.parse import quote
import json
import asyncio
import logging
import time
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

import httpx
import websockets

from bot.adapters.base import Adapter
from bot.errors import retry_with_backoff, safe_http_get, log_error_metrics, ErrorInfo, ErrorType
from bot.models import Market, Outcome, Quote
from bot.rate_limit import create_rate_limited_client, get_adapter_rate_limit, RateLimitedClient


class KalshiAdapter(Adapter):
    """
    Adapter for Kalshi prediction markets.
    
    API Docs: https://docs.kalshi.com
    Base URL: https://api.elections.kalshi.com/trade-api/v2
    
    Public endpoints (no auth required):
    - GET /markets - List markets
    - GET /markets/{ticker}/orderbook - Get orderbook
    - GET /events/{event_ticker} - Get event details
    """
    
    name = "kalshi"

    def __init__(
        self,
        base_url: str = "https://api.elections.kalshi.com/trade-api/v2",
        markets_limit: int = 50,
        rate_limit_config = None,
        ws_url: str = "wss://api.elections.kalshi.com",
        kalshi_access_key: Optional[str] = None,
        kalshi_private_key: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.markets_limit = markets_limit
        self._market_cache: Dict[str, dict] = {}
        self._rate_limit_config = rate_limit_config or get_adapter_rate_limit(self.name)
        self._client: Optional[RateLimitedClient] = None
        
        # WebSocket attributes
        self.ws_url = ws_url
        self.ws: Optional[websockets.WebSocketServerProtocol] = None
        self.message_id = 1
        self._ws_logger = logging.getLogger(f"{self.name}.websocket")
        
        # API credentials
        self.kalshi_access_key = kalshi_access_key
        self.kalshi_private_key = kalshi_private_key

    def _generate_signature(self, timestamp: str, method: str, path: str) -> str:
        """Generate Kalshi API signature using RSA-PSS."""
        import os
        import re
        
        # Try to load from PEM file if string key doesn't work
        if isinstance(self.kalshi_private_key, str) and not self.kalshi_private_key.startswith('-----BEGIN'):
            # Try loading from file in project root
            pem_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'kalshi_private.pem')
            if os.path.exists(pem_file):
                with open(pem_file, 'r') as f:
                    self.kalshi_private_key = f.read()
            else:
                # Try to extract from .env.txt
                env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env.txt')
                if os.path.exists(env_file):
                    with open(env_file, 'r') as f:
                        content = f.read()
                    match = re.search(r'-----BEGIN RSA PRIVATE KEY-----([^"]+)-----END RSA PRIVATE KEY-----', content, re.DOTALL)
                    if match:
                        # Clean up the key - remove \n and extra spaces
                        key = match.group(1).replace('\\n', '').replace(' ', '')
                        # Add proper line breaks every 64 characters
                        formatted_key = "-----BEGIN RSA PRIVATE KEY-----\n"
                        for i in range(0, len(key), 64):
                            formatted_key += key[i:i+64] + "\n"
                        formatted_key += "-----END RSA PRIVATE KEY-----"
                        self.kalshi_private_key = formatted_key
        
        if not self.kalshi_private_key:
            raise ValueError("Private key required for signature generation")
        
        # Create message to sign
        message = timestamp + method + path
        
        # Load the private key
        if isinstance(self.kalshi_private_key, str):
            try:
                if self.kalshi_private_key.startswith('-----BEGIN'):
                    # PEM format
                    private_key = serialization.load_pem_private_key(
                        self.kalshi_private_key.encode('utf-8'),
                        password=None,
                        backend=None
                    )
                else:
                    # Try to parse as raw key (base64 or hex)
                    try:
                        # Try base64 decode first
                        key_bytes = base64.b64decode(self.kalshi_private_key)
                        private_key = serialization.load_der_private_key(
                            key_bytes,
                            password=None
                        )
                    except:
                        # Try hex decode
                        key_bytes = bytes.fromhex(self.kalshi_private_key)
                        private_key = serialization.load_der_private_key(
                            key_bytes,
                            password=None
                        )
            except Exception as e:
                raise ValueError(f"Failed to parse private key: {e}. Expected PEM format starting with '-----BEGIN'")
        else:
            private_key = self.kalshi_private_key
        
        # Sign using RSA-PSS
        signature = private_key.sign(
            message.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        
        return base64.b64encode(signature).decode('utf-8')

    def _get_auth_headers(self, path: str = "/trade-api/ws/v2") -> Dict[str, str]:
        """Get authentication headers for WebSocket connection."""
        if not self.kalshi_access_key or not self.kalshi_private_key:
            raise ValueError("Kalshi access key and private key required for WebSocket authentication")
        
        timestamp = str(int(time.time() * 1000))  # Unix timestamp in milliseconds
        signature = self._generate_signature(timestamp, "GET", path)
        
        return {
            "KALSHI-ACCESS-KEY": self.kalshi_access_key,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": timestamp
        }

    def _get_client(self) -> RateLimitedClient:
        if self._client is None:
            self._client = create_rate_limited_client(
                self.name,
                timeout=20.0,
                custom_config=self._rate_limit_config
            )
        return self._client

    async def list_active_markets(self) -> list[Market]:
        """
        Fetch active markets from Kalshi.
        Uses /markets endpoint with status=open filter.
        Note: The elections API includes sports markets (NFL) but not NBA/economics.
        """
        url = f"{self.base_url}/markets"
        params = {
            "status": "open",
            "limit": str(self.markets_limit),
        }

        client = self._get_client()
        r = await retry_with_backoff(
            client.get, self.name, url, params=params,
            max_retries=3,
            adapter_name=self.name
        )
        data = r.json()

        markets_raw = data.get("markets", [])
        markets: list[Market] = []
        self._market_cache.clear()

        for m in markets_raw or []:
            if not isinstance(m, dict):
                continue

            ticker = str(m.get("ticker") or "")
            if not ticker:
                continue

            title = str(m.get("title") or m.get("subtitle") or ticker).strip()
            
            # Determine category from title
            title_lower = title.lower()
            category = "sports"  # Default - most are sports
            if any(word in title_lower for word in ["senate", "governor", "house", "election", "vote", "president", "congress"]):
                category = "elections"
            elif any(word in title_lower for word in ["earnings", "revenue", "stock", "price", "gdp", "inflation"]):
                category = "economics"
            elif any(word in title_lower for word in ["temperature", "weather", "snow", "rain", "degrees"]):
                category = "weather"
            
            # Cache market data with category
            m["category"] = category
            self._market_cache[ticker] = m

            markets.append(
                Market(
                    source=self.name,
                    market_id=ticker,
                    title=title,
                    url=f"https://kalshi.com/markets/{ticker.lower()}",
                    outcomes=[],
                )
            )

        return markets

    async def list_outcomes(self, market: Market) -> list[Outcome]:
        """
        Kalshi markets are binary YES/NO.
        """
        return [
            Outcome(outcome_id=f"{market.market_id}_YES", name="YES"),
            Outcome(outcome_id=f"{market.market_id}_NO", name="NO"),
        ]

    async def get_quotes(self, market: Market, outcomes: Iterable[Outcome]) -> list[Quote]:
        """
        Fetch orderbook from /markets/{ticker}/orderbook endpoint.
        
        Note: Kalshi requires authentication for real-time orderbook data.
        Without auth, the API returns None for orderbook levels.
        """
        url = f"{self.base_url}/markets/{quote(market.market_id, safe='')}/orderbook"

        # Try authenticated request if keys are available
        if self.kalshi_access_key and self.kalshi_private_key:
            timestamp = str(int(time.time() * 1000))
            signature = self._generate_signature(timestamp, "GET", f"/trade-api/v2/markets/{market.market_id}/orderbook")
            
            headers = {
                "KALSHI-ACCESS-KEY": self.kalshi_access_key,
                "KALSHI-ACCESS-SIGNATURE": signature,
                "KALSHI-ACCESS-TIMESTAMP": timestamp
            }
            
            client = self._get_client()
            r = await retry_with_backoff(
                client.get, self.name, url, headers=headers,
                max_retries=3,
                adapter_name=self.name,
                market_id=market.market_id
            )
        else:
            # Fallback to unauthenticated request
            client = self._get_client()
            r = await retry_with_backoff(
                client.get, self.name, url,
                max_retries=3,
                adapter_name=self.name,
                market_id=market.market_id
            )
        
        data = r.json()

        orderbook = data.get("orderbook", {})
        yes_levels = orderbook.get("yes", [])
        no_levels = orderbook.get("no", [])
        
        # Handle None or empty string values (no liquidity or no auth)
        if yes_levels is None or yes_levels == "":
            yes_levels = []
        if no_levels is None or no_levels == "":
            no_levels = []
        
        # If both are empty, likely need authentication or no liquidity
        if not yes_levels and not no_levels:
            # Return quotes with None values to indicate no data available
            return [Quote(
                outcome_id=o.outcome_id,
                bid=None,
                ask=None,
                mid=None,
                spread=None,
                bid_size=None,
                ask_size=None,
            ) for o in outcomes]

        # Extract best bid/ask for YES side
        # YES bids are people wanting to buy YES
        # NO bids at price X means YES ask at (100-X)
        yes_bid, yes_bid_size = _best_level(yes_levels)
        no_bid, no_bid_size = _best_level(no_levels)

        # Convert cents to probability (0-1)
        # YES bid price in cents / 100 = YES bid probability
        # NO bid at X cents means YES ask at (100-X) cents
        yes_bid_prob = yes_bid / 100.0 if yes_bid is not None else None
        yes_ask_prob = (100.0 - no_bid) / 100.0 if no_bid is not None else None
        
        no_bid_prob = no_bid / 100.0 if no_bid is not None else None
        no_ask_prob = (100.0 - yes_bid) / 100.0 if yes_bid is not None else None

        quotes: list[Quote] = []
        
        for o in outcomes:
            if o.name == "YES":
                quotes.append(Quote.from_bid_ask(
                    outcome_id=o.outcome_id,
                    bid=yes_bid_prob,
                    ask=yes_ask_prob,
                    bid_size=yes_bid_size,
                    ask_size=no_bid_size,
                ))
            else:
                quotes.append(Quote.from_bid_ask(
                    outcome_id=o.outcome_id,
                    bid=no_bid_prob,
                    ask=no_ask_prob,
                    bid_size=no_bid_size,
                    ask_size=yes_bid_size,
                ))

        return quotes

    async def check_exchange_status(self) -> bool:
        """Check if Kalshi exchange is active and trading is enabled."""
        url = f"{self.base_url}/exchange/status"
        
        client = self._get_client()
        try:
            r = await retry_with_backoff(
                client.get, self.name, url,
                max_retries=3,
                adapter_name=self.name
            )
            data = r.json()
            
            exchange_active = data.get("exchange_active", False)
            trading_active = data.get("trading_active", False)
            
            self._ws_logger.info(f"Exchange status: active={exchange_active}, trading={trading_active}")
            return exchange_active and trading_active
        except Exception as e:
            self._ws_logger.error(f"Failed to check exchange status: {e}")
            return False

    async def close(self) -> None:
        """Clean up resources."""
        self._market_cache.clear()
        if self.ws:
            await self.ws.close()
            self.ws = None
        if self._client and hasattr(self._client, 'close'):
            await self._client.close()

    async def connect_websocket(self) -> None:
        """Connect to Kalshi WebSocket for real-time data."""
        if self.ws:
            return  # Already connected
        
        try:
            # Get authentication headers for base WebSocket path
            auth_headers = self._get_auth_headers("/trade-api/ws/v2")
            
            # Connect with authentication
            self.ws = await websockets.connect(
                self.ws_url,
                additional_headers=auth_headers
            )
            self._ws_logger.info("Connected to Kalshi WebSocket with authentication")
        except ValueError as e:
            self._ws_logger.error(f"Authentication error: {e}")
            raise
        except Exception as e:
            self._ws_logger.error(f"Failed to connect to WebSocket: {e}")
            raise

    async def subscribe_to_markets(self, channels: List[str], market_tickers: List[str], endpoint: str = "/orderbook_delta") -> None:
        """Subscribe to specific channels and markets on a WebSocket endpoint"""
        # Build full WebSocket URL with endpoint
        ws_endpoint = f"{self.ws_url}{endpoint}"
        
        # Connect to the specific endpoint with correct auth path
        if self.ws:
            await self.ws.close()
        
        # Use the endpoint path for authentication
        auth_path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        auth_headers = self._get_auth_headers(auth_path)
        
        self.ws = await websockets.connect(ws_endpoint, additional_headers=auth_headers)
        
        subscription_message = {
            "id": self.message_id,
            "cmd": "subscribe",
            "params": {
                "channels": channels,
                "market_tickers": market_tickers
            }
        }
        
        await self.ws.send(json.dumps(subscription_message))
        self.message_id += 1
        self._ws_logger.info(f"Subscribed to {channels} on {endpoint} for markets: {market_tickers}")

    async def listen_to_updates(self, callback) -> None:
        """Listen for WebSocket updates and call callback with data."""
        if not self.ws:
            await self.connect_websocket()
        
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    await callback(data)
                except json.JSONDecodeError as e:
                    self._ws_logger.error(f"Failed to parse WebSocket message: {e}")
        except websockets.exceptions.ConnectionClosed:
            self._ws_logger.warning("WebSocket connection closed")
        except Exception as e:
            self._ws_logger.error(f"WebSocket error: {e}")
            raise

    async def subscribe_to_orderbook_deltas(self, market_tickers: List[str]) -> None:
        """Subscribe to real-time orderbook updates for arbitrage monitoring"""
        await self.subscribe_to_markets(["orderbook"], market_tickers, "/orderbook_delta")

    async def subscribe_to_market_lifecycle(self, market_tickers: List[str]) -> None:
        """Subscribe to market lifecycle events (open/close/settle)"""
        await self.subscribe_to_markets(["lifecycle"], market_tickers, "/market_lifecycle_v2")


def _best_level(levels: list) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract best price and size from orderbook levels.
    Levels are [[price_cents, quantity], ...]
    Returns (price_cents, quantity) or (None, None) if empty.
    """
    if not levels or not isinstance(levels, list):
        return None, None
    
    # Find best (highest) bid
    best_price = None
    best_size = None
    
    for level in levels:
        if not isinstance(level, (list, tuple)) or len(level) < 2:
            continue
        try:
            price = float(level[0])
            size = float(level[1])
            if best_price is None or price > best_price:
                best_price = price
                best_size = size
        except (ValueError, TypeError):
            continue
    
    return best_price, best_size
