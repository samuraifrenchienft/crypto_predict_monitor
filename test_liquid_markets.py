import asyncio
from bot.adapters.kalshi import KalshiAdapter

async def test_liquid_markets():
    """Test multiple markets to find one with liquidity"""
    
    adapter = KalshiAdapter(
        kalshi_access_key="7462d858-3aa1-4cda-936e-48551efcf81f",
        kalshi_private_key=None
    )
    
    print("=== Finding Markets with Liquidity ===")
    markets = await adapter.list_active_markets()
    
    # Test first 10 markets
    for i, market in enumerate(markets[:10]):
        print(f"\nTesting market {i+1}: {market.title[:50]}...")
        outcomes = await adapter.list_outcomes(market)
        
        quotes = await adapter.get_quotes(market, outcomes)
        has_liquidity = any(q.bid is not None or q.ask is not None for q in quotes)
        
        if has_liquidity:
            print(f"✓ Found market with liquidity!")
            for q in quotes:
                print(f"  {q.outcome_id}: bid={q.bid}, ask={q.ask}, spread={q.spread}")
            break
        else:
            print(f"  No liquidity (all bid/ask are None)")
    
    # Also test WebSocket subscription
    print("\n=== Testing WebSocket Subscription ===")
    try:
        await adapter.connect_websocket()
        await adapter.subscribe_to_markets(
            channels=["orderbook_delta"],
            market_tickers=[markets[0].market_id],
            endpoint="/trade-api/ws/v2"
        )
        print("✓ Subscribed to WebSocket updates")
        
        # Wait for messages
        await asyncio.sleep(2)
        
        await adapter.close()
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    asyncio.run(test_liquid_markets())
