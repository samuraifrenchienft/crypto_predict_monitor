"""
Enhanced Main Application with P&L Card System Integration
Complete Flask app with monitoring, P&L cards, and API routes
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS

from src.alerts import AlertRule
from src.config import load_settings, safe_settings_summary
from src.http_client import HttpClient, HttpClientError
from src.logging_setup import setup_logging
from src.monitor import run_monitor
from src.schemas import WebhookPayload
from src.webhook import send_webhook

# P&L Card System imports
from src.social.pnl_card_generator import PnLCardService
from src.api.routes.pnl_cards import init_pnl_service, pnl_bp
from src.utils.s3_uploader import init_s3_uploader, is_s3_available
from src.database.migrate import run_supabase_migrations, seed_test_data

logger = logging.getLogger("crypto_predict_monitor")

async def initialize_database():
    """Initialize database connection and run migrations"""
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            logger.warning("Missing Supabase credentials, using mock data")
            return None
        
        from supabase import create_client
        db_client = create_client(supabase_url, supabase_key)
        
        # Run migrations if enabled
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

async def initialize_pnl_cards(db_connection):
    """Initialize P&L card service and routes"""
    try:
        # Initialize background image path
        bg_path = "assets/valhalla_viral_bg.png"
        if not Path(bg_path).exists():
            nested_bg_path = "assets/assets/valhalla_viral_bg.png"
            if Path(nested_bg_path).exists():
                bg_path = nested_bg_path
            else:
                logger.warning(f"Background image not found, using default")
                bg_path = None
        
        # Initialize P&L card service
        init_pnl_service(db_connection=db_connection, background_image_path=bg_path)
        
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

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Configure CORS
    CORS(app, origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        os.getenv('FRONTEND_URL', 'http://localhost:3000')
    ])
    
    # Load configuration
    app.config.update({
        'SECRET_KEY': os.getenv('SECRET_KEY', 'dev-secret-key'),
        'SUPABASE_URL': os.getenv('SUPABASE_URL'),
        'SUPABASE_ANON_KEY': os.getenv('SUPABASE_ANON_KEY'),
        'DISCORD_WEBHOOK_URL': os.getenv('DISCORD_WEBHOOK_URL'),
        'AWS_S3_BUCKET': os.getenv('AWS_S3_BUCKET'),
        'AWS_REGION': os.getenv('AWS_REGION', 'us-east-1'),
    })
    
    # Add authentication decorator
    def require_auth(f):
        """Authentication decorator for API endpoints"""
        from functools import wraps
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            auth_header = request.headers.get('Authorization')
            
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({"error": "Authorization required"}), 401
            
            token = auth_header.split(' ')[1]
            
            # Simple token validation (replace with proper JWT in production)
            if not token or len(token) < 10:
                return jsonify({"error": "Invalid token"}), 401
            
            # Add user info to request context
            request.user = type('User', (), {
                'id': token, 
                'is_admin': token.startswith('admin_')
            })()
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    app.require_auth = require_auth
    
    # Add health endpoints
    @app.route('/health')
    def health_check():
        return jsonify({
            "status": "healthy",
            "timestamp": str(asyncio.get_event_loop().time()),
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

def main() -> int:
    """Main application entry point with P&L card integration"""
    settings = load_settings()
    setup_logging(settings.log_level)
    
    # Create Flask app
    app = create_app()
    
    # Initialize services
    async def init_services():
        # Initialize database
        db_connection = await initialize_database()
        
        # Initialize P&L cards
        await initialize_pnl_cards(db_connection)
        
        # Register Flask routes
        app.register_blueprint(pnl_bp)
        
        logger.info("🚀 All services initialized successfully")
    
    # Run async initialization
    asyncio.run(init_services())
    
    # Determine mode
    mode = (os.environ.get("CPM_MODE") or "api").strip().lower()
    if not mode:
        mode = "api"
    
    logger.info("Startup settings: %s", safe_settings_summary(settings))
    
    def _notify_failure(message: str) -> None:
        webhook = (settings.health_webhook_url or "").strip() if settings.health_webhook_url else ""
        if not webhook:
            return

        msg = str(message).strip()
        if len(msg) > 1800:
            msg = msg[:1800] + "..."

        try:
            payload = WebhookPayload(content=msg)
            send_webhook(webhook, payload, timeout_seconds=settings.request_timeout_seconds)
        except Exception as e:
            logger.warning("failure webhook send failed error=%s", type(e).__name__)
    
    try:
        if mode == "api":
            # Start Flask API server
            port = int(os.getenv('PORT', 5000))
            debug = os.getenv('ENVIRONMENT', 'development') == 'development'
            
            logger.info(f"🌟 Starting P&L Card API server on port {port}")
            app.run(host='0.0.0.0', port=port, debug=debug)
            return 0
            
        elif mode == "health":
            # Original health check logic
            base_url = (settings.base_url or "").strip()
            if settings.upstream == "dev" and not base_url:
                logger.error("Missing required setting: base_url")
                _notify_failure("CPM startup FAILED: missing base_url")
                return 2

            if settings.upstream == "dev":
                client = HttpClient(base_url=base_url, timeout_seconds=settings.request_timeout_seconds)
            else:
                polymarket_url = settings.polymarket_base_url or "https://clob.polymarket.com"
                client = HttpClient(base_url=polymarket_url, timeout_seconds=settings.request_timeout_seconds)
            
            try:
                health = client.get_json("/health")
                if not isinstance(health, dict):
                    logger.error("Health check returned unexpected JSON type: %s", type(health).__name__)
                    _notify_failure(
                        f"CPM health FAILED: unexpected JSON type={type(health).__name__} upstream={settings.upstream}"
                    )
                    return 1

                logger.info("Health check OK. Keys: %s", sorted(list(health.keys())))
                return 0
            except Exception as e:
                logger.error("Health check failed error=%s", type(e).__name__)
                _notify_failure(f"CPM health FAILED: {type(e).__name__} upstream={settings.upstream}")
                return 1
                
        elif mode == "monitor":
            # Original monitor logic
            base_url = (settings.base_url or "").strip()
            if settings.upstream == "dev" and not base_url:
                logger.error("Missing required setting: base_url")
                _notify_failure("CPM startup FAILED: missing base_url")
                return 2

            if settings.upstream == "dev":
                client = HttpClient(base_url=base_url, timeout_seconds=settings.request_timeout_seconds)
            else:
                polymarket_url = settings.polymarket_base_url or "https://clob.polymarket.com"
                client = HttpClient(base_url=polymarket_url, timeout_seconds=settings.request_timeout_seconds)
            
            rules: list[AlertRule] = []
            for rule_dict in settings.rules:
                if not isinstance(rule_dict, dict):
                    logger.warning("Skipping invalid rule: not a dict")
                    continue

                market_id = rule_dict.get("market_id")
                if not market_id:
                    logger.warning("Skipping rule: missing market_id")
                    continue

                try:
                    rule = AlertRule.model_validate(rule_dict)
                    rules.append(rule)
                except Exception:
                    logger.warning("Skipping rule: validation failed market_id=%s", market_id)
                    continue

            if not rules:
                logger.warning("no rules configured")

            try:
                run_monitor(
                    client,
                    poll_interval_seconds=settings.poll_interval_seconds,
                    rules=rules,
                    webhook_url=settings.webhook_url,
                    request_timeout_seconds=settings.request_timeout_seconds,
                    upstream=settings.upstream,
                    polymarket_base_url=settings.polymarket_base_url,
                    polymarket_markets=settings.polymarket_markets,
                    price_provider=settings.price_provider,
                    price_symbol=settings.price_symbol,
                    price_interval_minutes=settings.price_interval_minutes,
                )
                return 0
            except HttpClientError as e:
                logger.error("monitor failed: %s", str(e))
                _notify_failure(
                    f"CPM monitor FAILED: {str(e)[:200]} upstream={settings.upstream}"
                )
                return 1
            except Exception as e:
                logger.error("monitor crashed error=%s", type(e).__name__)
                _notify_failure(
                    f"CPM monitor CRASHED: {type(e).__name__} upstream={settings.upstream}"
                )
                return 1

        else:
            logger.error("Invalid CPM_MODE: %s", mode)
            _notify_failure(f"CPM startup FAILED: invalid CPM_MODE={mode}")
            return 2

    except HttpClientError as e:
        logger.error("Health check failed: %s", str(e))
        _notify_failure(f"CPM health FAILED: {str(e)[:200]} upstream={settings.upstream}")
        return 1
    except Exception as e:
        logger.error("startup failed error=%s", type(e).__name__)
        _notify_failure(f"CPM startup FAILED: {type(e).__name__} upstream={settings.upstream}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
