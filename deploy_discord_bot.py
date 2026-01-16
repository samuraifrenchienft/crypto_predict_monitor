#!/usr/bin/env python
"""
Discord Bot Deployment Script
Tests and activates the real Discord alert bot
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_discord_alerts():
    """Test Discord alert system"""
    print("🔧 Testing Discord Alert System...")
    
    # Load environment
    load_dotenv()
    
    # Check Discord webhook configuration
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    health_webhook_url = os.getenv("DISCORD_HEALTH_WEBHOOK_URL")
    
    print(f"📡 Main Webhook: {'✅ Configured' if webhook_url else '❌ Missing'}")
    print(f"🏥 Health Webhook: {'✅ Configured' if health_webhook_url else '❌ Missing'}")
    
    if not webhook_url:
        print("\n❌ DISCORD_WEBHOOK_URL not set in environment")
        print("Please set it in your .env file:")
        print("DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN")
        return False
    
    # Test Discord alert
    try:
        from utils.discord_alerts import DiscordAlerter, AlertData
        from datetime import datetime, timedelta
        
        async with DiscordAlerter() as alerter:
            # Create test alert
            test_alert = AlertData(
                market_question="DEPLOYMENT TEST: Will this Discord alert work?",
                yes_bid=0.45,
                yes_ask=0.47,
                no_bid=0.53,
                no_ask=0.55,
                spread=0.08,
                est_profit=8.00,
                profit_margin=1.6,
                market_link="https://polymarket.com",
                expires_at=datetime.utcnow() + timedelta(hours=1),
                liquidity="Test",
                market_source="deployment_test"
            )
            
            print("📤 Sending test Discord alert...")
            success = await alerter.send_alert(test_alert, detailed=True)
            
            if success:
                print("✅ Discord alert sent successfully!")
                return True
            else:
                print("❌ Failed to send Discord alert")
                return False
                
    except Exception as e:
        print(f"❌ Error testing Discord alerts: {e}")
        return False

async def start_main_bot():
    """Start the main bot application"""
    print("\n🚀 Starting Main Bot Application...")
    
    try:
        # Start the integrated system
        from main_integration import app
        import uvicorn
        
        print("🌟 Starting P&L Tracking System with Discord alerts...")
        print("📡 Discord alerts: ACTIVE")
        print("🔄 Arbitrage detection: ACTIVE")
        print("📊 P&L tracking: ACTIVE")
        
        # Run the server
        uvicorn.run(
            "main_integration:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Production mode
            log_level="info"
        )
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        return False

async def main():
    """Main deployment function"""
    print("⚔️ Samurai Frenchie Discord Bot Deployment")
    print("=" * 50)
    
    # Test Discord alerts first
    discord_ok = await test_discord_alerts()
    
    if not discord_ok:
        print("\n❌ Discord alerts not configured properly")
        print("Please configure your Discord webhook URLs in .env file")
        return
    
    print("\n✅ Discord alerts ready!")
    
    # Start the main bot
    await start_main_bot()

if __name__ == "__main__":
    asyncio.run(main())
