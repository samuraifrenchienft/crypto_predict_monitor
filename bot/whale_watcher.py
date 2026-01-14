"""
Whale watcher: fetch Polymarket trades from tracked wallets and detect convergence.
Polymarket-only implementation.
"""

from __future__ import annotations

import httpx
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional


async def fetch_polymarket_wallet_trades(
    wallet_address: str,
    limit: int = 50,
    after_time: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Fetch recent trades for a Polymarket wallet.
    Note: This requires the CLOB API which may have rate limits.
    
    Returns list of trades with:
    - market_id (token_id or condition_id)
    - side (BUY/SELL)
    - size
    - price
    - timestamp
    """
    # Polymarket CLOB trade history endpoint
    url = f"https://clob.polymarket.com/trades"
    params = {
        "maker": wallet_address,
        "limit": str(limit),
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        print(f"[whale_watcher] Polymarket trade fetch failed: {e}")
        return []
    
    trades = []
    for t in data if isinstance(data, list) else data.get("trades", []):
        ts_str = t.get("timestamp") or t.get("created_at")
        ts = None
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            except Exception:
                pass
        
        if after_time and ts and ts < after_time:
            continue
        
        trades.append({
            "platform": "polymarket",
            "address": wallet_address,
            "market_id": t.get("asset_id") or t.get("token_id"),
            "side": t.get("side"),
            "size": t.get("size"),
            "price": t.get("price"),
            "timestamp": ts.isoformat() if ts else None,
        })
    
    return trades


async def fetch_all_whale_positions(
    wallets: List[Dict[str, str]],
    time_window_hours: int = 6,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch recent Polymarket positions for all tracked wallets.
    
    wallets: list of {"address": ..., "platform": "polymarket", "label": ...}
    Returns: {"polymarket": [positions...]}
    """
    after_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
    positions: List[Dict[str, Any]] = []
    
    for w in wallets:
        platform = w.get("platform", "").lower()
        address = w.get("address", "")
        label = w.get("label", address)
        
        if not address:
            continue
        
        # Only process Polymarket wallets
        if platform != "polymarket":
            print(f"[whale_watcher] Skipping non-Polymarket wallet: {label} on {platform}")
            continue
        
        try:
            trades = await fetch_polymarket_wallet_trades(address, limit=50, after_time=after_time)
            for t in trades:
                t["label"] = label
            positions.extend(trades)
        except Exception as e:
            print(f"[whale_watcher] Failed to fetch for {label} on {platform}: {e}")
    
    return {"polymarket": positions}


def detect_convergence(
    positions_by_platform: Dict[str, List[Dict[str, Any]]],
    convergence_threshold: int = 2,
) -> List[Dict[str, Any]]:
    """
    Detect when multiple Polymarket wallets have traded on the same market.
    Returns list of convergence alerts.
    """
    # Only look at Polymarket positions
    polymarket_positions = positions_by_platform.get("polymarket", [])
    
    # Group by market_id
    market_to_wallets: Dict[str, List[Dict[str, Any]]] = {}
    for pos in polymarket_positions:
        market_id = pos.get("market_id")
        if not market_id:
            continue
        market_to_wallets.setdefault(market_id, []).append(pos)
    
    alerts = []
    for market_id, wallet_list in market_to_wallets.items():
        # Count unique wallets (by address)
        unique_wallets = set(w.get("address") for w in wallet_list)
        if len(unique_wallets) >= convergence_threshold:
            # Determine consensus direction (if any)
            sides = [w.get("side") for w in wallet_list]
            buy_count = sum(1 for s in sides if s == "BUY")
            sell_count = sum(1 for s in sides if s == "SELL")
            consensus = None
            if buy_count > sell_count:
                consensus = "YES"
            elif sell_count > buy_count:
                consensus = "NO"
            
            alerts.append({
                "market_id": market_id,
                "wallets": [{"label": w.get("label"), "platform": "polymarket", "outcome": w.get("side")} for w in wallet_list],
                "count": len(unique_wallets),
                "consensus": consensus,
                "positions": wallet_list,
            })
    
    return alerts
