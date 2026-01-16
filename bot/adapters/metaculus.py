from __future__ import annotations

from typing import Iterable, Optional, Dict
from urllib.parse import quote

import httpx

from bot.adapters.base import Adapter
from bot.errors import retry_with_backoff, safe_http_get, log_error_metrics, ErrorInfo, ErrorType
from bot.models import Market, Outcome, Quote
from bot.rate_limit import create_rate_limited_client, get_adapter_rate_limit, RateLimitedClient


class MetaculusAdapter(Adapter):
    """
    Adapter for Metaculus forecasting platform.
    
    API Docs: https://www.metaculus.com/api/
    Base URL: https://www.metaculus.com/api2
    
    No authentication required for read-only access.
    
    Endpoints:
    - GET /questions/ - List questions with filters
    - GET /questions/{id}/ - Get question details
    """
    
    name = "metaculus"

    def __init__(
        self,
        base_url: str = "https://www.metaculus.com/api2",
        questions_limit: int = 50,
        rate_limit_config = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.questions_limit = questions_limit
        self._question_cache: Dict[str, dict] = {}
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
        Fetch active binary questions from Metaculus.
        Uses /questions/ endpoint with status and type filters.
        """
        url = f"{self.base_url}/questions/"
        params = {
            "limit": str(self.questions_limit),
            "status": "open",
            "forecast_type": "binary",
            "order_by": "-activity",
            "type": "forecast",
        }
        print(f"[{self.name}] Fetching markets from {url} with params {params}")

        client = self._get_client()
        try:
            r = await retry_with_backoff(
                client.get, self.name, url, params=params,
                max_retries=3,
                adapter_name=self.name
            )
            print(f"[{self.name}] Got response status {r.status_code}")
            data = r.json()
        except Exception as e:
            print(f"[{self.name}] HTTP/API error: {e}")
            return []

        # Response can be paginated with "results" key or direct list
        questions_raw = data.get("results", data) if isinstance(data, dict) else data
        if not isinstance(questions_raw, list):
            questions_raw = []
        print(f"[{self.name}] Parsed {len(questions_raw)} raw questions")

        markets: list[Market] = []
        self._question_cache.clear()

        for q in questions_raw:
            if not isinstance(q, dict):
                continue

            question_id = q.get("id")
            if not question_id:
                continue
            
            question_id = str(question_id)
            title = str(q.get("title") or q.get("title_short") or question_id).strip()
            url_path = q.get("url") or q.get("page_url")
            
            # Build full URL if relative
            if url_path and not url_path.startswith("http"):
                url_path = f"https://www.metaculus.com{url_path}"

            # Cache question data
            self._question_cache[question_id] = q

            markets.append(
                Market(
                    source=self.name,
                    market_id=question_id,
                    title=title,
                    url=url_path,
                    outcomes=[],
                )
            )

        print(f"[{self.name}] Returning {len(markets)} markets")
        return markets

    async def list_outcomes(self, market: Market) -> list[Outcome]:
        """
        Metaculus binary questions have YES/NO outcomes.
        """
        return [
            Outcome(outcome_id=f"{market.market_id}_YES", name="YES"),
            Outcome(outcome_id=f"{market.market_id}_NO", name="NO"),
        ]

    async def get_quotes(self, market: Market, outcomes: Iterable[Outcome]) -> list[Quote]:
        """
        Fetch current community prediction from cached data or API.
        
        Metaculus provides:
        - community_prediction: aggregated forecast (0-1)
        - metaculus_prediction: Metaculus's own prediction (may be null)
        """
        # Try to get from cache first
        cached = self._question_cache.get(market.market_id)
        
        prob = None
        if cached:
            # Try different field names for community prediction
            prob = _extract_probability(cached)
        
        # If not in cache or no probability, fetch from API
        if prob is None:
            url = f"{self.base_url}/questions/{quote(market.market_id, safe='/')}/"
            
            client = self._get_client()
            try:
                r = await retry_with_backoff(
                    client.get, self.name, url,
                    max_retries=2,
                    adapter_name=self.name,
                    market_id=market.market_id
                )
                data = r.json()
                prob = _extract_probability(data)
            except Exception as e:
                # Log failure but continue with None probability
                log_error_metrics(ErrorInfo(
                    error_type=ErrorType.NETWORK,
                    message=f"Failed to fetch probability: {e}",
                    adapter_name=self.name,
                    market_id=market.market_id
                ))

        quotes: list[Quote] = []
        
        for o in outcomes:
            if prob is not None:
                # YES outcome gets probability, NO gets 1-probability
                if o.name == "YES":
                    quotes.append(Quote(
                        outcome_id=o.outcome_id,
                        bid=None,
                        ask=None,
                        mid=prob,
                        spread=None,
                        bid_size=None,
                        ask_size=None,
                    ))
                else:
                    quotes.append(Quote(
                        outcome_id=o.outcome_id,
                        bid=None,
                        ask=None,
                        mid=1.0 - prob,
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


def _extract_probability(data: dict) -> Optional[float]:
    """
    Extract community prediction probability from Metaculus question data.
    Tries multiple field names as API format varies.
    """
    # Try various field names
    for field in [
        "community_prediction",
        "q2",  # median prediction
        "prediction_timeseries",
    ]:
        val = data.get(field)
        if val is not None:
            if isinstance(val, (int, float)):
                try:
                    p = float(val)
                    if 0.0 <= p <= 1.0:
                        return p
                except (ValueError, TypeError):
                    pass
            elif isinstance(val, dict):
                # Nested structure like {"full": {"q2": 0.5}}
                for subfield in ["full", "latest", "current"]:
                    sub = val.get(subfield)
                    if isinstance(sub, dict):
                        for prob_field in ["q2", "median", "mean", "value"]:
                            p_val = sub.get(prob_field)
                            if p_val is not None:
                                try:
                                    p = float(p_val)
                                    if 0.0 <= p <= 1.0:
                                        return p
                                except (ValueError, TypeError):
                                    pass
                    elif isinstance(sub, (int, float)):
                        try:
                            p = float(sub)
                            if 0.0 <= p <= 1.0:
                                return p
                        except (ValueError, TypeError):
                            pass
            elif isinstance(val, list) and val:
                # Timeseries - get latest
                latest = val[-1]
                if isinstance(latest, dict):
                    for prob_field in ["community_prediction", "q2", "value"]:
                        p_val = latest.get(prob_field)
                        if p_val is not None:
                            try:
                                p = float(p_val)
                                if 0.0 <= p <= 1.0:
                                    return p
                            except (ValueError, TypeError):
                                pass

    # Try forecasts field (newer API)
    forecasts = data.get("forecasts")
    if isinstance(forecasts, dict):
        for key in ["community", "metaculus"]:
            forecast = forecasts.get(key)
            if isinstance(forecast, dict):
                for prob_field in ["q2", "median", "mean"]:
                    p_val = forecast.get(prob_field)
                    if p_val is not None:
                        try:
                            p = float(p_val)
                            if 0.0 <= p <= 1.0:
                                return p
                        except (ValueError, TypeError):
                            pass

    return None
