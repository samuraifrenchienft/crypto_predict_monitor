from __future__ import annotations

from typing import Iterable, Optional
from urllib.parse import quote

import httpx

from bot.adapters.base import Adapter
from bot.errors import retry_with_backoff, safe_http_get, log_error_metrics, ErrorInfo, ErrorType
from bot.models import Market, Outcome, Quote


class ManifoldAdapter(Adapter):
    """
    Adapter for Manifold Markets.
    
    API Docs: https://docs.manifold.markets/api
    Base URL: https://api.manifold.markets
    
    No authentication required for read-only access.
    """
    
    name = "manifold"

    def __init__(
        self,
        base_url: str = "https://api.manifold.markets",
        markets_limit: int = 50,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.markets_limit = markets_limit

    async def list_active_markets(self) -> list[Market]:
        """
        Fetch active binary markets from Manifold.
        Uses /v0/search-markets for filtering.
        """
        url = f"{self.base_url}/v0/search-markets"
        params = {
            "term": "",
            "sort": "liquidity",
            "filter": "open",
            "contractType": "BINARY",
            "limit": str(self.markets_limit),
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await retry_with_backoff(
                safe_http_get, client, url, params=params,
                max_retries=3,
                adapter_name=self.name
            )
            markets_raw = r.json()

        markets: list[Market] = []

        for m in markets_raw or []:
            if not isinstance(m, dict):
                continue

            market_id = str(m.get("id") or "")
            if not market_id:
                continue

            question = str(m.get("question") or market_id).strip()
            url_str = m.get("url")
            
            # Only include BINARY markets with probability
            outcome_type = m.get("outcomeType")
            if outcome_type != "BINARY":
                continue

            markets.append(
                Market(
                    source=self.name,
                    market_id=market_id,
                    title=question,
                    url=url_str,
                    outcomes=[],
                )
            )

        return markets

    async def list_outcomes(self, market: Market) -> list[Outcome]:
        """
        Manifold BINARY markets have YES/NO outcomes.
        The market_id is the outcome_id for probability lookup.
        """
        return [
            Outcome(outcome_id=f"{market.market_id}_YES", name="YES"),
            Outcome(outcome_id=f"{market.market_id}_NO", name="NO"),
        ]

    async def get_quotes(self, market: Market, outcomes: Iterable[Outcome]) -> list[Quote]:
        """
        Fetch current probability from /v0/market/[marketId]/prob endpoint.
        Manifold doesn't have traditional bid/ask, so we use probability as mid.
        """
        url = f"{self.base_url}/v0/market/{quote(market.market_id, safe='')}/prob"

        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await retry_with_backoff(
                safe_http_get, client, url,
                max_retries=3,
                adapter_name=self.name,
                market_id=market.market_id
            )
            data = r.json()

        prob = data.get("prob")
        if prob is None:
            # Fallback: try to get from full market endpoint
            market_url = f"{self.base_url}/v0/market/{quote(market.market_id, safe='')}"

            try:
                r = await retry_with_backoff(
                    safe_http_get, client, market_url,
                    max_retries=2,
                    adapter_name=self.name,
                    market_id=market.market_id
                )
                market_data = r.json()
                prob = market_data.get("probability")
            except Exception as e:
                # Log fallback failure but continue
                log_error_metrics(ErrorInfo(
                    error_type=ErrorType.NETWORK,
                    message=f"Fallback endpoint failed: {e}",
                    adapter_name=self.name,
                    market_id=market.market_id
                ))

        quotes: list[Quote] = []
        
        for o in outcomes:
            if prob is not None:
                try:
                    p = float(prob)
                    # YES outcome gets probability, NO gets 1-probability
                    if o.name == "YES":
                        quotes.append(Quote(
                            outcome_id=o.outcome_id,
                            bid=None,
                            ask=None,
                            mid=p,
                            spread=None,
                            bid_size=None,
                            ask_size=None,
                        ))
                    else:
                        quotes.append(Quote(
                            outcome_id=o.outcome_id,
                            bid=None,
                            ask=None,
                            mid=1.0 - p,
                            spread=None,
                            bid_size=None,
                            ask_size=None,
                        ))
                except (ValueError, TypeError):
                    quotes.append(Quote(
                        outcome_id=o.outcome_id,
                        bid=None,
                        ask=None,
                        mid=None,
                        spread=None,
                        bid_size=None,
                        ask_size=None,
                    ))
            else:
                quotes.append(Quote(
                    outcome_id=o.outcome_id,
                    bid=None,
                    ask=None,
                    mid=None,
                    spread=None,
                    bid_size=None,
                    ask_size=None,
                ))

        return quotes
