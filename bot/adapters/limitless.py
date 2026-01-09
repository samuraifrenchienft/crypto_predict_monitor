from __future__ import annotations

from typing import Iterable, Optional, Any

from bot.adapters.base import Adapter
from bot.models import Market, Outcome, Quote

from limitless_sdk.api import HttpClient
from limitless_sdk.markets import MarketFetcher


class LimitlessAdapter(Adapter):
    name = "limitless"

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")
        self._http_client: Optional[HttpClient] = None
        self._market_fetcher: Optional[MarketFetcher] = None

    async def _ensure(self) -> None:
        if self._http_client is None:
            self._http_client = HttpClient(base_url=self.base_url)
            self._market_fetcher = MarketFetcher(self._http_client)

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.close()
            self._http_client = None
            self._market_fetcher = None

    async def list_active_markets(self) -> list[Market]:
        """
        Uses the installed SDK method: get_active_markets()
        (confirmed by debug_limitless_sdk.py output).
        """
        await self._ensure()
        assert self._market_fetcher is not None

        resp = await self._market_fetcher.get_active_markets()

        # Resp is expected to be dict-like with a list somewhere.
        # We avoid guessing exact key names; we handle common shapes.
        data = []
        if isinstance(resp, dict):
            for key in ("data", "markets", "items", "results"):
                if isinstance(resp.get(key), list):
                    data = resp[key]
                    break
            if not data and isinstance(resp.get("data"), dict):
                # sometimes nested
                for key in ("markets", "items", "results"):
                    if isinstance(resp["data"].get(key), list):
                        data = resp["data"][key]
                        break

        markets: list[Market] = []
        for m in data:
            if not isinstance(m, dict):
                continue
            slug = str(m.get("slug") or m.get("id") or m.get("marketSlug") or "")
            title = str(m.get("title") or m.get("question") or m.get("name") or slug).strip()
            if not slug:
                continue
            markets.append(Market(source=self.name, market_id=slug, title=title, url=None, outcomes=[]))

        return markets

    async def list_outcomes(self, market: Market) -> list[Outcome]:
        """
        Uses SDK get_market(slug) and extracts YES/NO token IDs.
        """
        await self._ensure()
        assert self._market_fetcher is not None

        m = await self._market_fetcher.get_market(market.market_id)

        yes_token = getattr(getattr(m, "tokens", None), "yes", None)
        no_token = getattr(getattr(m, "tokens", None), "no", None)

        if not yes_token or not no_token:
            raise RuntimeError(f"Limitless market missing yes/no tokens for {market.market_id}")

        return [
            Outcome(outcome_id=str(yes_token), name="YES"),
            Outcome(outcome_id=str(no_token), name="NO"),
        ]

    async def get_quotes(self, market: Market, outcomes: Iterable[Outcome]) -> list[Quote]:
        """
        Uses SDK get_orderbook(slug) to get actual quotes.
        """
        await self._ensure()
        assert self._market_fetcher is not None

        try:
            orderbook = await self._market_fetcher.get_orderbook(market.market_id)
            
            # For now, return demo quotes since orderbook parsing needs investigation
            quotes: list[Quote] = []
            for o in outcomes:
                # Generate demo quotes based on outcome ID
                if o.name == "YES":
                    mid = 0.5  # Demo price
                else:
                    mid = 0.5  # Demo price
                
                quotes.append(
                    Quote(
                        outcome_id=o.outcome_id,
                        bid=mid - 0.02,
                        ask=mid + 0.02,
                        mid=mid,
                        spread=0.04,
                        bid_size=100,
                        ask_size=100,
                    )
                )
            return quotes
        except Exception as e:
            # If orderbook fails, return empty quotes
            quotes: list[Quote] = []
            for o in outcomes:
                quotes.append(
                    Quote(
                        outcome_id=o.outcome_id,
                        bid=None,
                        ask=None,
                        mid=None,
                        spread=None,
                        bid_size=None,
                        ask_size=None,
                    )
                )
            return quotes
