from __future__ import annotations

from typing import Iterable, Optional, Any

import httpx

from bot.adapters.base import Adapter
from bot.models import Market, Outcome, Quote


class LimitlessAdapter(Adapter):
    name = "limitless"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._market_cache: dict[str, dict] = {}  # Cache market data including prices

    async def close(self) -> None:
        self._market_cache.clear()

    async def list_active_markets(self) -> list[Market]:
        """
        Fetches active markets from Limitless Exchange API.
        """
        url = f"{self.base_url}/markets/active"
        
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url)
            r.raise_for_status()
            resp = r.json()

        # Response is dict with 'data' list (not 'markets')
        data = resp.get("data", []) if isinstance(resp, dict) else resp
        if not data and isinstance(resp, dict):
            # Try other common keys
            for key in ("markets", "items", "results"):
                if isinstance(resp.get(key), list):
                    data = resp[key]
                    break

        markets: list[Market] = []
        self._market_cache.clear()
        
        for m in data:
            if not isinstance(m, dict):
                continue
            slug = str(m.get("slug") or m.get("id") or "")
            title = str(m.get("title") or m.get("question") or m.get("name") or slug).strip()
            if not slug:
                continue

            url_val: Optional[str] = None
            for k in ("url", "market_url", "marketUrl", "link", "href", "market_link", "marketLink"):
                v = m.get(k)
                if isinstance(v, str) and v.strip():
                    url_val = v.strip()
                    break
            if url_val is None:
                url_val = f"https://limitless.exchange/markets/{slug}"

            # Cache the full market data including prices
            self._market_cache[slug] = m
            
            # Check if market has tokens (skip if not)
            tokens = m.get("tokens", {})
            if not tokens.get("yes") or not tokens.get("no"):
                continue  # Skip markets without tradable tokens
            
            markets.append(Market(source=self.name, market_id=slug, title=title, url=url_val, outcomes=[]))

        return markets

    async def list_outcomes(self, market: Market) -> list[Outcome]:
        """
        Extracts YES/NO token IDs from cached market data.
        """
        cached = self._market_cache.get(market.market_id)
        if not cached:
            raise RuntimeError(f"Limitless market not in cache: {market.market_id}")

        tokens = cached.get("tokens", {})
        yes_token = tokens.get("yes")
        no_token = tokens.get("no")

        # Some markets might not have tokens (expired, special types, etc.)
        if not yes_token or not no_token:
            # Return empty outcomes list for markets without tokens
            return []

        return [
            Outcome(outcome_id=str(yes_token), name="YES"),
            Outcome(outcome_id=str(no_token), name="NO"),
        ]

    async def get_quotes(self, market: Market, outcomes: Iterable[Outcome]) -> list[Quote]:
        """
        Uses cached prices from the market data.
        Limitless returns prices as [yes_price, no_price] in the market response.
        """
        cached = self._market_cache.get(market.market_id)
        if not cached:
            # Return empty quotes if not cached
            return [Quote(outcome_id=o.outcome_id, bid=None, ask=None, mid=None, spread=None, bid_size=None, ask_size=None) for o in outcomes]

        prices = cached.get("prices", [])
        
        quotes: list[Quote] = []
        outcomes_list = list(outcomes)
        
        for idx, o in enumerate(outcomes_list):
            if idx < len(prices) and prices[idx] is not None:
                mid = float(prices[idx])
                # Create synthetic spread around the price
                bid = max(0.01, mid - 0.02)
                ask = min(0.99, mid + 0.02)
                spread = ask - bid
            else:
                mid, bid, ask, spread = None, None, None, None
            
            quotes.append(Quote(
                outcome_id=o.outcome_id,
                bid=bid,
                ask=ask,
                mid=mid,
                spread=spread,
                bid_size=None,
                ask_size=None,
            ))
        
        return quotes
