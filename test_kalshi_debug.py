import asyncio
import os
from dotenv import load_dotenv
load_dotenv(".env")

# Helper to get env vars (handles PowerShell format)
def get_env(key: str):
    # Try standard env var first
    value = os.getenv(key)
    if value:
        return value.strip().strip('"').strip("'")
    
    # Try PowerShell format (remove $env: and quotes)
    ps_key = key.replace("KALSHI_", "env:KALSHI_")
    value = os.getenv(ps_key)
    if value:
        return value.strip().strip('"').strip("'")
    
    return None

from bot.adapters.kalshi import KalshiAdapter

async def test_kalshi():
    access_key = get_env("KALSHI_ACCESS_KEY")
    private_key = get_env("KALSHI_PRIVATE_KEY")
    
    print(f"Access Key: {access_key}")
    print(f"Private Key (first 50): {private_key[:50] if private_key else 'None'}")
    print(f"Private Key starts with PEM: {private_key.startswith('-----BEGIN') if private_key else 'None'}")
    
    adapter = KalshiAdapter(
        kalshi_access_key=access_key,
        kalshi_private_key=private_key
    )
    
    try:
        # Test 1: Get markets
        print("=== Testing Market List ===")
        markets = await adapter.list_active_markets()
        print(f"Found {len(markets)} markets")
        
        if markets:
            m = markets[0]
            print(f"\nTesting market: {m.title[:50]}...")
            
            # Test 2: Get outcomes
            outcomes = await adapter.list_outcomes(m)
            print(f"Outcomes: {[o.name for o in outcomes]}")
            
            # Test 3: Get quotes (HTTP API)
            print("\n=== Testing HTTP Orderbook ===")
            quotes = await adapter.get_quotes(m, outcomes)
            for q in quotes:
                print(f"{q.outcome_id[-3:]}: bid={q.bid}, ask={q.ask}, spread={q.spread}")
            
            # Test 4: Try WebSocket
            print("\n=== Testing WebSocket ===")
            try:
                await adapter.subscribe_to_orderbook_deltas([m.market_id])
                print("WebSocket subscription successful!")
                
                # Listen for a few seconds
                async def handle_msg(data):
                    print(f"WS Message: {data}")
                
                await asyncio.wait_for(adapter.listen_to_updates(handle_msg), timeout=5)
            except Exception as e:
                print(f"WebSocket error: {e}")
        
    finally:
        await adapter.close()

if __name__ == "__main__":
    asyncio.run(test_kalshi())
