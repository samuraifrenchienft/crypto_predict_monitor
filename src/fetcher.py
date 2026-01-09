from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from src.http_client import HttpClient, HttpClientError
from src.schemas import MarketEvent

logger = logging.getLogger("crypto_predict_monitor")

# In-memory cache for Polymarket probability tracking
_polymarket_cache: dict[str, float] = {}

class FetcherError(Exception):
    pass


def _parse_iso8601_tz_aware(ts: str) -> datetime:
    s = str(ts).strip()
    if not s:
        raise ValueError("ts missing")

    if s.endswith("Z") or s.endswith("z"):
        s = s[:-1] + "+00:00"

    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt


def fetch_events(
    client: HttpClient,
    upstream: str = "dev",
    polymarket_base_url: str | None = None,
    polymarket_markets: dict[str, dict] | None = None,
    price_provider: str = "coinbase",
    price_symbol: str = "BTC-USD",
    price_interval_minutes: int = 15,
) -> list[MarketEvent]:
    if upstream == "polymarket":
        return _fetch_polymarket_events(
            client, polymarket_base_url or "https://clob.polymarket.com", polymarket_markets or {}
        )
    
    if upstream == "price":
        return _fetch_price_events(
            client, price_provider, price_symbol, price_interval_minutes
        )
    
    if upstream == "multi":
        return _fetch_multi_events(
            client,
            polymarket_base_url or "https://clob.polymarket.com",
            polymarket_markets or {},
            price_provider,
            price_symbol,
            price_interval_minutes,
        )
    
    # Dev mode: fetch from /events endpoint
    try:
        payload: Any = client.get_json("/events")
    except HttpClientError:
        raise FetcherError("Failed to fetch events") from None

    if not isinstance(payload, dict):
        raise FetcherError("Invalid /events response")

    events_raw = payload.get("events")
    if not isinstance(events_raw, list):
        raise FetcherError("Invalid /events response")

    out: list[MarketEvent] = []

    for i, item in enumerate(events_raw):
        if not isinstance(item, dict):
            logger.warning("Skipping invalid event index=%s field=%s", i, "event")
            continue

        try:
            market_id_raw = item.get("id")
            market_id = str(market_id_raw).strip() if market_id_raw is not None else ""
            if not market_id:
                raise ValueError("market_id must be non-empty")
        except Exception:
            logger.warning("Skipping invalid event index=%s field=%s", i, "id")
            continue

        try:
            title_raw = item.get("title")
            title = str(title_raw).strip() if title_raw is not None else None
            if title == "":
                title = None
        except Exception:
            logger.warning("Skipping invalid event index=%s field=%s", i, "title")
            continue

        try:
            ts_raw = item.get("ts")
            timestamp = _parse_iso8601_tz_aware(ts_raw)
        except Exception:
            logger.warning("Skipping invalid event index=%s field=%s", i, "ts")
            continue

        try:
            p_raw = item.get("p")
            probability = float(p_raw)
        except Exception:
            logger.warning("Skipping invalid event index=%s field=%s", i, "p")
            continue

        try:
            source_raw = item.get("source")
            source = str(source_raw).strip() if source_raw is not None else None
            if source == "":
                source = None
        except Exception:
            logger.warning("Skipping invalid event index=%s field=%s", i, "source")
            continue

        try:
            evt = MarketEvent(
                market_id=market_id,
                title=title,
                timestamp=timestamp,
                probability=probability,
                source=source,
            )
        except Exception:
            logger.warning("Skipping invalid event index=%s field=%s", i, "validation")
            continue

        out.append(evt)

    return out


def _fetch_polymarket_events(
    client: HttpClient,
    base_url: str,
    markets: dict[str, dict],
) -> list[MarketEvent]:
    """Fetch market events from Polymarket CLOB API."""
    out: list[MarketEvent] = []
    
    for market_id, market_config in markets.items():
        try:
            token_id = market_config.get("token_id")
            if not token_id or not str(token_id).strip():
                logger.warning("Skipping market_id=%s: missing or empty token_id", market_id)
                continue
            
            token_id = str(token_id).strip()
            
            # Fetch current price from Polymarket CLOB /price endpoint
            try:
                # Create a temporary client for Polymarket API
                polymarket_client = HttpClient(
                    base_url=base_url,
                    timeout_seconds=client.timeout_seconds
                )
                try:
                    # Query for current price with token_id and side=SELL
                    response = polymarket_client.get_json(
                        f"/price?token_id={token_id}&side=SELL"
                    )
                finally:
                    polymarket_client.close()
            except HttpClientError as e:
                logger.warning(
                    "Failed to fetch Polymarket price for market_id=%s token_id=%s: %s",
                    market_id, token_id, str(e)
                )
                continue
            
            # Parse response - /price returns dict with "price" field as string
            if not isinstance(response, dict):
                logger.warning(
                    "Invalid Polymarket response for market_id=%s: expected dict",
                    market_id
                )
                continue
            
            # Extract probability (price is string "0.XX")
            price_raw = response.get("price")
            if price_raw is None:
                logger.warning(
                    "Missing price field for market_id=%s",
                    market_id
                )
                continue
            
            try:
                probability = float(price_raw)
                if probability < 0.0 or probability > 1.0:
                    logger.warning(
                        "Invalid probability for market_id=%s: %s (must be 0-1)",
                        market_id, probability
                    )
                    continue
            except (ValueError, TypeError):
                logger.warning(
                    "Invalid price value for market_id=%s: %s",
                    market_id, price_raw
                )
                continue
            
            # Use current time as timestamp
            timestamp = datetime.now(timezone.utc)
            
            # Create MarketEvent
            try:
                evt = MarketEvent(
                    market_id=market_id,
                    title=None,
                    timestamp=timestamp,
                    probability=probability,
                    source="polymarket",
                )
                out.append(evt)
                
                # Update cache for delta calculation
                _polymarket_cache[market_id] = probability
                
            except Exception as e:
                logger.warning(
                    "Failed to create MarketEvent for market_id=%s: %s",
                    market_id, str(e)
                )
                continue
                
        except Exception as e:
            logger.warning(
                "Unexpected error processing market_id=%s: %s",
                market_id, str(e)
            )
            continue
    
    return out


def _fetch_price_events(
    client: HttpClient,
    provider: str,
    symbol: str,
    interval_minutes: int,
) -> list[MarketEvent]:
    """Fetch price movement events from a price provider."""
    if provider != "coinbase":
        logger.warning("Unsupported price_provider=%s, only 'coinbase' is supported", provider)
        return []
    
    try:
        # Create Coinbase API client
        coinbase_client = HttpClient(
            base_url="https://api.exchange.coinbase.com",
            timeout_seconds=client.timeout_seconds
        )
        try:
            # Fetch candles: granularity in seconds
            granularity = interval_minutes * 60
            # Request last 2 candles to compute delta
            response = coinbase_client.get_json_any(
                f"/products/{symbol}/candles?granularity={granularity}"
            )
        finally:
            coinbase_client.close()
    except HttpClientError as e:
        logger.warning("Failed to fetch Coinbase price data for symbol=%s: %s", symbol, str(e))
        return []
    
    # Parse response
    if not isinstance(response, list) or len(response) < 2:
        logger.warning("Invalid Coinbase response for symbol=%s: expected list with at least 2 candles", symbol)
        return []
    
    # Each candle: [time, low, high, open, close, volume]
    # Sort by time ascending to ensure we have the correct order
    try:
        # Filter valid candles and sort by timestamp (index 0)
        valid_candles = []
        for candle in response:
            if isinstance(candle, list) and len(candle) >= 5:
                valid_candles.append(candle)
        
        if len(valid_candles) < 2:
            logger.warning("Insufficient valid candles for symbol=%s: need at least 2, got %d", symbol, len(valid_candles))
            return []
        
        # Sort by timestamp ascending
        sorted_candles = sorted(valid_candles, key=lambda c: float(c[0]))
        
        # Take the two most recent candles
        prior_candle = sorted_candles[-2]
        latest_candle = sorted_candles[-1]
        
        # Extract close prices (index 4)
        prior_close = float(prior_candle[4])
        last_close = float(latest_candle[4])
        
        # Extract timestamp from most recent candle (index 0, Unix timestamp)
        timestamp_seconds = float(latest_candle[0])
        timestamp = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)
        
    except (ValueError, TypeError, IndexError) as e:
        logger.warning("Failed to parse Coinbase candle data for symbol=%s: %s", symbol, str(e))
        return []
    
    # Compute delta percentage
    if prior_close == 0:
        logger.warning("Prior close price is zero for symbol=%s, cannot compute delta", symbol)
        return []
    
    delta_pct = (last_close - prior_close) / prior_close
    
    # Create market events for up and down movements
    out: list[MarketEvent] = []
    
    # Extract base symbol (e.g., "BTC" from "BTC-USD")
    base_symbol = symbol.split("-")[0].lower() if "-" in symbol else symbol.lower()
    
    # Up event
    try:
        up_event = MarketEvent(
            market_id=f"{base_symbol}_{interval_minutes}m_up",
            title=f"{symbol} {interval_minutes}m up",
            timestamp=timestamp,
            probability=1.0 if delta_pct > 0 else 0.0,
            source="coinbase",
        )
        out.append(up_event)
    except Exception as e:
        logger.warning("Failed to create up event for symbol=%s: %s", symbol, str(e))
    
    # Down event
    try:
        down_event = MarketEvent(
            market_id=f"{base_symbol}_{interval_minutes}m_down",
            title=f"{symbol} {interval_minutes}m down",
            timestamp=timestamp,
            probability=1.0 if delta_pct < 0 else 0.0,
            source="coinbase",
        )
        out.append(down_event)
    except Exception as e:
        logger.warning("Failed to create down event for symbol=%s: %s", symbol, str(e))
    
    return out


def _fetch_multi_events(
    client: HttpClient,
    polymarket_base_url: str,
    polymarket_markets: dict[str, dict],
    price_provider: str,
    price_symbol: str,
    price_interval_minutes: int,
) -> list[MarketEvent]:
    """Fetch events from both Polymarket and price sources, merge and deduplicate."""
    polymarket_events: list[MarketEvent] = []
    price_events: list[MarketEvent] = []
    
    # Fetch from Polymarket
    try:
        polymarket_events = _fetch_polymarket_events(client, polymarket_base_url, polymarket_markets)
    except Exception as e:
        logger.warning("Failed to fetch Polymarket events in multi mode: %s", str(e))
    
    # Fetch from price provider
    try:
        price_events = _fetch_price_events(client, price_provider, price_symbol, price_interval_minutes)
    except Exception as e:
        logger.warning("Failed to fetch price events in multi mode: %s", str(e))
    
    # Check if both failed
    if not polymarket_events and not price_events:
        raise FetcherError("All upstreams failed in multi mode")
    
    # Merge and deduplicate by market_id (prefer price events on collision)
    merged: dict[str, MarketEvent] = {}
    
    # Add Polymarket events first
    for evt in polymarket_events:
        merged[evt.market_id] = evt
    
    # Add price events (overwriting any collisions)
    for evt in price_events:
        merged[evt.market_id] = evt
    
    return list(merged.values())