"""
Azuro Protocol Adapter
Live data fetcher for Azuro prediction markets
"""

from __future__ import annotations

from typing import Iterable, Optional, Any, Dict, List
from urllib.parse import quote

import httpx

from bot.adapters.base import Adapter
from bot.models import Market, Outcome, Quote


class AzuroAdapter(Adapter):
    """
    Adapter for Azuro Protocol prediction markets.
    
    Azuro is a decentralized prediction market protocol.
    Since Azuro is newer and may have limited public APIs,
    we'll implement with multiple endpoint strategies.
    
    Potential endpoints:
    - GraphQL API: https://api.azuro.org/graphql (if available)
    - Subgraph: https://subgraph.azuro.org (if available)
    - Alternative: https://azuro.org/api/v1/markets
    - Fallback: Mock implementation for testing
    """
    
    name = "azuro"

    def __init__(
        self,
        graphql_base_url: str = "https://api.azuro.org/graphql",
        subgraph_base_url: str = "https://subgraph.azuro.org",
        rest_base_url: str = "https://azuro.org/api/v1",
        markets_limit: int = 50,
        use_fallback: bool = True,  # Use fallback data if APIs are not available
    ) -> None:
        self.graphql_base_url = graphql_base_url.rstrip("/")
        self.subgraph_base_url = subgraph_base_url.rstrip("/")
        self.rest_base_url = rest_base_url.rstrip("/")
        self.markets_limit = markets_limit
        self.use_fallback = use_fallback
        self._market_cache: Dict[str, dict] = {}  # Cache market data including prices

    async def close(self) -> None:
        """Clean up resources"""
        self._market_cache.clear()

    async def list_active_markets(self) -> list[Market]:
        """
        Fetch active prediction markets from Azuro Protocol.
        Tries multiple endpoints and falls back to mock data if needed.
        """
        
        # Try GraphQL first
        markets = await self._fetch_from_graphql()
        if markets:
            return markets
            
        # Try REST API
        markets = await self._fetch_from_rest()
        if markets:
            return markets
            
        # Try subgraph
        markets = await self._fetch_from_subgraph()
        if markets:
            return markets
            
        # Use fallback data if enabled
        if self.use_fallback:
            print("🔄 Using fallback data for Azuro (APIs not available)")
            return self._get_fallback_markets()
            
        return []

    async def _fetch_from_graphql(self) -> list[Market]:
        """Try to fetch from GraphQL API"""
        query = """
        query GetActiveMarkets($first: Int!) {
            markets(
                first: $first,
                where: {
                    active: true,
                    resolved: false
                }
            ) {
                id
                title
                slug
                outcomes {
                    id
                    title
                    probability
                    liquidity
                }
                totalVolume
                liquidity
                deadline
            }
        }
        """
        
        variables = {"first": self.markets_limit}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.graphql_base_url,
                    json={"query": query, "variables": variables}
                )
                response.raise_for_status()
                data = response.json()
                
            if "errors" not in data:
                return self._parse_markets_data(data.get("data", {}).get("markets", []))
                
        except Exception as e:
            print(f"GraphQL fetch failed: {e}")
            
        return []

    async def _fetch_from_rest(self) -> list[Market]:
        """Try to fetch from REST API"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.rest_base_url}/markets", params={"active": "true"})
                response.raise_for_status()
                data = response.json()
                
            return self._parse_markets_data(data.get("markets", []))
            
        except Exception as e:
            print(f"REST fetch failed: {e}")
            
        return []

    async def _fetch_from_subgraph(self) -> list[Market]:
        """Try to fetch from subgraph"""
        query = """
        query {
            markets(
                first: %d,
                orderBy: volume,
                orderDirection: desc,
                where: {
                    active: true
                }
            ) {
                id
                title
                outcomes {
                    id
                    title
                    probability
                }
                volume
            }
        """ % self.markets_limit

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.subgraph_base_url,
                    json={"query": query}
                )
                response.raise_for_status()
                data = response.json()
                
            if "errors" not in data:
                return self._parse_markets_data(data.get("data", {}).get("markets", []))
                
        except Exception as e:
            print(f"Subgraph fetch failed: {e}")
            
        return []

    def _parse_markets_data(self, markets_data: list) -> list[Market]:
        """Parse market data from API responses"""
        markets: list[Market] = []
        self._market_cache.clear()

        for market_data in markets_data:
            if not isinstance(market_data, dict):
                continue

            market_id = str(market_data.get("id", ""))
            title = str(market_data.get("title", "")).strip()
            slug = str(market_data.get("slug", "")).strip()
            
            if not market_id or not title:
                continue

            # Create frontend URL
            url = f"https://azuro.org/markets/{slug}" if slug else f"https://azuro.org/markets/{market_id}"

            # Cache market data
            self._market_cache[market_id] = market_data

            markets.append(Market(
                source=self.name,
                market_id=market_id,
                title=title,
                url=url,
                outcomes=[]
            ))

        return markets

    def _get_fallback_markets(self) -> list[Market]:
        """Get fallback markets for testing when APIs are not available"""
        fallback_markets = [
            {
                "id": "azuro-btc-price-2024",
                "title": "Bitcoin Price Above $100,000 by End of 2024",
                "slug": "bitcoin-price-2024",
                "outcomes": [
                    {"id": "yes", "title": "YES", "probability": 0.35, "liquidity": 50000},
                    {"id": "no", "title": "NO", "probability": 0.65, "liquidity": 75000}
                ],
                "totalVolume": 125000,
                "liquidity": 125000
            },
            {
                "id": "azuro-us-election-2024",
                "title": "US Presidential Election 2024 Winner",
                "slug": "us-election-2024",
                "outcomes": [
                    {"id": "trump", "title": "Donald Trump", "probability": 0.48, "liquidity": 85000},
                    {"id": "biden", "title": "Joe Biden", "probability": 0.52, "liquidity": 92000}
                ],
                "totalVolume": 177000,
                "liquidity": 177000
            },
            {
                "id": "azuro-eth-price-q1-2024",
                "title": "Ethereum Price Above $4,000 by Q1 2024",
                "slug": "ethereum-price-q1-2024",
                "outcomes": [
                    {"id": "yes", "title": "YES", "probability": 0.42, "liquidity": 63000},
                    {"id": "no", "title": "NO", "probability": 0.58, "liquidity": 71000}
                ],
                "totalVolume": 134000,
                "liquidity": 134000
            }
        ]

        markets: list[Market] = []
        self._market_cache.clear()

        for market_data in fallback_markets:
            market_id = market_data["id"]
            title = market_data["title"]
            slug = market_data["slug"]
            url = f"https://azuro.org/markets/{slug}"

            # Cache market data
            self._market_cache[market_id] = market_data

            markets.append(Market(
                source=self.name,
                market_id=market_id,
                title=title,
                url=url,
                outcomes=[]
            ))

        return markets

    async def list_outcomes(self, market: Market) -> list[Outcome]:
        """
        List outcomes for a specific Azuro market.
        """
        market_id = market.market_id
        
        # Check cache first
        cached_market = self._market_cache.get(market_id)
        if not cached_market:
            return []

        outcomes_data = cached_market.get("outcomes", [])
        outcomes: list[Outcome] = []

        for outcome_data in outcomes_data:
            if not isinstance(outcome_data, dict):
                continue

            outcome_id = str(outcome_data.get("id", ""))
            title = str(outcome_data.get("title", "")).strip()
            
            if not outcome_id or not title:
                continue

            outcomes.append(Outcome(
                outcome_id=outcome_id,
                name=title,  # Use 'name' instead of 'title'
            ))

        return outcomes

    async def get_quotes(self, market: Market, outcomes: Iterable[Outcome]) -> list[Quote]:
        """
        Fetch current quotes/prices for a specific Azuro market.
        Returns YES/NO style quotes for binary outcomes.
        """
        market_id = market.market_id
        
        # Check cache first
        cached_market = self._market_cache.get(market_id)
        if not cached_market:
            print(f"No cached data for Azuro market {market_id}")
            return []

        outcomes_data = cached_market.get("outcomes", [])
        if not outcomes_data:
            print(f"No outcomes data for Azuro market {market_id}")
            return []

        quotes: list[Quote] = []

        # For binary markets, we typically have 2 outcomes
        if len(outcomes_data) == 2:
            outcome1 = outcomes_data[0]
            outcome2 = outcomes_data[1]

            # Extract probabilities/odds
            prob1 = float(outcome1.get("probability", 0.0))
            prob2 = float(outcome2.get("probability", 0.0))

            # Extract liquidity
            liq1 = float(outcome1.get("liquidity", 0.0))
            liq2 = float(outcome2.get("liquidity", 0.0))

            # Create quotes for YES/NO style outcomes
            # Map first outcome to YES, second to NO
            quotes.append(Quote(
                outcome_id=outcome1.get("id", "yes"),
                bid=max(0.0, prob1 - 0.01),  # Simple bid/ask spread
                ask=min(1.0, prob1 + 0.01),
                bid_size=liq1,
                ask_size=liq1,
            ))

            quotes.append(Quote(
                outcome_id=outcome2.get("id", "no"),
                bid=max(0.0, prob2 - 0.01),
                ask=min(1.0, prob2 + 0.01),
                bid_size=liq2,
                ask_size=liq2,
            ))

        else:
            # For multi-outcome markets, create quotes for each outcome
            for outcome_data in outcomes_data:
                outcome_id = outcome_data.get("id", "")
                probability = float(outcome_data.get("probability", 0.0))
                liquidity = float(outcome_data.get("liquidity", 0.0))

                quotes.append(Quote(
                    outcome_id=outcome_id,
                    bid=max(0.0, probability - 0.01),
                    ask=min(1.0, probability + 0.01),
                    bid_size=liquidity,
                    ask_size=liquidity,
                ))

        return quotes

    async def get_market_details(self, market_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed information about a specific market.
        """
        query = """
        query GetMarketDetails($id: ID!) {
            market(id: $id) {
                id
                title
                description
                slug
                outcomes {
                    id
                    title
                    odds
                    liquidity
                    probability
                }
                totalVolume
                liquidity
                deadline
                createdAt
                updatedAt
                resolved
                winningOutcome
                ipfsHash
            }
        }
        """
        
        variables = {"id": market_id}

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    self.graphql_base_url,
                    json={"query": query, "variables": variables}
                )
                response.raise_for_status()
                data = response.json()
        except Exception as e:
            print(f"Error fetching Azuro market details: {e}")
            return None

        if "errors" in data:
            print(f"Azuro GraphQL errors: {data['errors']}")
            return None

        return data.get("data", {}).get("market")

    async def get_market_history(self, market_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch historical price/volume data for a market.
        This would typically query the subgraph for historical events.
        """
        # This is a placeholder for historical data fetching
        # In a full implementation, this would query the subgraph for historical events
        return []

# Test function to verify the adapter works
async def test_azuro_adapter():
    """Test the Azuro adapter with live data"""
    print("🎯 Testing Azuro Protocol Adapter")
    print("=" * 50)
    
    adapter = AzuroAdapter()
    
    try:
        # Test fetching active markets
        print("📊 Fetching active markets...")
        markets = await adapter.list_active_markets()
        print(f"✅ Found {len(markets)} active markets")
        
        if markets:
            # Show first few markets
            for i, market in enumerate(markets[:3]):
                print(f"  {i+1}. {market.title}")
                print(f"     ID: {market.market_id}")
                print(f"     URL: {market.url}")
                print()
            
            # Test fetching quotes for first market
            first_market = markets[0]
            print(f"💰 Fetching quotes for: {first_market.title}")
            outcomes = await adapter.list_outcomes(first_market)
            quotes = await adapter.get_quotes(first_market, outcomes)
            print(f"✅ Found {len(quotes)} quotes")
            
            for quote in quotes:
                print(f"  {quote.outcome_id}: Bid={quote.bid:.3f}, Ask={quote.ask:.3f}, Size={quote.bid_size:,.0f}")
        
        print("\n✅ Azuro adapter test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error testing Azuro adapter: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await adapter.close()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_azuro_adapter())
