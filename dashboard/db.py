from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


def _normalize_database_url(url: str) -> str:
    s = (url or "").strip()
    if s.startswith("postgres://"):
        return "postgresql://" + s[len("postgres://"):]
    return s


def get_database_url() -> str:
    url = _normalize_database_url(os.environ.get("DATABASE_URL") or "")
    if url:
        return url

    base_dir = os.path.dirname(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, "data", "app.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return f"sqlite:///{db_path}"


engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    future=True,
)

SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
)


def get_session():
    return SessionLocal()


def close_session() -> None:
    try:
        SessionLocal.remove()
    except Exception:
        return
