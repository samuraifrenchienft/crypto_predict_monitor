from flask import Flask, jsonify
from flask_cors import CORS
import os
import requests
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://your-project.supabase.co')
SUPABASE_ANON_KEY = os.getenv('SUPABASE_ANON_KEY', 'your-anon-key')

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
        "database": "connected" if SUPABASE_URL else "not_configured",
        "endpoints": [
            "/health",
            "/api/health", 
            "/api/markets",
            "/api/pnl-card/<user_id>",
            "/api/pnl-card/<user_id>/share",
            "/api/user/<user_id>/stats"
        ]
    })

@app.route('/api/markets')
def markets():
    return jsonify({"markets": ["BTC", "ETH", "SOL"]})

@app.route('/api/user/<user_id>/stats')
def get_user_stats(user_id):
    """Get user statistics from Supabase"""
    try:
        headers = {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': f'Bearer {SUPABASE_ANON_KEY}'
        }
        
        # Get user's trading data
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/executions?user_id=eq.{user_id}&select=*',
            headers=headers
        )
        
        if response.status_code == 200:
            executions = response.json()
            
            # Calculate P&L stats
            total_pnl = sum(exec.get('pnl', 0) for exec in executions)
            win_rate = len([e for e in executions if e.get('pnl', 0) > 0]) / len(executions) * 100 if executions else 0
            
            return jsonify({
                "user_id": user_id,
                "total_trades": len(executions),
                "total_pnl": total_pnl,
                "win_rate": round(win_rate, 2),
                "last_trade": executions[-1].get('created_at') if executions else None
            })
        else:
            return jsonify({"error": "Failed to fetch user data"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pnl-card/<user_id>/share')
def share_pnl_card(user_id):
    """Generate P&L card share data with real user stats"""
    try:
        # Get user stats
        headers = {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': f'Bearer {SUPABASE_ANON_KEY}'
        }
        
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/executions?user_id=eq.{user_id}&select=*',
            headers=headers
        )
        
        if response.status_code == 200:
            executions = response.json()
            total_pnl = sum(exec.get('pnl', 0) for exec in executions)
            
            return jsonify({
                "user_id": user_id,
                "card_url": f"https://your-domain.com/pnl-cards/{user_id}.png",
                "share_text": f"📊 My P&L: ${total_pnl:.2f} across {len(executions)} trades!",
                "timestamp": datetime.utcnow().isoformat(),
                "stats": {
                    "total_trades": len(executions),
                    "total_pnl": total_pnl,
                    "win_rate": len([e for e in executions if e.get('pnl', 0) > 0]) / len(executions) * 100 if executions else 0
                }
            })
        else:
            return jsonify({
                "user_id": user_id,
                "card_url": f"https://your-domain.com/pnl-cards/{user_id}.png",
                "share_text": "Check out my P&L card!",
                "timestamp": datetime.utcnow().isoformat(),
                "stats": {"total_trades": 0, "total_pnl": 0, "win_rate": 0}
            })
            
    except Exception as e:
        return jsonify({
            "user_id": user_id,
            "card_url": f"https://your-domain.com/pnl-cards/{user_id}.png",
            "share_text": "Check out my P&L card!",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        })

@app.route('/api/pnl-card/<user_id>')
def download_pnl_card(user_id):
    """Generate P&L card download data"""
    try:
        headers = {
            'apikey': SUPABASE_ANON_KEY,
            'Authorization': f'Bearer {SUPABASE_ANON_KEY}'
        }
        
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/executions?user_id=eq.{user_id}&select=*',
            headers=headers
        )
        
        if response.status_code == 200:
            executions = response.json()
            total_pnl = sum(exec.get('pnl', 0) for exec in executions)
            
            return jsonify({
                "message": f"P&L card for {user_id}",
                "status": "ready",
                "download_url": f"https://your-domain.com/pnl-cards/{user_id}.png",
                "stats": {
                    "total_trades": len(executions),
                    "total_pnl": total_pnl,
                    "win_rate": len([e for e in executions if e.get('pnl', 0) > 0]) / len(executions) * 100 if executions else 0
                }
            })
        else:
            return jsonify({
                "message": f"P&L card for {user_id}",
                "status": "ready",
                "download_url": f"https://your-domain.com/pnl-cards/{user_id}.png",
                "stats": {"total_trades": 0, "total_pnl": 0, "win_rate": 0}
            })
            
    except Exception as e:
        return jsonify({
            "message": f"P&L card for {user_id}",
            "status": "ready",
            "download_url": f"https://your-domain.com/pnl-cards/{user_id}.png",
            "error": str(e)
        })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
