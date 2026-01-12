import asyncio
from bot.adapters.kalshi import KalshiAdapter

async def test_websocket():
    """Test WebSocket connection with authentication"""
    
    adapter = KalshiAdapter(
        kalshi_access_key="7462d858-3aa1-4cda-936e-48551efcf81f",
        kalshi_private_key=None  # Will load from PEM file
    )
    
    # Check if keys are loaded
    print(f"Access key: {adapter.kalshi_access_key}")
    print(f"Private key loaded: {adapter.kalshi_private_key is not None}")
    
    # Try to connect to WebSocket
    try:
        await adapter.connect_websocket()
        print("✓ WebSocket connected successfully")
        
        # Try to subscribe
        await adapter.subscribe_to_markets(
            channels=["orderbook_delta"],
            market_tickers=["KXMVESPORTSMULTIGAMEEXTENDED-S202504B73C89560-FDE43D216B4"],
            endpoint="/orderbook_delta"
        )
        print("✓ Subscribed to orderbook updates")
        
        # Wait a bit for messages
        await asyncio.sleep(2)
        
        await adapter.close()
    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_websocket())
