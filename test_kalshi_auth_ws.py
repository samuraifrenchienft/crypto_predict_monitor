import asyncio
import os
from bot.adapters.kalshi import KalshiAdapter

async def test_authenticated_websocket():
    # Get credentials from environment variables
    access_key = os.getenv("KALSHI_ACCESS_KEY")
    private_key = os.getenv("KALSHI_PRIVATE_KEY")
    
    if not access_key or not private_key:
        print("Error: Set KALSHI_ACCESS_KEY and KALSHI_PRIVATE_KEY environment variables")
        return
    
    adapter = KalshiAdapter(
        kalshi_access_key=access_key,
        kalshi_private_key=private_key
    )
    
    def handle_update(data):
        print(f"Received update: {data}")
    
    try:
        # Get some market tickers
        markets = await adapter.list_active_markets()
        tickers = [m.market_id for m in markets[:3]]
        print(f"Subscribing to markets: {tickers}")
        
        # Connect and subscribe
        await adapter.connect_websocket()
        await adapter.subscribe_to_markets(["orderbook"], tickers)
        
        # Listen for updates (will run for 30 seconds)
        print("Listening for updates...")
        await asyncio.wait_for(adapter.listen_to_updates(handle_update), timeout=30)
        
    except asyncio.TimeoutError:
        print("Test completed (30 second timeout)")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(test_authenticated_websocket())
