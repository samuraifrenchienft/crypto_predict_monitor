"""
P&L Card Integration for Main Application
Add this to your main.py to initialize the P&L card service
"""

import asyncio
import logging
from pathlib import Path

# Add these imports to your main.py
from src.social.pnl_card_generator import PnLCardService
from src.api.routes.pnl_cards import init_pnl_service, pnl_bp
from src.utils.s3_uploader import init_s3_uploader, is_s3_available

logger = logging.getLogger(__name__)

# Global P&L card service
pnl_card_service = None

async def initialize_pnl_cards(app, db_connection=None):
    """Initialize P&L card service and routes"""
    global pnl_card_service
    
    try:
        # Initialize background image path
        bg_path = "assets/valhalla_viral_bg.png"
        if not Path(bg_path).exists():
            logger.warning(f"Background image not found at {bg_path}, using default")
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
            logger.info("S3 uploader initialized")
        
        logger.info("✅ P&L Card Service initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize P&L Card Service: {e}")
        raise

# Add to your existing Flask app initialization
def create_app():
    """Your existing app creation function - modify this"""
    app = Flask(__name__)
    
    # ... your existing app setup ...
    
    # Initialize P&L cards
    asyncio.run(initialize_pnl_cards(app, db_connection))
    
    return app

# For FastAPI users:
async def init_fastapi_app():
    """Initialize P&L cards for FastAPI"""
    from fastapi import FastAPI
    
    app = FastAPI()
    
    # Initialize P&L cards
    await initialize_pnl_cards(app, db_connection)
    
    return app
