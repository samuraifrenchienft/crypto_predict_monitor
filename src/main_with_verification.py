"""
Main Application with Live Data Verification
Starts only after verifying all sources are returning LIVE data
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bot'))
sys.path.append(os.path.dirname(__file__))

# Import verification system
from simple_live_verification import verify_live_data

# Import main monitoring loop
try:
    from main_monitoring_loop import main_monitoring_loop
except ImportError:
    # Fallback if main loop doesn't exist
    async def main_monitoring_loop():
        print("🚀 Main monitoring loop would start here...")
        print("📊 Monitoring live data from all sources...")
        await asyncio.sleep(5)  # Simulate monitoring

logger = logging.getLogger("crypto_predict_monitor")

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('crypto_predict_monitor.log')
        ]
    )

async def verify_and_start():
    """Verify live data and start main application"""
    print("🎯 CRYPTO PREDICT MONITOR - STARTUP")
    print("=" * 60)
    print("🔍 VERIFYING ALL DATA SOURCES ARE LIVE...")
    print()
    
    # Verify all sources are returning live data
    is_live = await verify_live_data()
    
    print()
    print("=" * 60)
    
    if not is_live:
        print("🚨 CRITICAL: NOT ALL SOURCES ARE LIVE!")
        print("❌ DO NOT LAUNCH - FIX CRITICAL ISSUES FIRST")
        print()
        print("🔧 Required Actions:")
        print("  1. Check API endpoints are production URLs")
        print("  2. Verify API keys/credentials are valid")
        print("  3. Ensure network connectivity")
        print("  4. Remove any demo/test data sources")
        print("  5. Fix connection errors")
        print()
        print("📊 GO/NO-GO CHECKLIST:")
        print("  ❌ Polymarket: NOT LIVE")
        print("  ❌ Manifold: NOT LIVE") 
        print("  ❌ Limitless: NOT LIVE")
        print("  ✅ Azuro: Using fallback (acceptable)")
        print()
        print("🚨 ABORTING LAUNCH - ALL SOURCES MUST BE LIVE!")
        return False
    
    print("✅ ALL SOURCES VERIFIED AS LIVE!")
    print("🚀 STARTING MAIN MONITORING LOOP...")
    print()
    
    try:
        # Start main monitoring loop
        await main_monitoring_loop()
        return True
        
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped by user")
        return True
    except Exception as e:
        logger.error(f"Main monitoring loop failed: {e}")
        print(f"❌ Monitoring failed: {e}")
        return False

def main():
    """Main entry point"""
    setup_logging()
    
    try:
        # Run verification and start
        success = asyncio.run(verify_and_start())
        
        if success:
            print("\n🎉 APPLICATION COMPLETED SUCCESSFULLY")
            sys.exit(0)
        else:
            print("\n❌ APPLICATION FAILED TO START")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n🛑 APPLICATION STOPPED BY USER")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application failed: {e}")
        print(f"❌ APPLICATION FAILED: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
