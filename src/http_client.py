from __future__ import annotations

import logging
from typing import Any, Mapping
from urllib.parse import urlparse

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from src.logging_setup import redact_dict, redact_value

logger = logging.getLogger("crypto_predict_monitor")


class HttpClientError(Exception):
    pass


class _RetriableHttpError(Exception):
    def __init__(self, method: str, path: str, status_code: int, body_preview: str) -> None:
        super().__init__(f"Retriable HTTP error {status_code} for {method} {path}")
        self.method = method
        self.path = path
        self.status_code = int(status_code)
        self.body_preview = body_preview


def _safe_path_for_log(path: str) -> str:
    p = str(path or "").strip()
    if p.startswith("http://") or p.startswith("https://"):
        try:
            parsed = urlparse(p)
            p = parsed.path or "/"
        except Exception:
            p = "/"
    if not p:
        p = "/"
    if not p.startswith("/"):
        p = "/" + p
    return p


def _truncate_and_redact_text(text: str, limit: int = 300) -> str:
    s = str(text or "")
    if len(s) > limit:
        s = s[:limit]
    try:
        return redact_value(s)
    except Exception:
        return "[REDACTED]"


def _before_sleep_log(retry_state: RetryCallState) -> None:
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    if exc is None:
        return

    wait_s = 0.0
    try:
        wait_s = float(getattr(retry_state.next_action, "sleep", 0.0) or 0.0)
    except Exception:
        wait_s = 0.0

    method = getattr(exc, "method", None)
    path = getattr(exc, "path", None)
    if isinstance(method, str) and isinstance(path, str):
        logger.warning(
            "HTTP retrying method=%s path=%s attempt=%s wait_s=%.2f error=%s",
            method,
            _safe_path_for_log(path),
            retry_state.attempt_number,
            wait_s,
            type(exc).__name__,
        )
        return

    req = getattr(exc, "request", None)
    if isinstance(req, httpx.Request):
        try:
            method = str(req.method or "GET").upper()
        except Exception:
            method = "GET"
        try:
            path = _safe_path_for_log(str(req.url))
        except Exception:
            path = "/"
        logger.warning(
            "HTTP retrying method=%s path=%s attempt=%s wait_s=%.2f error=%s",
            method,
            path,
            retry_state.attempt_number,
            wait_s,
            type(exc).__name__,
        )
        return

    logger.warning(
        "HTTP retrying attempt=%s wait_s=%.2f error=%s",
        retry_state.attempt_number,
        wait_s,
        type(exc).__name__,
    )


class HttpClient:
    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float = 20.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else None
        self.timeout_seconds = float(timeout_seconds)
        self._base_headers: dict[str, str] = dict(headers or {})
        self._client = httpx.Client(timeout=httpx.Timeout(self.timeout_seconds), headers=self._base_headers)

    def close(self) -> None:
        self._client.close()

    def _build_url(self, path: str) -> str:
        p = str(path or "").strip()
        if p.startswith("http://") or p.startswith("https://"):
            return p
        if not self.base_url:
            return p
        if not p:
            return self.base_url
        return f"{self.base_url}/{p.lstrip('/')}"

    def _merge_headers(self, headers: Mapping[str, str] | None) -> dict[str, str] | None:
        if not headers:
            return None
        out: dict[str, str] = {}
        for k, v in headers.items():
            out[str(k)] = str(v)
        return out

    @retry(
        retry=retry_if_exception_type(
            (
                httpx.TransportError,
                httpx.ReadTimeout,
                httpx.ConnectTimeout,
                _RetriableHttpError,
            )
        ),
        stop=stop_after_attempt(5),
        wait=wait_random_exponential(multiplier=0.5, max=10.0),
        reraise=True,
        before_sleep=_before_sleep_log,
    )
    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
        json_body: dict | None = None,
    ) -> dict:
        method_u = str(method).upper()
        safe_path = _safe_path_for_log(path)

        merged_headers = self._merge_headers(headers)
        safe_headers: dict[str, Any] | None = None
        if merged_headers is not None:
            try:
                safe_headers = redact_dict(merged_headers)
            except Exception:
                safe_headers = None

        safe_params: dict[str, Any] | None = None
        if params is not None:
            try:
                safe_params = redact_dict(params)
            except Exception:
                safe_params = None

        logger.debug("HTTP request method=%s path=%s params=%s headers=%s", method_u, safe_path, safe_params, safe_headers)

        url = self._build_url(path)
        try:
            resp = self._client.request(
                method=method_u,
                url=url,
                params=params,
                headers=merged_headers,
                json=json_body,
            )
        except Exception as e:
            setattr(e, "method", method_u)
            setattr(e, "path", path)
            logger.warning("HTTP request error method=%s path=%s error=%s", method_u, safe_path, type(e).__name__)
            raise

        status = int(resp.status_code)
        logger.debug("HTTP response method=%s path=%s status=%s", method_u, safe_path, status)

        if 500 <= status <= 599:
            body_preview = _truncate_and_redact_text(resp.text, limit=300)
            logger.warning(
                "HTTP 5xx method=%s path=%s status=%s body=%s",
                method_u,
                safe_path,
                status,
                body_preview,
            )
            raise _RetriableHttpError(method_u, path, status, body_preview)

        if 400 <= status <= 499:
            body_preview = _truncate_and_redact_text(resp.text, limit=300)
            logger.error(
                "HTTP 4xx method=%s path=%s status=%s body=%s",
                method_u,
                safe_path,
                status,
                body_preview,
            )
            raise HttpClientError(f"HTTP {status} for {method_u} {safe_path}: {body_preview}")

        try:
            data = resp.json()
        except Exception:
            body_preview = _truncate_and_redact_text(resp.text, limit=300)
            logger.error(
                "HTTP invalid JSON method=%s path=%s status=%s body=%s",
                method_u,
                safe_path,
                status,
                body_preview,
            )
            raise HttpClientError(f"Invalid JSON for {method_u} {safe_path} (status {status})")

        if not isinstance(data, dict):
            logger.error(
                "HTTP JSON not dict method=%s path=%s status=%s type=%s",
                method_u,
                safe_path,
                status,
                type(data).__name__,
            )
            raise HttpClientError(f"Expected JSON object for {method_u} {safe_path} (status {status})")

        return data

    def get_json(
        self,
        path: str,
        *,
        params: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict:
        return self._request_json("GET", path, params=params, headers=headers, json_body=None)

    def post_json(
        self,
        path: str,
        *,
        json_body: dict,
        params: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict:
        if not isinstance(json_body, dict):
            raise HttpClientError("json_body must be a dict")
        return self._request_json("POST", path, params=params, headers=headers, json_body=json_body)

    @retry(
        retry=retry_if_exception_type(
            (
                httpx.TransportError,
                httpx.ReadTimeout,
                httpx.ConnectTimeout,
                _RetriableHttpError,
            )
        ),
        stop=stop_after_attempt(5),
        wait=wait_random_exponential(multiplier=0.5, max=10.0),
        reraise=True,
        before_sleep=_before_sleep_log,
    )
    def _request_json_any(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
        json_body: dict | None = None,
    ) -> Any:
        method_u = str(method).upper()
        safe_path = _safe_path_for_log(path)

        merged_headers = self._merge_headers(headers)
        safe_headers: dict[str, Any] | None = None
        if merged_headers is not None:
            try:
                safe_headers = redact_dict(merged_headers)
            except Exception:
                safe_headers = None

        safe_params: dict[str, Any] | None = None
        if params is not None:
            try:
                safe_params = redact_dict(params)
            except Exception:
                safe_params = None

        logger.debug("HTTP request method=%s path=%s params=%s headers=%s", method_u, safe_path, safe_params, safe_headers)

        url = self._build_url(path)
        try:
            resp = self._client.request(
                method=method_u,
                url=url,
                params=params,
                headers=merged_headers,
                json=json_body,
            )
        except Exception as e:
            setattr(e, "method", method_u)
            setattr(e, "path", path)
            logger.warning("HTTP request error method=%s path=%s error=%s", method_u, safe_path, type(e).__name__)
            raise

        status = int(resp.status_code)
        logger.debug("HTTP response method=%s path=%s status=%s", method_u, safe_path, status)

        if 500 <= status <= 599:
            body_preview = _truncate_and_redact_text(resp.text, limit=300)
            logger.warning(
                "HTTP 5xx method=%s path=%s status=%s body=%s",
                method_u,
                safe_path,
                status,
                body_preview,
            )
            raise _RetriableHttpError(method_u, path, status, body_preview)

        if 400 <= status <= 499:
            body_preview = _truncate_and_redact_text(resp.text, limit=300)
            logger.error(
                "HTTP 4xx method=%s path=%s status=%s body=%s",
                method_u,
                safe_path,
                status,
                body_preview,
            )
            raise HttpClientError(f"HTTP {status} for {method_u} {safe_path}: {body_preview}")

        try:
            data = resp.json()
        except Exception:
            body_preview = _truncate_and_redact_text(resp.text, limit=300)
            logger.error(
                "HTTP invalid JSON method=%s path=%s status=%s body=%s",
                method_u,
                safe_path,
                status,
                body_preview,
            )
            raise HttpClientError(f"Invalid JSON for {method_u} {safe_path} (status {status})")

        if not isinstance(data, (dict, list)):
            logger.error(
                "HTTP JSON not dict/list method=%s path=%s status=%s type=%s",
                method_u,
                safe_path,
                status,
                type(data).__name__,
            )
            raise HttpClientError(f"Expected JSON object or array for {method_u} {safe_path} (status {status})")

        return data

    def get_json_any(
        self,
        path: str,
        *,
        params: dict[str, object] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        """GET request that returns JSON (dict or list)."""
        return self._request_json_any("GET", path, params=params, headers=headers, json_body=None)