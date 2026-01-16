# 📜 Project Rules

> These rules keep the codebase consistent and maintainable.
> Follow them for all contributions.

---

## 🎯 Quick Preferences

| Category | Preference |
|----------|------------|
| **Comments** | SPARSE — explain WHY, not WHAT |
| **Testing** | 80% coverage, mock externals, write tests AFTER code |
| **Documentation** | Batched updates (3-5 features), major decisions only in DECISIONS.md |
| **Type Hints** | Always use them |
| **Secrets** | Environment variables only, never hardcode |

---

## 🔴 Absolute Rules (Never Break These)

### 1. No Trading Execution

This is an **alerts-only** system until Phase D.

```python
# ❌ BAD - Never do this
def execute_trade(symbol: str, amount: float):
    broker.buy(symbol, amount)  # NO TRADING!

# ✅ GOOD - Alerts only
def send_alert(message: str):
    webhook.send(message)  # Just notify
```

### 2. No Hardcoded Secrets

All secrets come from environment variables.

```python
# ❌ BAD - Hardcoded secret
API_KEY = "sk-1234567890abcdef"
WEBHOOK_URL = "https://discord.com/api/webhooks/123/abc"

# ✅ GOOD - From environment
API_KEY = os.environ.get("CPM_API_KEY")
WEBHOOK_URL = os.environ.get("CPM_WEBHOOK_URL")
```

### 3. No Logging Secrets

Use redaction for all sensitive data in logs.

```python
# ❌ BAD - Logs the secret
logger.info(f"Using webhook: {webhook_url}")
logger.debug(f"API response: {response.json()}")

# ✅ GOOD - Redacted
logger.info("Webhook configured: [REDACTED]")
logger.debug("API response received, status=%s", response.status_code)
```

### 4. No Deleting Tests

Tests can be updated or replaced, never deleted without replacement.

```python
# ❌ BAD - Deleting a test because it's "annoying"
# def test_cooldown_prevents_spam():  # DELETED

# ✅ GOOD - Update the test if behavior changed
def test_cooldown_prevents_spam():
    # Updated to match new cooldown logic
    ...
```

---

## 💻 Code Style

### Sparse Comments (Explain WHY, Not WHAT)

The code shows WHAT it does. Comments explain WHY.

```python
# ❌ BAD - Explains what (obvious from code)
# Loop through each market
for market in markets:
    process(market)

# ❌ BAD - Restates the code
# Set timeout to 30
timeout = 30

# ✅ GOOD - Explains why
# Process sequentially to respect API rate limits
for market in markets:
    process(market)

# ✅ GOOD - Explains the reasoning
# 30s matches Polymarket's max response time under load
timeout = 30
```

### Always Use Type Hints

Every function parameter and return type needs a type hint.

```python
# ❌ BAD - No type hints
def fetch_price(symbol):
    return get_data(symbol)

def process_events(events):
    for e in events:
        handle(e)

# ✅ GOOD - Clear types
def fetch_price(symbol: str) -> float:
    return get_data(symbol)

def process_events(events: list[MarketEvent]) -> None:
    for e in events:
        handle(e)
```

### Use `from __future__ import annotations`

Put this at the top of every Python file for forward references.

```python
# ✅ GOOD - At the top of every file
from __future__ import annotations

import logging
from typing import Any
```

### Import Order

1. Standard library
2. Third-party packages
3. Local imports

```python
# ✅ GOOD - Proper order
from __future__ import annotations
import logging
import time
from typing import Any

from pydantic import BaseModel
import httpx

from src.schemas import MarketEvent
from src.http_client import HttpClient
```

### Prefer Explicit Over Implicit

```python
# ❌ BAD - Implicit behavior
def process(data):
    if data:  # What counts as truthy?
        return data[0]

# ✅ GOOD - Explicit checks
def process(data: list[str]) -> str | None:
    if len(data) > 0:
        return data[0]
    return None
```

---

## 🧪 Testing Rules

### Write Tests AFTER Code

Get the code working first, then lock it down with tests.

```
1. Write the feature code
2. Manually verify it works
3. Write tests to prevent regressions
4. Run pytest to confirm
```

### Target 80% Coverage

Not 100%, but enough to catch regressions.

```powershell
# Check coverage
(.venv) PS> pytest --cov=src

# Aim for 80%+ on critical modules
```

### Mock All External Services

Never hit real APIs in tests.

```python
# ❌ BAD - Hits real API
def test_fetch_price():
    result = fetch_price_from_coinbase("BTC-USD")
    assert result > 0

# ✅ GOOD - Mocked
def test_fetch_price():
    with patch("src.fetcher.HttpClient.get_json") as mock:
        mock.return_value = {"price": "50000.00"}
        result = fetch_price_from_coinbase("BTC-USD")
        assert result == 50000.0
```

### What to Mock vs What to Test

```python
# ✅ MOCK THESE (external dependencies)
- HTTP requests (Polymarket, Coinbase, Discord)
- File system operations
- Time/datetime (for deterministic tests)

# ❌ DON'T MOCK THESE (internal logic)
- Pydantic validation
- Alert rule evaluation
- Configuration parsing
```

---

## 📝 Documentation Rules

### Batched Updates (3-5 Features)

Don't update docs after every tiny change. Wait for a batch.

```
❌ BAD: Update README after adding one function
❌ BAD: Update TASKS.md after every commit

✅ GOOD: Complete "Add Coinbase integration" feature set, then update:
   - TASKS.md (mark complete)
   - BUILD_FLOW.md (add new env vars)
   - SPEC.md (add new data flow)
```

### DECISIONS.md: Major Choices Only

Only add significant architectural decisions.

```markdown
✅ ADD: "Why we use Pydantic instead of dataclasses"
✅ ADD: "Why alerts are edge-triggered not level-triggered"
✅ ADD: "Why we chose httpx over requests"

❌ SKIP: "Why this variable is named 'x'"
❌ SKIP: "Why we use f-strings"
❌ SKIP: "Why this function returns None"
```

---

## ⚙️ Configuration Rules

### Environment Variables via Pydantic Settings

```python
# ✅ GOOD - Pydantic Settings
class Settings(BaseSettings):
    webhook_url: str
    upstream: str = "dev"
    
    model_config = SettingsConfigDict(env_prefix="CPM_")
```

### Validate All Inputs at Load Time

```python
# ✅ GOOD - Validation at load time
@field_validator("upstream")
@classmethod
def _validate_upstream(cls, v: str) -> str:
    allowed = {"dev", "polymarket", "price", "multi"}
    if v not in allowed:
        raise ValueError(f"upstream must be one of {allowed}")
    return v
```

### Fail Fast on Invalid Configuration

```python
# ✅ GOOD - Fail fast
def load_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        logger.error("Invalid configuration: %s", e)
        raise SystemExit(1)
```

---

## 🔒 Security Rules

### All HTTP Calls Through HttpClient

Never use `httpx` or `requests` directly. Use the `HttpClient` abstraction.

```python
# ❌ BAD - Direct HTTP call
response = httpx.get("https://api.example.com/data")

# ✅ GOOD - Through HttpClient
response = client.get_json("/data")
```

### URL-Encode User Input

```python
# ❌ BAD - Unencoded user input
url = f"/price?token_id={token_id}"

# ✅ GOOD - Encoded
from urllib.parse import quote
url = f"/price?token_id={quote(token_id, safe='')}"
```

### Use Timeouts on All HTTP Calls

```python
# ❌ BAD - No timeout (could hang forever)
response = client.get(url)

# ✅ GOOD - Explicit timeout
response = client.get(url, timeout=30.0)
```

---

## 🏗️ Architecture Rules

### Graceful Degradation

Continue on per-market failures. Don't crash the whole system.

```python
# ❌ BAD - One failure crashes everything
for market in markets:
    data = fetch_market(market)  # If this fails, loop stops
    process(data)

# ✅ GOOD - Continue on failure
for market in markets:
    try:
        data = fetch_market(market)
        process(data)
    except FetchError as e:
        logger.warning("Failed to fetch %s: %s", market, e)
        continue  # Keep going with other markets
```

### Use Pydantic for All Data Models

```python
# ❌ BAD - Plain dict
event = {"market_id": "btc", "probability": 0.75}

# ✅ GOOD - Pydantic model
class MarketEvent(BaseModel):
    market_id: str
    probability: float

event = MarketEvent(market_id="btc", probability=0.75)
```

---

## 📋 Quick Reference

| Rule | Example |
|------|---------|
| No trading | `send_alert()` not `execute_trade()` |
| No hardcoded secrets | `os.environ.get("KEY")` not `"sk-123"` |
| No logging secrets | `"[REDACTED]"` not `f"{api_key}"` |
| Type hints | `def f(x: str) -> int:` not `def f(x):` |
| Sparse comments | Explain WHY, not WHAT |
| Mock externals | `with patch(...)` in tests |
| 80% coverage | `pytest --cov=src` |
| Batched docs | Update after 3-5 features |

---

*Last updated: Phase C completion*
