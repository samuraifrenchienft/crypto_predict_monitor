"""Unit tests for Manifold Markets adapter."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
import httpx

from bot.adapters.manifold import ManifoldAdapter
from bot.models import Market, Outcome, Quote


class TestManifoldAdapter:
    """Test suite for ManifoldAdapter."""

    @pytest.fixture
    def adapter(self) -> ManifoldAdapter:
        """Create a ManifoldAdapter instance for testing."""
        return ManifoldAdapter(base_url="https://test.manifold.markets", markets_limit=10)

    @pytest.fixture
    def sample_markets_response(self) -> dict:
        """Sample API response for markets."""
        return {
            "markets": [
                {
                    "id": "test-market-1",
                    "question": "Will chess be solved by 2040?",
                    "url": "https://manifold.markets/test-market-1",
                    "outcomeType": "BINARY",
                    "probability": 0.25
                },
                {
                    "id": "test-market-2",
                    "question": "Will AI achieve AGI by 2030?",
                    "url": "https://manifold.markets/test-market-2",
                    "outcomeType": "BINARY",
                    "probability": 0.75
                },
                {
                    "id": "non-binary-market",
                    "question": "What will the temperature be?",
                    "url": "https://manifold.markets/non-binary",
                    "outcomeType": "MULTIPLE_CHOICE",  # Should be filtered out
                    "probability": 0.5
                }
            ]
        }

    @pytest.fixture
    def sample_prob_response(self) -> dict:
        """Sample API response for probability."""
        return {"prob": 0.42}

    @pytest.fixture
    def sample_market_response(self) -> dict:
        """Sample API response for full market details."""
        return {
            "id": "test-market-1",
            "question": "Will chess be solved by 2040?",
            "url": "https://manifold.markets/test-market-1",
            "outcomeType": "BINARY",
            "probability": 0.42
        }

    @pytest.mark.asyncio
    async def test_list_active_markets_success(self, adapter, sample_markets_response):
        """Test successful market listing."""
        with patch('bot.adapters.manifold.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.manifold.safe_http_get') as mock_get:
            
            # Mock the HTTP response
            mock_response = AsyncMock()
            mock_response.json.return_value = sample_markets_response
            mock_get.return_value = mock_response
            mock_retry.return_value = mock_response

            markets = await adapter.list_active_markets()

            assert len(markets) == 2  # Only binary markets included
            assert markets[0].source == "manifold"
            assert markets[0].market_id == "test-market-1"
            assert markets[0].title == "Will chess be solved by 2040?"
            assert markets[0].url == "https://manifold.markets/test-market-1"
            
            # Verify non-binary market was filtered out
            market_ids = [m.market_id for m in markets]
            assert "non-binary-market" not in market_ids

    @pytest.mark.asyncio
    async def test_list_active_markets_empty_response(self, adapter):
        """Test handling of empty market response."""
        with patch('bot.adapters.manifold.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.manifold.safe_http_get') as mock_get:
            
            mock_response = AsyncMock()
            mock_response.json.return_value = {"markets": []}
            mock_get.return_value = mock_response
            mock_retry.return_value = mock_response

            markets = await adapter.list_active_markets()

            assert markets == []

    @pytest.mark.asyncio
    async def test_list_active_markets_malformed_data(self, adapter):
        """Test handling of malformed market data."""
        with patch('bot.adapters.manifold.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.manifold.safe_http_get') as mock_get:
            
            # Response with malformed entries
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "markets": [
                    {"id": "valid-market", "question": "Valid?", "outcomeType": "BINARY"},
                    {"question": "Missing id", "outcomeType": "BINARY"},  # Missing id
                    None,  # Invalid entry
                    {"id": "", "question": "Empty id", "outcomeType": "BINARY"},  # Empty id
                ]
            }
            mock_get.return_value = mock_response
            mock_retry.return_value = mock_response

            markets = await adapter.list_active_markets()

            assert len(markets) == 1
            assert markets[0].market_id == "valid-market"

    @pytest.mark.asyncio
    async def test_list_outcomes(self, adapter):
        """Test outcome listing for a market."""
        market = Market(
            source="manifold",
            market_id="test-market-1",
            title="Test Market",
            url="https://example.com",
            outcomes=[]
        )

        outcomes = await adapter.list_outcomes(market)

        assert len(outcomes) == 2
        assert outcomes[0].outcome_id == "test-market-1_YES"
        assert outcomes[0].name == "YES"
        assert outcomes[1].outcome_id == "test-market-1_NO"
        assert outcomes[1].name == "NO"

    @pytest.mark.asyncio
    async def test_get_quotes_with_probability_endpoint(self, adapter, sample_prob_response):
        """Test getting quotes using probability endpoint."""
        market = Market(
            source="manifold",
            market_id="test-market-1",
            title="Test Market",
            url="https://example.com",
            outcomes=[]
        )
        outcomes = await adapter.list_outcomes(market)

        with patch('bot.adapters.manifold.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.manifold.safe_http_get') as mock_get:
            
            # Mock probability endpoint response
            mock_response = AsyncMock()
            mock_response.json.return_value = sample_prob_response
            mock_get.return_value = mock_response
            mock_retry.return_value = mock_response

            quotes = await adapter.get_quotes(market, outcomes)

            assert len(quotes) == 2
            # YES outcome gets the probability
            yes_quote = next(q for q in quotes if q.outcome_id.endswith("_YES"))
            assert yes_quote.mid == 0.42
            assert yes_quote.bid is None
            assert yes_quote.ask is None
            
            # NO outcome gets 1 - probability
            no_quote = next(q for q in quotes if q.outcome_id.endswith("_NO"))
            assert no_quote.mid == 0.58  # 1 - 0.42

    @pytest.mark.asyncio
    async def test_get_quotes_fallback_to_market_endpoint(self, adapter, sample_market_response):
        """Test getting quotes with fallback to market endpoint."""
        market = Market(
            source="manifold",
            market_id="test-market-1",
            title="Test Market",
            url="https://example.com",
            outcomes=[]
        )
        outcomes = await adapter.list_outcomes(market)

        with patch('bot.adapters.manifold.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.manifold.safe_http_get') as mock_get, \
             patch('bot.adapters.manifold.log_error_metrics') as mock_log:
            
            # First call (prob endpoint) returns no probability
            mock_prob_response = AsyncMock()
            mock_prob_response.json.return_value = {"prob": None}
            
            # Second call (market endpoint) returns probability
            mock_market_response = AsyncMock()
            mock_market_response.json.return_value = sample_market_response
            
            # Configure mock to return different responses
            def side_effect(*args, **kwargs):
                if "prob" in kwargs.get('url', ''):
                    return mock_prob_response
                else:
                    return mock_market_response
            
            mock_get.side_effect = side_effect
            mock_retry.side_effect = side_effect

            quotes = await adapter.get_quotes(market, outcomes)

            assert len(quotes) == 2
            yes_quote = next(q for q in quotes if q.outcome_id.endswith("_YES"))
            assert yes_quote.mid == 0.42

    @pytest.mark.asyncio
    async def test_get_quotes_fallback_fails(self, adapter):
        """Test getting quotes when both endpoints fail."""
        market = Market(
            source="manifold",
            market_id="test-market-1",
            title="Test Market",
            url="https://example.com",
            outcomes=[]
        )
        outcomes = await adapter.list_outcomes(market)

        with patch('bot.adapters.manifold.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.manifold.safe_http_get') as mock_get, \
             patch('bot.adapters.manifold.log_error_metrics') as mock_log:
            
            # Both endpoints fail
            mock_get.side_effect = Exception("Network error")
            mock_retry.side_effect = Exception("Network error")

            quotes = await adapter.get_quotes(market, outcomes)

            assert len(quotes) == 2
            # All quotes should be empty when probability is unavailable
            for quote in quotes:
                assert quote.mid is None
                assert quote.bid is None
                assert quote.ask is None

    @pytest.mark.asyncio
    async def test_get_quotes_invalid_probability(self, adapter):
        """Test handling of invalid probability values."""
        market = Market(
            source="manifold",
            market_id="test-market-1",
            title="Test Market",
            url="https://example.com",
            outcomes=[]
        )
        outcomes = await adapter.list_outcomes(market)

        with patch('bot.adapters.manifold.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.manifold.safe_http_get') as mock_get:
            
            # Mock response with invalid probability
            mock_response = AsyncMock()
            mock_response.json.return_value = {"prob": "invalid"}
            mock_get.return_value = mock_response
            mock_retry.return_value = mock_response

            quotes = await adapter.get_quotes(market, outcomes)

            assert len(quotes) == 2
            # All quotes should be None for invalid probability
            for quote in quotes:
                assert quote.mid is None

    def test_adapter_name(self):
        """Test adapter name property."""
        adapter = ManifoldAdapter()
        assert adapter.name == "manifold"

    def test_adapter_initialization(self):
        """Test adapter initialization with custom parameters."""
        adapter = ManifoldAdapter(
            base_url="https://custom.manifold.markets",
            markets_limit=100
        )
        assert adapter.base_url == "https://custom.manifold.markets"
        assert adapter.markets_limit == 100
