from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import os
import yaml
from dotenv import load_dotenv


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
