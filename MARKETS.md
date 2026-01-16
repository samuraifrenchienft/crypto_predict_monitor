# Market Configuration

## Overview
This document describes how to configure prediction markets for monitoring.

## Polymarket Markets

### Configuration Format
Markets are configured via the `CPM_POLYMARKET_MARKETS_JSON` environment variable as a JSON string:

```json
{
  "market_custom_id_1": {
    "token_id": "12345678"
  },
  "market_custom_id_2": {
    "token_id": "87654321"
  }
}
```

### Finding Token IDs
1. Navigate to the Polymarket market page
2. Inspect the URL or page source for the token ID
3. Token IDs are numeric strings identifying specific outcome tokens

### Example Configuration
```bash
set CPM_POLYMARKET_MARKETS_JSON={"btc_above_100k":{"token_id":"123"},"eth_above_5k":{"token_id":"456"}}
```

## Alert Rules

### Rule Configuration
Alert rules are configured via `CPM_RULES_JSON` environment variable:

```json
[
  {
    "market_id": "btc_above_100k",
    "min_probability": 0.7,
    "severity": "warning",
    "escalate": [
      {
        "min_probability": 0.9,
        "severity": "critical"
      }
    ]
  }
]
```

### Rule Fields
- `market_id` (required) - Must match a market from Polymarket config or price events
- `min_probability` - Alert if probability >= this value
- `max_probability` - Alert if probability <= this value
- `min_delta` - Alert if absolute change >= this value
- `cooldown_seconds` - Minimum time between alerts for this rule
- `once` - If true, only fire once per monitor session
- `severity` - Base severity: "info", "warning", or "critical"
- `escalate` - List of escalation rules for higher severity
- `reason_template` - Custom message template with placeholders

## Price Events

### Automatic Market IDs
When using `CPM_UPSTREAM=price` or `CPM_UPSTREAM=multi`, price events are automatically generated:

- `{symbol}_up` - Probability 1.0 if price increased, 0.0 otherwise
- `{symbol}_down` - Probability 1.0 if price decreased, 0.0 otherwise

Example for `CPM_PRICE_SYMBOL=BTC-USD` with `CPM_PRICE_INTERVAL_MINUTES=15`:
- `btc_15m_up`
- `btc_15m_down`

### Price Alert Example
```json
{
  "market_id": "btc_15m_up",
  "min_probability": 0.5,
  "min_delta": 0.02,
  "severity": "info"
}
```

## Multi-Upstream Mode
When using `CPM_UPSTREAM=multi`, events from both Polymarket and price sources are merged. If there's a market_id collision, price events take precedence.
