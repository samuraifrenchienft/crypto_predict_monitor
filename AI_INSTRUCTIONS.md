# AI Instructions

## Project Context
This is a crypto prediction market monitoring system that sends alerts based on probability changes. It is **alerts-only** with no trading execution until Phase D.

## Architecture
- `src/main.py` - Entry point, mode selection (health/monitor)
- `src/config.py` - Settings and environment variable loading
- `src/monitor.py` - Main monitoring loop
- `src/fetcher.py` - Multi-upstream event fetching (dev/polymarket/price/multi)
- `src/alerts.py` - Alert rule evaluation with severity escalation
- `src/webhook.py` - Discord webhook delivery with retries
- `src/http_client.py` - HTTP abstraction with retry logic
- `src/schemas.py` - Pydantic models for events and payloads
- `src/logging_setup.py` - Logging configuration with redaction

## Upstream Modes
1. **dev** - Fetch from local dev server `/events` endpoint
2. **polymarket** - Fetch from Polymarket CLOB `/price` endpoint
3. **price** - Fetch BTC price from Coinbase candles API
4. **multi** - Merge polymarket + price events

## Key Patterns
- Use Pydantic for all configuration and validation
- HTTP calls go through `HttpClient` with automatic retries
- Logs are redacted automatically (no raw secrets/tokens)
- Per-market error handling (continue on individual failures)
- In-memory caching for delta calculation

## When Making Changes
- Preserve existing error handling patterns
- Keep logging consistent (market_id, severity, etc.)
- Validate inputs at boundaries
- Test both success and failure paths
- Update relevant documentation files

## Current Phase
**Phase C**: Multi-upstream support with price feeds. Execution disabled.
