"""
Health check endpoint for arbitrage bot on Render
"""

from flask import Flask, jsonify
import os
import asyncio
from arbitrage_main import ProfessionalArbitrageSystem

app = Flask(__name__)

@app.route('/health')
def health_check():
    """Health check endpoint for Render"""
    return jsonify({
        'status': 'healthy',
        'service': 'crypto-arbitrage-bot',
        'mode': 'production'
    })

@app.route('/')
def index():
    """Basic info endpoint"""
    return jsonify({
        'service': 'Crypto Arbitrage Bot',
        'status': 'running',
        'description': '24/7 arbitrage monitoring and Discord alerts'
    })

if __name__ == '__main__':
    # Run health check server
    app.run(host='0.0.0.0', port=5000)
