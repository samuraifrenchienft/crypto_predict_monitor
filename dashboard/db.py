from __future__ import annotations

import logging
import os
import time
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import QueuePool


logger = logging.getLogger(__name__)


def _normalize_database_url(url: str) -> str:
    """Normalize database URL and log connection type"""
    s = (url or "").strip()
    if s.startswith("postgres://"):
        normalized = "postgresql://" + s[len("postgres://"):]
        logger.info("Converting postgres:// to postgresql://")
        return normalized
    return s


def get_database_url() -> str:
    """Get database URL with proper logging and validation"""
    url = _normalize_database_url(os.environ.get("DATABASE_URL") or "")
    if url:
        logger.info(f"Using PostgreSQL database: {url[:20]}...")
        return url

    # Fallback to SQLite for local development
    base_dir = os.path.dirname(os.path.dirname(__file__))
    db_path = os.path.join(base_dir, "data", "app.db")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    logger.info(f"DATABASE_URL not set, using SQLite: {db_path}")
    return f"sqlite:///{db_path}"


# Database connection configuration
database_url = get_database_url()
is_postgresql = database_url.startswith("postgresql://")

# Engine configuration with proper pooling
engine_kwargs = {
    "pool_pre_ping": True,
    "future": True,
    "echo": os.getenv("DB_ECHO", "false").lower() == "true",
}

# Add PostgreSQL-specific settings
if is_postgresql:
    engine_kwargs.update({
        "poolclass": QueuePool,
        "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "30")),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "3600")),
        "connect_args": {
            "application_name": "crypto_predict_monitor",
            "connect_timeout": int(os.getenv("DB_CONNECT_TIMEOUT", "10")),
        }
    })
    logger.info("Configured PostgreSQL connection pool")
else:
    logger.info("Using SQLite database")

engine = create_engine(database_url, **engine_kwargs)

SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
)


# Add connection logging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Log new database connections"""
    if is_postgresql:
        logger.info("New PostgreSQL connection established")
    else:
        logger.debug("New SQLite connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout"""
    logger.debug("Connection checked out from pool")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Log connection checkin"""
    logger.debug("Connection checked in to pool")


def get_session():
    """Get a database session with error handling"""
    try:
        session = SessionLocal()
        logger.debug("Database session created")
        return session
    except Exception as e:
        logger.error(f"Failed to create database session: {e}")
        raise


def close_session() -> None:
    """Close database session with error handling"""
    try:
        SessionLocal.remove()
        logger.debug("Database session closed")
    except Exception as e:
        logger.error(f"Error closing database session: {e}")


def test_connection() -> bool:
    """Test database connection"""
    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def get_connection_info() -> dict:
    """Get database connection information"""
    pool = engine.pool
    
    # Get pool statistics safely
    pool_info = {}
    try:
        if hasattr(pool, 'size'):
            pool_info['pool_size'] = pool.size()
        else:
            pool_info['pool_size'] = 'N/A'
            
        if hasattr(pool, 'checkedin'):
            pool_info['checked_in'] = pool.checkedin()
        else:
            pool_info['checked_in'] = 'N/A'
            
        if hasattr(pool, 'checkedout'):
            pool_info['checked_out'] = pool.checkedout()
        else:
            pool_info['checked_out'] = 'N/A'
            
        if hasattr(pool, 'overflow'):
            pool_info['overflow'] = pool.overflow()
        else:
            pool_info['overflow'] = 'N/A'
    except Exception as e:
        logger.warning(f"Error getting pool info: {e}")
        pool_info = {
            'pool_size': 'N/A',
            'checked_in': 'N/A',
            'checked_out': 'N/A',
            'overflow': 'N/A'
        }
    
    return {
        "database_type": "postgresql" if is_postgresql else "sqlite",
        **pool_info
    }
