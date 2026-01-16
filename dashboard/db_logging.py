"""
Database logging and monitoring utilities.
Provides structured logging for database operations and health monitoring.
"""

import logging
import time
import traceback
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Dict, Any, Optional, Callable

from dashboard.db import engine, get_connection_info, test_connection
from dashboard.async_db import async_postgres_manager


logger = logging.getLogger(__name__)


class DatabaseLogger:
    """Enhanced database logging with metrics and health monitoring"""
    
    def __init__(self):
        self.query_count = 0
        self.error_count = 0
        self.slow_queries = []
        self.connection_errors = []
        self.start_time = time.time()
    
    def log_query(self, query: str, duration: float, error: Optional[Exception] = None):
        """Log a database query with metrics"""
        self.query_count += 1
        
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "query": query[:100] + "..." if len(query) > 100 else query,
            "duration_ms": round(duration * 1000, 2),
            "query_count": self.query_count,
        }
        
        if error:
            self.error_count += 1
            log_data.update({
                "error": str(error),
                "error_type": type(error).__name__,
                "traceback": traceback.format_exc()
            })
            logger.error(f"Database query failed: {log_data}")
        else:
            if duration > 1.0:  # Slow query threshold (1 second)
                self.slow_queries.append(log_data)
                logger.warning(f"Slow database query detected: {log_data}")
            else:
                logger.debug(f"Database query executed: {log_data}")
    
    def log_connection_error(self, error: Exception):
        """Log database connection errors"""
        self.connection_errors.append({
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(error),
            "error_type": type(error).__name__,
            "traceback": traceback.format_exc()
        })
        logger.error(f"Database connection error: {error}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get database performance metrics"""
        uptime = time.time() - self.start_time
        
        return {
            "uptime_seconds": round(uptime, 2),
            "total_queries": self.query_count,
            "error_count": self.error_count,
            "error_rate": round(self.error_count / max(self.query_count, 1) * 100, 2),
            "slow_query_count": len(self.slow_queries),
            "connection_error_count": len(self.connection_errors),
            "queries_per_second": round(self.query_count / max(uptime, 1), 2),
            "avg_slow_query_duration": round(
                sum(q["duration_ms"] for q in self.slow_queries) / max(len(self.slow_queries), 1), 2
            ) if self.slow_queries else 0,
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get database health status"""
        metrics = self.get_metrics()
        connection_info = get_connection_info()
        
        # Determine health status
        health_issues = []
        
        if metrics["error_rate"] > 5.0:
            health_issues.append(f"High error rate: {metrics['error_rate']}%")
        
        if metrics["slow_query_count"] > 10:
            health_issues.append(f"Many slow queries: {metrics['slow_query_count']}")
        
        if metrics["connection_error_count"] > 0:
            health_issues.append(f"Connection errors: {metrics['connection_error_count']}")
        
        # Test actual connection
        connection_test = test_connection()
        if not connection_test:
            health_issues.append("Connection test failed")
        
        status = "healthy" if not health_issues else "unhealthy"
        
        return {
            "status": status,
            "issues": health_issues,
            "metrics": metrics,
            "connection_info": connection_info,
            "last_check": datetime.utcnow().isoformat(),
        }


# Global database logger instance
db_logger = DatabaseLogger()


@contextmanager
def logged_database_session():
    """Context manager for logging database sessions"""
    session = None
    start_time = time.time()
    try:
        from dashboard.db import get_session
        session = get_session()
        yield session
        duration = time.time() - start_time
        db_logger.log_query("session_commit", duration)
    except Exception as e:
        duration = time.time() - start_time
        db_logger.log_query("session_error", duration, e)
        raise
    finally:
        if session:
            try:
                session.close()
            except Exception as e:
                db_logger.log_connection_error(e)


@asynccontextmanager
async def logged_async_database_session():
    """Async context manager for logging database sessions"""
    session = None
    start_time = time.time()
    try:
        manager = await get_async_postgres_manager()
        session = await manager.get_session()
        yield session
        duration = time.time() - start_time
        db_logger.log_query("async_session_commit", duration)
    except Exception as e:
        duration = time.time() - start_time
        db_logger.log_query("async_session_error", duration, e)
        raise
    finally:
        if session:
            try:
                await session.close()
            except Exception as e:
                db_logger.log_connection_error(e)


def log_database_operation(operation: str):
    """Decorator to log database operations"""
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                db_logger.log_query(operation, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                db_logger.log_query(operation, duration, e)
                raise
        return wrapper
    return decorator


async def log_async_database_operation(operation: str):
    """Decorator to log async database operations"""
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                db_logger.log_query(f"async_{operation}", duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                db_logger.log_query(f"async_{operation}", duration, e)
                raise
        return wrapper
    return decorator


def get_database_health() -> Dict[str, Any]:
    """Get comprehensive database health report"""
    return db_logger.get_health_status()


def get_database_metrics() -> Dict[str, Any]:
    """Get database performance metrics"""
    return db_logger.get_metrics()


def reset_database_metrics():
    """Reset database metrics counters"""
    global db_logger
    db_logger = DatabaseLogger()
    logger.info("Database metrics reset")


# Import async manager
try:
    from dashboard.async_db import get_async_postgres_manager
except ImportError:
    logger.warning("Async database module not available")
    get_async_postgres_manager = None
