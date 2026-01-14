from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import os
import yaml
from dotenv import load_dotenv


def _env_bool(key: str) -> Optional[bool]:
    v = os.getenv(key)
    if v is None:
        return None
    s = v.strip().lower()
    if s in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if s in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean for {key}: {v}")


def _env_int(key: str) -> Optional[int]:
    v = os.getenv(key)
    if v is None:
        return None
    return int(v)


def _env_float(key: str) -> Optional[float]:
    v = os.getenv(key)
    if v is None:
        return None
    return float(v)


def _env_str(key: str) -> Optional[str]:
    v = os.getenv(key)
    if v is None:
        return None
    v = v.strip()
    return v if v else None


@dataclass(frozen=True)
class BotConfig:
    poll_interval_seconds: int
    snapshot_dir: Path
    max_markets_per_adapter: int


@dataclass(frozen=True)
class DiscordAlertConfig:
    enabled: bool
    online_message: bool
    min_seconds_between_same_alert: int


@dataclass(frozen=True)
class Thresholds:
    min_spread: float
    price_move_pct: float
    top_of_book_size_move_pct: float


@dataclass(frozen=True)
class ArbitrageConfig:
    mode: str  # "cross_market" or "any_market"
    min_spread: float
    prioritize_new_events: bool
    new_event_hours: int


@dataclass(frozen=True)
class WhaleWatchConfig:
    enabled: bool
    wallets: List[Dict[str, str]]
    convergence_threshold: int
    time_window_hours: int
    max_market_age_hours: int


@dataclass(frozen=True)
class PolymarketCfg:
    enabled: bool
    gamma_base_url: str
    clob_base_url: str
    data_base_url: str
    events_limit: int
    use_websocket: bool


@dataclass(frozen=True)
class LimitlessCfg:
    enabled: bool
    base_url: str
    use_websocket: bool


@dataclass(frozen=True)
class ManifoldCfg:
    enabled: bool
    base_url: str
    markets_limit: int = 50
    requests_per_second: float = 2.0
    requests_per_minute: int = 120


@dataclass(frozen=True)
class AzuroCfg:
    enabled: bool
    graphql_base_url: str
    subgraph_base_url: str
    rest_base_url: str
    markets_limit: int
    use_fallback: bool
    use_websocket: bool
    burst_size: int = 10


@dataclass(frozen=True)
class AppConfig:
    bot: BotConfig
    discord: DiscordAlertConfig
    thresholds: Thresholds
    arbitrage: ArbitrageConfig
    whale_watch: WhaleWatchConfig
    polymarket: PolymarketCfg
    limitless: LimitlessCfg
    manifold: ManifoldCfg
    azuro: AzuroCfg
    discord_webhook_url: Optional[str]


def _must_get(d: Dict[str, Any], key: str) -> Any:
    if key not in d:
        raise KeyError(f"Missing required config key: {key}")
    return d[key]


def load_config() -> AppConfig:
    # loads .env from project root if present
    load_dotenv()

    cfg_path = Path("config.yaml")
    if not cfg_path.exists():
        raise FileNotFoundError("config.yaml not found in project root")

    raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}

    bot_raw = _must_get(raw, "bot")
    alerts_raw = _must_get(_must_get(raw, "alerts"), "discord")
    thr_raw = _must_get(raw, "thresholds")
    arb_raw = raw.get("arbitrage", {})
    whale_raw = raw.get("whale_watch", {})
    ad_raw = _must_get(raw, "adapters")

    bot = BotConfig(
        poll_interval_seconds=int(_must_get(bot_raw, "poll_interval_seconds")),
        snapshot_dir=Path(str(_must_get(bot_raw, "snapshot_dir"))),
        max_markets_per_adapter=int(_must_get(bot_raw, "max_markets_per_adapter")),
    )

    discord = DiscordAlertConfig(
        enabled=bool(_must_get(alerts_raw, "enabled")),
        online_message=bool(_must_get(alerts_raw, "online_message")),
        min_seconds_between_same_alert=int(_must_get(alerts_raw, "min_seconds_between_same_alert")),
    )

    thresholds = Thresholds(
        min_spread=float(_must_get(thr_raw, "min_spread")),
        price_move_pct=float(_must_get(thr_raw, "price_move_pct")),
        top_of_book_size_move_pct=float(_must_get(thr_raw, "top_of_book_size_move_pct")),
    )

    arbitrage = ArbitrageConfig(
        mode=str(arb_raw.get("mode", "cross_market")),
        min_spread=float(arb_raw.get("min_spread", thresholds.min_spread)),
        prioritize_new_events=bool(arb_raw.get("prioritize_new_events", True)),
        new_event_hours=int(arb_raw.get("new_event_hours", 24)),
    )

    whale_watch = WhaleWatchConfig(
        enabled=bool(whale_raw.get("enabled", False)),
        wallets=whale_raw.get("wallets", []),
        convergence_threshold=int(whale_raw.get("convergence_threshold", 2)),
        time_window_hours=int(whale_raw.get("time_window_hours", 6)),
        max_market_age_hours=int(whale_raw.get("max_market_age_hours", 24)),
    )

    pm_raw = _must_get(ad_raw, "polymarket")
    polymarket = PolymarketCfg(
        enabled=bool(_must_get(pm_raw, "enabled")),
        gamma_base_url=str(_must_get(pm_raw, "gamma_base_url")),
        clob_base_url=str(_must_get(pm_raw, "clob_base_url")),
        data_base_url=str(_must_get(pm_raw, "data_base_url")),
        events_limit=int(_must_get(pm_raw, "events_limit")),
        use_websocket=bool(_must_get(pm_raw, "use_websocket")),
    )

    lim_raw = _must_get(ad_raw, "limitless")
    limitless = LimitlessCfg(
        enabled=bool(_must_get(lim_raw, "enabled")),
        base_url=str(_must_get(lim_raw, "base_url")),
        use_websocket=bool(_must_get(lim_raw, "use_websocket")),
    )


    mf_raw = ad_raw.get("manifold", {})
    manifold = ManifoldCfg(
        enabled=bool(mf_raw.get("enabled", False)),
        base_url=str(mf_raw.get("base_url", "https://api.manifold.markets")),
        markets_limit=int(mf_raw.get("markets_limit", 50)),
        requests_per_second=float(mf_raw.get("requests_per_second", 2.0)),
        requests_per_minute=int(mf_raw.get("requests_per_minute", 120)),
        burst_size=int(mf_raw.get("burst_size", 10)),
    )

    az_raw = ad_raw.get("azuro", {})
    azuro = AzuroCfg(
        enabled=bool(az_raw.get("enabled", False)),
        graphql_base_url=str(az_raw.get("graphql_base_url", "https://api.azuro.org/graphql")),
        subgraph_base_url=str(az_raw.get("subgraph_base_url", "https://subgraph.azuro.org")),
        rest_base_url=str(az_raw.get("rest_base_url", "https://azuro.org/api/v1")),
        markets_limit=int(az_raw.get("markets_limit", 50)),
        use_fallback=bool(az_raw.get("use_fallback", True)),
        use_websocket=bool(az_raw.get("use_websocket", False)),
    )

    # Secret lives ONLY in .env; we just read it (no printing).
    webhook = os.getenv("DISCORD_WEBHOOK_URL") or None

    pm_enabled = _env_bool("POLYMARKET_ENABLED")
    pm_gamma = _env_str("POLYMARKET_GAMMA_BASE_URL")
    pm_clob = _env_str("POLYMARKET_CLOB_BASE_URL")
    pm_data = _env_str("POLYMARKET_DATA_BASE_URL")
    pm_events_limit = _env_int("POLYMARKET_EVENTS_LIMIT")

    lim_enabled = _env_bool("LIMITLESS_ENABLED")
    lim_base_url = _env_str("LIMITLESS_BASE_URL")

    mf_enabled = _env_bool("MANIFOLD_ENABLED")
    mf_base_url = _env_str("MANIFOLD_BASE_URL")
    mf_markets_limit = _env_int("MANIFOLD_MARKETS_LIMIT")
    mf_rps = _env_float("MANIFOLD_REQUESTS_PER_SECOND")
    mf_rpm = _env_int("MANIFOLD_REQUESTS_PER_MINUTE")
    mf_burst = _env_int("MANIFOLD_BURST_SIZE")

    az_enabled = _env_bool("AZURO_ENABLED")
    az_graphql = _env_str("AZURO_GRAPHQL_BASE_URL")
    az_subgraph = _env_str("AZURO_SUBGRAPH_BASE_URL")
    az_rest = _env_str("AZURO_REST_BASE_URL")
    az_markets_limit = _env_int("AZURO_MARKETS_LIMIT")
    az_fallback = _env_bool("AZURO_USE_FALLBACK")
    az_websocket = _env_bool("AZURO_USE_WEBSOCKET")

    polymarket = PolymarketCfg(
        enabled=pm_enabled if pm_enabled is not None else polymarket.enabled,
        gamma_base_url=pm_gamma or polymarket.gamma_base_url,
        clob_base_url=pm_clob or polymarket.clob_base_url,
        data_base_url=pm_data or polymarket.data_base_url,
        events_limit=pm_events_limit if pm_events_limit is not None else polymarket.events_limit,
        use_websocket=polymarket.use_websocket,
    )

    limitless = LimitlessCfg(
        enabled=lim_enabled if lim_enabled is not None else limitless.enabled,
        base_url=lim_base_url or limitless.base_url,
        use_websocket=limitless.use_websocket,
    )

    manifold = ManifoldCfg(
        enabled=mf_enabled if mf_enabled is not None else manifold.enabled,
        base_url=mf_base_url or manifold.base_url,
        markets_limit=mf_markets_limit if mf_markets_limit is not None else manifold.markets_limit,
        requests_per_second=mf_rps if mf_rps is not None else manifold.requests_per_second,
        requests_per_minute=mf_rpm if mf_rpm is not None else manifold.requests_per_minute,
        burst_size=mf_burst if mf_burst is not None else manifold.burst_size,
    )

    azuro = AzuroCfg(
        enabled=az_enabled if az_enabled is not None else azuro.enabled,
        graphql_base_url=az_graphql or azuro.graphql_base_url,
        subgraph_base_url=az_subgraph or azuro.subgraph_base_url,
        rest_base_url=az_rest or azuro.rest_base_url,
        markets_limit=az_markets_limit if az_markets_limit is not None else azuro.markets_limit,
        use_fallback=az_fallback if az_fallback is not None else azuro.use_fallback,
        use_websocket=az_websocket if az_websocket is not None else azuro.use_websocket,
    )

    return AppConfig(
        bot=bot,
        discord=discord,
        thresholds=thresholds,
        arbitrage=arbitrage,
        whale_watch=whale_watch,
        polymarket=polymarket,
        limitless=limitless,
        manifold=manifold,
        azuro=azuro,
        discord_webhook_url=webhook,
    )
