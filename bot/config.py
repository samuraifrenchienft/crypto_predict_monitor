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
class KalshiCfg:
    enabled: bool
    base_url: str
    markets_limit: int = 50


@dataclass(frozen=True)
class ManifoldCfg:
    enabled: bool
    base_url: str
    markets_limit: int = 50


@dataclass(frozen=True)
class MetaculusCfg:
    enabled: bool
    base_url: str
    questions_limit: int = 50
    requests_per_second: float = 1.5
    requests_per_minute: int = 90
    burst_size: int = 8


@dataclass(frozen=True)
class ManifoldCfg:
    enabled: bool
    base_url: str
    markets_limit: int = 50
    requests_per_second: float = 2.0
    requests_per_minute: int = 120
    burst_size: int = 10


@dataclass(frozen=True)
class KalshiCfg:
    enabled: bool
    base_url: str
    markets_limit: int = 50
    requests_per_second: float = 1.0
    requests_per_minute: int = 60
    burst_size: int = 5


@dataclass(frozen=True)
class AppConfig:
    bot: BotConfig
    discord: DiscordAlertConfig
    thresholds: Thresholds
    polymarket: PolymarketCfg
    limitless: LimitlessCfg
    kalshi: KalshiCfg
    manifold: ManifoldCfg
    metaculus: MetaculusCfg
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

    k_raw = _must_get(ad_raw, "kalshi")
    kalshi = KalshiCfg(
        enabled=bool(_must_get(k_raw, "enabled")),
        base_url=str(_must_get(k_raw, "base_url")),
        markets_limit=int(k_raw.get("markets_limit", 50)),
        requests_per_second=float(k_raw.get("requests_per_second", 1.0)),
        requests_per_minute=int(k_raw.get("requests_per_minute", 60)),
        burst_size=int(k_raw.get("burst_size", 5)),
    )

    mc_raw = ad_raw.get("metaculus", {})
    metaculus = MetaculusCfg(
        enabled=bool(mc_raw.get("enabled", False)),
        base_url=str(mc_raw.get("base_url", "https://www.metaculus.com/api2")),
        questions_limit=int(mc_raw.get("questions_limit", 50)),
        requests_per_second=float(mc_raw.get("requests_per_second", 1.5)),
        requests_per_minute=int(mc_raw.get("requests_per_minute", 90)),
        burst_size=int(mc_raw.get("burst_size", 8)),
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

    kal_enabled = _env_bool("KALSHI_ENABLED")
    kal_base_url = _env_str("KALSHI_BASE_URL")
    kal_markets_limit = _env_int("KALSHI_MARKETS_LIMIT")
    kal_rps = _env_float("KALSHI_REQUESTS_PER_SECOND")
    kal_rpm = _env_int("KALSHI_REQUESTS_PER_MINUTE")
    kal_burst = _env_int("KALSHI_BURST_SIZE")

    mf_enabled = _env_bool("MANIFOLD_ENABLED")
    mf_base_url = _env_str("MANIFOLD_BASE_URL")
    mf_markets_limit = _env_int("MANIFOLD_MARKETS_LIMIT")
    mf_rps = _env_float("MANIFOLD_REQUESTS_PER_SECOND")
    mf_rpm = _env_int("MANIFOLD_REQUESTS_PER_MINUTE")
    mf_burst = _env_int("MANIFOLD_BURST_SIZE")

    mc_enabled = _env_bool("METACULUS_ENABLED")
    mc_base_url = _env_str("METACULUS_BASE_URL")
    mc_questions_limit = _env_int("METACULUS_QUESTIONS_LIMIT")
    mc_rps = _env_float("METACULUS_REQUESTS_PER_SECOND")
    mc_rpm = _env_int("METACULUS_REQUESTS_PER_MINUTE")
    mc_burst = _env_int("METACULUS_BURST_SIZE")

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

    kalshi = KalshiCfg(
        enabled=kal_enabled if kal_enabled is not None else kalshi.enabled,
        base_url=kal_base_url or kalshi.base_url,
        markets_limit=kal_markets_limit if kal_markets_limit is not None else kalshi.markets_limit,
        requests_per_second=kal_rps if kal_rps is not None else kalshi.requests_per_second,
        requests_per_minute=kal_rpm if kal_rpm is not None else kalshi.requests_per_minute,
        burst_size=kal_burst if kal_burst is not None else kalshi.burst_size,
    )

    manifold = ManifoldCfg(
        enabled=mf_enabled if mf_enabled is not None else manifold.enabled,
        base_url=mf_base_url or manifold.base_url,
        markets_limit=mf_markets_limit if mf_markets_limit is not None else manifold.markets_limit,
        requests_per_second=mf_rps if mf_rps is not None else manifold.requests_per_second,
        requests_per_minute=mf_rpm if mf_rpm is not None else manifold.requests_per_minute,
        burst_size=mf_burst if mf_burst is not None else manifold.burst_size,
    )

    metaculus = MetaculusCfg(
        enabled=mc_enabled if mc_enabled is not None else metaculus.enabled,
        base_url=mc_base_url or metaculus.base_url,
        questions_limit=mc_questions_limit if mc_questions_limit is not None else metaculus.questions_limit,
        requests_per_second=mc_rps if mc_rps is not None else metaculus.requests_per_second,
        requests_per_minute=mc_rpm if mc_rpm is not None else metaculus.requests_per_minute,
        burst_size=mc_burst if mc_burst is not None else metaculus.burst_size,
    )

    return AppConfig(
        bot=bot,
        discord=discord,
        thresholds=thresholds,
        polymarket=polymarket,
        limitless=limitless,
        kalshi=kalshi,
        manifold=manifold,
        metaculus=metaculus,
        discord_webhook_url=webhook,
    )
