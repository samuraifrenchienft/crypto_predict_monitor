#!/usr/bin/env python3
"""Send changelog to Discord webhook"""
import os
import requests
from datetime import datetime

# Load webhook URL from environment
webhook_url = os.getenv("CPM_WEBHOOK_URL", "")

if not webhook_url:
    print("ERROR: CPM_WEBHOOK_URL not set")
    exit(1)

# Changelog message
changelog = {
    "embeds": [{
        "title": "🔧 CPM Bot Configuration Update",
        "description": "**Minimum Spread Threshold Lowered to 1.0%**",
        "color": 0x00ff00,  # Green
        "fields": [
            {
                "name": "📊 Changes Made",
                "value": (
                    "• **Min Spread**: 1.5% → **1.0%**\n"
                    "• **Good Tier**: Now triggers at 1.0%+ spread\n"
                    "• **Fair Tier**: Adjusted to 0.75%+ spread\n"
                    "• All config files synchronized"
                ),
                "inline": False
            },
            {
                "name": "📁 Files Updated",
                "value": (
                    "• `config.yaml`\n"
                    "• `src/arbitrage_config.py`\n"
                    "• `scripts/render_startup.py`\n"
                    "• `bot/tiered_arbitrage_filter.py`\n"
                    "• `bot/config.py`"
                ),
                "inline": False
            },
            {
                "name": "🎯 Updated Tier System",
                "value": (
                    "🔵 **Exceptional**: 3.0%+ spread\n"
                    "🟢 **Excellent**: 2.51%+ spread\n"
                    "💛 **Very Good**: 2.01%+ spread\n"
                    "🟠 **Good**: 1.0%+ spread ← YOUR STRATEGY\n"
                    "⚪ **Fair**: 0.75%+ (filtered out)\n"
                    "⚫ **Poor**: <0.75% (filtered out)"
                ),
                "inline": False
            },
            {
                "name": "✅ Impact",
                "value": (
                    "• More opportunities will be detected\n"
                    "• Discord alerts will trigger at 1.0%+ spread\n"
                    "• Better coverage of arbitrage opportunities\n"
                    "• No conflicts between config files"
                ),
                "inline": False
            },
            {
                "name": "🚀 Next Steps",
                "value": (
                    "1. Deploy to Render (auto-deploy enabled)\n"
                    "2. Monitor logs for increased opportunity detection\n"
                    "3. Watch for Discord alerts at new 1.0% threshold"
                ),
                "inline": False
            }
        ],
        "footer": {
            "text": f"CPM Monitor | Updated {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"
        },
        "timestamp": datetime.utcnow().isoformat()
    }],
    "username": "CPM Configuration Bot"
}

# Send to Discord
try:
    response = requests.post(webhook_url, json=changelog, timeout=10)
    if response.status_code == 204:
        print("✅ Changelog sent to Discord successfully")
    else:
        print(f"❌ Discord API returned {response.status_code}: {response.text}")
except Exception as e:
    print(f"❌ Failed to send changelog: {e}")
