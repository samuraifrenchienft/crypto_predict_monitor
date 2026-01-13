"""
P&L Card API Routes
Flask/FastAPI endpoints for P&L card generation and sharing
"""

from flask import Blueprint, send_file, jsonify, request
import io
import logging
from datetime import datetime
from typing import Optional

from src.social.pnl_card_generator import PnLCardService

logger = logging.getLogger(__name__)

# Create blueprint
pnl_bp = Blueprint('pnl_cards', __name__, url_prefix='/api/pnl-card')

# Global service instance (will be initialized in main.py)
pnl_card_service: Optional[PnLCardService] = None

def init_pnl_service(db_connection=None, background_image_path: str = None):
    """Initialize P&L card service"""
    global pnl_card_service
    pnl_card_service = PnLCardService(
        db_connection=db_connection,
        background_image_path=background_image_path
    )
    logger.info("P&L Card Service initialized")

def require_auth(f):
    """Simple auth decorator - replace with your actual auth"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # TODO: Implement your actual authentication logic
        # This is a placeholder that checks for a simple token
        
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({"error": "Authorization required"}), 401
        
        # For now, we'll just extract user_id from the token
        # In production, validate the token properly
        try:
            user_id = token.split(' ')[1]  # Simplified - use proper JWT validation
            request.user = type('User', (), {'id': user_id, 'is_admin': False})()
        except:
            return jsonify({"error": "Invalid token"}), 401
            
        return f(*args, **kwargs)
    return decorated_function

@pnl_bp.route('/<user_id>', methods=['GET'])
@require_auth
def download_card(user_id: str):
    """Download P&L card as PNG"""
    
    # Security check
    if request.user.id != user_id and not request.user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    
    if not pnl_card_service:
        return jsonify({"error": "Service not initialized"}), 500
    
    try:
        import asyncio
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        card_bytes, snapshot = loop.run_until_complete(pnl_card_service.generate_card_bytes(user_id))
        loop.close()
        
        if not card_bytes:
            return jsonify({"error": "No P&L data for this user"}), 404
        
        return send_file(
            io.BytesIO(card_bytes),
            mimetype='image/png',
            as_attachment=True,
            download_name=f"pnl_{user_id}_{datetime.now().strftime('%Y%m%d')}.png"
        )
    except Exception as e:
        logger.error(f"Card generation error: {e}")
        return jsonify({"error": "Failed to generate card"}), 500

@pnl_bp.route('/<user_id>/share', methods=['GET'])
@require_auth
def share_card(user_id: str):
    """Get shareable card metadata"""
    
    if request.user.id != user_id and not request.user.is_admin:
        return jsonify({"error": "Unauthorized"}), 403
    
    if not pnl_card_service:
        return jsonify({"error": "Service not initialized"}), 500
    
    try:
        import asyncio
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        card_bytes, snapshot = loop.run_until_complete(pnl_card_service.generate_card_bytes(user_id))
        loop.close()
        
        if not snapshot:
            return jsonify({"error": "No P&L data"}), 404
        
        # Generate share text
        pnl_emoji = "🚀" if snapshot.total_pnl_percentage >= 0 else "📉"
        share_text = (
            f"{pnl_emoji} {snapshot.total_pnl_percentage:+.2f}% on {snapshot.predictions_count} "
            f"crypto predictions! {snapshot.win_rate:.0f}% win rate. "
            f"Check it out on Crypto Predict Monitor! #trading #crypto"
        )
        
        return jsonify({
            "user": snapshot.username,
            "pnl_percentage": snapshot.total_pnl_percentage,
            "pnl_usd": snapshot.total_pnl_usd,
            "period": snapshot.period,
            "win_rate": snapshot.win_rate,
            "trades": snapshot.predictions_count,
            "volume": snapshot.total_volume,
            "share_text": share_text,
            "generated_at": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Share metadata error: {e}")
        return jsonify({"error": str(e)}), 500

@pnl_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "pnl_cards",
        "initialized": pnl_card_service is not None,
        "timestamp": datetime.utcnow().isoformat()
    })

# Error handlers
@pnl_bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@pnl_bp.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

# Rate limiting (simple implementation)
from collections import defaultdict
from time import time

rate_limits = defaultdict(list)

def check_rate_limit(user_id: str, limit: int = 5, window: int = 300) -> bool:
    """Check if user is within rate limit"""
    now = time()
    user_requests = rate_limits[user_id]
    
    # Remove old requests outside window
    rate_limits[user_id] = [req_time for req_time in user_requests if now - req_time < window]
    
    if len(rate_limits[user_id]) >= limit:
        return False
    
    rate_limits[user_id].append(now)
    return True

# Add rate limiting to endpoints
@pnl_bp.before_request
def limit_requests():
    """Apply rate limiting to all endpoints"""
    if hasattr(request, 'user') and request.user:
        if not check_rate_limit(request.user.id):
            return jsonify({"error": "Rate limit exceeded"}), 429
