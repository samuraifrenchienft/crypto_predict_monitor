from __future__ import annotations

import logging
import os

from src.alerts import AlertRule
from src.config import load_settings, safe_settings_summary
from src.http_client import HttpClient, HttpClientError
from src.logging_setup import setup_logging
from src.monitor import run_monitor
from src.schemas import WebhookPayload
from src.webhook import send_webhook


def main() -> int:
    settings = load_settings()
    setup_logging(settings.log_level)
    logger = logging.getLogger("crypto_predict_monitor")

    def _notify_failure(message: str) -> None:
        webhook = (settings.health_webhook_url or "").strip() if settings.health_webhook_url else ""
        if not webhook:
            return

        msg = str(message).strip()
        if len(msg) > 1800:
            msg = msg[:1800] + "..."

        try:
            payload = WebhookPayload(content=msg)
            send_webhook(webhook, payload, timeout_seconds=settings.request_timeout_seconds)
        except Exception as e:
            logger.warning("failure webhook send failed error=%s", type(e).__name__)

    logger.info("Startup settings: %s", safe_settings_summary(settings))

    mode = (os.environ.get("CPM_MODE") or "health").strip().lower()
    if not mode:
        mode = "health"

    base_url = (settings.base_url or "").strip()
    if settings.upstream == "dev" and not base_url:
        logger.error("Missing required setting: base_url")
        _notify_failure("CPM startup FAILED: missing base_url")
        return 2

    # For polymarket mode, base_url may be None; client will be created with polymarket_base_url in monitor
    if settings.upstream == "dev":
        client = HttpClient(base_url=base_url, timeout_seconds=settings.request_timeout_seconds)
    else:
        # Polymarket mode: create client with polymarket_base_url
        polymarket_url = settings.polymarket_base_url or "https://clob.polymarket.com"
        client = HttpClient(base_url=polymarket_url, timeout_seconds=settings.request_timeout_seconds)
    try:
        if mode == "health":
            try:
                health = client.get_json("/health")
                if not isinstance(health, dict):
                    logger.error("Health check returned unexpected JSON type: %s", type(health).__name__)
                    _notify_failure(
                        f"CPM health FAILED: unexpected JSON type={type(health).__name__} upstream={settings.upstream}"
                    )
                    return 1

                logger.info("Health check OK. Keys: %s", sorted(list(health.keys())))
                return 0
            except Exception as e:
                logger.error("Health check failed error=%s", type(e).__name__)
                _notify_failure(f"CPM health FAILED: {type(e).__name__} upstream={settings.upstream}")
                return 1

        if mode == "monitor":
            rules: list[AlertRule] = []
            for rule_dict in settings.rules:
                if not isinstance(rule_dict, dict):
                    logger.warning("Skipping invalid rule: not a dict")
                    continue

                market_id = rule_dict.get("market_id")
                if not market_id:
                    logger.warning("Skipping rule: missing market_id")
                    continue

                try:
                    rule = AlertRule.model_validate(rule_dict)
                    rules.append(rule)
                except Exception:
                    logger.warning("Skipping rule: validation failed market_id=%s", market_id)
                    continue

            if not rules:
                logger.warning("no rules configured")

            try:
                run_monitor(
                    client,
                    poll_interval_seconds=settings.poll_interval_seconds,
                    rules=rules,
                    webhook_url=settings.webhook_url,
                    request_timeout_seconds=settings.request_timeout_seconds,
                    upstream=settings.upstream,
                    polymarket_base_url=settings.polymarket_base_url,
                    polymarket_markets=settings.polymarket_markets,
                    price_provider=settings.price_provider,
                    price_symbol=settings.price_symbol,
                    price_interval_minutes=settings.price_interval_minutes,
                )
                return 0
            except HttpClientError as e:
                logger.error("monitor failed: %s", str(e))
                _notify_failure(
                    f"CPM monitor FAILED: {str(e)[:200]} upstream={settings.upstream}"
                )
                return 1
            except Exception as e:
                logger.error("monitor crashed error=%s", type(e).__name__)
                _notify_failure(
                    f"CPM monitor CRASHED: {type(e).__name__} upstream={settings.upstream}"
                )
                return 1

        logger.error("Invalid CPM_MODE: %s", mode)
        _notify_failure(f"CPM startup FAILED: invalid CPM_MODE={mode}")
        return 2

    except HttpClientError as e:
        logger.error("Health check failed: %s", str(e))
        _notify_failure(f"CPM health FAILED: {str(e)[:200]} upstream={settings.upstream}")
        return 1
    except Exception as e:
        logger.error("startup failed error=%s", type(e).__name__)
        _notify_failure(f"CPM startup FAILED: {type(e).__name__} upstream={settings.upstream}")
        return 1

    finally:
        try:
            client.close()
        except Exception:
            logger.warning("Failed to close HTTP client")


if __name__ == "__main__":
    raise SystemExit(main())