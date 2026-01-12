import asyncio
import os
from dotenv import load_dotenv
load_dotenv('.env')

from bot.adapters.kalshi import KalshiAdapter

async def test_kalshi_auth():
    """Test Kalshi adapter with authentication"""
    
    # Create adapter with None to force PEM file loading
    adapter = KalshiAdapter(
        kalshi_access_key="7462d858-3aa1-4cda-936e-48551efcf81f",
        kalshi_private_key=None  # Will load from PEM file
    )
    
    print("=== Testing Market List ===")
    markets = await adapter.list_active_markets()
    print(f"Found {len(markets)} markets")
    
    if markets:
        print(f"\nTesting market: {markets[0].title[:50]}...")
        outcomes = await adapter.list_outcomes(markets[0])
        print(f"Outcomes: {[o.name for o in outcomes]}")
        
        print("\n=== Testing HTTP Orderbook (Authenticated) ===")
        quotes = await adapter.get_quotes(markets[0], outcomes)
        for q in quotes:
            print(f"{q.outcome_id}: bid={q.bid}, ask={q.ask}, spread={q.spread}")
        
        print("\n=== Testing Exchange Status ===")
        status = await adapter.check_exchange_status()
        print(f"Exchange status: {status}")
        
        print("\n=== Testing WebSocket ===")
        try:
            await adapter.connect_websocket()
            print("✓ WebSocket connected successfully")
            await adapter.close()
        except Exception as e:
            print(f"WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_kalshi_auth())
