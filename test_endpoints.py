import asyncio
from bot.adapters.kalshi import KalshiAdapter

async def test_endpoints():
    """Test different WebSocket endpoints"""
    
    adapter = KalshiAdapter(
        kalshi_access_key="7462d858-3aa1-4cda-936e-48551efcf81f",
        kalshi_private_key=None
    )
    
    endpoints = [
        "/trade-api/ws/v2",
        "/trade-api/ws/v2/orderbook_delta",
        "/trade-api/ws/v2/ticker",
        "/trade-api/ws/v2/market_lifecycle_v2",
        "/ws/v2",
        "/ws/v2/orderbook_delta"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"\nTesting endpoint: {endpoint}")
            await adapter.connect_websocket()
            print(f"✓ Connected to base WebSocket")
            
            # Try to subscribe to this endpoint
            await adapter.subscribe_to_markets(
                channels=["orderbook_delta"],
                market_tickers=["KXMVESPORTSMULTIGAMEEXTENDED-S202504B73C89560-FDE43D216B4"],
                endpoint=endpoint
            )
            print(f"✓ Subscribed to {endpoint}")
            
            await adapter.close()
            break
        except Exception as e:
            print(f"✗ Failed: {e}")
            await adapter.close()

if __name__ == "__main__":
    asyncio.run(test_endpoints())
