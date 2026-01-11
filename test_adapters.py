import asyncio
from bot.adapters.limitless import LimitlessAdapter
from bot.adapters.polymarket import PolymarketAdapter

async def test():
    # Test Limitless
    print("=== Testing Limitless ===")
    try:
        limitless = LimitlessAdapter('https://api.limitless.exchange')
        markets = await limitless.list_active_markets()
        print(f"Limitless markets: {len(markets)}")
        if markets:
            m = markets[0]
            print(f"First market: {m.title[:50]}")
            outcomes = await limitless.list_outcomes(m)
            quotes = await limitless.get_quotes(m, outcomes)
            print(f"Quotes: {[(q.bid, q.ask, q.mid) for q in quotes]}")
    except Exception as e:
        print(f"Limitless error: {e}")
    
    # Test Polymarket
    print("\n=== Testing Polymarket ===")
    try:
        poly = PolymarketAdapter(
            gamma_base_url='https://gamma-api.polymarket.com',
            clob_base_url='https://clob.polymarket.com',
            data_base_url='https://data-api.polymarket.com',
            events_limit=5
        )
        markets = await poly.list_active_markets()
        print(f"Polymarket markets: {len(markets)}")
        if markets:
            for i, m in enumerate(markets[:3]):
                print(f"\nMarket {i+1}: {m.title[:50]}")
                outcomes = await poly.list_outcomes(m)
                quotes = await poly.get_quotes(m, outcomes)
                print(f"Quotes: {[(round(q.bid, 3) if q.bid else None, round(q.ask, 3) if q.ask else None) for q in quotes]}")
    except Exception as e:
        print(f"Polymarket error: {e}")

asyncio.run(test())
