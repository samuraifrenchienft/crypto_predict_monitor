"""
Flask web application for the crypto prediction monitor dashboard.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import math
import os
import sys
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List

import httpx
from flask import Flask, g, render_template, jsonify, request, redirect, send_file, session
from flask_cors import CORS
from sqlalchemy import func
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import load_config
from bot.adapters.manifold import ManifoldAdapter
from bot.adapters.azuro import AzuroAdapter
from bot.adapters.polymarket import PolymarketAdapter
from bot.models import Market, Quote
from bot.arbitrage import detect_cross_market_arbitrage
from bot.alerts.discord import DiscordAlerter
from bot.whale_watcher import fetch_all_whale_positions, detect_convergence
from utils.alert_manager import ArbitrageAlertManager, create_alert_from_opportunity
import secrets
import hashlib
from datetime import datetime, timezone
from web3 import Web3

from dashboard.db import close_session, get_session, engine, test_connection, get_connection_info
from dashboard.db_logging import get_database_health, logged_database_session
from dashboard.models import (
    Alert,
    AlertStatus,
    Base,
    MonitorStatus,
    PointsEvent,
    ReferralConversion,
    ReferralVisit,
    TradeExecution,
    TradeMonitor,
    User,
    UserAlertState,
    UserGrowth,
    UserTier,
)
from dashboard.auth import (
    apply_tier_rules,
    discord_callback_async,
    discord_login,
    get_current_user,
    logout,
    require_tier,
    wallet_challenge,
    wallet_verify,
)


import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

app.secret_key = os.environ.get("FLASK_SECRET_KEY") or os.urandom(32)

# Initialize database with proper error handling
try:
    logger.info("Initializing database...")
    
    # Test database connection
    if test_connection():
        logger.info("Database connection test passed")
    else:
        logger.error("Database connection test failed")
    
    # Log connection info
    conn_info = get_connection_info()
    logger.info(f"Database connection info: {conn_info}")
    
    # Create tables
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
    
except Exception as e:
    logger.error(f"Database initialization failed: {e}")
    import traceback
    traceback.print_exc()


@app.before_request
def _open_db_session():
    g.db = get_session()

    try:
        user = get_current_user(g.db)
        if user is not None:
            apply_tier_rules(user)
            g.user_growth = _ensure_user_growth(g.db, user)
            _maybe_apply_pending_referral(g.db, user)
            g.db.commit()
    except Exception:
        # Fail-safe: never block request due to auth/db issues
        return


@app.teardown_request
def _close_db_session(_exc):
    try:
        db = getattr(g, "db", None)
        if db is not None:
            db.close()
    finally:
        close_session()

# Global cache for market data (cleared for fresh restart)
market_cache: Dict[str, List[Dict[str, Any]]] = {}
last_update: Dict[str, datetime] = {}
_cache_lock = threading.Lock()
_background_started = False

# Clear cache on startup for fresh data
print("Clearing market cache for fresh restart...")
market_cache.clear()
last_update.clear()


def _run_async(coro):
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None

    if running and running.is_running():
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(coro)
        finally:
            try:
                loop.close()
            finally:
                asyncio.set_event_loop(running)

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    finally:
        loop.close()


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
    print("DEBUG: update_all_markets starting")
    try:
        cfg = load_config()
        print(f"DEBUG: Config loaded. Azuro enabled: {cfg.azuro.enabled}")
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

        if cfg.azuro.enabled:
            print("DEBUG: Adding Azuro adapter")
            adapters.append(("azuro", AzuroAdapter(
                graphql_base_url=cfg.azuro.graphql_base_url,
                subgraph_base_url=cfg.azuro.subgraph_base_url,
                rest_base_url=cfg.azuro.rest_base_url,
                markets_limit=cfg.azuro.markets_limit,
                use_fallback=cfg.azuro.use_fallback,
            )))
        else:
            print("DEBUG: Azuro not enabled in config")
        
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
        
        print(f"DEBUG: Adapters configured: {[name for name, _ in adapters]}")
        # Fetch data from all adapters
        for adapter_name, adapter in adapters:
            print(f"Fetching data from {adapter_name}...")
            try:
                data = await fetch_market_data(adapter_name, adapter)
                print(f"DEBUG: Fetched {len(data)} markets from {adapter_name}")
                with _cache_lock:
                    market_cache[adapter_name] = data
                    last_update[adapter_name] = datetime.now(timezone.utc)
                print(f"Fetched {len(data)} markets from {adapter_name}")
            except Exception as e:
                print(f"Error fetching from {adapter_name}: {e}")
                import traceback
                traceback.print_exc()
                # Add empty data to show the adapter is configured
                with _cache_lock:
                    market_cache[adapter_name] = []
                    last_update[adapter_name] = datetime.now(timezone.utc)
                
    except Exception as e:
        print(f"Error updating markets: {e}")
        # NO DEMO DATA - Show error state instead of fake data
        with _cache_lock:
            market_cache[adapter_name] = []
            last_update[adapter_name] = datetime.now(timezone.utc)


def _build_quotes_for_arbitrage() -> tuple[Dict[str, List[Market]], Dict[str, Dict[str, List[Quote]]]]:
    markets_by_source: Dict[str, List[Market]] = {}
    quotes_by_source: Dict[str, Dict[str, List[Quote]]] = {}

    with _cache_lock:
        cache_snapshot = json.loads(json.dumps(market_cache))

    for source, markets in cache_snapshot.items():
        markets_by_source[source] = []
        quotes_by_source[source] = {}
        for m in markets or []:
            market = Market(source=source, market_id=m["market_id"], title=m["title"], url=m.get("url"), outcomes=[])
            markets_by_source[source].append(market)
            quotes_by_source[source][m["market_id"]] = [
                Quote(
                    outcome_id=o["outcome_id"],
                    bid=o.get("bid"),
                    ask=o.get("ask"),
                    mid=o.get("mid"),
                    spread=o.get("spread"),
                    bid_size=o.get("bid_size"),
                    ask_size=o.get("ask_size"),
                    ts=datetime.fromisoformat(o["timestamp"]) if o.get("timestamp") else None,
                )
                for o in (m.get("outcomes") or [])
            ]

    return markets_by_source, quotes_by_source


async def _arbitrage_alert_loop() -> None:
    cfg = load_config()
    alerter = DiscordAlerter(
        webhook_url=cfg.discord_health_webhook_url,  # Use health webhook for dashboard changes
        enabled=cfg.discord.enabled,
        min_seconds_between_same_alert=cfg.discord.min_seconds_between_same_alert,
    )

    min_profit = float(os.environ.get("ALERT_MIN_PROFIT", "0.01"))

    while True:
        try:
            # Discord health check
            if cfg.discord_health_webhook_url:
                await alerter.health_check()
            
            # Refresh referrals
            try:
                from dashboard.db import get_session
                from dashboard.models import ReferralVisit
                with get_session() as session:
                    from sqlalchemy import select
                    visits = session.execute(select(ReferralVisit)).scalars().all()
                    print(f"[referrals] tracking {len(visits)} visits")
            except Exception as e:
                print(f"[referrals] error: {e}")

            if cfg.arbitrage.mode == "cross_market":
                markets_by_source, quotes_by_source = _build_quotes_for_arbitrage()
                opportunities = detect_cross_market_arbitrage(
                    markets_by_source,
                    quotes_by_source,
                    min_spread=cfg.thresholds.min_spread,  # Now uses updated config (1.5%)
                    prioritize_new=cfg.arbitrage.prioritize_new_events,
                    new_event_hours=cfg.arbitrage.new_event_hours,
                )

                for opp in opportunities[:3]:
                    # Create alert in database for P&L tracking
                    await create_alert_from_opportunity(opp, "system_user")
                    
                    # Send Discord notification
                    title = opp.get("normalized_title", "Arbitrage Opportunity")
                    markets = opp.get("markets", [])
                    if len(markets) >= 2:
                        buy_yes_at = markets[0].get("source", "unknown")
                        buy_no_at = markets[1].get("source", "unknown")
                        buy_yes_price = markets[0].get("mid", 0)
                        buy_no_price = markets[1].get("mid", 0)
                        profit_cents = int(opp.get("spread", 0) * 100)

                        key = f"arb:{opp.get('normalized_title')}:{buy_yes_at}:{buy_no_at}"
                        content = (
                            f"🎯 Arbitrage {profit_cents}¢\n"
                            f"{title}\n"
                            f"BUY YES on {buy_yes_at} @ {buy_yes_price}\n"
                            f"BUY NO on {buy_no_at} @ {buy_no_price}"
                        )
                        await alerter.send(key=key, content=content)

        except Exception as e:
            print(f"[arbitrage_alert_loop] error: {e}")

        await asyncio.sleep(cfg.bot.poll_interval_seconds)


def _start_background_tasks() -> None:
    global _background_started
    if _background_started:
        return
    _background_started = True

    def runner() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_arbitrage_alert_loop())
        finally:
            loop.close()

    t = threading.Thread(target=runner, daemon=True)
    t.start()


def _classic_arb_opportunities_from_cache() -> List[Dict[str, Any]]:
    opportunities: List[Dict[str, Any]] = []

    with _cache_lock:
        snapshot = json.loads(json.dumps(market_cache))

    for source in ("polymarket", "azuro"):
        for m in snapshot.get(source, []) or []:
            outcomes = m.get("outcomes") or []
            yes = next((o for o in outcomes if str(o.get("name")).upper() == "YES"), None)
            no = next((o for o in outcomes if str(o.get("name")).upper() == "NO"), None)

            if not yes or not no:
                continue

            yes_ask = yes.get("ask")
            no_ask = no.get("ask")
            if yes_ask is None or no_ask is None:
                continue

            try:
                yes_ask_f = float(yes_ask)
                no_ask_f = float(no_ask)
            except Exception:
                continue

            sum_price = yes_ask_f + no_ask_f
            if sum_price >= 1.0:
                continue

            profit_est = 1.0 - sum_price

            opportunities.append(
                {
                    "source": source,
                    "market_id": m.get("market_id"),
                    "question": m.get("title"),
                    "market_link": m.get("url"),
                    "yes_price": yes_ask_f,
                    "no_price": no_ask_f,
                    "sum_price": sum_price,
                    "profit_est": profit_est,
                }
            )

    opportunities.sort(key=lambda x: float(x.get("profit_est") or 0.0), reverse=True)
    return opportunities


def _tier_status_label(user: User) -> str:
    g_row = getattr(g, "user_growth", None)
    points = None
    if g_row is not None:
        try:
            points = int(getattr(g_row, "points_earned", 0) or 0)
        except Exception:
            points = None
    if points is None:
        try:
            gr = g.db.get(UserGrowth, user.id)
            points = int(gr.points_earned or 0) if gr is not None else 0
        except Exception:
            points = 0
    return _points_tier_label(int(points or 0))


def _points_tier_label(points: int) -> str:
    p = int(points or 0)
    if p >= 25:
        return "partner"
    if p >= 15:
        return "oni"
    if p >= 10:
        return "samurai"
    if p >= 5:
        return "ronin"
    return "recruit"


def _obfuscate_wallet(addr: Optional[str]) -> Optional[str]:
    if not addr:
        return None
    a = str(addr).strip()
    if len(a) <= 12:
        return a
    return f"{a[:6]}...{a[-4:]}"


def _ensure_user_growth(db, user: User) -> UserGrowth:
    g_row = db.get(UserGrowth, user.id)
    if g_row is None:
        g_row = UserGrowth(user_id=user.id)
        db.add(g_row)
        db.flush()
    return g_row


def _award_points(
    db,
    user_id: int,
    *,
    event_key: str,
    event_type: str,
    points: int,
    related_user_id: Optional[int] = None,
    related_referral_conversion_id: Optional[int] = None,
) -> bool:
    if not event_key:
        return False

    existing = db.query(PointsEvent).filter(PointsEvent.event_key == event_key).first()
    if existing is not None:
        return False

    pe = PointsEvent(
        user_id=int(user_id),
        event_key=str(event_key),
        event_type=str(event_type),
        points=int(points),
        related_user_id=int(related_user_id) if related_user_id is not None else None,
        related_referral_conversion_id=int(related_referral_conversion_id) if related_referral_conversion_id is not None else None,
    )
    db.add(pe)

    u_growth = db.get(UserGrowth, int(user_id))
    if u_growth is None:
        u_growth = UserGrowth(user_id=int(user_id))
        db.add(u_growth)
        db.flush()

    u_growth.points_earned = int(u_growth.points_earned or 0) + int(points)
    return True


def _hash_ip(ip: Optional[str]) -> Optional[str]:
    if not ip:
        return None
    raw = f"{ip}|{app.secret_key}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _maybe_apply_pending_referral(db, user: User) -> None:
    code = session.get("pending_referral_code")
    if not isinstance(code, str) or not code.strip():
        return

    g_row = _ensure_user_growth(db, user)
    if g_row.referred_by_user_id is not None:
        session.pop("pending_referral_code", None)
        return

    ref = db.query(UserGrowth).filter(UserGrowth.referral_code == code.strip()).first()
    if ref is None:
        session.pop("pending_referral_code", None)
        return
    if int(ref.user_id) == int(user.id):
        session.pop("pending_referral_code", None)
        return

    g_row.referred_by_user_id = int(ref.user_id)
    g_row.referred_at = datetime.now(timezone.utc)

    event_key = f"ref_signup:{int(ref.user_id)}:{int(user.id)}"
    _award_points(db, int(ref.user_id), event_key=event_key, event_type="referral_signup", points=5, related_user_id=int(user.id))

    session.pop("pending_referral_code", None)


def _award_active_referral_points_due(db) -> int:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30)
    due = (
        db.query(ReferralConversion)
        .filter(ReferralConversion.converted_at <= cutoff)
        .order_by(ReferralConversion.converted_at.asc())
        .limit(200)
        .all()
    )

    awarded = 0
    for conv in due:
        referred = db.get(User, int(conv.referred_user_id))
        if referred is None:
            continue
        apply_tier_rules(referred, now=now)
        if not referred.subscription_active:
            continue
        if referred.user_tier not in {UserTier.premium, UserTier.pro}:
            continue

        event_key = f"ref_active_30d:{int(conv.id)}"
        ok = _award_points(
            db,
            int(conv.referrer_user_id),
            event_key=event_key,
            event_type="referral_active_30d",
            points=5,
            related_user_id=int(conv.referred_user_id),
            related_referral_conversion_id=int(conv.id),
        )
        if ok:
            awarded += 1

    return awarded


def _env_admin_key() -> Optional[str]:
    v = os.environ.get("ADMIN_API_KEY")
    if not isinstance(v, str):
        return None
    v = v.strip()
    return v or None


def _record_referral_conversion_if_applicable(db, referred_user: User, old_tier: UserTier, new_tier: UserTier) -> None:
    if old_tier == new_tier:
        return
    if new_tier not in {UserTier.premium, UserTier.pro}:
        return

    g_row = db.get(UserGrowth, referred_user.id)
    if g_row is None or g_row.referred_by_user_id is None:
        return

    referrer_id = int(g_row.referred_by_user_id)
    existing = (
        db.query(ReferralConversion)
        .filter(ReferralConversion.referrer_user_id == referrer_id)
        .filter(ReferralConversion.referred_user_id == int(referred_user.id))
        .filter(ReferralConversion.to_tier == new_tier.value)
        .first()
    )
    if existing is not None:
        return

    points = 25 if new_tier == UserTier.pro else 15
    commission = 0.0

    conv = ReferralConversion(
        referrer_user_id=referrer_id,
        referred_user_id=int(referred_user.id),
        from_tier=old_tier.value,
        to_tier=new_tier.value,
        points_awarded=int(points),
        commission_awarded=float(commission),
    )
    db.add(conv)
    db.flush()

    referrer_growth = db.get(UserGrowth, referrer_id)
    if referrer_growth is None:
        referrer_growth = UserGrowth(user_id=referrer_id)
        db.add(referrer_growth)
        db.flush()

    event_key = f"ref_convert:{referrer_id}:{int(referred_user.id)}:{new_tier.value}"
    _award_points(
        db,
        referrer_id,
        event_key=event_key,
        event_type="referral_conversion",
        points=int(points),
        related_user_id=int(referred_user.id),
        related_referral_conversion_id=int(conv.id) if getattr(conv, "id", None) is not None else None,
    )
    referrer_growth.commission_earned = float(referrer_growth.commission_earned or 0.0) + float(commission)


def _market_bids_from_cache(source: str, market_id: str) -> Dict[str, float] | None:
    with _cache_lock:
        snapshot = json.loads(json.dumps(market_cache))

    for m in snapshot.get(source, []) or []:
        if str(m.get("market_id") or "") != str(market_id):
            continue
        outcomes = m.get("outcomes") or []
        yes = next((o for o in outcomes if str(o.get("name")).upper() == "YES"), None)
        no = next((o for o in outcomes if str(o.get("name")).upper() == "NO"), None)
        if not yes or not no:
            return None
        yb = yes.get("bid")
        nb = no.get("bid")
        if yb is None or nb is None:
            return None
        try:
            return {"yes_bid": float(yb), "no_bid": float(nb)}
        except Exception:
            return None
    return None


def _finalize_due_trade_monitors() -> int:
    db = get_session()
    try:
        now = datetime.now(timezone.utc)
        due = (
            db.query(TradeMonitor)
            .filter(TradeMonitor.status == MonitorStatus.active)
            .filter(TradeMonitor.ends_at <= now)
            .order_by(TradeMonitor.ends_at.asc())
            .limit(100)
            .all()
        )

        finalized = 0
        for mon in due:
            bids = _market_bids_from_cache(mon.source, mon.market_id)
            exit_proceeds = None
            pnl = None

            if bids and mon.entry_cost is not None:
                exit_proceeds = float(bids["yes_bid"]) + float(bids["no_bid"])
                pnl = float(exit_proceeds) - float(mon.entry_cost)

            ex = TradeExecution(
                user_id=mon.user_id,
                alert_id=mon.alert_id,
                source=mon.source,
                market_id=mon.market_id,
                market_name=mon.market_name,
                entry_cost=mon.entry_cost,
                exit_proceeds=exit_proceeds,
                pnl=pnl,
                executed_at=now,
            )

            user = db.get(User, mon.user_id)
            if user is not None:
                ex.wallet_address = user.wallet_address

            db.add(ex)
            mon.status = MonitorStatus.finalized
            mon.finalized_at = now
            finalized += 1

        db.commit()
        return finalized
    finally:
        db.close()


def _should_queue_for_user(user: User, db, opp: Dict[str, Any]) -> bool:
    # Premium/Pro: queue everything.
    if user.user_tier in {UserTier.premium, UserTier.pro} and user.subscription_active:
        return True

    # Free (including trial): queue only 1st, 3rd, 5th... detections.
    state = db.get(UserAlertState, user.id)
    if state is None:
        state = UserAlertState(user_id=user.id, counter=0)
        db.add(state)
        db.flush()

    state.counter = int(state.counter or 0) + 1
    return (state.counter % 2) == 1


def _enqueue_classic_arbs(min_profit: float) -> int:
    db = get_session()
    try:
        opportunities = _classic_arb_opportunities_from_cache()
        if not opportunities:
            return 0

        users = db.query(User).filter(User.discord_id.isnot(None)).all()
        now = datetime.now(timezone.utc)

        created = 0
        for user in users:
            apply_tier_rules(user, now=now)

            for opp in opportunities[:10]:
                profit_est = float(opp.get("profit_est") or 0.0)
                if profit_est < min_profit:
                    continue

                market_id = str(opp.get("market_id") or "")
                source = str(opp.get("source") or "")
                yes_price = float(opp.get("yes_price") or 0.0)
                no_price = float(opp.get("no_price") or 0.0)
                minute_bucket = now.strftime("%Y%m%d%H%M")
                raw = f"{user.id}:{source}:{market_id}:{minute_bucket}:{yes_price:.4f}:{no_price:.4f}".encode("utf-8")
                alert_id = hashlib.sha256(raw).hexdigest()[:32]

                if db.query(Alert).filter(Alert.alert_id == alert_id).first() is not None:
                    continue

                if not _should_queue_for_user(user, db, opp):
                    continue

                a = Alert(
                    user_id=user.id,
                    alert_id=alert_id,
                    source=source,
                    market_id=market_id,
                    question=str(opp.get("question") or market_id),
                    market_link=opp.get("market_link"),
                    yes_price=float(opp.get("yes_price") or 0.0),
                    no_price=float(opp.get("no_price") or 0.0),
                    sum_price=float(opp.get("sum_price") or 0.0),
                    profit_est=profit_est,
                    status=AlertStatus.queued,
                    created_at=now,
                )
                db.add(a)
                created += 1

        db.commit()
        return created
    finally:
        db.close()


def _discord_dm(bot_token: str, recipient_id: str, content: str) -> bool:
    if not bot_token:
        return False

    headers = {
        "Authorization": f"Bot {bot_token}",
        "Content-Type": "application/json",
    }

    try:
        with httpx.Client(timeout=20.0, headers=headers) as client:
            # Create DM channel
            r = client.post("https://discord.com/api/v10/users/@me/channels", json={"recipient_id": recipient_id})
            if r.status_code < 200 or r.status_code >= 300:
                return False
            channel_id = r.json().get("id")
            if not channel_id:
                return False

            r2 = client.post(f"https://discord.com/api/v10/channels/{channel_id}/messages", json={"content": content})
            return 200 <= r2.status_code < 300
    except Exception:
        return False


@app.route("/")
def index():
    """Main dashboard page."""
    try:
        return render_template("index.html")
    except Exception as e:
        return f"<h1>Template Error</h1><p>Error: {str(e)}</p><p>Check that templates/index.html exists</p>", 500


@app.route("/leaderboard")
def leaderboard():
    """Dedicated leaderboard page."""
    try:
        return render_template("leaderboard.html")
    except Exception as e:
        return f"<h1>Template Error</h1><p>Error: {str(e)}</p><p>Check that templates/leaderboard.html exists</p>", 500


@app.route("/r/<code>")
def referral_landing(code: str):
    c = str(code or "").strip()
    if not c:
        return redirect("/")

    try:
        ref = g.db.query(UserGrowth).filter(UserGrowth.referral_code == c).first()
        referrer_user_id = int(ref.user_id) if ref is not None else None
        rv = ReferralVisit(
            referral_code=c,
            referrer_user_id=referrer_user_id,
            ip_hash=_hash_ip(request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
        )
        g.db.add(rv)
        g.db.commit()
    except Exception:
        try:
            g.db.rollback()
        except Exception:
            pass

    session["pending_referral_code"] = c
    return redirect("/")


@app.route("/auth/discord/login")
def auth_discord_login():
    return discord_login()


@app.route("/auth/discord/callback")
def auth_discord_callback():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        resp, status = loop.run_until_complete(discord_callback_async(g.db))
        return resp, status
    finally:
        loop.close()


@app.route("/auth/logout")
def auth_logout():
    return logout()


@app.route("/api/register", methods=["POST"])
def register_user():
    data = request.get_json(silent=True) or {}
    email = data.get("email")

    if not isinstance(email, str) or not email.strip():
        return jsonify({"error": "email_required"}), 400

    user = User(
        email=email.strip(),
        user_tier=UserTier.free,
        trial_start_date=datetime.now(timezone.utc),
        trial_active=True,
    )
    g.db.add(user)
    g.db.commit()
    g.db.refresh(user)

    return jsonify({"user_id": user.id, "user_tier": user.user_tier.value, "trial_active": user.trial_active}), 201


@app.route("/api/me")
def me():
    user = get_current_user(g.db)
    if not user:
        return jsonify({"authenticated": False}), 200

    apply_tier_rules(user)

    g_row = _ensure_user_growth(g.db, user)
    g.user_growth = g_row
    g.db.commit()

    points = int(g_row.points_earned or 0)
    tier_status = _points_tier_label(points)

    return jsonify(
        {
            "authenticated": True,
            "user_id": user.id,
            "email": user.email,
            "discord_id": user.discord_id,
            "user_tier": user.user_tier.value,
            "trial_active": user.trial_active,
            "trial_start_date": user.trial_start_date.isoformat() if user.trial_start_date else None,
            "trial_expires_at": user.trial_expires_at().isoformat() if user.trial_expires_at() else None,
            "trial_seconds_left": user.trial_seconds_left(),
            "subscription_active": user.subscription_active,
            "subscription_expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
            "wallet_connected": user.wallet_connected,
            "wallet_address": user.wallet_address,
            "referral_code": g_row.referral_code,
            "referred_by_user_id": g_row.referred_by_user_id,
            "points_earned": points,
            "points_tier": tier_status,
        }
    )


@app.route("/api/wallet/challenge", methods=["POST"])
@require_tier(UserTier.free)
def wallet_connect_challenge():
    user = g.current_user
    data = request.get_json(silent=True) or {}
    address = data.get("address")
    if not isinstance(address, str) or not address.strip():
        return jsonify({"error": "address_required"}), 400
    return jsonify(wallet_challenge(g.db, user, address.strip()))


@app.route("/api/wallet/verify", methods=["POST"])
@require_tier(UserTier.free)
def wallet_connect_verify():
    user = g.current_user
    data = request.get_json(silent=True) or {}
    address = data.get("address")
    signature = data.get("signature")
    if not isinstance(address, str) or not address.strip():
        return jsonify({"error": "address_required"}), 400
    if not isinstance(signature, str) or not signature.strip():
        return jsonify({"error": "signature_required"}), 400

    try:
        ok = wallet_verify(g.db, user, address.strip(), signature.strip())
    except Exception:
        ok = False

    return jsonify({"verified": bool(ok), "wallet_connected": bool(ok)})


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
    now = datetime.now(timezone.utc)
    with _cache_lock:
        latest = max(last_update.values()) if last_update else None

    should_refresh = False
    if not market_cache:
        should_refresh = True
    elif latest is None:
        should_refresh = True
    else:
        should_refresh = (now - latest) > timedelta(seconds=30)

    if should_refresh:
        try:
            _run_async(update_all_markets())
        except Exception as e:
            print(f"Error updating markets in /api/markets: {type(e).__name__}")

    with _cache_lock:
        snapshot = json.loads(json.dumps(market_cache))
        latest2 = max(last_update.values()) if last_update else None

    sources = sorted(snapshot.keys())
    active_sources = [k for k in sources if snapshot.get(k)]
    total_markets = sum(len(v) if isinstance(v, list) else 0 for v in snapshot.values())
    total_events = total_markets

    return jsonify(
        {
            "markets": snapshot,
            "sources": sources,
            "active_sources": active_sources,
            "last_update": latest2.isoformat() if latest2 else None,
            "total_markets": total_markets,
            "total_events": total_events,
        }
    )


@app.route("/api/alerts/queued")
@require_tier(UserTier.free)
def list_queued_alerts():
    user = g.current_user
    alerts = (
        g.db.query(Alert)
        .filter(Alert.user_id == user.id)
        .filter(Alert.status == AlertStatus.queued)
        .order_by(Alert.created_at.asc())
        .limit(100)
        .all()
    )

    return jsonify(
        {
            "queued": [
                {
                    "alert_id": a.alert_id,
                    "source": a.source,
                    "market_id": a.market_id,
                    "question": a.question,
                    "market_link": a.market_link,
                    "yes_price": a.yes_price,
                    "no_price": a.no_price,
                    "sum_price": a.sum_price,
                    "profit_est": a.profit_est,
                    "status": a.status.value,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in alerts
            ],
            "count": len(alerts),
        }
    )


@app.route("/api/alerts/release", methods=["POST"])
@require_tier(UserTier.free)
def release_queued_alerts():
    user = g.current_user
    if not user.discord_id:
        return jsonify({"error": "missing_discord_id"}), 400

    bot_token = os.environ.get("DISCORD_BOT_TOKEN") or ""
    if not bot_token:
        return jsonify({"error": "missing_discord_bot_token"}), 500

    alerts = (
        g.db.query(Alert)
        .filter(Alert.user_id == user.id)
        .filter(Alert.status == AlertStatus.queued)
        .order_by(Alert.created_at.asc())
        .limit(25)
        .all()
    )

    sent = 0
    now = datetime.now(timezone.utc)
    for a in alerts:
        profit_cents = (float(a.profit_est or 0.0) * 100.0)
        content = (
            f"🎯 Classic Arb {profit_cents:.1f}¢\n"
            f"{a.question}\n"
            f"YES ask: {float(a.yes_price or 0.0):.3f} | NO ask: {float(a.no_price or 0.0):.3f} | Sum: {float(a.sum_price or 0.0):.3f}\n"
            f"{a.market_link or ''}"
        ).strip()

        if _discord_dm(bot_token=bot_token, recipient_id=str(user.discord_id), content=content):
            a.status = AlertStatus.released
            a.released_at = now
            if g.db.query(TradeMonitor).filter(TradeMonitor.alert_id == a.alert_id).first() is None:
                g.db.add(
                    TradeMonitor(
                        user_id=user.id,
                        alert_id=a.alert_id,
                        source=a.source,
                        market_id=a.market_id,
                        market_name=a.question,
                        entry_yes_price=a.yes_price,
                        entry_no_price=a.no_price,
                        entry_cost=a.sum_price,
                        started_at=now,
                        ends_at=now + timedelta(hours=2),
                        status=MonitorStatus.active,
                    )
                )
            sent += 1

    g.db.commit()
    return jsonify({"released": sent, "queued_remaining": max(0, len(alerts) - sent)})


@app.route("/api/executions")
@require_tier(UserTier.free)
def my_executions():
    user = g.current_user
    rows = (
        g.db.query(TradeExecution)
        .filter(TradeExecution.user_id == user.id)
        .filter(TradeExecution.source == "polymarket")
        .order_by(TradeExecution.executed_at.desc())
        .limit(200)
        .all()
    )

    return jsonify(
        {
            "executions": [
                {
                    "trade_id": r.trade_id,
                    "alert_id": r.alert_id,
                    "source": r.source,
                    "market_id": r.market_id,
                    "market_name": r.market_name,
                    "entry_cost": r.entry_cost,
                    "exit_proceeds": r.exit_proceeds,
                    "pnl": r.pnl,
                    "executed_at": r.executed_at.isoformat() if r.executed_at else None,
                }
                for r in rows
            ]
        }
    )


@app.route("/api/leaderboard/trading")
def trading_leaderboard():
    now = datetime.now(timezone.utc)

    def compute(start: Optional[datetime]) -> Dict[int, Dict[str, Any]]:
        q = g.db.query(TradeExecution).filter(TradeExecution.source == "polymarket")
        if start is not None:
            q = q.filter(TradeExecution.executed_at >= start)
        rows = q.all()

        by_user: Dict[int, Dict[str, Any]] = {}
        for r in rows:
            uid = int(r.user_id)
            b = by_user.setdefault(
                uid,
                {
                    "total_pnl": 0.0,
                    "trade_count": 0,
                    "win_count": 0,
                    "best_trade": None,
                    "worst_trade": None,
                    "volume_traded": 0.0,
                    "wallet_address": None,
                },
            )

            pnl = float(r.pnl or 0.0)
            b["total_pnl"] += pnl
            b["trade_count"] += 1
            if pnl > 0:
                b["win_count"] += 1
            if b["best_trade"] is None or pnl > float(b["best_trade"]):
                b["best_trade"] = pnl
            if b["worst_trade"] is None or pnl < float(b["worst_trade"]):
                b["worst_trade"] = pnl
            b["volume_traded"] += float(r.entry_cost or 0.0)
            if not b["wallet_address"] and r.wallet_address:
                b["wallet_address"] = r.wallet_address

        return by_user

    all_time = compute(None)
    d30 = compute(now - timedelta(days=30))
    d7 = compute(now - timedelta(days=7))

    user_ids = set(all_time.keys()) | set(d30.keys()) | set(d7.keys())
    leaders = []
    for uid in user_ids:
        b_all = all_time.get(uid) or {}
        b_30 = d30.get(uid) or {}
        b_7 = d7.get(uid) or {}

        trade_count = int(b_all.get("trade_count") or 0)
        win_rate = (float(b_all.get("win_count") or 0) / trade_count * 100.0) if trade_count else 0.0

        leaders.append(
            {
                "user_id": uid,
                "wallet": _obfuscate_wallet(b_all.get("wallet_address") or b_30.get("wallet_address") or b_7.get("wallet_address")),
                "trade_count": trade_count,
                "win_rate_pct": float(win_rate),
                "best_trade": b_all.get("best_trade"),
                "worst_trade": b_all.get("worst_trade"),
                "volume_traded": float(b_all.get("volume_traded") or 0.0),
                "total_pnl_all_time": float(b_all.get("total_pnl") or 0.0),
                "total_pnl_30d": float(b_30.get("total_pnl") or 0.0),
                "total_pnl_7d": float(b_7.get("total_pnl") or 0.0),
            }
        )

    leaders.sort(key=lambda x: float(x.get("total_pnl_all_time") or 0.0), reverse=True)
    return jsonify({"leaders": leaders[:100]})


@app.route("/api/leaderboard/community")
def community_leaderboard():
    for u in g.db.query(User).limit(5000).all():
        _ensure_user_growth(g.db, u)
    g.db.commit()

    referrals_signed_up = (
        g.db.query(UserGrowth.referred_by_user_id, func.count(UserGrowth.user_id))
        .filter(UserGrowth.referred_by_user_id.isnot(None))
        .group_by(UserGrowth.referred_by_user_id)
        .all()
    )
    signups_by_user = {int(uid): int(cnt) for uid, cnt in referrals_signed_up}

    conversions_all = (
        g.db.query(ReferralConversion.referrer_user_id, func.count(ReferralConversion.id))
        .group_by(ReferralConversion.referrer_user_id)
        .all()
    )
    conv_by_user = {int(uid): int(cnt) for uid, cnt in conversions_all}

    conversions_by_tier = (
        g.db.query(ReferralConversion.referrer_user_id, ReferralConversion.to_tier, func.count(ReferralConversion.id))
        .group_by(ReferralConversion.referrer_user_id, ReferralConversion.to_tier)
        .all()
    )
    conv_tier_map: Dict[int, Dict[str, int]] = {}
    for uid, to_tier, cnt in conversions_by_tier:
        conv_tier_map.setdefault(int(uid), {})[str(to_tier or "") or "unknown"] = int(cnt)

    rows = g.db.query(User, UserGrowth).join(UserGrowth, UserGrowth.user_id == User.id).all()
    leaders = []
    for u, g_row in rows:
        leaders.append(
            {
                "user_id": u.id,
                "tier_status": _tier_status_label(u),
                "referrals_signed_up": signups_by_user.get(int(u.id), 0),
                "referrals_converted": conv_by_user.get(int(u.id), 0),
                "referrals_converted_breakdown": conv_tier_map.get(int(u.id), {}),
                "points_earned": int(g_row.points_earned or 0),
                "commission_earned": float(g_row.commission_earned or 0.0),
            }
        )

    leaders.sort(key=lambda x: (int(x.get("points_earned") or 0), int(x.get("referrals_converted") or 0)), reverse=True)
    return jsonify({"leaders": leaders[:200]})


@app.route("/api/referral/code")
@require_tier(UserTier.free)
def my_referral_code():
    user = g.current_user
    g_row = _ensure_user_growth(g.db, user)
    g.db.commit()
    base_url = request.host_url.rstrip("/")
    return jsonify({"referral_code": g_row.referral_code, "referral_link": f"{base_url}/r/{g_row.referral_code}"})


@app.route("/api/referral/claim", methods=["POST"])
@require_tier(UserTier.free)
def claim_referral_code():
    user = g.current_user
    data = request.get_json(silent=True) or {}
    code = data.get("code")
    if not isinstance(code, str) or not code.strip():
        return jsonify({"error": "code_required"}), 400

    g_row = _ensure_user_growth(g.db, user)
    if g_row.referred_by_user_id is not None:
        return jsonify({"error": "already_referred"}), 400

    ref = g.db.query(UserGrowth).filter(UserGrowth.referral_code == code.strip()).first()
    if ref is None:
        return jsonify({"error": "invalid_code"}), 404
    if int(ref.user_id) == int(user.id):
        return jsonify({"error": "cannot_self_refer"}), 400

    g_row.referred_by_user_id = int(ref.user_id)
    g_row.referred_at = datetime.now(timezone.utc)

    event_key = f"ref_signup:{int(ref.user_id)}:{int(user.id)}"
    _award_points(g.db, int(ref.user_id), event_key=event_key, event_type="referral_signup", points=5, related_user_id=int(user.id))
    g.db.commit()
    return jsonify({"claimed": True, "referred_by_user_id": g_row.referred_by_user_id})


@app.route("/api/pnl/graphic")
@require_tier(UserTier.free)
def pnl_graphic():
    user = g.current_user
    try:
        from PIL import Image, ImageDraw, ImageFont
    except Exception:
        return jsonify({"error": "pillow_not_installed"}), 500

    timeframe = request.args.get("timeframe")
    tf = str(timeframe or "all").strip().lower()
    now = datetime.now(timezone.utc)
    start = None
    if tf in {"30d", "30", "month"}:
        start = now - timedelta(days=30)
        tf_label = "30D"
    elif tf in {"7d", "7", "week"}:
        start = now - timedelta(days=7)
        tf_label = "7D"
    else:
        tf_label = "ALL"

    q = g.db.query(TradeExecution).filter(TradeExecution.user_id == int(user.id)).filter(TradeExecution.source == "polymarket")
    if start is not None:
        q = q.filter(TradeExecution.executed_at >= start)
    rows = q.order_by(TradeExecution.executed_at.desc()).limit(5000).all()

    total_pnl = 0.0
    trade_count = 0
    win_count = 0
    for r in rows:
        pnl = float(r.pnl or 0.0)
        total_pnl += pnl
        trade_count += 1
        if pnl > 0:
            win_count += 1
    win_rate = (float(win_count) / float(trade_count) * 100.0) if trade_count else 0.0

    g_row = _ensure_user_growth(g.db, user)
    points = int(g_row.points_earned or 0)
    tier_status = _points_tier_label(points)

    w = 900
    h = 450
    img = Image.new("RGB", (w, h), color=(12, 16, 22))
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("arial.ttf", 36)
        font_big = ImageFont.truetype("arial.ttf", 64)
        font_body = ImageFont.truetype("arial.ttf", 24)
    except Exception:
        font_title = ImageFont.load_default()
        font_big = ImageFont.load_default()
        font_body = ImageFont.load_default()

    pnl_color = (34, 197, 94) if total_pnl >= 0 else (239, 68, 68)
    pnl_str = f"{total_pnl:+.4f}"
    wallet = _obfuscate_wallet(user.wallet_address) or ""

    draw.text((40, 30), f"P&L SUMMARY ({tf_label})", fill=(226, 232, 240), font=font_title)
    draw.text((40, 95), pnl_str, fill=pnl_color, font=font_big)
    draw.text((40, 190), f"Trades: {trade_count}   Win Rate: {win_rate:.1f}%", fill=(148, 163, 184), font=font_body)
    draw.text((40, 230), f"Points: {points}   Tier: {tier_status}", fill=(148, 163, 184), font=font_body)
    draw.text((40, 270), f"Wallet: {wallet}", fill=(100, 116, 139), font=font_body)
    draw.text((40, 390), "crypto_predict_monitor", fill=(71, 85, 105), font=font_body)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png", as_attachment=False, download_name="pnl.png")


@app.route("/api/admin/set_tier", methods=["POST"])
def admin_set_tier():
    admin_key = _env_admin_key()
    provided = request.headers.get("X-Admin-Key")
    if not admin_key or not provided or provided.strip() != admin_key:
        return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    discord_id = data.get("discord_id")
    email = data.get("email")
    tier = data.get("tier")

    if not isinstance(tier, str) or tier.strip() not in {"free", "premium", "pro"}:
        return jsonify({"error": "invalid_tier"}), 400

    user = None
    if isinstance(user_id, int):
        user = g.db.get(User, user_id)
    elif isinstance(user_id, str) and user_id.strip().isdigit():
        user = g.db.get(User, int(user_id.strip()))
    elif isinstance(discord_id, str) and discord_id.strip():
        user = g.db.query(User).filter(User.discord_id == discord_id.strip()).first()
    elif isinstance(email, str) and email.strip():
        user = g.db.query(User).filter(User.email == email.strip()).first()

    if user is None:
        return jsonify({"error": "user_not_found"}), 404

    old_tier = user.user_tier
    new_tier = UserTier(tier.strip())

    subscription_active = data.get("subscription_active")
    if subscription_active is not None:
        user.subscription_active = bool(subscription_active)

    expires_at = data.get("subscription_expires_at")
    if isinstance(expires_at, str) and expires_at.strip():
        try:
            user.subscription_expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        except Exception:
            return jsonify({"error": "invalid_subscription_expires_at"}), 400

    user.user_tier = new_tier
    apply_tier_rules(user)

    _ensure_user_growth(g.db, user)
    _record_referral_conversion_if_applicable(g.db, user, old_tier=old_tier, new_tier=new_tier)
    g.db.commit()

    return jsonify(
        {
            "user_id": user.id,
            "old_tier": old_tier.value,
            "new_tier": user.user_tier.value,
            "subscription_active": bool(user.subscription_active),
            "subscription_expires_at": user.subscription_expires_at.isoformat() if user.subscription_expires_at else None,
        }
    )


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
            min_spread=cfg.thresholds.min_spread,  # Now uses updated config (1.5%)
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
@require_tier(UserTier.premium)
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
        min_spread=cfg.thresholds.min_spread,  # Now uses updated config (1.5%)
        prioritize_new=cfg.arbitrage.prioritize_new_events,
        new_event_hours=cfg.arbitrage.new_event_hours,
    )
    return jsonify({"opportunities": opportunities})


@app.route("/api/pnl/<user_address>")
def get_pnl_data(user_address: str):
    """Get Polymarket P&L data for a user"""
    try:
        # Query real execution data from database
        executions = (
            db.query(Execution)
            .filter(
                Execution.user_address == user_address.lower(),
                Execution.market == "polymarket"
            )
            .order_by(Execution.executed_at.desc())
            .all()
        )
        
        if not executions:
            return jsonify({
                "total_pnl": 0.0,
                "polymarket_pnl": 0.0,
                "total_trades": 0,
                "gas_spent": 0.0,
                "polymarket_trades": 0,
                "win_rate": 0.0,
                "winning_trades": 0,
                "losing_trades": 0,
                "executions": []
            })
        
        # Calculate real P&L from executions
        total_pnl = sum(exec.pnl or 0 for exec in executions)
        total_trades = len(executions)
        winning_trades = len([exec for exec in executions if (exec.pnl or 0) > 0])
        losing_trades = len([exec for exec in executions if (exec.pnl or 0) < 0])
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        gas_spent = sum(exec.gas_used or 0 for exec in executions) * 0.00000002  # Approximate gas cost
        
        # Format execution data
        execution_data = []
        for exec in executions:
            execution_data.append({
                "id": str(exec.id),
                "market": exec.market,
                "market_ticker": exec.market_ticker or "Unknown",
                "side": exec.side,
                "entry_price": exec.entry_price,
                "exit_price": exec.exit_price,
                "quantity": exec.quantity,
                "pnl": exec.pnl,
                "status": exec.status,
                "entry_timestamp": exec.executed_at.isoformat() if exec.executed_at else None,
                "exit_timestamp": exec.closed_at.isoformat() if exec.closed_at else None
            })
        
        pnl_data = {
            "total_pnl": total_pnl,
            "polymarket_pnl": total_pnl,
            "total_trades": total_trades,
            "gas_spent": gas_spent,
            "polymarket_trades": total_trades,
            "win_rate": win_rate,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "executions": execution_data
        }
        
        return jsonify(pnl_data)
    except Exception as e:
        logger.error(f"Error fetching Polymarket P&L data: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/leaderboard")
def get_leaderboard():
    """Get trading leaderboard"""
    try:
        # Query real leaderboard data from database
        leaders = (
            db.query(Leaderboard)
            .order_by(Leaderboard.total_pnl.desc())
            .limit(100)
            .all()
        )
        
        if not leaders:
            return jsonify([])
        
        # Format leaderboard data
        leaderboard_data = []
        for i, leader in enumerate(leaders, 1):
            leaderboard_data.append({
                "rank": i,
                "user_id": leader.user_address[:6] + "..." + leader.user_address[-4:] if leader.user_address else "Unknown",
                "total_pnl": leader.total_pnl or 0.0,
                "total_trades": leader.total_trades or 0,
                "win_rate": leader.win_rate or 0.0
            })
        
        return jsonify(leaderboard_data)
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/alerts/create", methods=["POST"])
def create_alert():
    """Create an arbitrage alert"""
    try:
        data = request.get_json()
        opportunity = data.get("opportunity")
        user_id = data.get("user_id")
        
        if not opportunity:
            return jsonify({"error": "Missing opportunity data"}), 400
        
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400
        
        # Create alert
        from utils.alert_manager import ArbitrageAlertManager
        alert_manager = ArbitrageAlertManager()
        alert = asyncio.run(alert_manager.create_alert(
            user_id=user_id,
            market=opportunity.get("market", "unknown"),
            ticker=opportunity.get("ticker", "unknown"),
            spread=opportunity.get("spread", 0),
            yes_price=opportunity.get("yes_price"),
            no_price=opportunity.get("no_price")
        ))
        
        if alert:
            return jsonify({"status": "success", "alert_id": alert["id"]})
        else:
            return jsonify({"status": "error", "message": "Failed to create alert"})
    except Exception as e:
        logger.error(f"Error creating alert: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/wallet/challenge", methods=["POST"])
def create_wallet_challenge():
    """Create a challenge message for wallet signature verification"""
    try:
        data = request.get_json()
        wallet_address = data.get("wallet_address")
        
        if not wallet_address:
            return jsonify({"error": "Wallet address is required"}), 400
        
        # Validate address format
        if not wallet_address.startswith("0x") or len(wallet_address) != 42:
            return jsonify({"error": "Invalid wallet address format"}), 400
        
        # Generate nonce
        nonce = secrets.token_hex(16)
        timestamp = int(datetime.now(timezone.utc).timestamp())
        
        # Create challenge message
        message = f"Sign this message to verify your wallet ownership.\n\nNonce: {nonce}\nTimestamp: {timestamp}\nAddress: {wallet_address}"
        
        # Store challenge in session (in production, use Redis)
        session[f"challenge_{wallet_address}"] = {
            "nonce": nonce,
            "timestamp": timestamp,
            "message": message
        }
        
        return jsonify({
            "message": message,
            "nonce": nonce,
            "timestamp": timestamp
        })
        
    except Exception as e:
        logger.error(f"Error creating wallet challenge: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/wallet/verify", methods=["POST"])
def verify_wallet_signature():
    """Verify wallet signature"""
    try:
        data = request.get_json()
        address = data.get("address")
        message = data.get("message")
        signature = data.get("signature")
        
        if not all([address, message, signature]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Get stored challenge
        challenge = session.get(f"challenge_{address}")
        if not challenge:
            return jsonify({"error": "Challenge not found or expired"}), 400
        
        # Verify timestamp (5 minute window)
        timestamp = challenge.get("timestamp")
        if timestamp and (int(datetime.now(timezone.utc).timestamp()) - timestamp) > 300:
            return jsonify({"error": "Challenge expired"}), 400
        
        # Verify message matches
        if message != challenge.get("message"):
            return jsonify({"error": "Message mismatch"}), 400
        
        # Recover address from signature
        try:
            # Hash the message
            message_hash = Web3.keccak(text=message)
            
            # Recover address
            recovered_address = Web3.eth.account.recover_message(
                sign_hash=message_hash,
                signature=signature
            )
            
            # Normalize addresses
            recovered_address = recovered_address.lower()
            provided_address = address.lower()
            
            # Check if addresses match
            is_valid = recovered_address == provided_address
            
            # Clean up challenge
            session.pop(f"challenge_{address}", None)
            
            return jsonify({"valid": is_valid})
            
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return jsonify({"error": "Signature verification failed"}), 400
            
    except Exception as e:
        logger.error(f"Error verifying wallet signature: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/wallet/connect", methods=["POST"])
def connect_wallet():
    """Connect and store wallet"""
    try:
        data = request.get_json()
        wallet_address = data.get("wallet_address")
        signature = data.get("signature")
        
        if not wallet_address or not signature:
            return jsonify({"error": "Wallet address and signature required"}), 400
        
        # Validate address
        if not wallet_address.startswith("0x") or len(wallet_address) != 42:
            return jsonify({"error": "Invalid wallet address format"}), 400
        
        # Store wallet in database
        user = User(
            discord_id=user_id,
            wallet_address=wallet_address,
            connected_at=datetime.now(timezone.utc)
        )
        
        # Check if user already exists
        existing_user = db.query(User).filter(User.discord_id == user_id).first()
        if existing_user:
            existing_user.wallet_address = wallet_address
            existing_user.connected_at = datetime.now(timezone.utc)
            db.commit()
        else:
            db.add(user)
            db.commit()
        
        logger.info(f"Wallet connected: {wallet_address}")
        
        return jsonify({
            "status": "success",
            "wallet_address": wallet_address,
            "connected_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error connecting wallet: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/wallet/disconnect", methods=["POST"])
def disconnect_wallet():
    """Disconnect wallet"""
    try:
        data = request.get_json()
        wallet_address = data.get("wallet_address")
        
        if not wallet_address:
            return jsonify({"error": "Wallet address required"}), 400
        
        # Remove wallet from database
        user = db.query(User).filter(User.wallet_address == wallet_address).first()
        if user:
            user.wallet_address = None
            db.commit()
        
        logger.info(f"Wallet disconnected: {wallet_address}")
        
        return jsonify({
            "status": "success",
            "disconnected_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error disconnecting wallet: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/webhooks/create", methods=["POST"])
def create_webhook():
    """Create Alchemy webhook for wallet"""
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        wallet_address = data.get("wallet_address")
        
        if not user_id or not wallet_address:
            return jsonify({"error": "User ID and wallet address required"}), 400
        
        # Create real Alchemy webhook for wallet monitoring
        import httpx
        
        alchemy_url = f"https://dashboard.alchemy.com/api/notify-webhook"
        webhook_data = {
            "network": "ETH_MAINNET",
            "address": wallet_address,
            "webhook_url": f"{request.host_url}/api/webhooks/alchemy",
            "types": ["TRANSACTION"]
        }
        
        response = httpx.post(alchemy_url, json=webhook_data)
        if response.status_code != 200:
            logger.error(f"Failed to create Alchemy webhook: {response.text}")
            return jsonify({"error": "Failed to create webhook"}), 500
        
        webhook_id = response.json().get("data", {}).get("id")
        logger.info(f"Created webhook {webhook_id} for user {user_id}, wallet {wallet_address}")
        
        return jsonify({
            "status": "success",
            "webhook_id": webhook_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error creating webhook: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/whales")
@require_tier(UserTier.premium)
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


@app.route("/api/health")
def health_check():
    """Health check endpoint with database status"""
    try:
        db_health = get_database_health()
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "database": db_health
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }), 500


@app.route("/api/database/metrics")
def database_metrics():
    """Get database performance metrics"""
    try:
        from dashboard.db_logging import get_database_metrics
        metrics = get_database_metrics()
        
        return jsonify({
            "metrics": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to get database metrics: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/test/alert", methods=["POST"])
def test_discord_alert():
    """Test Discord alert endpoint"""
    try:
        data = request.get_json() or {}
        message = data.get("message", "Test alert from dashboard")
        
        # Use the ProfessionalArbitrageAlerts system
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        
        from professional_alerts import ProfessionalArbitrageAlerts
        import asyncio
        
        async def send_test_alert():
            async with ProfessionalArbitrageAlerts() as alerts:
                if not alerts.webhook_url:
                    return {"error": "No webhook URL configured"}
                
                test_payload = {
                    "content": f"🧪 {message}",
                    "username": "CPM Monitor",
                    "embeds": [{
                        "title": "Dashboard Alert Test",
                        "description": "Test alert from dashboard API endpoint",
                        "color": 0x00ff00,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }]
                }
                
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(alerts.webhook_url, json=test_payload) as response:
                        if response.status == 204:
                            return {"success": True, "message": "Test alert sent successfully"}
                        else:
                            text = await response.text()
                            return {"error": f"Failed to send alert: {text}"}
        
        result = asyncio.run(send_test_alert())
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Test alert failed: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/arbitrage", methods=["GET"])
def get_arbitrage_opportunities():
    """Get current arbitrage opportunities"""
    try:
        # This would integrate with the arbitrage detection system
        # For now, return a placeholder response
        return jsonify({
            "opportunities": [],
            "last_checked": datetime.now(timezone.utc).isoformat(),
            "status": "Arbitrage detection system not running"
        })
    except Exception as e:
        logger.error(f"Failed to get arbitrage opportunities: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/alert", methods=["POST"])
def create_discord_alert():
    """Create and send a Discord alert"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        alert_type = data.get("type", "info")
        message = data.get("message", "")
        severity = data.get("severity", "info")
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        # Use the ProfessionalArbitrageAlerts system
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        
        from professional_alerts import ProfessionalArbitrageAlerts
        import asyncio
        
        async def send_alert():
            async with ProfessionalArbitrageAlerts() as alerts:
                if not alerts.webhook_url:
                    return {"error": "No webhook URL configured"}
                
                # Set color based on severity
                colors = {
                    "info": 0x00ff00,
                    "warning": 0xffff00,
                    "error": 0xff0000,
                    "critical": 0xff0000
                }
                
                alert_payload = {
                    "content": f"🚨 {alert_type.upper()}: {message}",
                    "username": "CPM Monitor",
                    "embeds": [{
                        "title": f"{alert_type.title()} Alert",
                        "description": message,
                        "color": colors.get(severity, 0x00ff00),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }]
                }
                
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.post(alerts.webhook_url, json=alert_payload) as response:
                        if response.status == 204:
                            return {"success": True, "message": "Alert sent successfully"}
                        else:
                            text = await response.text()
                            return {"error": f"Failed to send alert: {text}"}
        
        result = asyncio.run(send_alert())
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Create alert failed: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Run Flask app
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
