from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy", 
        "service": "Samurai Frenchie P&L Cards",
        "timestamp": datetime.utcnow().isoformat()
    })

@app.route('/api/health')
def api_health():
    return jsonify({
        "status": "healthy",
        "endpoints": {
            "health": "/health",
            "api_health": "/api/health",
            "markets": "/api/markets",
            "user_stats": "/api/user/<user_id>/stats",
            "pnl_card": "/api/pnl-card/<user_id>",
            "pnl_card_share": "/api/pnl-card/<user_id>/share"
        }
    })

@app.route('/api/markets')
def markets():
    return jsonify({
        "markets": [
            {"name": "LIMITLESS", "status": "active", "pairs": 45},
            {"name": "MANIFOLD", "status": "active", "markets": 120},
            {"name": "POLYMARKET", "status": "active", "contracts": 89}
        ]
    })

@app.route('/api/user/<user_id>/stats')
def user_stats(user_id):
    try:
        # Mock data for testing - in production this would fetch from database
        mock_data = [
            {'user_id': user_id, 'pnl': 100.50, 'created_at': '2024-01-01'},
            {'user_id': user_id, 'pnl': -25.00, 'created_at': '2024-01-02'}
        ]
        
        total_pnl = sum(trade['pnl'] for trade in mock_data)
        total_trades = len(mock_data)
        
        return jsonify({
            "user_id": user_id,
            "total_trades": total_trades,
            "total_pnl": total_pnl,
            "win_rate": 75.0 if total_trades > 0 else 0,
            "avg_trade_size": total_pnl / total_trades if total_trades > 0 else 0,
            "last_updated": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Failed to fetch user stats: {str(e)}"}), 500

@app.route('/api/pnl-card/<user_id>/share')
def pnl_card_share(user_id):
    try:
        # Mock P&L data
        pnl_data = [
            {'user_id': user_id, 'pnl': 200.75, 'created_at': '2024-01-01'}
        ]
        
        total_pnl = sum(trade['pnl'] for trade in pnl_data)
        
        share_text = f"🎯 Samurai Frenchie P&L: ${total_pnl:.2f} | {len(pnl_data)} trades"
        card_url = f"https://samurai-frenchie.com/pnl-card/{user_id}"
        
        return jsonify({
            "user_id": user_id,
            "share_text": share_text,
            "card_url": card_url,
            "total_pnl": total_pnl,
            "trade_count": len(pnl_data),
            "generated_at": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Failed to generate share card: {str(e)}"}), 500

@app.route('/api/pnl-card/<user_id>')
def pnl_card_download(user_id):
    try:
        # Mock card generation
        return jsonify({
            "user_id": user_id,
            "download_url": f"https://samurai-frenchie.com/downloads/pnl-card-{user_id}.png",
            "card_url": f"https://samurai-frenchie.com/pnl-card/{user_id}",
            "status": "ready",
            "expires_at": (datetime.utcnow().replace(hour=23, minute=59, second=59)).isoformat(),
            "generated_at": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": f"Failed to generate P&L card: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
