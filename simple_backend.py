from flask import Flask, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "crypto_predict_monitor"})

@app.route('/api/health')
def api_health():
    return jsonify({
        "service": "crypto_predict_monitor",
        "status": "healthy",
        "mode": "api",
        "pnl_cards": "ready",
        "endpoints": [
            "/health",
            "/api/health", 
            "/api/markets",
            "/api/pnl-card/<user_id>",
            "/api/pnl-card/<user_id>/share"
        ]
    })

@app.route('/api/markets')
def markets():
    return jsonify({"markets": ["BTC", "ETH", "SOL"]})

@app.route('/api/pnl-card/<user_id>/share')
def share_pnl_card(user_id):
    return jsonify({
        "user_id": user_id,
        "card_url": f"https://your-domain.com/pnl-cards/{user_id}.png",
        "share_text": f"Check out my P&L card!",
        "timestamp": "2026-01-13T07:04:00Z"
    })

@app.route('/api/pnl-card/<user_id>')
def download_pnl_card(user_id):
    return jsonify({
        "message": f"P&L card for {user_id}",
        "status": "ready",
        "download_url": f"https://your-domain.com/pnl-cards/{user_id}.png"
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
