from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Outcome(BaseModel):
    outcome_id: str
    name: str


class Quote(BaseModel):
    outcome_id: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    mid: Optional[float] = None
    spread: Optional[float] = None
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    ts: datetime = Field(default_factory=utc_now)

    @staticmethod
    def from_bid_ask(
        outcome_id: str,
        bid: Optional[float],
        ask: Optional[float],
        bid_size: Optional[float] = None,
        ask_size: Optional[float] = None,
    ) -> "Quote":
        mid = None
        spread = None
        if bid is not None and ask is not None:
            mid = (bid + ask) / 2.0
            spread = ask - bid
        return Quote(
            outcome_id=outcome_id,
            bid=bid,
            ask=ask,
            mid=mid,
            spread=spread,
            bid_size=bid_size,
            ask_size=ask_size,
        )


class Market(BaseModel):
    source: str
    market_id: str
    title: str
    url: Optional[str] = None
    outcomes: List[Outcome] = Field(default_factory=list)
