# Technical Specification

## System Overview
Crypto prediction market monitor that fetches probability data from multiple sources and sends Discord alerts based on configurable rules.

## Upstream Data Sources

### Dev Mode (`CPM_UPSTREAM=dev`)
- Fetches from `/events` endpoint
- Returns list of events with probability and metadata
- Used for local testing

### Polymarket Mode (`CPM_UPSTREAM=polymarket`)
- Fetches from Polymarket CLOB API `/price` endpoint
- Query params: `token_id={token_id}&side=SELL`
- Returns current price as float (0.0-1.0)
- Requires market mapping via `CPM_POLYMARKET_MARKETS_JSON`

### Price Mode (`CPM_UPSTREAM=price`)
- Fetches from Coinbase `/products/{symbol}/candles` endpoint
- Computes price movement delta between last 2 candles
- Emits two events: `{symbol}_up` and `{symbol}_down`
- Probability: 1.0 if movement in direction, 0.0 otherwise

### Multi Mode (`CPM_UPSTREAM=multi`)
- Fetches from both Polymarket and Price sources
- Merges events, deduplicates by market_id
- Prefers price events on collision
- Continues if one upstream fails

## Alert Rules

### Rule Structure
```python
{
  "market_id": str,           # Required
  "min_probability": float,   # Optional threshold
  "max_probability": float,   # Optional threshold
  "min_delta": float,         # Optional change threshold
  "cooldown_seconds": int,    # Optional cooldown between alerts
  "once": bool,               # Optional fire-once flag
  "severity": str,            # "info" | "warning" | "critical"
  "escalate": [               # Optional severity escalation
    {
      "min_probability": float,
      "min_delta": float,
      "severity": str
    }
  ],
  "reason_template": str      # Optional custom reason message
}
```

### Alert Evaluation
1. Check if market_id matches event
2. Evaluate thresholds (min_probability, max_probability, min_delta)
3. Check false→true transition (edge-triggered)
4. Check cooldown period
5. Check once-only flag
6. Resolve severity with escalation rules
7. Format message with custom template if provided
8. Send webhook if configured

## Webhook Payload

### Schema Version 1
```json
{
  "schema_version": 1,
  "content": "Alert message",
  "alert": {
    "market_id": "string",
    "severity": "warning",
    "probability": 0.75,
    "delta": 0.05,
    "reason": "Trigger reason"
  }
}
```

### Delivery
- POST to Discord webhook URL
- Retry on 429, 5xx, transport errors
- Up to 5 attempts with exponential backoff
- Idempotency-Key header for deduplication
- Timeout configurable via `CPM_REQUEST_TIMEOUT_SECONDS`

## HTTP Client

### Features
- Automatic retries (5 attempts, exponential backoff)
- Timeout handling
- Error logging with redaction
- Support for both dict and list JSON responses
- Transport error recovery

### Methods
- `get_json(path)` - Returns dict only
- `get_json_any(path)` - Returns dict or list
- `post_json(path, json_body)` - POST with dict body

## Data Models

### MarketEvent
```python
market_id: str
title: str | None
timestamp: datetime
probability: float
delta: float | None
source: str | None
raw: dict | None
```

### AlertMessage
```python
market_id: str
severity: str
probability: float
delta: float | None
message: str
reason: str
```

## Configuration Validation
- All settings loaded via Pydantic
- Environment variables prefixed with `CPM_`
- Fail fast on invalid configuration
- Safe logging (redact secrets)
- Startup summary with sanitized values
