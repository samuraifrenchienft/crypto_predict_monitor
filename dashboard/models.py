from __future__ import annotations

import enum
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class UserTier(str, enum.Enum):
    free = "free"
    premium = "premium"
    pro = "pro"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True, index=True)
    discord_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True, index=True)

    user_tier: Mapped[UserTier] = mapped_column(Enum(UserTier), nullable=False, default=UserTier.free)

    trial_start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    subscription_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    wallet_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    wallet_connected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    wallet_nonce: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    wallet_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def trial_expires_at(self) -> Optional[datetime]:
        if not self.trial_start_date:
            return None
        return self.trial_start_date + timedelta(days=7)

    def trial_seconds_left(self, now: Optional[datetime] = None) -> Optional[int]:
        if not self.trial_start_date:
            return None
        now_dt = now or datetime.now(timezone.utc)
        expires = self.trial_expires_at()
        if not expires:
            return None
        return max(0, int((expires - now_dt).total_seconds()))


class AlertStatus(str, enum.Enum):
    queued = "queued"
    released = "released"
    executed = "executed"


class UserAlertState(Base):
    __tablename__ = "user_alert_state"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    counter: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    alert_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False)
    market_id: Mapped[str] = mapped_column(String(128), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    market_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    yes_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    no_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sum_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profit_est: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus), nullable=False, default=AlertStatus.queued)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    released_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
