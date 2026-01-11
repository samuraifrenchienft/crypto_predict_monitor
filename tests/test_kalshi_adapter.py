"""Unit tests for Kalshi adapter."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
import httpx

from bot.adapters.kalshi import KalshiAdapter, _best_level
from bot.models import Market, Outcome, Quote


class TestKalshiAdapter:
    """Test suite for KalshiAdapter."""

    @pytest.fixture
    def adapter(self) -> KalshiAdapter:
        """Create a KalshiAdapter instance for testing."""
        return KalshiAdapter(base_url="https://api.test.kalshi.com", markets_limit=10)

    @pytest.fixture
    def sample_markets_response(self) -> dict:
        """Sample API response for markets."""
        return {
            "markets": [
                {
                    "ticker": "HIGH-TEMP-2024",
                    "title": "Will temperature exceed 100°F?",
                    "subtitle": "Daily temperature prediction",
                    "url": "https://kalshi.com/markets/HIGH-TEMP-2024"
                },
                {
                    "ticker": "STOCK-UP-2024",
                    "title": "Will S&P 500 increase?",
                    "url": "https://kalshi.com/markets/STOCK-UP-2024"
                },
                {
                    "ticker": "INVALID-MARKET",
                    # Missing required fields
                }
            ]
        }

    @pytest.fixture
    def sample_orderbook_response(self) -> dict:
        """Sample API response for orderbook."""
        return {
            "orderbook": {
                "yes": [
                    [45, 100],  # price: 45 cents, quantity: 100
                    [44, 200],
                    [43, 150]
                ],
                "no": [
                    [55, 120],  # price: 55 cents, quantity: 120
                    [56, 180],
                    [57, 90]
                ]
            }
        }

    @pytest.fixture
    def empty_orderbook_response(self) -> dict:
        """Sample empty orderbook response."""
        return {
            "orderbook": {
                "yes": [],
                "no": []
            }
        }

    @pytest.mark.asyncio
    async def test_list_active_markets_success(self, adapter, sample_markets_response):
        """Test successful market listing."""
        with patch('bot.adapters.kalshi.retry_with_backoff') as mock_retry, \
             patch.object(adapter, '_get_client') as mock_client:
            
            mock_response = AsyncMock()
            mock_response.json.return_value = sample_markets_response
            mock_retry.return_value = mock_response

            markets = await adapter.list_active_markets()

            assert len(markets) == 2  # Only valid markets included
            assert markets[0].source == "kalshi"
            assert markets[0].market_id == "HIGH-TEMP-2024"
            assert markets[0].title == "Will temperature exceed 100°F?"
            assert markets[0].url == "https://kalshi.com/markets/high-temp-2024"
            
            # Verify invalid market was filtered out
            market_ids = [m.market_id for m in markets]
            assert "INVALID-MARKET" not in market_ids

    @pytest.mark.asyncio
    async def test_list_active_markets_uses_subtitle(self, adapter):
        """Test market listing uses subtitle when title is missing."""
        response_with_subtitle = {
            "markets": [
                {
                    "ticker": "TEST-MARKET",
                    "subtitle": "This is the subtitle",
                    "url": "https://kalshi.com/markets/test-market"
                }
            ]
        }

        with patch.object(adapter, '_get_client') as mock_client:
            
            mock_http_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = response_with_subtitle
            mock_http_client.get.return_value = mock_response
            mock_client.return_value = mock_http_client

            markets = await adapter.list_active_markets()

            assert len(markets) == 1
            assert markets[0].title == "This is the subtitle"

    @pytest.mark.asyncio
    async def test_list_active_markets_falls_back_to_ticker(self, adapter):
        """Test market listing falls back to ticker when no title/subtitle."""
        response_minimal = {
            "markets": [
                {
                    "ticker": "MINIMAL-MARKET",
                    "url": "https://kalshi.com/markets/minimal"
                }
            ]
        }

        with patch.object(adapter, '_get_client') as mock_client:
            
            mock_http_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = response_minimal
            mock_http_client.get.return_value = mock_response
            mock_client.return_value = mock_http_client

            markets = await adapter.list_active_markets()

            assert len(markets) == 1
            assert markets[0].title == "MINIMAL-MARKET"

    @pytest.mark.asyncio
    async def test_list_outcomes(self, adapter):
        """Test outcome listing for a market."""
        market = Market(
            source="kalshi",
            market_id="TEST-MARKET",
            title="Test Market",
            url="https://example.com",
            outcomes=[]
        )

        outcomes = await adapter.list_outcomes(market)

        assert len(outcomes) == 2
        assert outcomes[0].outcome_id == "TEST-MARKET_YES"
        assert outcomes[0].name == "YES"
        assert outcomes[1].outcome_id == "TEST-MARKET_NO"
        assert outcomes[1].name == "NO"

    @pytest.mark.asyncio
    async def test_get_quotes_with_orderbook(self, adapter, sample_orderbook_response):
        """Test getting quotes from orderbook."""
        market = Market(
            source="kalshi",
            market_id="TEST-MARKET",
            title="Test Market",
            url="https://example.com",
            outcomes=[]
        )
        outcomes = await adapter.list_outcomes(market)

        with patch.object(adapter, '_get_client') as mock_client:
            
            mock_http_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = sample_orderbook_response
            mock_http_client.get.return_value = mock_response
            mock_client.return_value = mock_http_client

            quotes = await adapter.get_quotes(market, outcomes)

            assert len(quotes) == 2
            
            # YES quote
            yes_quote = next(q for q in quotes if q.outcome_id.endswith("_YES"))
            # YES bid = 45/100 = 0.45, YES ask = (100-55)/100 = 0.45
            assert yes_quote.bid == 0.45
            assert yes_quote.ask == 0.45
            assert yes_quote.bid_size == 100
            assert yes_quote.ask_size == 120
            
            # NO quote
            no_quote = next(q for q in quotes if q.outcome_id.endswith("_NO"))
            # NO bid = 55/100 = 0.55, NO ask = (100-45)/100 = 0.55
            assert no_quote.bid == 0.55
            assert no_quote.ask == 0.55
            assert no_quote.bid_size == 120
            assert no_quote.ask_size == 100

    @pytest.mark.asyncio
    async def test_get_quotes_empty_orderbook(self, adapter, empty_orderbook_response):
        """Test getting quotes from empty orderbook."""
        market = Market(
            source="kalshi",
            market_id="TEST-MARKET",
            title="Test Market",
            url="https://example.com",
            outcomes=[]
        )
        outcomes = await adapter.list_outcomes(market)

        with patch.object(adapter, '_get_client') as mock_client:
            
            mock_http_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = empty_orderbook_response
            mock_http_client.get.return_value = mock_response
            mock_client.return_value = mock_http_client

            quotes = await adapter.get_quotes(market, outcomes)

            assert len(quotes) == 2
            # All quotes should be None for empty orderbook
            for quote in quotes:
                assert quote.bid is None
                assert quote.ask is None
                assert quote.bid_size is None
                assert quote.ask_size is None

    @pytest.mark.asyncio
    async def test_get_quotes_malformed_orderbook(self, adapter):
        """Test handling of malformed orderbook data."""
        malformed_response = {
            "orderbook": {
                "yes": [
                    [45],  # Missing quantity
                    "invalid",  # Invalid entry
                    [44, 200, "extra"]  # Too many values
                ],
                "no": None  # Invalid type
            }
        }

        market = Market(
            source="kalshi",
            market_id="TEST-MARKET",
            title="Test Market",
            url="https://example.com",
            outcomes=[]
        )
        outcomes = await adapter.list_outcomes(market)

        with patch.object(adapter, '_get_client') as mock_client:
            
            mock_http_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.json.return_value = malformed_response
            mock_http_client.get.return_value = mock_response
            mock_client.return_value = mock_http_client

            quotes = await adapter.get_quotes(market, outcomes)

            assert len(quotes) == 2
            # Should handle gracefully with None values
            for quote in quotes:
                assert quote.bid is None
                assert quote.ask is None

    def test_adapter_name(self):
        """Test adapter name property."""
        adapter = KalshiAdapter()
        assert adapter.name == "kalshi"

    def test_adapter_initialization(self):
        """Test adapter initialization with custom parameters."""
        adapter = KalshiAdapter(
            base_url="https://custom.kalshi.com",
            markets_limit=100
        )
        assert adapter.base_url == "https://custom.kalshi.com"
        assert adapter.markets_limit == 100
        assert adapter._market_cache == {}


class TestBestLevel:
    """Test suite for _best_level helper function."""

    def test_best_level_normal(self):
        """Test _best_level with normal data."""
        levels = [
            [45, 100],
            [46, 200],  # Best (highest) price
            [44, 150]
        ]
        
        price, size = _best_level(levels)
        assert price == 46
        assert size == 200

    def test_best_level_empty(self):
        """Test _best_level with empty list."""
        price, size = _best_level([])
        assert price is None
        assert size is None

    def test_best_level_invalid_type(self):
        """Test _best_level with invalid input type."""
        price, size = _best_level(None)
        assert price is None
        assert size is None

    def test_best_level_malformed_entries(self):
        """Test _best_level with malformed entries."""
        levels = [
            [45],  # Missing quantity
            "invalid",  # Invalid entry
            [46, "not_a_number"],  # Invalid quantity
            [47.5, 100],  # Valid float price
            [48, 150, "extra"]  # Too many values
        ]
        
        price, size = _best_level(levels)
        assert price == 48.0  # Highest valid price
        assert size == 150

    def test_best_level_all_invalid(self):
        """Test _best_level with all invalid entries."""
        levels = [
            "invalid",
            [45],  # Missing quantity
            None,
            ["not", "numbers"]
        ]
        
        price, size = _best_level(levels)
        assert price is None
        assert size is None
