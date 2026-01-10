from __future__ import annotations

import enum
import uuid
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


class MonitorStatus(str, enum.Enum):
    active = "active"
    finalized = "finalized"
    canceled = "canceled"


class TradeMonitor(Base):
    __tablename__ = "trade_monitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    alert_id: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)

    source: Mapped[str] = mapped_column(String(32), nullable=False)
    market_id: Mapped[str] = mapped_column(String(128), nullable=False)
    market_name: Mapped[str] = mapped_column(Text, nullable=False)

    entry_yes_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_no_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    entry_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    status: Mapped[MonitorStatus] = mapped_column(Enum(MonitorStatus), nullable=False, default=MonitorStatus.active, index=True)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class TradeExecution(Base):
    __tablename__ = "trade_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    trade_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True, default=lambda: uuid.uuid4().hex)
    alert_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    source: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    market_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    market_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    entry_cost: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_proceeds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pnl: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    wallet_address: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)


class UserGrowth(Base):
    __tablename__ = "user_growth"

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    referral_code: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True, default=lambda: uuid.uuid4().hex[:12])
    referred_by_user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    referred_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    points_earned: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    commission_earned: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class ReferralConversion(Base):
    __tablename__ = "referral_conversions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    referrer_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    referred_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    from_tier: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    to_tier: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    commission_awarded: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    converted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True, default=lambda: datetime.now(timezone.utc))
