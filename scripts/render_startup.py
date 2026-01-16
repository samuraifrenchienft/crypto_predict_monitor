#!/usr/bin/env python3
"""
Render startup script for the dashboard.
Handles database initialization and startup checks.
"""

import logging
import os
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def initialize_database():
    """Initialize database tables and test connection"""
    try:
        from dashboard.db import test_connection, get_connection_info, engine
        from dashboard.models import Base
        
        logger.info("🔍 Testing database connection...")
        
        # Test connection
        if not test_connection():
            logger.error("❌ Database connection test failed")
            return False
        
        logger.info("✅ Database connection test passed")
        
        # Log connection info
        conn_info = get_connection_info()
        logger.info(f"📊 Database connection info: {conn_info}")
        
        # Create tables
        logger.info("🔧 Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created successfully")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_imports():
    """Test all critical imports"""
    try:
        logger.info("🔍 Testing imports...")
        
        # Test basic dependencies first
        try:
            import yaml
            logger.info("✅ yaml imported successfully")
        except ImportError as e:
            logger.error(f"❌ yaml import failed: {e}")
            return False
        
        try:
            import pydantic
            logger.info("✅ pydantic imported successfully")
        except ImportError as e:
            logger.error(f"❌ pydantic import failed: {e}")
            return False
        
        # Test dashboard app import
        import dashboard.app
        logger.info("✅ Dashboard app imported successfully")
        
        # Test database components
        from dashboard.db import get_session, test_connection
        logger.info("✅ Database components imported successfully")
        
        # Test models
        from dashboard.models import Base, User, Alert
        logger.info("✅ Models imported successfully")
        
        # Test logging
        from dashboard.db_logging import get_database_health
        logger.info("✅ Database logging imported successfully")
        
        # Test async database
        try:
            from dashboard.async_db import get_async_postgres_manager
            logger.info("✅ Async database imported successfully")
        except ImportError:
            logger.warning("⚠️  Async database module not available")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def start_application():
    """Start the Flask application with gunicorn"""
    try:
        logger.info("🚀 Starting application...")
        
        # Get port from environment
        port = int(os.environ.get("PORT", 5000))
        logger.info(f"📡 Starting on port {port}")
        
        # Import the app
        import dashboard.app
        
        # Start with gunicorn
        import subprocess
        cmd = [
            "gunicorn",
            "--bind", f"0.0.0.0:{port}",
            "--workers", "1",
            "--timeout", "120",
            "--access-logfile", "-",
            "--error-logfile", "-",
            "dashboard.app:app"
        ]
        
        logger.info(f"🎯 Running command: {' '.join(cmd)}")
        subprocess.run(cmd)
        
    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        sys.exit(1)


def main():
    """Main startup function"""
    logger.info("🎯 Render Dashboard Startup Script")
    logger.info("=" * 50)
    
    # Environment check
    logger.info("🌍 Environment check:")
    logger.info(f"   Python version: {sys.version}")
    logger.info(f"   Working directory: {os.getcwd()}")
    logger.info(f"   PORT: {os.environ.get('PORT', 'not set')}")
    logger.info(f"   DATABASE_URL set: {'yes' if os.environ.get('DATABASE_URL') else 'no'}")
    
    # Test imports
    logger.info("\n📦 Testing imports...")
    if not test_imports():
        logger.error("❌ Import tests failed, exiting")
        sys.exit(1)
    
    # Initialize database
    logger.info("\n🗄️  Initializing database...")
    if not initialize_database():
        logger.error("❌ Database initialization failed, exiting")
        sys.exit(1)
    
    # Start application
    logger.info("\n🚀 Starting application...")
    start_application()


if __name__ == "__main__":
    main()
