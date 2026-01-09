# Project Rules

## Development Principles
- **Alerts-only**: This project monitors prediction markets and sends alerts. No trading execution.
- **Multi-venue**: Support multiple data sources (dev server, Polymarket, price feeds).
- **Type safety**: Use Pydantic models for all configuration and data validation.
- **Logging**: Redact sensitive data. Use structured logging with context.
- **Error handling**: Graceful degradation. Continue on per-market failures.

## Code Standards
- Python 3.11+ with type hints
- Use `from __future__ import annotations`
- Prefer explicit over implicit
- No hardcoded secrets or URLs in code
- All HTTP calls through `HttpClient` abstraction

## Configuration
- Environment variables via Pydantic Settings
- JSON for market mappings
- Validate all inputs at load time
- Fail fast on invalid configuration

## Testing
- Unit tests for core logic
- Integration tests for HTTP clients
- Mock external APIs in tests
- Test error paths and edge cases

## Security
- Never log raw API responses with sensitive data
- Use redaction filters for logs
- Secrets via environment variables only
- No secrets in version control
