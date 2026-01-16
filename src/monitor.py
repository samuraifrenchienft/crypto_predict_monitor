from __future__ import annotations

import logging
import time

from src.alerts import AlertRule, AlertState, evaluate_event
from src.fetcher import fetch_events
from src.http_client import HttpClient
from src.schemas import WebhookPayload
from src.webhook import send_webhook

logger = logging.getLogger("crypto_predict_monitor")


def run_monitor(
    client: HttpClient,
    *,
    poll_interval_seconds: float,
    rules: list[AlertRule],
    webhook_url: str | None = None,
    request_timeout_seconds: float = 20.0,
    upstream: str = "dev",
    polymarket_base_url: str | None = None,
    polymarket_markets: dict[str, dict] | None = None,
    price_provider: str = "coinbase",
    price_symbol: str = "BTC-USD",
    price_interval_minutes: int = 15,
) -> None:
    poll_s = float(poll_interval_seconds)
    if poll_s <= 0:
        raise ValueError("poll_interval_seconds must be > 0")

    state = AlertState()
    webhook = (webhook_url or "").strip() if webhook_url else None

    try:
        while True:
            events = fetch_events(
                client,
                upstream=upstream,
                polymarket_base_url=polymarket_base_url,
                polymarket_markets=polymarket_markets,
                price_provider=price_provider,
                price_symbol=price_symbol,
                price_interval_minutes=price_interval_minutes,
            )

            for event in events:
                matching_rules = [r for r in rules if r.market_id == event.market_id]
                if not matching_rules:
                    continue

                prev = state.get_prev(event.market_id)

                for rule in matching_rules:
                    alert = evaluate_event(event, rule, prev, state)
                    if alert is None:
                        continue

                    delta_str = ""
                    if prev is not None:
                        delta = abs(event.probability - prev)
                        delta_str = f" delta={delta:.4f}"

                    logger.warning(
                        "ALERT market_id=%s severity=%s probability=%.4f%s",
                        event.market_id,
                        alert.severity,
                        event.probability,
                        delta_str,
                    )

                    if webhook:
                        try:
                            logger.info(
                                "webhook dispatch market_id=%s severity=%s",
                                event.market_id,
                                alert.severity,
                            )
                            payload = WebhookPayload(content=alert.message)
                            send_webhook(webhook, payload, timeout_seconds=request_timeout_seconds)
                        except Exception as e:
                            logger.error("webhook send failed error=%s", type(e).__name__)

                state.set_current(event.market_id, event.probability)

            ids = [e.market_id for e in events]
            logger.info("fetched events count=%s ids=%s", len(events), ids)

            time.sleep(poll_s)
    except KeyboardInterrupt:
        logger.info("monitor shutdown requested")
        return