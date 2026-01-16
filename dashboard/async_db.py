"""
Async PostgreSQL database connection module.
Provides async connection pooling and utilities for async operations.
"""

import logging
import os
from typing import Optional, Dict, Any

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)


class AsyncPostgresManager:
    """Manages async PostgreSQL connections and pools"""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.sqlalchemy_engine: Optional[Any] = None
        self.session_maker: Optional[async_sessionmaker[AsyncSession]] = None
        self.is_connected = False
    
    async def initialize(self) -> bool:
        """Initialize async PostgreSQL connection pool"""
        try:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                logger.warning("DATABASE_URL not set, async PostgreSQL disabled")
                return False
            
            # Normalize URL
            if database_url.startswith("postgres://"):
                database_url = "postgresql://" + database_url[len("postgres://"):]
            
            # Convert to asyncpg URL format
            if database_url.startswith("postgresql://"):
                asyncpg_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
            else:
                logger.error("Unsupported database URL format for async operations")
                return False
            
            # Initialize asyncpg pool
            self.pool = await asyncpg.create_pool(
                database_url,
                min_size=int(os.getenv("DB_POOL_MIN_SIZE", "2")),
                max_size=int(os.getenv("DB_POOL_MAX_SIZE", "10")),
                command_timeout=int(os.getenv("DB_COMMAND_TIMEOUT", "60")),
                server_settings={
                    "application_name": "crypto_predict_monitor_async",
                }
            )
            
            # Initialize SQLAlchemy async engine
            self.sqlalchemy_engine = create_async_engine(
                asyncpg_url,
                echo=os.getenv("DB_ECHO", "false").lower() == "true",
                pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
                max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
                pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "30")),
                pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "3600")),
            )
            
            self.session_maker = async_sessionmaker(
                self.sqlalchemy_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            self.is_connected = True
            logger.info("Async PostgreSQL connection pool initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize async PostgreSQL pool: {e}")
            return False
    
    async def get_connection(self) -> asyncpg.Connection:
        """Get a connection from the pool"""
        if not self.pool:
            raise RuntimeError("Async PostgreSQL pool not initialized")
        return await self.pool.acquire()
    
    async def release_connection(self, conn: asyncpg.Connection) -> None:
        """Release a connection back to the pool"""
        if self.pool and conn:
            await self.pool.release(conn)
    
    async def get_session(self) -> AsyncSession:
        """Get SQLAlchemy async session"""
        if not self.session_maker:
            raise RuntimeError("Async SQLAlchemy session maker not initialized")
        return self.session_maker()
    
    async def execute_query(self, query: str, *args) -> list:
        """Execute a query and return results"""
        conn = None
        try:
            conn = await self.get_connection()
            result = await conn.fetch(query, *args)
            return [dict(row) for row in result]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
        finally:
            if conn:
                await self.release_connection(conn)
    
    async def test_connection(self) -> bool:
        """Test async database connection"""
        try:
            if not self.pool:
                return False
            
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            
            logger.info("Async PostgreSQL connection test successful")
            return True
        except Exception as e:
            logger.error(f"Async PostgreSQL connection test failed: {e}")
            return False
    
    async def get_pool_info(self) -> Dict[str, Any]:
        """Get connection pool information"""
        if not self.pool:
            return {"status": "not_initialized"}
        
        return {
            "status": "active",
            "min_size": self.pool._minsize,
            "max_size": self.pool._maxsize,
            "current_size": len(self.pool._queue._queue),
            "available": self.pool._queue.qsize(),
        }
    
    async def close(self) -> None:
        """Close all connections and cleanup"""
        try:
            if self.sqlalchemy_engine:
                await self.sqlalchemy_engine.dispose()
            
            if self.pool:
                await self.pool.close()
            
            self.is_connected = False
            logger.info("Async PostgreSQL connections closed")
        except Exception as e:
            logger.error(f"Error closing async PostgreSQL connections: {e}")


# Global instance
async_postgres_manager = AsyncPostgresManager()


async def get_async_postgres_manager() -> AsyncPostgresManager:
    """Get the global async PostgreSQL manager"""
    if not async_postgres_manager.is_connected:
        await async_postgres_manager.initialize()
    return async_postgres_manager


async def execute_async_query(query: str, *args) -> list:
    """Convenience function to execute async queries"""
    manager = await get_async_postgres_manager()
    return await manager.execute_query(query, *args)


async def get_async_session() -> AsyncSession:
    """Convenience function to get async SQLAlchemy session"""
    manager = await get_async_postgres_manager()
    return await manager.get_session()
