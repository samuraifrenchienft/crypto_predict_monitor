"""
Flask web application for the crypto prediction monitor dashboard.
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import load_config
from bot.adapters.manifold import ManifoldAdapter
from bot.adapters.kalshi import KalshiAdapter
from bot.adapters.metaculus import MetaculusAdapter
from bot.adapters.polymarket import PolymarketAdapter
from bot.models import Market, Quote


app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Global cache for market data
market_cache: Dict[str, List[Dict[str, Any]]] = {}
last_update: Dict[str, datetime] = {}


def serialize_market(market: Market, quotes: List[Quote]) -> Dict[str, Any]:
    """Serialize market and quotes for JSON response."""
    return {
        "source": market.source,
        "market_id": market.market_id,
        "title": market.title,
        "url": market.url,
        "outcomes": [
            {
                "outcome_id": q.outcome_id,
                "name": q.outcome_id.split("_")[-1],  # Extract YES/NO
                "bid": q.bid,
                "ask": q.ask,
                "mid": q.mid,
                "spread": q.spread,
                "bid_size": q.bid_size,
                "ask_size": q.ask_size,
                "timestamp": q.ts.isoformat() if q.ts else None,
            }
            for q in quotes
        ],
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


async def fetch_market_data(adapter_name: str, adapter) -> List[Dict[str, Any]]:
    """Fetch market data from an adapter."""
    try:
        markets = await adapter.list_active_markets()
        print(f"{adapter_name}: Found {len(markets)} markets")
        markets = markets[:10]  # Limit to 10 markets per adapter
        
        market_data = []
        for market in markets:
            try:
                outcomes = await adapter.list_outcomes(market)
                quotes = await adapter.get_quotes(market, outcomes)
                print(f"{adapter_name}: Market {market.market_id} has {len(quotes)} quotes")
                market_data.append(serialize_market(market, quotes))
            except Exception as e:
                print(f"Error fetching quotes for {market.market_id}: {e}")
                # Add market without quotes
                market_data.append(serialize_market(market, []))
        
        print(f"{adapter_name}: Returning {len(market_data)} markets")
        return market_data
    except Exception as e:
        print(f"Error fetching data from {adapter_name}: {e}")
        return []


async def update_all_markets():
    """Update market data from all enabled adapters."""
    try:
        cfg = load_config()
        adapters = []
        
        # Create adapters based on config
        if cfg.polymarket.enabled:
            adapters.append(("polymarket", PolymarketAdapter(
                gamma_base_url=cfg.polymarket.gamma_base_url,
                clob_base_url=cfg.polymarket.clob_base_url,
                data_base_url=cfg.polymarket.data_base_url,
                events_limit=cfg.polymarket.events_limit,
            )))
        
        if cfg.limitless.enabled:
            try:
                from bot.adapters.limitless import LimitlessAdapter

                adapters.append(("limitless", LimitlessAdapter(
                    base_url=cfg.limitless.base_url,
                )))
            except ModuleNotFoundError as e:
                print(f"limitless disabled at runtime (missing dependency): {e}")

        if cfg.kalshi.enabled:
            from bot.rate_limit import RateLimitConfig
            adapters.append(("kalshi", KalshiAdapter(
                base_url=cfg.kalshi.base_url,
                markets_limit=cfg.kalshi.markets_limit,
                rate_limit_config=RateLimitConfig(
                    requests_per_second=cfg.kalshi.requests_per_second,
                    requests_per_minute=cfg.kalshi.requests_per_minute,
                    burst_size=cfg.kalshi.burst_size,
                ),
            )))
        
        if cfg.manifold.enabled:
            from bot.rate_limit import RateLimitConfig
            adapters.append(("manifold", ManifoldAdapter(
                base_url=cfg.manifold.base_url,
                markets_limit=cfg.manifold.markets_limit,
                rate_limit_config=RateLimitConfig(
                    requests_per_second=cfg.manifold.requests_per_second,
                    requests_per_minute=cfg.manifold.requests_per_minute,
                    burst_size=cfg.manifold.burst_size,
                ),
            )))
        
        if cfg.metaculus.enabled:
            from bot.rate_limit import RateLimitConfig
            print(f"Metaculus enabled in config, creating adapter...")
            adapters.append(("metaculus", MetaculusAdapter(
                base_url=cfg.metaculus.base_url,
                questions_limit=cfg.metaculus.questions_limit,
                rate_limit_config=RateLimitConfig(
                    requests_per_second=cfg.metaculus.requests_per_second,
                    requests_per_minute=cfg.metaculus.requests_per_minute,
                    burst_size=cfg.metaculus.burst_size,
                ),
            )))
            print(f"Metaculus adapter created")
        
        # Fetch data from all adapters
        for adapter_name, adapter in adapters:
            print(f"Fetching data from {adapter_name}...")
            try:
                data = await fetch_market_data(adapter_name, adapter)
                market_cache[adapter_name] = data
                last_update[adapter_name] = datetime.now(timezone.utc)
                print(f"Fetched {len(data)} markets from {adapter_name}")
            except Exception as e:
                print(f"Error fetching from {adapter_name}: {e}")
                # Add empty data to show the adapter is configured
                market_cache[adapter_name] = []
                last_update[adapter_name] = datetime.now(timezone.utc)
                
    except Exception as e:
        print(f"Error updating markets: {e}")
        # Add demo data if configuration fails
        market_cache["demo"] = [
            {
                "source": "demo",
                "market_id": "demo-1",
                "title": "Demo Market - Configuration Needed",
                "url": "#",
                "outcomes": [
                    {"outcome_id": "demo-1_YES", "name": "YES", "bid": 0.45, "ask": 0.55, "mid": 0.50, "spread": 0.10, "bid_size": 100, "ask_size": 100, "timestamp": datetime.now(timezone.utc).isoformat()},
                    {"outcome_id": "demo-1_NO", "name": "NO", "bid": 0.45, "ask": 0.55, "mid": 0.50, "spread": 0.10, "bid_size": 100, "ask_size": 100, "timestamp": datetime.now(timezone.utc).isoformat()}
                ],
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
        ]
        last_update["demo"] = datetime.now(timezone.utc)


@app.route("/")
def index():
    """Main dashboard page."""
    try:
        return render_template("index.html")
    except Exception as e:
        return f"<h1>Template Error</h1><p>Error: {str(e)}</p><p>Check that templates/index.html exists</p>", 500


@app.route("/test")
def test():
    """Test endpoint to verify app is running."""
    return jsonify({
        "status": "ok",
        "message": "Dashboard is running",
        "time": datetime.now(timezone.utc).isoformat()
    })


@app.route("/api/markets")
def get_markets():
    """Get all market data."""
    # Trigger update if cache is empty or old
    if not market_cache or any(
        datetime.now(timezone.utc) - last_update.get(source, datetime.min) > timedelta(minutes=5)
        for source in market_cache
    ):
        # Run async update in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(update_all_markets())
        finally:
            loop.close()
    
    return jsonify({
        "markets": market_cache,
        "last_update": {
            source: time.isoformat() if time else None
            for source, time in last_update.items()
        },
        "total_markets": sum(len(markets) for markets in market_cache.values()),
    })


@app.route("/api/markets/<source>")
def get_markets_by_source(source: str):
    """Get market data from a specific source."""
    if source not in market_cache:
        return jsonify({"error": f"Source '{source}' not found"}), 404
    
    return jsonify({
        "markets": market_cache[source],
        "last_update": last_update[source].isoformat() if source in last_update else None,
        "total": len(market_cache[source]),
    })


@app.route("/api/refresh")
def refresh_markets():
    """Force refresh of all market data."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(update_all_markets())
        return jsonify({
            "status": "success",
            "message": "Market data refreshed",
            "total_markets": sum(len(markets) for markets in market_cache.values()),
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500
    finally:
        loop.close()


@app.route("/api/stats")
def get_stats():
    """Get statistics about the markets."""
    stats = {
        "total_markets": sum(len(markets) for markets in market_cache.values()),
        "sources": list(market_cache.keys()),
        "last_updates": {
            source: time.isoformat() if time else None
            for source, time in last_update.items()
        },
    }
    
    # Calculate additional stats
    all_quotes = []
    for markets in market_cache.values():
        for market in markets:
            all_quotes.extend(market["outcomes"])
    
    stats["total_outcomes"] = len(all_quotes)
    stats["markets_with_quotes"] = sum(
        1 for markets in market_cache.values()
        for market in markets
        if any(outcome["mid"] is not None for outcome in market["outcomes"])
    )
    
    return jsonify(stats)


if __name__ == "__main__":
    # Run Flask app
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
