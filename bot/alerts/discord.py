from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Dict

import httpx


@dataclass
class DiscordAlerter:
    webhook_url: Optional[str]
    enabled: bool
    min_seconds_between_same_alert: int

    _last_sent: Dict[str, float] = None

    def __post_init__(self) -> None:
        if self._last_sent is None:
            self._last_sent = {}

    def _can_send(self, key: str) -> bool:
        now = time.time()
        last = self._last_sent.get(key, 0.0)
        return (now - last) >= float(self.min_seconds_between_same_alert)

    async def send(self, key: str, content: str) -> bool:
        """
        Fail-safe:
        - Never raises on webhook failures.
        - Returns True only if Discord accepted the message (2xx).
        """
        if not self.enabled:
            return False
        if not self.webhook_url:
            return False
        if not self._can_send(key):
            return False

        payload = {"content": content}
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(self.webhook_url, json=payload)

                if 200 <= resp.status_code < 300:
                    self._last_sent[key] = time.time()
                    return True

                # 401/403/404 etc -> skip silently (do not crash)
                return False

        except Exception:
            # Network/DNS/timeout/etc -> skip silently (do not crash)
            return False
