"""Unit tests for error handling utilities."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest
import httpx

from bot.errors import (
    AdapterError, RetryableError, FatalError,
    ErrorType, ErrorInfo, classify_http_error, classify_exception,
    should_retry, get_retry_delay, retry_with_backoff,
    safe_http_get, safe_http_request, log_error_metrics
)


class TestErrorTypes:
    """Test error type enums and classes."""

    def test_error_type_values(self):
        """Test ErrorType enum values."""
        assert ErrorType.NETWORK.value == "network"
        assert ErrorType.RATE_LIMIT.value == "rate_limit"
        assert ErrorType.SERVER_ERROR.value == "server_error"
        assert ErrorType.CLIENT_ERROR.value == "client_error"
        assert ErrorType.DATA_ERROR.value == "data_error"
        assert ErrorType.CONFIG_ERROR.value == "config_error"
        assert ErrorType.UNKNOWN.value == "unknown"

    def test_adapter_error_creation(self):
        """Test AdapterError creation."""
        error = AdapterError("Test message", ErrorType.NETWORK, adapter_name="test")
        
        assert str(error) == "Test message"
        assert error.error_info.error_type == ErrorType.NETWORK
        assert error.error_info.message == "Test message"
        assert error.error_info.adapter_name == "test"

    def test_adapter_error_with_extra_kwargs(self):
        """Test AdapterError with extra kwargs."""
        error = AdapterError(
            "Test message",
            ErrorType.SERVER_ERROR,
            adapter_name="test",
            market_id="market123",
            status_code=500
        )
        
        assert error.error_info.market_id == "market123"
        assert error.error_info.status_code == 500
        # Should filter out non-ErrorInfo fields
        assert "extra_field" not in error.error_info.__dict__

    def test_retryable_error_inheritance(self):
        """Test RetryableError inheritance."""
        error = RetryableError("Retryable", ErrorType.NETWORK)
        assert isinstance(error, AdapterError)
        assert isinstance(error, RetryableError)

    def test_fatal_error_inheritance(self):
        """Test FatalError inheritance."""
        error = FatalError("Fatal", ErrorType.CLIENT_ERROR)
        assert isinstance(error, AdapterError)
        assert isinstance(error, FatalError)


class TestErrorClassification:
    """Test error classification functions."""

    def test_classify_http_error(self):
        """Test HTTP error classification."""
        # Test rate limit
        mock_response = AsyncMock()
        mock_response.status_code = 429
        error = httpx.HTTPStatusError("Rate limited", request=AsyncMock(), response=mock_response)
        assert classify_http_error(mock_response) == ErrorType.RATE_LIMIT
        
        # Test server error
        mock_response.status_code = 500
        assert classify_http_error(mock_response) == ErrorType.SERVER_ERROR
        
        # Test client error
        mock_response.status_code = 404
        assert classify_http_error(mock_response) == ErrorType.CLIENT_ERROR
        
        # Test unknown
        mock_response.status_code = 999
        assert classify_http_error(mock_response) == ErrorType.UNKNOWN

    def test_classify_exception(self):
        """Test exception classification."""
        # Network errors
        assert classify_exception(httpx.TimeoutException("timeout")) == ErrorType.NETWORK
        assert classify_exception(httpx.NetworkError("network")) == ErrorType.NETWORK
        
        # HTTP errors
        mock_response = AsyncMock()
        mock_response.status_code = 500
        http_error = httpx.HTTPStatusError("server error", request=AsyncMock(), response=mock_response)
        assert classify_exception(http_error) == ErrorType.SERVER_ERROR
        
        # Data errors
        assert classify_exception(ValueError("invalid value")) == ErrorType.DATA_ERROR
        assert classify_exception(TypeError("wrong type")) == ErrorType.DATA_ERROR
        assert classify_exception(KeyError("missing key")) == ErrorType.DATA_ERROR
        
        # Config errors
        assert classify_exception(FileNotFoundError("file not found")) == ErrorType.CONFIG_ERROR
        assert classify_exception(PermissionError("permission denied")) == ErrorType.CONFIG_ERROR
        
        # Unknown
        assert classify_exception(Exception("unknown")) == ErrorType.UNKNOWN


class TestRetryLogic:
    """Test retry logic functions."""

    def test_should_retry(self):
        """Test should_retry function."""
        # Should retry
        network_error = ErrorInfo(ErrorType.NETWORK, "Network error")
        assert should_retry(network_error) is True
        
        rate_limit_error = ErrorInfo(ErrorType.RATE_LIMIT, "Rate limited")
        assert should_retry(rate_limit_error) is True
        
        server_error = ErrorInfo(ErrorType.SERVER_ERROR, "Server error")
        assert should_retry(server_error) is True
        
        # Data errors - retry a few times
        data_error = ErrorInfo(ErrorType.DATA_ERROR, "Data error", retry_count=1)
        assert should_retry(data_error) is True
        
        data_error_too_many = ErrorInfo(ErrorType.DATA_ERROR, "Data error", retry_count=3)
        assert should_retry(data_error_too_many) is False
        
        # Should not retry
        client_error = ErrorInfo(ErrorType.CLIENT_ERROR, "Client error")
        assert should_retry(client_error) is False
        
        config_error = ErrorInfo(ErrorType.CONFIG_ERROR, "Config error")
        assert should_retry(config_error) is False

    def test_get_retry_delay(self):
        """Test retry delay calculation."""
        # Rate limits start at 5 seconds
        rate_limit = ErrorInfo(ErrorType.RATE_LIMIT, "Rate limited", retry_count=0)
        assert get_retry_delay(rate_limit) == 5.0
        
        rate_limit_retry = ErrorInfo(ErrorType.RATE_LIMIT, "Rate limited", retry_count=1)
        assert get_retry_delay(rate_limit_retry) == 10.0
        
        # Server errors: 2, 4, 8 seconds
        server_error = ErrorInfo(ErrorType.SERVER_ERROR, "Server error", retry_count=0)
        assert get_retry_delay(server_error) == 1.0
        
        server_error_retry = ErrorInfo(ErrorType.SERVER_ERROR, "Server error", retry_count=1)
        assert get_retry_delay(server_error_retry) == 2.0
        
        # Network errors: 1, 2, 4 seconds
        network_error = ErrorInfo(ErrorType.NETWORK, "Network error", retry_count=0)
        assert get_retry_delay(network_error) == 1.0
        
        # Default: 1 second
        unknown_error = ErrorInfo(ErrorType.UNKNOWN, "Unknown error", retry_count=0)
        assert get_retry_delay(unknown_error) == 1.0

    @pytest.mark.asyncio
    async def test_retry_with_backoff_success(self):
        """Test retry_with_backoff with success on first try."""
        mock_func = AsyncMock(return_value="success")
        
        result = await retry_with_backoff(
            mock_func,
            max_retries=3,
            adapter_name="test"
        )
        
        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_backoff_retry_success(self):
        """Test retry_with_backoff with success after retry."""
        mock_func = AsyncMock()
        mock_func.side_effect = [
            httpx.TimeoutException("timeout"),
            "success"
        ]
        
        with patch('bot.errors.asyncio.sleep') as mock_sleep:
            result = await retry_with_backoff(
                mock_func,
                max_retries=3,
                adapter_name="test"
            )
        
        assert result == "success"
        assert mock_func.call_count == 2
        mock_sleep.assert_called_once_with(1.0)

    @pytest.mark.asyncio
    async def test_retry_with_backoff_fatal_error(self):
        """Test retry_with_backoff with fatal error."""
        mock_func = AsyncMock()
        mock_func.side_effect = httpx.HTTPStatusError(
            "404",
            request=AsyncMock(),
            response=AsyncMock(status_code=404)
        )
        
        with pytest.raises(FatalError) as exc_info:
            await retry_with_backoff(
                mock_func,
                max_retries=3,
                adapter_name="test"
            )
        
        assert exc_info.value.error_info.error_type == ErrorType.CLIENT_ERROR
        assert mock_func.call_count == 1  # No retries for fatal errors

    @pytest.mark.asyncio
    async def test_retry_with_backoff_exhausted(self):
        """Test retry_with_backoff with exhausted retries."""
        mock_func = AsyncMock()
        mock_func.side_effect = httpx.TimeoutException("timeout")
        
        with patch('bot.errors.asyncio.sleep') as mock_sleep:
            with pytest.raises(RetryableError) as exc_info:
                await retry_with_backoff(
                    mock_func,
                    max_retries=2,
                    adapter_name="test"
                )
        
        assert exc_info.value.error_info.error_type == ErrorType.NETWORK
        assert mock_func.call_count == 3  # 1 initial + 2 retries
        assert mock_sleep.call_count == 2


class TestSafeHttpRequests:
    """Test safe HTTP request functions."""

    @pytest.mark.asyncio
    async def test_safe_http_request_success(self):
        """Test safe_http_request success."""
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_client.request.return_value = mock_response
        
        response = await safe_http_request(
            mock_client,
            "GET",
            "https://example.com",
            params={"test": "value"}
        )
        
        assert response == mock_response
        mock_client.request.assert_called_once_with(
            "GET",
            "https://example.com",
            params={"test": "value"}
        )

    @pytest.mark.asyncio
    async def test_safe_http_request_timeout(self):
        """Test safe_http_request with timeout."""
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.TimeoutException("timeout")
        
        with pytest.raises(AdapterError) as exc_info:
            await safe_http_request(mock_client, "GET", "https://example.com")
        
        assert exc_info.value.error_info.error_type == ErrorType.NETWORK
        assert "timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_safe_http_request_network_error(self):
        """Test safe_http_request with network error."""
        mock_client = AsyncMock()
        mock_client.request.side_effect = httpx.NetworkError("network error")
        
        with pytest.raises(AdapterError) as exc_info:
            await safe_http_request(mock_client, "GET", "https://example.com")
        
        assert exc_info.value.error_info.error_type == ErrorType.NETWORK
        assert "network error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_safe_http_get_success(self):
        """Test safe_http_get success."""
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        
        with patch('bot.errors.safe_http_request') as mock_request:
            mock_request.return_value = mock_response
            
            response = await safe_http_get(mock_client, "https://example.com")
        
        assert response == mock_response

    @pytest.mark.asyncio
    async def test_safe_http_get_rate_limit(self):
        """Test safe_http_get with rate limit."""
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 429
        
        with patch('bot.errors.safe_http_request') as mock_request:
            mock_request.return_value = mock_response
            
            with pytest.raises(AdapterError) as exc_info:
                await safe_http_get(mock_client, "https://example.com")
        
        assert exc_info.value.error_info.error_type == ErrorType.RATE_LIMIT
        assert exc_info.value.error_info.status_code == 429

    @pytest.mark.asyncio
    async def test_safe_http_get_server_error(self):
        """Test safe_http_get with server error."""
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 500
        
        with patch('bot.errors.safe_http_request') as mock_request:
            mock_request.return_value = mock_response
            
            with pytest.raises(AdapterError) as exc_info:
                await safe_http_get(mock_client, "https://example.com")
        
        assert exc_info.value.error_info.error_type == ErrorType.SERVER_ERROR
        assert exc_info.value.error_info.status_code == 500

    @pytest.mark.asyncio
    async def test_safe_http_get_client_error(self):
        """Test safe_http_get with client error."""
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 404
        
        with patch('bot.errors.safe_http_request') as mock_request:
            mock_request.return_value = mock_response
            
            with pytest.raises(AdapterError) as exc_info:
                await safe_http_get(mock_client, "https://example.com")
        
        assert exc_info.value.error_info.error_type == ErrorType.CLIENT_ERROR
        assert exc_info.value.error_info.status_code == 404


class TestErrorMetrics:
    """Test error metrics logging."""

    def test_log_error_metrics(self):
        """Test log_error_metrics function."""
        error_info = ErrorInfo(
            error_type=ErrorType.NETWORK,
            message="Test error",
            adapter_name="test_adapter",
            market_id="test_market",
            status_code=500,
            retry_count=2
        )
        
        with patch('bot.errors.logger.info') as mock_logger:
            log_error_metrics(error_info)
        
        mock_logger.assert_called_once()
        call_args = mock_logger.call_args[0][0]
        assert "ERROR_METRIC: network" in call_args
        assert "adapter=test_adapter" in call_args
        assert "status=500" in call_args
        assert "retries=2" in call_args
