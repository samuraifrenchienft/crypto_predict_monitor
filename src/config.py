from __future__ import annotations

import json
import logging
import os
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from src.logging_setup import redact_dict

logger = logging.getLogger("crypto_predict_monitor")


_ALLOWED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
_ALLOWED_UPSTREAMS = {"dev", "polymarket", "price", "multi"}
_SENSITIVE_FIELDS = {"api_key", "webhook_url", "rules_json", "polymarket_markets_json"}


def _none_if_blank(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    return s if s else None


class Settings(BaseModel):
    env: str = "dev"
    log_level: str = "INFO"
    upstream: str = "dev"
    base_url: str | None = None
    request_timeout_seconds: float = 20.0
    poll_interval_seconds: float = 30.0
    websocket_url: str | None = None
    api_key: str | None = None
    webhook_url: str | None = None
    rules_json: str | None = None
    rules: list[dict] = Field(default_factory=list)
    polymarket_base_url: str | None = None
    polymarket_markets_json: str | None = None
    polymarket_markets: dict[str, dict] | None = None
    price_provider: str = "coinbase"
    price_symbol: str = "BTC-USD"
    price_interval_minutes: int = 15

    @field_validator("env")
    @classmethod
    def _validate_env(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("env must be non-empty")
        return s

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, v: str) -> str:
        s = str(v).strip().upper()
        if s not in _ALLOWED_LOG_LEVELS:
            raise ValueError("log_level must be one of DEBUG/INFO/WARNING/ERROR/CRITICAL")
        return s

    @field_validator("upstream")
    @classmethod
    def _validate_upstream(cls, v: str) -> str:
        s = str(v).strip().lower()
        if s not in _ALLOWED_UPSTREAMS:
            raise ValueError("upstream must be one of dev/polymarket/price/multi")
        return s

    @field_validator("request_timeout_seconds", "poll_interval_seconds")
    @classmethod
    def _validate_positive(cls, v: float) -> float:
        try:
            f = float(v)
        except Exception as e:
            raise ValueError("must be a number") from e
        if f <= 0:
            raise ValueError("must be > 0")
        return f

    @field_validator("base_url", "websocket_url", "api_key", "webhook_url", "rules_json", "polymarket_base_url", "polymarket_markets_json", "price_provider", "price_symbol")
    @classmethod
    def _normalize_optional_str(cls, v: str | None) -> str | None:
        return _none_if_blank(v)

    @field_validator("price_interval_minutes")
    @classmethod
    def _validate_price_interval(cls, v: int) -> int:
        try:
            i = int(v)
        except Exception as e:
            raise ValueError("must be an integer") from e
        if i <= 0:
            raise ValueError("must be > 0")
        return i


def _safe_validation_message(err: ValidationError) -> str:
    issues: list[str] = []
    for e in err.errors(include_url=False):
        loc = e.get("loc") or ()
        field = str(loc[0]) if loc else "settings"
        msg = str(e.get("msg") or "invalid value")
        issues.append(f"{field}: {msg}")

    if not issues:
        return "Invalid settings"

    return "Invalid settings: " + "; ".join(issues)


def load_settings() -> Settings:
    data: dict[str, Any] = {}

    mapping = {
        "env": "CPM_ENV",
        "log_level": "CPM_LOG_LEVEL",
        "upstream": "CPM_UPSTREAM",
        "base_url": "CPM_BASE_URL",
        "request_timeout_seconds": "CPM_REQUEST_TIMEOUT_SECONDS",
        "poll_interval_seconds": "CPM_POLL_INTERVAL_SECONDS",
        "websocket_url": "CPM_WEBSOCKET_URL",
        "api_key": "CPM_API_KEY",
        "webhook_url": "CPM_WEBHOOK_URL",
        "rules_json": "CPM_RULES_JSON",
        "polymarket_base_url": "CPM_POLYMARKET_BASE_URL",
        "polymarket_markets_json": "CPM_POLYMARKET_MARKETS_JSON",
        "price_provider": "CPM_PRICE_PROVIDER",
        "price_symbol": "CPM_PRICE_SYMBOL",
        "price_interval_minutes": "CPM_PRICE_INTERVAL_MINUTES",
    }

    for field, env_key in mapping.items():
        if env_key in os.environ:
            data[field] = os.environ.get(env_key)

    if "polymarket_base_url" not in data or not data.get("polymarket_base_url"):
        data["polymarket_base_url"] = "https://clob.polymarket.com"

    rules_json_raw = data.get("rules_json")
    if rules_json_raw:
        try:
            parsed = json.loads(rules_json_raw)
        except Exception:
            logger.error("Invalid CPM_RULES_JSON: must be valid JSON")
            raise SystemExit(2)

        if not isinstance(parsed, list):
            logger.error("Invalid CPM_RULES_JSON: must be a JSON array")
            raise SystemExit(2)

        data["rules"] = parsed

    polymarket_markets_json_raw = data.get("polymarket_markets_json")
    if polymarket_markets_json_raw:
        try:
            parsed = json.loads(polymarket_markets_json_raw)
        except Exception:
            logger.error("Invalid CPM_POLYMARKET_MARKETS_JSON: must be valid JSON")
            raise SystemExit(2)

        if not isinstance(parsed, dict):
            logger.error("Invalid CPM_POLYMARKET_MARKETS_JSON: must be a JSON object")
            raise SystemExit(2)

        for key, value in parsed.items():
            if not key or not str(key).strip():
                logger.error("Invalid CPM_POLYMARKET_MARKETS_JSON: all keys must be non-empty strings")
                raise SystemExit(2)
            if not isinstance(value, dict):
                logger.error(f"Invalid CPM_POLYMARKET_MARKETS_JSON: value for key '{key}' must be an object")
                raise SystemExit(2)
            token_id = value.get("token_id")
            if not token_id or not str(token_id).strip():
                logger.error(f"Invalid CPM_POLYMARKET_MARKETS_JSON: 'token_id' for key '{key}' must be a non-empty string")
                raise SystemExit(2)

        data["polymarket_markets"] = parsed

    upstream = data.get("upstream", "dev")
    if upstream == "polymarket":
        if not polymarket_markets_json_raw:
            logger.error("CPM_POLYMARKET_MARKETS_JSON is required when CPM_UPSTREAM=polymarket")
            raise SystemExit(2)
    elif upstream == "dev":
        if not data.get("base_url"):
            logger.error("CPM_BASE_URL is required when CPM_UPSTREAM=dev")
            raise SystemExit(2)
    elif upstream == "price":
        # Price mode does not require base_url or polymarket settings
        # Price settings have defaults, so no validation needed
        pass
    elif upstream == "multi":
        # Multi mode requires polymarket settings
        if not polymarket_markets_json_raw:
            logger.error("CPM_POLYMARKET_MARKETS_JSON is required when CPM_UPSTREAM=multi")
            raise SystemExit(2)
        # Price settings have defaults, so no validation needed

    try:
        return Settings.model_validate(data)
    except ValidationError as e:
        raise ValueError(_safe_validation_message(e)) from None


def safe_settings_summary(settings: Settings) -> dict:
    d = settings.model_dump()
    
    rules_count = len(settings.rules)
    rule_market_ids: list[str] = []
    for r in settings.rules:
        if isinstance(r, dict):
            mid = r.get("market_id")
            if mid:
                rule_market_ids.append(str(mid))

    polymarket_markets_count = 0
    polymarket_market_ids: list[str] = []
    if settings.polymarket_markets:
        polymarket_markets_count = len(settings.polymarket_markets)
        polymarket_market_ids = list(settings.polymarket_markets.keys())

    try:
        safe = redact_dict(d)
    except Exception:
        safe: dict[str, Any] = {}
        for k, v in d.items():
            if k in _SENSITIVE_FIELDS:
                safe[k] = "[REDACTED]"
            else:
                safe[k] = v

    # Remove raw JSON fields from summary
    safe.pop("polymarket_markets_json", None)
    safe.pop("polymarket_markets", None)

    safe["rules_count"] = rules_count
    safe["rule_market_ids"] = rule_market_ids
    safe["polymarket_markets_count"] = polymarket_markets_count
    safe["polymarket_market_ids"] = polymarket_market_ids
    
    # Include price settings in summary
    safe["price_provider"] = settings.price_provider
    safe["price_symbol"] = settings.price_symbol
    safe["price_interval_minutes"] = settings.price_interval_minutes

    return safe