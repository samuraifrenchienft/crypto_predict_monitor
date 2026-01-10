from __future__ import annotations

import enum
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
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
