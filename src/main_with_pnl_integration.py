"""
Main Application Integration for P&L Card System
Complete integration with database, API routes, and authentication
"""

import os
import asyncio
import logging
from pathlib import Path
from flask import Flask
from flask_cors import CORS
from datetime import datetime

# Import P&L card system
from src.social.pnl_card_generator import PnLCardService
from src.api.routes.pnl_cards import init_pnl_service, pnl_bp
from src.utils.s3_uploader import init_s3_uploader, is_s3_available
from src.database.migrate import run_supabase_migrations, seed_test_data

# Import existing components
from src.logging_setup import setup_logging
from src.security.protection_layers import WebhookSignatureValidator, RateLimiter

logger = logging.getLogger(__name__)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Configure CORS
    CORS(app, origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:3001",  # Alternative port
        os.getenv('FRONTEND_URL', 'http://localhost:3000')
    ])
    
    # Setup logging
    setup_logging()
    
    # Load configuration
    app.config.update({
        'SECRET_KEY': os.getenv('SECRET_KEY', 'dev-secret-key'),
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_ANON_KEY': os.getenv('SUPABASE_ANON_KEY'),
        'DISCORD_WEBHOOK_URL': os.getenv('DISCORD_WEBHOOK_URL'),
        'AWS_S3_BUCKET': os.getenv('AWS_S3_BUCKET'),
        'AWS_REGION': os.getenv('AWS_REGION', 'us-east-1'),
    })
    
    return app

async def initialize_database():
    """Initialize database connection and run migrations"""
    try:
        # Initialize Supabase connection
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            logger.warning("Missing Supabase credentials, using mock data")
            return None
        
        from supabase import create_client
        db_client = create_client(supabase_url, supabase_key)
        
        # Run migrations
        if os.getenv('RUN_MIGRATIONS', 'false').lower() == 'true':
            logger.info("Running database migrations...")
            if run_supabase_migrations():
                logger.info("✅ Migrations completed successfully")
                
                # Seed test data in development
                if os.getenv('ENVIRONMENT', 'development') == 'development':
                    seed_test_data()
                    logger.info("✅ Test data seeded")
            else:
                logger.error("❌ Migrations failed")
                return None
        
        return db_client
        
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return None

async def initialize_pnl_cards(app, db_connection):
    """Initialize P&L card service and routes"""
    try:
        # Initialize background image path
        bg_path = "assets/valhalla_viral_bg.png"
        if not Path(bg_path).exists():
            # Try nested path
            nested_bg_path = "assets/assets/valhalla_viral_bg.png"
            if Path(nested_bg_path).exists():
                bg_path = nested_bg_path
            else:
                logger.warning(f"Background image not found, using default")
                bg_path = None
        
        # Initialize P&L card service
        init_pnl_service(
            db_connection=db_connection,
            background_image_path=bg_path
        )
        
        # Register Flask routes
        app.register_blueprint(pnl_bp)
        
        # Initialize S3 if environment variables are set
        s3_bucket = os.getenv('AWS_S3_BUCKET')
        if s3_bucket:
            aws_region = os.getenv('AWS_REGION', 'us-east-1')
            init_s3_uploader(s3_bucket, aws_region)
            logger.info("✅ S3 uploader initialized")
        
        logger.info("✅ P&L Card Service initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize P&L Card Service: {e}")
        raise

def setup_authentication(app):
    """Setup authentication middleware"""
    from functools import wraps
    
    def require_auth(f):
        """Enhanced authentication decorator"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get token from header
            token = None
            auth_header = request.headers.get('Authorization')
            
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            
            if not token:
                return jsonify({"error": "Authorization required"}), 401
            
            # Validate token (simplified for demo)
            try:
                # In production, validate JWT with proper verification
                user_id = token  # Simplified - token is user_id for demo
                request.user = type('User', (), {
                    'id': user_id, 
                    'is_admin': user_id.startswith('admin_')
                })()
                return f(*args, **kwargs)
            except Exception:
                return jsonify({"error": "Invalid token"}), 401
        
        return decorated_function
    
    # Add to app context
    app.require_auth = require_auth
    return app

def add_health_endpoints(app):
    """Add health check endpoints"""
    @app.route('/health')
    def health_check():
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0",
            "services": {
                "pnl_cards": "active",
                "database": "connected" if os.getenv('SUPABASE_URL') else "mock",
                "s3": "connected" if is_s3_available() else "disabled"
            }
        })
    
    @app.route('/api/health')
    def api_health():
        return jsonify({
            "api": "healthy",
            "endpoints": {
                "pnl_cards": "/api/pnl-card",
                "leaderboard": "/api/pnl-card/<user_id>/leaderboard"
            }
        })
    
    return app

def main():
    """Main application entry point"""
    # Create app
    app = create_app()
    
    # Setup authentication
    app = setup_authentication(app)
    
    # Add health endpoints
    app = add_health_endpoints(app)
    
    # Initialize services
    async def init_services():
        # Initialize database
        db_connection = await initialize_database()
        
        # Initialize P&L cards
        await initialize_pnl_cards(app, db_connection)
        
        logger.info("🚀 All services initialized successfully")
    
    # Run async initialization
    asyncio.run(init_services())
    
    # Start server
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('ENVIRONMENT', 'development') == 'development'
    
    logger.info(f"🌟 Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)

if __name__ == "__main__":
    main()
