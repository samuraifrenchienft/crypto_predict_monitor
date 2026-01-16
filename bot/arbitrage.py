"""
Cross-market arbitrage detection and whale-watching utilities.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Set, Tuple

from bot.models import Market, Quote


def normalize_title(title: str) -> str:
    """
    Normalize a market title for matching across platforms.
    - Lowercase
    - Remove punctuation and extra whitespace
    - Strip common words/phrases that differ across platforms
    """
    if not isinstance(title, str):
        return ""
    # Lowercase and strip
    s = title.lower().strip()
    # Remove punctuation (keep alphanum and spaces)
    s = re.sub(r"[^\w\s]", " ", s)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s)
    # Remove common noise words that differ across platforms
    noise = {
        "will", "the", "is", "to", "by", "in", "on", "at", "for", "of", "with", "as",
        "this", "that", "these", "those", "from", "up", "down", "out", "off", "over",
        "under", "again", "further", "then", "once", "here", "there", "when", "where",
        "why", "how", "all", "any", "both", "each", "few", "more", "most", "other",
        "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than",
        "too", "very", "can", "will", "just", "don", "should", "now",
    }
    tokens = [t for t in s.split() if t not in noise]
    return " ".join(tokens)


def group_by_normalized_title(markets_by_source: Dict[str, List[Market]]) -> Dict[str, List[Tuple[str, Market]]]:
    """
    Group markets by normalized title across all sources.
    Returns: {normalized_title: [(source, market), ...], ...}
    """
    groups: Dict[str, List[Tuple[str, Market]]] = {}
    for source, markets in markets_by_source.items():
        for market in markets:
            norm = normalize_title(market.title)
            groups.setdefault(norm, []).append((source, market))
    return groups


def is_new_event(market: Market, hours: int = 24) -> bool:
    """
    Determine if a market is "new" based on creation time.
    For now, we approximate by checking if we have never seen it before.
    In a real implementation, you would use market.creation_time if available.
    """
    # Placeholder: treat all markets as "new" for this demo
    # TODO: use market.created_at if API provides it
    return True


def score_arbitrage_opportunity(
    markets: List[Tuple[str, Market]],
    quotes_by_source: Dict[str, Dict[str, List[Quote]]],
    min_spread: float = 0.08,
    prioritize_new: bool = True,
    new_event_hours: int = 24,
) -> List[Dict[str, Any]]:
    """
    Score arbitrage opportunities for a group of matched markets.
    Returns a list of opportunities with spreads, signals, and clear action guidance.
    """
    opportunities = []
    # Collect mids per source
    mids_by_source: Dict[str, float] = {}
    for source, market in markets:
        quotes = quotes_by_source.get(source, {}).get(market.market_id, [])
        # Use the first quote's mid as representative (binary YES/NO)
        if quotes:
            mids_by_source[source] = quotes[0].mid
    if len(mids_by_source) < 2:
        return opportunities  # need at least two sources to compare
    # Compute pairwise spreads
    sources = list(mids_by_source.keys())
    for i in range(len(sources)):
        for j in range(i + 1, len(sources)):
            s1, s2 = sources[i], sources[j]
            mid1, mid2 = mids_by_source[s1], mids_by_source[s2]
            if mid1 is None or mid2 is None or mid1 == "" or mid2 == "":
                continue
            spread = abs(mid1 - mid2)
            if spread >= min_spread:
                # Determine if this is a new event (any market in the group is new)
                is_new = any(is_new_event(m, new_event_hours) for _, m in markets)
                priority = "high" if prioritize_new and is_new else "normal"
                
                # === CLEAR BUY SIGNAL FOR NOVICES ===
                # The cheaper platform is where you BUY YES
                # The expensive platform is where you BUY NO (or sell YES)
                if mid1 < mid2:
                    cheap_source, cheap_mid = s1, mid1
                    expensive_source, expensive_mid = s2, mid2
                else:
                    cheap_source, cheap_mid = s2, mid2
                    expensive_source, expensive_mid = s1, mid1
                
                # Calculate potential profit per $1 wagered
                # Buy YES at cheap_mid, effective NO at (1 - expensive_mid)
                # Profit = 1 - cheap_mid - (1 - expensive_mid) = expensive_mid - cheap_mid = spread
                profit_per_dollar = spread
                
                # Build human-readable action
                action = {
                    "buy_yes_at": cheap_source,
                    "buy_yes_price": round(cheap_mid, 3),
                    "buy_no_at": expensive_source,
                    "buy_no_price": round(1 - expensive_mid, 3),
                    "profit_cents": round(spread * 100, 1),
                    "signal": "🟢 BUY" if spread >= 0.10 else "🟡 WATCH",
                    "explanation": f"Buy YES on {cheap_source} at {cheap_mid:.0%}, Buy NO on {expensive_source} at {1-expensive_mid:.0%}. Potential profit: {spread*100:.1f}¢ per $1.",
                }
                
                opportunities.append({
                    "normalized_title": normalize_title(markets[0][1].title),
                    "sources": [s1, s2],
                    "mids": {s1: mid1, s2: mid2},
                    "spread": spread,
                    "priority": priority,
                    "action": action,
                    "markets": [{"source": s, "market_id": m.market_id, "title": m.title} for s, m in markets],
                })
    # Sort by spread descending, then priority
    opportunities.sort(key=lambda o: (o["priority"] == "high", o["spread"]), reverse=True)
    return opportunities


def detect_cross_market_arbitrage(
    markets_by_source: Dict[str, List[Market]],
    quotes_by_source: Dict[str, Dict[str, List[Quote]]],
    min_spread: float = 0.08,
    prioritize_new: bool = True,
    new_event_hours: int = 24,
) -> List[Dict[str, Any]]:
    """
    Detect cross-market arbitrage opportunities.
    Returns a list of opportunities sorted by spread and priority.
    """
    groups = group_by_normalized_title(markets_by_source)
    all_opportunities = []
    for norm, markets in groups.items():
        if len(markets) < 2:
            continue  # need at least two sources
        opps = score_arbitrage_opportunity(markets, quotes_by_source, min_spread, prioritize_new, new_event_hours)
        all_opportunities.extend(opps)
    # Global sort: high priority first, then by spread
    all_opportunities.sort(key=lambda o: (o["priority"] == "high", o["spread"]), reverse=True)
    return all_opportunities


# Whale-watching utilities (placeholder for now; will require platform-specific APIs)
def detect_whale_convergence(
    markets_by_source: Dict[str, List[Market]],
    whale_positions: Dict[str, List[Dict[str, Any]]],  # {platform: [{market_id, address, size, timestamp}, ...]}
    convergence_threshold: int = 2,
    time_window_hours: int = 6,
    max_market_age_hours: int = 24,
) -> List[Dict[str, Any]]:
    """
    Detect when multiple tracked wallets invest in the same new market.
    Returns a list of convergence alerts.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(hours=time_window_hours)
    alerts = []
    # Group positions by market_id across platforms
    market_to_wallets: Dict[str, List[Dict[str, Any]]] = {}
    for platform, positions in whale_positions.items():
        for pos in positions:
            # Filter by time window
            pos_time = pos.get("timestamp")
            if isinstance(pos_time, str):
                try:
                    pos_time = datetime.fromisoformat(pos_time)
                except Exception:
                    continue
            if not isinstance(pos_time, datetime) or pos_time < window_start:
                continue
            market_id = pos.get("market_id")
            if not market_id:
                continue
            market_to_wallets.setdefault(market_id, []).append({**pos, "platform": platform})
    # Detect convergence
    for market_id, wallet_list in market_to_wallets.items():
        unique_wallets = set((w["platform"], w.get("address")) for w in wallet_list)
        if len(unique_wallets) >= convergence_threshold:
            # Try to find the market title
            title = market_id
            for source, markets in markets_by_source.items():
                for m in markets:
                    if m.market_id == market_id:
                        title = m.title
                        break
            alerts.append({
                "market_id": market_id,
                "title": title,
                "converged_wallets": list(unique_wallets),
                "count": len(unique_wallets),
                "positions": wallet_list,
            })
    return alerts
