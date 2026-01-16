# Project Context

## Project Purpose
Monitor crypto prediction markets and price movements, sending Discord alerts when configured thresholds are met. This is an **alerts-only** system with no trading execution.

## Current Phase
**Phase C**: Multi-upstream support with price feeds and Polymarket integration.

**Phase D** (Future): Trading execution will be enabled.

## Architecture Overview

### Core Components
1. **Monitor Loop** (`src/monitor.py`)
   - Polls data sources at configured interval
   - Evaluates alert rules against events
   - Dispatches webhooks for triggered alerts

2. **Multi-Upstream Fetcher** (`src/fetcher.py`)
   - Dev mode: Local/remote `/events` endpoint
   - Polymarket mode: CLOB API `/price` endpoint
   - Price mode: Coinbase candles API
   - Multi mode: Merged Polymarket + Price data

3. **Alert Engine** (`src/alerts.py`)
   - Rule-based evaluation with thresholds
   - Edge-triggered (false→true transitions)
   - Cooldown and once-only support
   - Severity escalation based on conditions
   - Custom reason templates

4. **Webhook Delivery** (`src/webhook.py`)
   - Discord webhook integration
   - Automatic retries with exponential backoff
   - Idempotency keys for deduplication
   - Schema versioning for forward compatibility

5. **HTTP Client** (`src/http_client.py`)
   - Unified HTTP abstraction
   - Automatic retry logic (5 attempts)
   - Timeout handling
   - Supports both dict and list JSON responses
   - Automatic log redaction

## Data Flow
```
Upstream Source → Fetcher → MarketEvent → Alert Evaluator → AlertMessage → Webhook
```

## Key Design Decisions
- **No trading**: Alerts only, execution disabled until Phase D
- **Multi-venue**: Support multiple data sources simultaneously
- **Graceful degradation**: Continue on per-market failures
- **Type safety**: Pydantic models throughout
- **Security**: Automatic log redaction, no secrets in code
- **Reliability**: Retries, timeouts, error handling at all boundaries

## State Management
- **In-memory only**: No database, no persistence
- **Previous probability cache**: For delta calculation
- **Alert state tracking**: For cooldown and once-only logic
- **Resets on restart**: All state is ephemeral

## Dependencies
- `httpx` - HTTP client
- `pydantic` - Data validation
- `pydantic-settings` - Configuration management
- `tenacity` - Retry logic
- `rich` - Logging output

## Future Enhancements (Phase D+)
- Trading execution integration
- Position management
- Risk controls
- Database persistence
- Web dashboard
- Multi-user support
