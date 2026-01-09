"""Unit tests for Metaculus adapter."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
import httpx

from bot.adapters.metaculus import MetaculusAdapter, _extract_probability
from bot.models import Market, Outcome, Quote


class TestMetaculusAdapter:
    """Test suite for MetaculusAdapter."""

    @pytest.fixture
    def adapter(self) -> MetaculusAdapter:
        """Create a MetaculusAdapter instance for testing."""
        return MetaculusAdapter(base_url="https://test.metaculus.com/api2", questions_limit=10)

    @pytest.fixture
    def sample_questions_response(self) -> dict:
        """Sample API response for questions."""
        return {
            "results": [
                {
                    "id": 12345,
                    "title": "Will the UN adopt a climate resolution?",
                    "title_short": "UN climate resolution",
                    "url": "/questions/12345",
                    "type": "forecast",
                    "status": "open",
                    "forecast_type": "binary"
                },
                {
                    "id": 67890,
                    "title": "Will AI achieve superintelligence?",
                    "url": "https://www.metaculus.com/questions/67890",
                    "type": "forecast",
                    "status": "open",
                    "forecast_type": "binary"
                },
                {
                    "id": 11111,
                    "title": "What will the GDP be?",
                    "type": "forecast",
                    "status": "open",
                    "forecast_type": "numeric"  # Should be filtered out
                }
            ]
        }

    @pytest.fixture
    def sample_questions_direct_list(self) -> list:
        """Sample API response as direct list (no 'results' key)."""
        return [
            {
                "id": 22222,
                "title": "Will quantum computing break encryption?",
                "url": "/questions/22222",
                "type": "forecast",
                "status": "open",
                "forecast_type": "binary"
            }
        ]

    @pytest.fixture
    def sample_question_detail(self) -> dict:
        """Sample API response for question details."""
        return {
            "id": 12345,
            "title": "Will the UN adopt a climate resolution?",
            "url": "/questions/12345",
            "type": "forecast",
            "status": "open",
            "forecast_type": "binary",
            "community_prediction": 0.65
        }

    @pytest.mark.asyncio
    async def test_list_active_markets_with_results_key(self, adapter, sample_questions_response):
        """Test successful market listing with 'results' key."""
        with patch('bot.adapters.metaculus.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.metaculus.safe_http_get') as mock_get:
            
            mock_response = AsyncMock()
            mock_response.json.return_value = sample_questions_response
            mock_get.return_value = mock_response
            mock_retry.return_value = mock_response

            markets = await adapter.list_active_markets()

            assert len(markets) == 2  # Only binary questions included
            assert markets[0].source == "metaculus"
            assert markets[0].market_id == "12345"
            assert markets[0].title == "Will the UN adopt a climate resolution?"
            assert markets[0].url == "https://www.metaculus.com/questions/12345"
            
            # Verify non-binary question was filtered out
            market_ids = [m.market_id for m in markets]
            assert "11111" not in market_ids

    @pytest.mark.asyncio
    async def test_list_active_markets_direct_list(self, adapter, sample_questions_direct_list):
        """Test market listing with direct list response."""
        with patch('bot.adapters.metaculus.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.metaculus.safe_http_get') as mock_get:
            
            mock_response = AsyncMock()
            mock_response.json.return_value = sample_questions_direct_list
            mock_get.return_value = mock_response
            mock_retry.return_value = mock_response

            markets = await adapter.list_active_markets()

            assert len(markets) == 1
            assert markets[0].market_id == "22222"
            assert markets[0].title == "Will quantum computing break encryption?"

    @pytest.mark.asyncio
    async def test_list_active_markets_empty_response(self, adapter):
        """Test handling of empty questions response."""
        with patch('bot.adapters.metaculus.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.metaculus.safe_http_get') as mock_get:
            
            mock_response = AsyncMock()
            mock_response.json.return_value = {"results": []}
            mock_get.return_value = mock_response
            mock_retry.return_value = mock_response

            markets = await adapter.list_active_markets()

            assert markets == []

    @pytest.mark.asyncio
    async def test_list_active_markets_malformed_data(self, adapter):
        """Test handling of malformed question data."""
        with patch('bot.adapters.metaculus.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.metaculus.safe_http_get') as mock_get:
            
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "results": [
                    {"id": 12345, "title": "Valid", "type": "forecast", "status": "open", "forecast_type": "binary"},
                    {"title": "Missing id", "type": "forecast", "status": "open", "forecast_type": "binary"},
                    None,  # Invalid entry
                    {"id": "", "title": "Empty id", "type": "forecast", "status": "open", "forecast_type": "binary"}
                ]
            }
            mock_get.return_value = mock_response
            mock_retry.return_value = mock_response

            markets = await adapter.list_active_markets()

            assert len(markets) == 1
            assert markets[0].market_id == "12345"

    @pytest.mark.asyncio
    async def test_list_outcomes(self, adapter):
        """Test outcome listing for a market."""
        market = Market(
            source="metaculus",
            market_id="12345",
            title="Test Question",
            url="https://example.com",
            outcomes=[]
        )

        outcomes = await adapter.list_outcomes(market)

        assert len(outcomes) == 2
        assert outcomes[0].outcome_id == "12345_YES"
        assert outcomes[0].name == "YES"
        assert outcomes[1].outcome_id == "12345_NO"
        assert outcomes[1].name == "NO"

    @pytest.mark.asyncio
    async def test_get_quotes_with_cached_probability(self, adapter):
        """Test getting quotes using cached probability."""
        market = Market(
            source="metaculus",
            market_id="12345",
            title="Test Question",
            url="https://example.com",
            outcomes=[]
        )
        outcomes = await adapter.list_outcomes(market)

        # Pre-populate cache
        adapter._question_cache["12345"] = {"community_prediction": 0.75}

        quotes = await adapter.get_quotes(market, outcomes)

        assert len(quotes) == 2
        # YES outcome gets the probability
        yes_quote = next(q for q in quotes if q.outcome_id.endswith("_YES"))
        assert yes_quote.mid == 0.75
        assert yes_quote.bid is None
        assert yes_quote.ask is None
        
        # NO outcome gets 1 - probability
        no_quote = next(q for q in quotes if q.outcome_id.endswith("_NO"))
        assert no_quote.mid == 0.25  # 1 - 0.75

    @pytest.mark.asyncio
    async def test_get_quotes_fetch_from_api(self, adapter, sample_question_detail):
        """Test getting quotes by fetching from API."""
        market = Market(
            source="metaculus",
            market_id="12345",
            title="Test Question",
            url="https://example.com",
            outcomes=[]
        )
        outcomes = await adapter.list_outcomes(market)

        with patch('bot.adapters.metaculus.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.metaculus.safe_http_get') as mock_get:
            
            mock_response = AsyncMock()
            mock_response.json.return_value = sample_question_detail
            mock_get.return_value = mock_response
            mock_retry.return_value = mock_response

            quotes = await adapter.get_quotes(market, outcomes)

            assert len(quotes) == 2
            yes_quote = next(q for q in quotes if q.outcome_id.endswith("_YES"))
            assert yes_quote.mid == 0.65

    @pytest.mark.asyncio
    async def test_get_quotes_api_fails(self, adapter):
        """Test getting quotes when API fails."""
        market = Market(
            source="metaculus",
            market_id="12345",
            title="Test Question",
            url="https://example.com",
            outcomes=[]
        )
        outcomes = await adapter.list_outcomes(market)

        with patch('bot.adapters.metaculus.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.metaculus.safe_http_get') as mock_get, \
             patch('bot.adapters.metaculus.log_error_metrics') as mock_log:
            
            mock_get.side_effect = Exception("Network error")
            mock_retry.side_effect = Exception("Network error")

            quotes = await adapter.get_quotes(market, outcomes)

            assert len(quotes) == 2
            # All quotes should be None when probability is unavailable
            for quote in quotes:
                assert quote.mid is None
                assert quote.bid is None
                assert quote.ask is None

    @pytest.mark.asyncio
    async def test_get_quotes_no_probability_in_response(self, adapter):
        """Test getting quotes when response has no probability."""
        market = Market(
            source="metaculus",
            market_id="12345",
            title="Test Question",
            url="https://example.com",
            outcomes=[]
        )
        outcomes = await adapter.list_outcomes(market)

        with patch('bot.adapters.metaculus.retry_with_backoff') as mock_retry, \
             patch('bot.adapters.metaculus.safe_http_get') as mock_get:
            
            # Response without probability
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "id": 12345,
                "title": "Test Question",
                "no_probability_here": "value"
            }
            mock_get.return_value = mock_response
            mock_retry.return_value = mock_response

            quotes = await adapter.get_quotes(market, outcomes)

            assert len(quotes) == 2
            for quote in quotes:
                assert quote.mid is None

    def test_adapter_name(self):
        """Test adapter name property."""
        adapter = MetaculusAdapter()
        assert adapter.name == "metaculus"

    def test_adapter_initialization(self):
        """Test adapter initialization with custom parameters."""
        adapter = MetaculusAdapter(
            base_url="https://custom.metaculus.com/api2",
            questions_limit=100
        )
        assert adapter.base_url == "https://custom.metaculus.com/api2"
        assert adapter.questions_limit == 100
        assert adapter._question_cache == {}


class TestExtractProbability:
    """Test suite for _extract_probability helper function."""

    def test_extract_community_prediction(self):
        """Test extracting community prediction."""
        data = {"community_prediction": 0.75}
        assert _extract_probability(data) == 0.75

    def test_extract_q2_field(self):
        """Test extracting from q2 field."""
        data = {"q2": 0.42}
        assert _extract_probability(data) == 0.42

    def test_extract_nested_full(self):
        """Test extracting from nested full structure."""
        data = {
            "full": {
                "q2": 0.65
            }
        }
        assert _extract_probability(data) is None  # Not a direct field

    def test_extract_nested_latest(self):
        """Test extracting from nested latest structure."""
        data = {
            "latest": {
                "median": 0.58
            }
        }
        assert _extract_probability(data) is None  # Not a direct field

    def test_extract_timeseries_latest(self):
        """Test extracting from timeseries latest entry."""
        data = {
            "prediction_timeseries": [
                {"community_prediction": 0.40},
                {"community_prediction": 0.45},
                {"community_prediction": 0.50}
            ]
        }
        assert _extract_probability(data) == 0.50  # Latest

    def test_extract_forecasts_community(self):
        """Test extracting from forecasts structure."""
        data = {
            "forecasts": {
                "community": {
                    "q2": 0.72
                }
            }
        }
        assert _extract_probability(data) == 0.72

    def test_extract_invalid_probability(self):
        """Test handling of invalid probability values."""
        data = {"community_prediction": "invalid"}
        assert _extract_probability(data) is None

    def test_extract_out_of_range(self):
        """Test handling of out-of-range probability values."""
        data = {"community_prediction": 1.5}  # > 1.0
        assert _extract_probability(data) is None

    def test_extract_none(self):
        """Test handling of None probability."""
        data = {"community_prediction": None}
        assert _extract_probability(data) is None

    def test_extract_not_found(self):
        """Test when no probability field is found."""
        data = {"other_field": "value"}
        assert _extract_probability(data) is None

    def test_extract_complex_nested(self):
        """Test extracting from complex nested structure."""
        data = {
            "forecasts": {
                "community": {
                    "q2": 0.68
                }
            }
        }
        assert _extract_probability(data) == 0.68
