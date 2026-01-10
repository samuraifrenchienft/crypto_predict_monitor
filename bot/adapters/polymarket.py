from __future__ import annotations

import json
from typing import Iterable, Optional, Dict, Tuple

import httpx

from bot.adapters.base import Adapter
from bot.models import Market, Outcome, Quote


class PolymarketAdapter(Adapter):
    name = "polymarket"

    def __init__(
        self,
        gamma_base_url: str,
        clob_base_url: str,
        data_base_url: str,
        events_limit: int = 50,
    ) -> None:
        self.gamma_base_url = gamma_base_url.rstrip("/")
        self.clob_base_url = clob_base_url.rstrip("/")
        self.data_base_url = data_base_url.rstrip("/")
        self.events_limit = events_limit
        self._market_outcome_cache: Dict[str, Tuple[list[str], list[str]]] = {}
        self._market_prices_cache: Dict[str, dict] = {}  # Cache bestBid, bestAsk, outcomePrices

    async def list_active_markets(self) -> list[Market]:
        """
        Use Gamma /markets because it includes clobTokenIds and prices.
        Cache prices from Gamma API directly (more reliable than CLOB book endpoint).
        """
        url = f"{self.gamma_base_url}/markets"
        params = {
            "active": "true",
            "closed": "false",
            "archived": "false",
            "order": "volume24hr",  # Sort by recent volume (most active)
            "ascending": "false",  # Descending order
            "limit": str(self.events_limit),
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            markets_raw = r.json()

        markets: list[Market] = []
        self._market_outcome_cache.clear()
        self._market_prices_cache.clear()

        for m in markets_raw or []:
            if not isinstance(m, dict):
                continue

            market_id = str(m.get("id") or "")
            title = str(m.get("question") or m.get("title") or market_id).strip()
            if not market_id:
                continue

            outcomes_str = m.get("outcomes")
            token_ids_str = m.get("clobTokenIds")

            outcome_names = _parse_json_array_str(outcomes_str)
            token_ids = _parse_json_array_str(token_ids_str)

            if outcome_names and token_ids and len(outcome_names) == len(token_ids):
                self._market_outcome_cache[market_id] = (outcome_names, token_ids)
                
                # Cache prices from Gamma API
                self._market_prices_cache[market_id] = {
                    "bestBid": m.get("bestBid"),
                    "bestAsk": m.get("bestAsk"),
                    "outcomePrices": _parse_json_array_str(m.get("outcomePrices")),
                }

            markets.append(Market(source=self.name, market_id=market_id, title=title, url=None, outcomes=[]))

        return markets

    async def list_outcomes(self, market: Market) -> list[Outcome]:
        cached = self._market_outcome_cache.get(market.market_id)
        if not cached:
            raise RuntimeError(
                f"Polymarket outcomes/token ids not available for market_id={market.market_id}. "
                f"Gamma /markets did not provide parseable 'outcomes' + 'clobTokenIds' arrays."
            )

        names, token_ids = cached
        if len(names) != len(token_ids):
            raise RuntimeError(
                f"Polymarket outcome/token mismatch for market_id={market.market_id}: "
                f"{len(names)} outcomes vs {len(token_ids)} token ids."
            )

        outcomes: list[Outcome] = []
        for name, tid in zip(names, token_ids):
            n = str(name)
            nl = n.strip().lower()
            if nl == "yes":
                n = "YES"
            elif nl == "no":
                n = "NO"
            outcomes.append(Outcome(outcome_id=str(tid), name=n))
        return outcomes

    async def get_quotes(self, market: Market, outcomes: Iterable[Outcome]) -> list[Quote]:
        """
        Use cached prices from Gamma API instead of CLOB book endpoint.
        The Gamma API provides bestBid, bestAsk, and outcomePrices which are more reliable.
        """
        cached_prices = self._market_prices_cache.get(market.market_id, {})
        outcome_prices = cached_prices.get("outcomePrices", [])
        
        quotes: list[Quote] = []
        outcomes_list = list(outcomes)
        
        for idx, o in enumerate(outcomes_list):
            # Use outcomePrices from Gamma API
            if idx < len(outcome_prices):
                try:
                    mid = float(outcome_prices[idx])
                    # Create spread around mid price
                    bid = max(0.001, mid - 0.005)
                    ask = min(0.999, mid + 0.005)
                except (ValueError, TypeError):
                    bid, ask, mid = None, None, None
            else:
                bid, ask, mid = None, None, None
            
            quotes.append(Quote.from_bid_ask(o.outcome_id, bid=bid, ask=ask, bid_size=None, ask_size=None))

        return quotes


def _parse_json_array_str(v: object) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v]
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except Exception:
            return []
    return []


def _best_level(levels: Optional[list]) -> tuple[Optional[float], Optional[float]]:
    if not levels or not isinstance(levels, list):
        return None, None
    first = levels[0] if levels else None
    if not isinstance(first, dict):
        return None, None

    price = first.get("price")
    size = first.get("size")
    try:
        p = float(price) if price is not None else None
    except Exception:
        p = None
    try:
        s = float(size) if size is not None else None
    except Exception:
        s = None
    return p, s
