# Build and Deployment Flow

## Local Development

### Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Unix)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running

#### Health Check Mode
```bash
python -m src.main
# or
set CPM_MODE=health
python -m src.main
```

#### Monitor Mode
```bash
set CPM_MODE=monitor
set CPM_UPSTREAM=dev
set CPM_BASE_URL=http://localhost:8000
set CPM_WEBHOOK_URL=https://discord.com/api/webhooks/...
python -m src.main
```

#### Dev Server (for testing)
```bash
python tools/dev_server.py
```

## Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_alerts.py
```

## Configuration Modes

### Dev Mode
- `CPM_UPSTREAM=dev`
- Requires `CPM_BASE_URL`
- Fetches from local/remote `/events` endpoint

### Polymarket Mode
- `CPM_UPSTREAM=polymarket`
- Requires `CPM_POLYMARKET_MARKETS_JSON`
- Optional `CPM_POLYMARKET_BASE_URL`

### Price Mode
- `CPM_UPSTREAM=price`
- Requires `CPM_PRICE_PROVIDER=coinbase`
- Requires `CPM_PRICE_SYMBOL` (e.g., "BTC-USD")
- Optional `CPM_PRICE_INTERVAL_MINUTES` (default: 15)

### Multi Mode
- `CPM_UPSTREAM=multi`
- Combines Polymarket + Price sources
- Requires all Polymarket and Price settings

## Environment Variables
See `SECRETS.md` for complete list.

## Deployment
**Phase C**: Alerts-only monitoring. No trading execution.
**Phase D**: Trading execution will be enabled (future).

Current deployment is manual. Future phases may include:
- Docker containerization
- Cloud deployment (AWS/GCP)
- CI/CD pipeline
- Automated testing
