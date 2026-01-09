# Secrets Management

## Environment Variables

### Required for Dev Mode
- `CPM_BASE_URL` - Base URL for dev server events endpoint
- `CPM_WEBHOOK_URL` - Discord webhook URL for alerts

### Required for Polymarket Mode
- `CPM_POLYMARKET_MARKETS_JSON` - JSON string mapping market_id to token_id

### Required for Price Mode
- `CPM_PRICE_PROVIDER` - Price provider (currently only "coinbase")
- `CPM_PRICE_SYMBOL` - Trading pair symbol (e.g., "BTC-USD")

### Optional
- `CPM_POLYMARKET_BASE_URL` - Override Polymarket CLOB API URL (default: https://clob.polymarket.com)
- `CPM_LOG_LEVEL` - Logging level (default: INFO)
- `CPM_POLL_INTERVAL_SECONDS` - Polling interval (default: 60)
- `CPM_REQUEST_TIMEOUT_SECONDS` - HTTP timeout (default: 20)

## Security Guidelines
- Never commit secrets to version control
- Use `.env` files locally (gitignored)
- Rotate webhooks if exposed
- Use read-only API keys where possible
- Redact secrets in logs automatically

## Local Development
Create a `.env` file at project root:
```bash
CPM_MODE=monitor
CPM_UPSTREAM=dev
CPM_BASE_URL=http://localhost:8000
CPM_WEBHOOK_URL=https://discord.com/api/webhooks/...
CPM_LOG_LEVEL=DEBUG
```

Load with:
```bash
python -m src.main
```
