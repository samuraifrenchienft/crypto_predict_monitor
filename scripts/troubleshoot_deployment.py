#!/usr/bin/env python3
"""
Deployment troubleshooting script for Render dashboard.
Diagnoses common deployment issues.
"""

import logging
import os
import sys
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_environment():
    """Check environment variables and setup"""
    logger.info("🌍 Environment Check")
    logger.info("=" * 30)
    
    env_vars = [
        'PORT',
        'DATABASE_URL',
        'PYTHONPATH',
        'FLASK_ENV',
        'PYTHON_VERSION',
        'SUPABASE_URL',
        'SUPABASE_KEY',
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            if var == 'DATABASE_URL':
                logger.info(f"✅ {var}: {value[:20]}...")
            else:
                logger.info(f"✅ {var}: {value}")
        else:
            logger.warning(f"⚠️  {var}: not set")
    
    # Python version
    logger.info(f"🐍 Python version: {sys.version}")
    
    # Working directory
    logger.info(f"📁 Working directory: {os.getcwd()}")
    
    # Check files
    critical_files = [
        'dashboard/app.py',
        'dashboard/db.py',
        'dashboard/models.py',
        'requirements.txt',
        'render.yaml',
    ]
    
    logger.info("\n📄 Critical Files Check:")
    for file_path in critical_files:
        if os.path.exists(file_path):
            logger.info(f"✅ {file_path}")
        else:
            logger.error(f"❌ {file_path} - MISSING")


def check_dependencies():
    """Check Python dependencies"""
    logger.info("\n📦 Dependencies Check")
    logger.info("=" * 30)
    
    try:
        import flask
        logger.info(f"✅ Flask: {flask.__version__}")
    except ImportError:
        logger.error("❌ Flask not installed")
        return False
    
    try:
        import sqlalchemy
        logger.info(f"✅ SQLAlchemy: {sqlalchemy.__version__}")
    except ImportError:
        logger.error("❌ SQLAlchemy not installed")
        return False
    
    try:
        import psycopg2
        logger.info(f"✅ psycopg2: {psycopg2.__version__}")
    except ImportError:
        logger.error("❌ psycopg2 not installed")
        return False
    
    try:
        import asyncpg
        logger.info(f"✅ asyncpg: {asyncpg.__version__}")
    except ImportError:
        logger.warning("⚠️  asyncpg not installed (async features disabled)")
    
    return True


def check_database_connection():
    """Test database connection"""
    logger.info("\n🗄️  Database Connection Check")
    logger.info("=" * 30)
    
    try:
        from dashboard.db import test_connection, get_connection_info
        
        # Test connection
        if test_connection():
            logger.info("✅ Database connection successful")
        else:
            logger.error("❌ Database connection failed")
            return False
        
        # Get connection info
        conn_info = get_connection_info()
        logger.info(f"📊 Connection info: {conn_info}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_imports():
    """Test critical imports"""
    logger.info("\n🔍 Import Check")
    logger.info("=" * 30)
    
    imports_to_test = [
        ('dashboard.app', 'Dashboard app'),
        ('dashboard.db', 'Database module'),
        ('dashboard.models', 'Database models'),
        ('dashboard.db_logging', 'Database logging'),
        ('dashboard.async_db', 'Async database'),
    ]
    
    failed_imports = []
    
    for module_name, description in imports_to_test:
        try:
            __import__(module_name)
            logger.info(f"✅ {description}")
        except ImportError as e:
            logger.error(f"❌ {description}: {e}")
            failed_imports.append(module_name)
        except Exception as e:
            logger.error(f"❌ {description}: {e}")
            failed_imports.append(module_name)
    
    return len(failed_imports) == 0


def check_flask_app():
    """Test Flask app creation"""
    logger.info("\n🌐 Flask App Check")
    logger.info("=" * 30)
    
    try:
        import dashboard.app
        
        # Get app instance
        app = dashboard.app.app
        logger.info("✅ Flask app created successfully")
        
        # Test routes
        routes = []
        for rule in app.url_map.iter_rules():
            routes.append(f"{rule.rule} -> {rule.endpoint}")
        
        logger.info(f"🛣️  Found {len(routes)} routes")
        
        # Check for critical routes
        critical_routes = ['/api/health', '/api/database/metrics']
        for route in critical_routes:
            if any(route in r for r in routes):
                logger.info(f"✅ Route {route} found")
            else:
                logger.warning(f"⚠️  Route {route} not found")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Flask app check failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_health_check():
    """Run local health check"""
    logger.info("\n🏥 Health Check")
    logger.info("=" * 30)
    
    try:
        import dashboard.app
        import dashboard.db_logging
        
        # Get health status
        health = dashboard.db_logging.get_database_health()
        logger.info(f"📊 Database health: {health['status']}")
        
        if health['status'] == 'unhealthy':
            logger.warning(f"⚠️  Health issues: {health['issues']}")
        
        # Get metrics
        metrics = dashboard.db_logging.get_database_metrics()
        logger.info(f"📊 Database metrics: {metrics}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False


def generate_deployment_report():
    """Generate deployment troubleshooting report"""
    logger.info("\n📋 Generating Deployment Report")
    logger.info("=" * 50)
    
    checks = [
        ("Environment", check_environment),
        ("Dependencies", check_dependencies),
        ("Database Connection", check_database_connection),
        ("Imports", check_imports),
        ("Flask App", check_flask_app),
        ("Health Check", run_health_check),
    ]
    
    results = {}
    
    for check_name, check_func in checks:
        try:
            results[check_name] = check_func()
        except Exception as e:
            logger.error(f"❌ {check_name} check crashed: {e}")
            results[check_name] = False
    
    # Summary
    logger.info("\n" + "=" * 50)
    logger.info("📊 DEPLOYMENT READINESS SUMMARY")
    logger.info("=" * 50)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{check_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\nOverall: {passed}/{total} checks passed")
    
    if passed == total:
        logger.info("🎉 All checks passed! Ready for deployment.")
        return True
    else:
        logger.error("💥 Some checks failed. Fix issues before deploying.")
        return False


def main():
    """Main function"""
    logger.info("🔧 Render Dashboard Deployment Troubleshooter")
    logger.info("=" * 60)
    
    success = generate_deployment_report()
    
    if success:
        logger.info("\n🚀 Deployment ready! Push your changes to trigger Render deployment.")
        sys.exit(0)
    else:
        logger.error("\n❌ Deployment not ready. Fix the issues above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
