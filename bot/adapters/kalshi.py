from __future__ import annotations

from typing import Iterable, Optional, Dict, Tuple
from urllib.parse import quote

import httpx

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
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.markets_limit = markets_limit
        self._market_cache: Dict[str, dict] = {}
        self._rate_limit_config = rate_limit_config or get_adapter_rate_limit(self.name)
        self._client: Optional[RateLimitedClient] = None

    def _get_client(self) -> RateLimitedClient:
        """Get or create a rate-limited HTTP client."""
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
            
            # Cache market data for later use
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
        
        Orderbook format:
        {
            "orderbook": {
                "yes": [[price_cents, quantity], ...],
                "no": [[price_cents, quantity], ...]
            }
        }
        
        Prices are in cents (0-100).
        """
        url = f"{self.base_url}/markets/{quote(market.market_id, safe='')}/orderbook"

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
