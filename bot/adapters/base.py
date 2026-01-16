from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, Optional

from bot.models import Market, Outcome, Quote


class Adapter(ABC):
    """
    Read-only adapter contract.

    Requirements:
    - list active markets
    - list outcomes for a market
    - fetch quotes (best bid/ask + mid/spread when available)

    WebSocket support is optional:
    - if not supported or not enabled, websocket_url() returns None
    """

    name: str

    @abstractmethod
    async def list_active_markets(self) -> list[Market]:
        raise NotImplementedError

    @abstractmethod
    async def list_outcomes(self, market: Market) -> list[Outcome]:
        raise NotImplementedError

    @abstractmethod
    async def get_quotes(self, market: Market, outcomes: Iterable[Outcome]) -> list[Quote]:
        raise NotImplementedError

    def websocket_url(self) -> Optional[str]:
        return None
