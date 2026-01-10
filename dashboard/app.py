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
from bot.adapters.polymarket import PolymarketAdapter
from bot.models import Market, Quote
from bot.arbitrage import detect_cross_market_arbitrage
from bot.whale_watcher import fetch_all_whale_positions, detect_convergence


app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Global cache for market data
market_cache: Dict[str, List[Dict[str, Any]]] = {}
last_update: Dict[str, datetime] = {}


def serialize_market(market: Market, outcomes: List[Any], quotes: List[Quote]) -> Dict[str, Any]:
    """Serialize market and quotes for JSON response."""
    outcome_name_by_id: Dict[str, str] = {}
    for o in outcomes or []:
        try:
            oid = getattr(o, "outcome_id", None)
            oname = getattr(o, "name", None)
            if oid is not None and oname is not None:
                outcome_name_by_id[str(oid)] = str(oname)
        except Exception:
            continue

    return {
        "source": market.source,
        "market_id": market.market_id,
        "title": market.title,
        "url": market.url,
        "outcomes": [
            {
                "outcome_id": q.outcome_id,
                "name": outcome_name_by_id.get(str(q.outcome_id), str(q.outcome_id)),
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
                
                # Only filter out markets with absolutely no price data (no bid, ask, or mid)
                has_any_price = any(
                    q.bid is not None or q.ask is not None or q.mid is not None 
                    for q in quotes
                )
                if not has_any_price and quotes:
                    print(f"{adapter_name}: Skipping {market.market_id} - no price or probability data")
                    continue
                
                market_data.append(serialize_market(market, outcomes, quotes))
            except Exception as e:
                print(f"Error fetching quotes for {market.market_id}: {e}")
                # Skip markets with errors
                continue
        
        print(f"{adapter_name}: Returning {len(market_data)} markets with price data")
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
    
    total_events = sum(len(markets) for markets in market_cache.values())
    sources = list(market_cache.keys())
    active_sources = sum(1 for _, markets in market_cache.items() if markets)

    return jsonify({
        "markets": market_cache,
        "sources": sources,
        "active_sources": active_sources,
        "last_update": {
            source: time.isoformat() if time else None
            for source, time in last_update.items()
        },
        # Backwards compatible field name used by the frontend
        "total_markets": total_events,
        # Prefer this naming going forward (each card is an event/market)
        "total_events": total_events,
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
    cfg = load_config()
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
    
    # Cross-market arbitrage summary
    if cfg.arbitrage.mode == "cross_market" and len(market_cache) > 1:
        # Convert cached dicts back to Market/Quote models for detection
        markets_by_source: Dict[str, List[Market]] = {}
        quotes_by_source: Dict[str, Dict[str, List[Quote]]] = {}
        for source, markets in market_cache.items():
            markets_by_source[source] = []
            quotes_by_source[source] = {}
            for m in markets:
                market = Market(source=source, market_id=m["market_id"], title=m["title"], url=m.get("url"), outcomes=[])
                markets_by_source[source].append(market)
                quotes_by_source[source][m["market_id"]] = [
                    Quote(
                        outcome_id=o["outcome_id"],
                        bid=o["bid"],
                        ask=o["ask"],
                        mid=o["mid"],
                        spread=o["spread"],
                        bid_size=o["bid_size"],
                        ask_size=o["ask_size"],
                        ts=datetime.fromisoformat(o["timestamp"]) if o.get("timestamp") else None,
                    )
                    for o in m["outcomes"]
                ]
        opportunities = detect_cross_market_arbitrage(
            markets_by_source,
            quotes_by_source,
            min_spread=cfg.arbitrage.min_spread,
            prioritize_new=cfg.arbitrage.prioritize_new_events,
            new_event_hours=cfg.arbitrage.new_event_hours,
        )
        stats["arbitrage"] = {
            "mode": cfg.arbitrage.mode,
            "opportunities": len(opportunities),
            "high_priority": sum(1 for o in opportunities if o.get("priority") == "high"),
            "top_spreads": [o["spread"] for o in opportunities[:5]],
        }
    else:
        stats["arbitrage"] = {"mode": cfg.arbitrage.mode, "opportunities": 0}
    
    return jsonify(stats)


@app.route("/api/arbitrage")
def get_arbitrage():
    """Get cross-market arbitrage opportunities."""
    cfg = load_config()
    if cfg.arbitrage.mode != "cross_market":
        return jsonify({"error": "Arbitrage mode not set to cross_market"}, 400)
    if len(market_cache) < 2:
        return jsonify({"opportunities": []})
    # Reuse conversion logic from /api/stats
    markets_by_source: Dict[str, List[Market]] = {}
    quotes_by_source: Dict[str, Dict[str, List[Quote]]] = {}
    for source, markets in market_cache.items():
        markets_by_source[source] = []
        quotes_by_source[source] = {}
        for m in markets:
            market = Market(source=source, market_id=m["market_id"], title=m["title"], url=m.get("url"), outcomes=[])
            markets_by_source[source].append(market)
            quotes_by_source[source][m["market_id"]] = [
                Quote(
                    outcome_id=o["outcome_id"],
                    bid=o["bid"],
                    ask=o["ask"],
                    mid=o["mid"],
                    spread=o["spread"],
                    bid_size=o["bid_size"],
                    ask_size=o["ask_size"],
                    ts=datetime.fromisoformat(o["timestamp"]) if o.get("timestamp") else None,
                )
                for o in m["outcomes"]
            ]
    opportunities = detect_cross_market_arbitrage(
        markets_by_source,
        quotes_by_source,
        min_spread=cfg.arbitrage.min_spread,
        prioritize_new=cfg.arbitrage.prioritize_new_events,
        new_event_hours=cfg.arbitrage.new_event_hours,
    )
    return jsonify({"opportunities": opportunities})


@app.route("/api/whales")
def get_whale_alerts():
    """Get whale convergence alerts based on tracked wallets."""
    cfg = load_config()
    if not cfg.whale_watch.enabled:
        return jsonify({"error": "Whale watching is disabled", "alerts": []})
    
    # Load wallets from file (user-saved) or config
    wallets = load_tracked_wallets() or cfg.whale_watch.wallets
    if not wallets:
        return jsonify({"error": "No wallets configured", "alerts": []})
    
    # Fetch positions asynchronously
    loop = asyncio.new_event_loop()
    try:
        positions = loop.run_until_complete(
            fetch_all_whale_positions(wallets, cfg.whale_watch.time_window_hours)
        )
        alerts = detect_convergence(positions, cfg.whale_watch.convergence_threshold)
        
        # Add signal clarity for novices
        for alert in alerts:
            if alert.get("consensus") == "YES":
                alert["signal"] = "🟢 WHALES BULLISH"
                alert["action"] = f"Multiple tracked wallets are betting YES on this market"
            elif alert.get("consensus") == "NO":
                alert["signal"] = "🔴 WHALES BEARISH"
                alert["action"] = f"Multiple tracked wallets are betting NO on this market"
            else:
                alert["signal"] = "🟡 WHALES SPLIT"
                alert["action"] = f"Tracked wallets disagree on direction"
        
        return jsonify({
            "alerts": alerts,
            "wallets_tracked": len(wallets),
            "time_window_hours": cfg.whale_watch.time_window_hours,
        })
    except Exception as e:
        return jsonify({"error": str(e), "alerts": []}), 500
    finally:
        loop.close()


# Wallet tracking file path
WALLETS_FILE = Path(__file__).parent.parent / "data" / "tracked_wallets.json"


def load_tracked_wallets() -> List[Dict[str, str]]:
    """Load tracked wallets from file."""
    if WALLETS_FILE.exists():
        try:
            return json.loads(WALLETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def save_tracked_wallets(wallets: List[Dict[str, str]]) -> bool:
    """Save tracked wallets to file."""
    try:
        WALLETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        WALLETS_FILE.write_text(json.dumps(wallets, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"Failed to save wallets: {e}")
        return False


@app.route("/api/wallets", methods=["GET"])
def get_wallets():
    """Get tracked wallets."""
    wallets = load_tracked_wallets()
    return jsonify({"wallets": wallets})


@app.route("/api/wallets", methods=["POST"])
def set_wallets():
    """Save tracked wallets."""
    data = request.get_json()
    wallets = data.get("wallets", [])
    
    # Validate: max 4 wallets
    if len(wallets) > 4:
        return jsonify({"error": "Maximum 4 wallets allowed"}), 400
    
    # Validate each wallet has required fields
    for w in wallets:
        if not w.get("address") or not w.get("platform"):
            return jsonify({"error": "Each wallet must have address and platform"}), 400
    
    if save_tracked_wallets(wallets):
        return jsonify({"success": True, "wallets": wallets})
    else:
        return jsonify({"error": "Failed to save wallets"}), 500


if __name__ == "__main__":
    # Run Flask app
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
