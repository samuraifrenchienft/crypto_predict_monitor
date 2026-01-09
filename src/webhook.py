# src/webhook.py
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from typing import Any, Dict, Optional

import httpx
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from .schemas import WebhookPayload

logger = logging.getLogger(__name__)


class WebhookError(RuntimeError):
    pass


def _redact_webhook_url(url: str) -> str:
    """
    Keep logs safe:
    - Do not log full query strings / tokens
    - Do not leak creds embedded in URL
    """
    try:
        u = httpx.URL(url)
        host = u.host or ""
        port = f":{u.port}" if u.port else ""
        path = u.path or ""
        scheme = u.scheme or "http"
        # no query, no userinfo
        return f"{scheme}://{host}{port}{path}"
    except Exception:
        return "[REDACTED]"


def _canonical_json(obj: Any) -> str:
    """
    Stable JSON encoding for hashing/idempotency.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _stable_idempotency_key(payload: WebhookPayload) -> str:
    """
    Idempotency should be stable for the same alert/event payload.
    If you retry, the key must NOT change.
    """
    # Prefer hashing the payload body (excluding sent_at if it changes per send)
    body = payload.model_dump(exclude_none=True)

    # sent_at can change per attempt; strip it so retries stay stable.
    body.pop("sent_at", None)

    digest = hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()[:32]

    # Try to include run_id if present for traceability, but keep it stable.
    run_id = getattr(payload, "run_id", None) or "no_run_id"
    return f"{run_id}:{digest}"


def _is_retryable_http_status(status_code: int) -> bool:
    return status_code == 429 or 500 <= status_code <= 599


class _RetryableStatusError(WebhookError):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=0.5, max=8.0),
    retry=(
        retry_if_exception_type(httpx.TransportError)
        | retry_if_exception_type(_RetryableStatusError)
    ),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
def send_webhook(
    webhook_url: str,
    payload: WebhookPayload,
    *,
    timeout_seconds: float = 15.0,
) -> None:
    """
    Send an alert webhook.

    Hardening rules:
    - Stable Idempotency-Key for retries (NOT a random UUID per attempt)
    - Retry only on transport errors and 429/5xx
    - Do not retry other 4xx
    - Safe logging (no secrets / no full URL / no full body)
    """
    url = str(webhook_url).strip()
    if not url:
        raise WebhookError("webhook_url must be a non-empty string")

    if not isinstance(payload, WebhookPayload):
        raise WebhookError("payload must be a WebhookPayload")

    schema_version = getattr(payload, "schema_version", None)
    if schema_version is None:
        raise WebhookError("payload.schema_version must be present")
    try:
        version = int(schema_version)
    except Exception:
        raise WebhookError("payload.schema_version must be an integer")
    if version < 1:
        raise WebhookError("payload.schema_version must be >= 1")

    # Body to send
    body: Dict[str, Any] = payload.model_dump(exclude_none=True)

    # Stable idempotency key (same payload => same key)
    idempotency_key = _stable_idempotency_key(payload)

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "crypto-predict-monitor/1",
        "Idempotency-Key": idempotency_key,
    }

    safe_url = _redact_webhook_url(url)

    # Minimal log context (no body)
    market_id: Optional[str] = None
    severity: Optional[str] = None
    try:
        # Try payload.alert.market_id first
        alert = getattr(payload, "alert", None)
        if alert is not None:
            market_id = getattr(alert, "market_id", None)
            severity = getattr(alert, "severity", None)
        
        # Fallback to payload.market_id if alert not present
        if market_id is None:
            market_id = getattr(payload, "market_id", None)
        if severity is None:
            severity = getattr(payload, "severity", None)
    except Exception:
        pass

    logger.info(
        "webhook send start url=%s market_id=%s severity=%s",
        safe_url,
        market_id,
        severity,
    )

    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            resp = client.post(url, json=body, headers=headers)

        status = resp.status_code

        # Success
        if 200 <= status <= 299:
            logger.info(
                "webhook send ok url=%s status=%s market_id=%s severity=%s",
                safe_url,
                status,
                market_id,
                severity,
            )
            return

        # Retryable statuses (tenacity will retry via raised exception)
        if _is_retryable_http_status(status):
            logger.warning(
                "webhook send retryable url=%s status=%s market_id=%s severity=%s",
                safe_url,
                status,
                market_id,
                severity,
            )
            raise _RetryableStatusError(
                status_code=status,
                message=f"retryable webhook status={status}",
            )

        # Non-retryable 4xx (except 429 handled above)
        logger.warning(
            "webhook send non-retryable url=%s status=%s market_id=%s severity=%s",
            safe_url,
            status,
            market_id,
            severity,
        )
        return

    except httpx.TransportError as e:
        # TransportError is retryable by tenacity
        logger.warning(
            "webhook send transport error url=%s market_id=%s severity=%s error=%s",
            safe_url,
            market_id,
            severity,
            type(e).__name__,
        )
        raise
