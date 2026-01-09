# Crypto Predict Monitor

**Alerts-only** prediction market monitoring system with multi-venue support.

## Overview
This project monitors crypto prediction markets and price movements, sending Discord alerts when configured thresholds are met. **Trading execution is disabled until Phase D.**

## Features
- **Multi-venue support**: Dev server, Polymarket CLOB, Coinbase price feeds
- **Flexible alert rules**: Thresholds, cooldowns, severity escalation, custom templates
- **Reliable delivery**: Automatic retries, idempotency, schema versioning
- **Type-safe**: Pydantic models throughout
- **Secure**: Automatic log redaction, no hardcoded secrets

## Quick Start

### Installation
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or: source .venv/bin/activate  # Unix
pip install -r requirements.txt
```

### Configuration
Set environment variables (see `SECRETS.md` for details):
```bash
set CPM_MODE=monitor
set CPM_UPSTREAM=dev
set CPM_BASE_URL=http://localhost:8000
set CPM_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Run
```bash
python -m src.main
```

## Upstream Modes
- **dev** - Local/remote events endpoint
- **polymarket** - Polymarket CLOB API
- **price** - Coinbase price feeds (BTC, ETH, etc.)
- **multi** - Combined Polymarket + Price data

## Documentation
- `RULES.md` - Development principles and code standards
- `SECRETS.md` - Environment variables and security guidelines
- `SPEC.md` - Technical specification and API details
- `BUILD_FLOW.md` - Build, test, and deployment instructions
- `MARKETS.md` - Market configuration and alert rules
- `CONTEXT.md` - Project purpose and architecture overview
- `DECISIONS.md` - Architecture decision records
- `TASKS.md` - Completed and pending tasks
- `AI_INSTRUCTIONS.md` - AI assistant context and patterns

## Project Status
**Current Phase**: Phase C - Multi-upstream monitoring with alerts-only functionality.

**Phase D** (Future): Trading execution will be enabled.

## Architecture
```
Upstream Source → Fetcher → MarketEvent → Alert Evaluator → AlertMessage → Webhook
```

Core components:
- `src/main.py` - Entry point
- `src/monitor.py` - Main monitoring loop
- `src/fetcher.py` - Multi-upstream event fetching
- `src/alerts.py` - Alert rule evaluation
- `src/webhook.py` - Discord webhook delivery
- `src/http_client.py` - HTTP abstraction with retries

## Testing
```bash
pytest
pytest --cov=src
```

## License
Proprietary - All rights reserved.
