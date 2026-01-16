from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Optional

import httpx
from eth_account import Account
from eth_account.messages import encode_defunct
from flask import Response, g, jsonify, redirect, request, session
from sqlalchemy import select

from dashboard.models import User, UserTier


def _env_str(key: str) -> Optional[str]:
    v = os.environ.get(key)
    if v is None:
        return None
    s = v.strip()
    return s if s else None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_current_user(db) -> Optional[User]:
    uid = session.get("user_id")
    if not uid:
        return None
    try:
        return db.get(User, int(uid))
    except Exception:
        return None


def apply_tier_rules(user: User, now: Optional[datetime] = None) -> None:
    now_dt = now or _utcnow()

    if user.trial_active and user.trial_start_date:
        if now_dt >= (user.trial_start_date + timedelta(days=7)):
            user.trial_active = False

    if user.user_tier in {UserTier.premium, UserTier.pro}:
        if not user.subscription_active:
            user.user_tier = UserTier.free
        elif user.subscription_expires_at and user.subscription_expires_at <= now_dt:
            user.subscription_active = False
            user.user_tier = UserTier.free


def has_access(user: User, required: UserTier) -> bool:
    if required == UserTier.free:
        return True

    if user.user_tier in {UserTier.premium, UserTier.pro} and user.subscription_active:
        return True

    if user.user_tier == UserTier.free and user.trial_active:
        return True

    return False


def require_tier(required: UserTier) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            db = getattr(g, "db", None)
            if db is None:
                return jsonify({"error": "db session missing"}), 500

            user = get_current_user(db)
            if not user:
                return jsonify({"error": "unauthorized"}), 401

            apply_tier_rules(user)
            db.commit()

            if not has_access(user, required):
                return jsonify({"error": "forbidden", "required_tier": required.value}), 403

            g.current_user = user
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def discord_login() -> Response:
    client_id = _env_str("DISCORD_CLIENT_ID")
    redirect_uri = _env_str("DISCORD_REDIRECT_URI")

    if not client_id or not redirect_uri:
        return jsonify({"error": "missing_discord_oauth_env"}), 500

    state = secrets.token_urlsafe(32)
    session["discord_oauth_state"] = state

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "identify email",
        "state": state,
        "prompt": "none",
    }

    url = httpx.URL("https://discord.com/api/oauth2/authorize", params=params)
    return redirect(str(url))


async def _discord_exchange_code(code: str) -> dict:
    client_id = _env_str("DISCORD_CLIENT_ID")
    client_secret = _env_str("DISCORD_CLIENT_SECRET")
    redirect_uri = _env_str("DISCORD_REDIRECT_URI")

    if not client_id or not client_secret or not redirect_uri:
        raise RuntimeError("missing discord oauth env")

    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.post("https://discord.com/api/oauth2/token", data=data)
        resp.raise_for_status()
        return resp.json()


async def _discord_fetch_user(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        resp = await client.get("https://discord.com/api/users/@me")
        resp.raise_for_status()
        return resp.json()


async def discord_callback_async(db) -> tuple[Response, int]:
    code = request.args.get("code")
    state = request.args.get("state")

    if not code or not state:
        return jsonify({"error": "missing_code_or_state"}), 400

    expected = session.get("discord_oauth_state")
    if not expected or expected != state:
        return jsonify({"error": "invalid_state"}), 400

    token = await _discord_exchange_code(code)
    access_token = token.get("access_token")
    if not access_token:
        return jsonify({"error": "missing_access_token"}), 400

    profile = await _discord_fetch_user(access_token)
    discord_id = str(profile.get("id") or "").strip()
    email = profile.get("email")

    if not discord_id:
        return jsonify({"error": "missing_discord_id"}), 400

    existing = db.execute(select(User).where(User.discord_id == discord_id)).scalar_one_or_none()
    if existing is None:
        user = User(
            discord_id=discord_id,
            email=str(email).strip() if isinstance(email, str) and email.strip() else None,
            user_tier=UserTier.free,
            trial_start_date=_utcnow(),
            trial_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user = existing
        if isinstance(email, str) and email.strip() and not user.email:
            user.email = email.strip()
        apply_tier_rules(user)
        db.commit()

    session["user_id"] = int(user.id)
    return redirect("/"), 302


def logout() -> Response:
    session.pop("user_id", None)
    session.pop("discord_oauth_state", None)
    return redirect("/")


def wallet_challenge(db, user: User, address: str) -> dict:
    nonce = secrets.token_urlsafe(16)
    user.wallet_nonce = nonce
    user.wallet_address = address
    user.wallet_connected = False
    db.commit()

    msg = f"Connect wallet to Crypto Predict Monitor. Nonce: {nonce}"
    return {"address": address, "message": msg, "nonce": nonce}


def wallet_verify(db, user: User, address: str, signature: str) -> bool:
    if not user.wallet_nonce:
        return False

    msg = f"Connect wallet to Crypto Predict Monitor. Nonce: {user.wallet_nonce}"
    recovered = Account.recover_message(encode_defunct(text=msg), signature=signature)
    if not recovered:
        return False

    if recovered.lower() != address.lower():
        return False

    user.wallet_address = address
    user.wallet_connected = True
    user.wallet_verified_at = _utcnow()
    user.wallet_nonce = None
    db.commit()
    return True
