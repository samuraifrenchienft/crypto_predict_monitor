# AI Instructions

> **For AI Assistants**: This document tells you how to work on this project.
> **For Humans**: This explains our coding standards and workflows.

---

## 1. Project Mission & Context

### What This Project Does
This is a **crypto prediction market monitoring system** that watches market probabilities and sends Discord alerts when interesting things happen.

**Think of it like a smoke detector for crypto markets** — it watches for changes and alerts you, but it doesn't fight the fire (no trading).

### Current Status
- **Phase C**: Alerts-only monitoring ✅
- **Phase D**: Trading execution (FUTURE - not yet implemented)

### The Golden Rule
```
🚫 NO TRADING EXECUTION UNTIL PHASE D 🚫
```
This project only sends alerts. It does NOT buy, sell, or execute any trades.

---

## 2. Code Structure (Exact File Paths)

```
c:\Users\AbuBa\crypto_predict_monitor\
│
├── src\                          # All main source code lives here
│   ├── __init__.py              # Makes src a Python package
│   ├── main.py                  # Entry point - start here when running
│   ├── config.py                # Loads settings from environment variables
│   ├── monitor.py               # Main loop that polls for events
│   ├── fetcher.py               # Gets data from Polymarket/Coinbase/dev
│   ├── alerts.py                # Decides when to fire alerts
│   ├── webhook.py               # Sends messages to Discord
│   ├── http_client.py           # Makes HTTP requests with retries
│   ├── schemas.py               # Data models (what events look like)
│   └── logging_setup.py         # Configures logging with redaction
│
├── tests\                        # All test files
│   ├── test_alerts.py
│   ├── test_config.py
│   ├── test_fetcher.py
│   └── ...
│
├── tools\                        # Helper scripts
│   └── dev_server.py            # Fake server for local testing
│
├── config\                       # Configuration files
├── data\                         # Data storage
│
├── AI_INSTRUCTIONS.md           # This file (you're reading it)
├── RULES.md                     # Project rules
├── SECRETS.md                   # Environment variable reference
├── SPEC.md                      # Technical specification
├── BUILD_FLOW.md                # How to build and run
├── TASKS.md                     # Task tracking
├── DECISIONS.md                 # Major architectural decisions
├── MARKETS.md                   # Market configuration guide
├── CONTEXT.md                   # Project context
├── README.md                    # Project overview
└── requirements.txt             # Python dependencies
```

### File Responsibilities (Who Does What)

| File | Responsibility | Analogy |
|------|---------------|---------|
| `main.py` | Starts everything, picks mode | The ignition key |
| `config.py` | Reads settings from environment | The settings menu |
| `monitor.py` | Runs the main loop | The engine |
| `fetcher.py` | Gets market data | The eyes |
| `alerts.py` | Decides when to alert | The brain |
| `webhook.py` | Sends Discord messages | The mouth |
| `http_client.py` | Makes web requests | The hands |
| `schemas.py` | Defines data shapes | The blueprint |
| `logging_setup.py` | Handles logging safely | The diary |

---

## 3. Code Style Guide

### Comment Philosophy: SPARSE Comments

**Explain WHY, not WHAT.** The code shows what; comments explain why.

```python
# ❌ BAD - explains what (obvious from code)
# Loop through each market
for market in markets:
    process(market)

# ✅ GOOD - explains why (not obvious)
# Process markets sequentially to respect API rate limits
for market in markets:
    process(market)
```

```python
# ❌ BAD - restates the code
# Set timeout to 30 seconds
timeout = 30

# ✅ GOOD - explains the reasoning
# 30s timeout matches Polymarket's max response time under load
timeout = 30
```

### Type Hints: Always Use Them

```python
# ❌ BAD - no type hints
def fetch_price(symbol):
    return get_data(symbol)

# ✅ GOOD - clear types
def fetch_price(symbol: str) -> float:
    return get_data(symbol)
```

### Docstrings: Only for Complex Functions

```python
# Simple function - no docstring needed
def is_valid_probability(p: float) -> bool:
    return 0.0 <= p <= 1.0

# Complex function - docstring explains behavior
def evaluate_event(
    event: MarketEvent,
    rule: AlertRule,
    prev_prob: float | None,
    state: AlertState | None = None,
) -> AlertMessage | None:
    """
    Evaluate if an event triggers an alert based on the rule.
    
    Returns None if no alert should fire (cooldown, already fired, etc).
    Handles edge-triggered alerts (only fires on false→true transitions).
    """
    ...
```

### Import Order

```python
# 1. Standard library
from __future__ import annotations
import logging
import time
from typing import Any

# 2. Third-party packages
from pydantic import BaseModel
import httpx

# 3. Local imports
from src.schemas import MarketEvent
from src.http_client import HttpClient
```

---

## 4. Testing Philosophy

### Core Principles

1. **Write tests AFTER code** — Get the code working first, then lock it down with tests
2. **Target 80% coverage** — Not 100%, but enough to catch regressions
3. **Mock all external services** — Never hit real APIs in tests

### What to Mock

```python
# ✅ MOCK THESE (external dependencies)
- HTTP requests to Polymarket
- HTTP requests to Coinbase
- Discord webhook calls
- File system operations
- Time/datetime (for deterministic tests)

# ❌ DON'T MOCK THESE (internal logic)
- Pydantic validation
- Alert rule evaluation
- Configuration parsing
```

### Test File Location

Tests go in `c:\Users\AbuBa\crypto_predict_monitor\tests\`

Name pattern: `test_<module>.py`

```
tests\
├── test_alerts.py      # Tests for src/alerts.py
├── test_config.py      # Tests for src/config.py
├── test_fetcher.py     # Tests for src/fetcher.py
├── test_webhook.py     # Tests for src/webhook.py
└── conftest.py         # Shared fixtures
```

### Running Tests (PowerShell)

```powershell
# Run all tests
pytest

# Run with coverage report
pytest --cov=src

# Run specific test file
pytest tests/test_alerts.py

# Run specific test function
pytest tests/test_alerts.py::test_cooldown_prevents_spam

# Run with verbose output
pytest -v

# Run and stop on first failure
pytest -x
```

---

## 5. Documentation Updates

### Batched Approach (3-5 Features at Once)

**Don't update docs after every tiny change.** Wait until you have 3-5 related changes, then update docs together.

```
❌ BAD: Update README after adding one function
❌ BAD: Update TASKS.md after every commit

✅ GOOD: Complete "Add Coinbase integration" feature set, then update:
   - TASKS.md (mark complete)
   - BUILD_FLOW.md (add new env vars)
   - SPEC.md (add new data flow)
```

### Which Doc to Update

| Change Type | Update This File |
|-------------|------------------|
| New feature complete | `TASKS.md` |
| New environment variable | `SECRETS.md`, `BUILD_FLOW.md` |
| Architecture change | `SPEC.md`, `DECISIONS.md` |
| New upstream mode | `AI_INSTRUCTIONS.md`, `BUILD_FLOW.md` |
| Bug fix | Nothing (unless it changes behavior) |

### DECISIONS.md: Major Choices Only

Only add to DECISIONS.md for **significant architectural decisions**:

```markdown
✅ ADD: "Why we use Pydantic instead of dataclasses"
✅ ADD: "Why alerts are edge-triggered not level-triggered"
✅ ADD: "Why we chose httpx over requests"

❌ SKIP: "Why this variable is named 'x'"
❌ SKIP: "Why we use f-strings"
❌ SKIP: "Why this function returns None"
```

---

## 6. Critical Rules (Never Break These)

### 🔴 ABSOLUTE RULES

1. **NO TRADING EXECUTION** — This is alerts-only until Phase D
2. **NO HARDCODED SECRETS** — All secrets come from environment variables
3. **NO LOGGING SECRETS** — Use redaction for all sensitive data
4. **NO DELETING TESTS** — Tests can be updated, never deleted without replacement

### 🟡 STRONG GUIDELINES

1. **Always use type hints** — Every function parameter and return type
2. **Always validate input** — Use Pydantic for external data
3. **Always handle errors** — No bare `except:` clauses
4. **Always use timeouts** — Every HTTP request needs a timeout

### 🟢 PREFERENCES

1. Prefer `httpx` over `requests`
2. Prefer Pydantic over dataclasses
3. Prefer explicit over implicit
4. Prefer composition over inheritance

---

## 7. AI Behavior Guidelines

### When to "Just Do It" (No Need to Ask)

```
✅ JUST DO IT:
- Fix obvious bugs (typos, missing imports, syntax errors)
- Add type hints to existing code
- Improve error messages
- Add input validation
- Fix security issues (redaction, URL encoding)
- Refactor for clarity (same behavior, cleaner code)
- Add tests for existing code
- Update documentation for completed features
```

### When to Ask First

```
🛑 ASK FIRST:
- Adding new dependencies to requirements.txt
- Changing public API signatures
- Deleting files or functions
- Changing configuration schema
- Adding new environment variables
- Architectural changes (new modules, patterns)
- Anything that changes existing behavior
- Anything involving secrets or credentials
```

### How to Ask

```
❌ BAD: "Should I do X?"
✅ GOOD: "I want to do X because Y. This will affect Z. Should I proceed?"
```

---

## 8. Common Tasks (Step-by-Step)

### Task: Add a New Alert Rule Type

**Goal**: Add support for a new condition in alert rules

**Step 1**: Update the AlertRule model
```
File: c:\Users\AbuBa\crypto_predict_monitor\src\alerts.py
```
```python
class AlertRule(BaseModel):
    market_id: str
    min_probability: float | None = None
    max_probability: float | None = None
    min_delta: float | None = None
    # ADD YOUR NEW FIELD HERE
    new_condition: float | None = None  # Example
```

**Step 2**: Add validation if needed
```python
@field_validator("new_condition")
@classmethod
def _validate_new_condition(cls, v: float | None) -> float | None:
    if v is None:
        return None
    if v < 0:
        raise ValueError("new_condition must be >= 0")
    return v
```

**Step 3**: Update evaluate_event() to check the new condition
```python
# In evaluate_event() function, add check:
if rule.new_condition is not None:
    if some_check(event, rule.new_condition):
        triggered = True
        trigger_reason = f"new_condition triggered"
```

**Step 4**: Add tests
```
File: c:\Users\AbuBa\crypto_predict_monitor\tests\test_alerts.py
```
```python
def test_new_condition_triggers_alert():
    rule = AlertRule(market_id="test", new_condition=0.5)
    event = MarketEvent(...)
    result = evaluate_event(event, rule, None)
    assert result is not None
```

**Step 5**: Run tests
```powershell
pytest tests/test_alerts.py -v
```

---

### Task: Add a New Upstream Data Source

**Goal**: Fetch data from a new API

**Step 1**: Add new mode to allowed upstreams
```
File: c:\Users\AbuBa\crypto_predict_monitor\src\config.py
```
```python
_ALLOWED_UPSTREAMS = {"dev", "polymarket", "price", "multi", "newmode"}
```

**Step 2**: Add fetch function
```
File: c:\Users\AbuBa\crypto_predict_monitor\src\fetcher.py
```
```python
def _fetch_newmode_events(
    client: HttpClient,
    # ... parameters
) -> list[MarketEvent]:
    """Fetch events from NewMode API."""
    # Implementation here
    pass
```

**Step 3**: Wire it up in fetch_events()
```python
def fetch_events(...) -> list[MarketEvent]:
    if upstream == "newmode":
        return _fetch_newmode_events(client, ...)
    # ... existing code
```

**Step 4**: Add any new config settings
```
File: c:\Users\AbuBa\crypto_predict_monitor\src\config.py
```
```python
class Settings(BaseModel):
    # ... existing fields
    newmode_api_url: str | None = None
```

**Step 5**: Update documentation (batched with other changes)

---

### Task: Fix a Bug

**Step 1**: Reproduce the bug
```powershell
# Set up environment
$env:CPM_UPSTREAM = "dev"
$env:CPM_BASE_URL = "http://localhost:8000"

# Run and observe the error
python -m src.main
```

**Step 2**: Write a failing test first (optional but recommended)
```python
def test_bug_123_should_not_crash():
    # This test should fail before the fix
    result = buggy_function(problematic_input)
    assert result is not None
```

**Step 3**: Fix the bug in the source code

**Step 4**: Verify the test passes
```powershell
pytest tests/test_module.py::test_bug_123_should_not_crash -v
```

**Step 5**: Run full test suite
```powershell
pytest
```

---

## 9. Development Workflow

### Daily Process

```powershell
# 1. Navigate to project
cd c:\Users\AbuBa\crypto_predict_monitor

# 2. Activate virtual environment
.venv\Scripts\activate

# 3. Pull latest changes (if using git)
git pull

# 4. Run tests to make sure everything works
pytest

# 5. Make your changes...

# 6. Run tests again
pytest

# 7. Check coverage
pytest --cov=src

# 8. Commit (if using git)
git add .
git commit -m "Description of changes"
```

### Environment Setup (One-Time)

```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install pytest pytest-cov
```

### Running the Monitor

```powershell
# Set required environment variables
$env:CPM_MODE = "monitor"
$env:CPM_UPSTREAM = "polymarket"
$env:CPM_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK"
$env:CPM_POLYMARKET_MARKETS_JSON = '{"btc_up": {"token_id": "abc123"}}'
$env:CPM_RULES_JSON = '[{"market_id": "btc_up", "min_probability": 0.7}]'

# Run
python -m src.main
```

### Running the Dev Server (For Testing)

```powershell
# Terminal 1: Start dev server
python tools/dev_server.py

# Terminal 2: Run monitor against dev server
$env:CPM_MODE = "monitor"
$env:CPM_UPSTREAM = "dev"
$env:CPM_BASE_URL = "http://localhost:8000"
python -m src.main
```

---

## 10. Key Concepts Explained

### Pydantic (Data Validation Library)

**What it is**: A library that validates data and converts it to Python objects.

**Analogy**: Like a bouncer at a club who checks IDs. If your data doesn't match the expected format, it gets rejected.

```python
from pydantic import BaseModel

class Person(BaseModel):
    name: str
    age: int  # Must be an integer

# ✅ This works
person = Person(name="Alice", age=30)

# ❌ This raises an error (age must be int)
person = Person(name="Bob", age="thirty")
```

**Why we use it**: 
- Catches bad data early
- Provides clear error messages
- Auto-generates documentation

---

### Webhooks (Discord Notifications)

**What it is**: A way to send messages to Discord without a bot.

**Analogy**: Like a mailbox. You put a letter (JSON payload) in the mailbox (webhook URL), and Discord delivers it.

```python
# Simplified webhook call
import httpx

webhook_url = "https://discord.com/api/webhooks/123/abc"
payload = {"content": "Hello from the monitor!"}

httpx.post(webhook_url, json=payload)
```

**Why we use it**:
- No bot token needed
- Simple HTTP POST
- Discord handles delivery

---

### Mocking (Test Isolation)

**What it is**: Replacing real dependencies with fake ones during tests.

**Analogy**: Like using a crash test dummy instead of a real person. You test the car's safety without risking anyone.

```python
from unittest.mock import patch, MagicMock

def test_webhook_sends_message():
    # Replace real HTTP client with a fake
    with patch("src.webhook.httpx.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        
        send_webhook("http://fake.url", payload)
        
        # Verify it was called
        mock_post.assert_called_once()
```

**Why we mock**:
- Tests run fast (no network calls)
- Tests are reliable (no API failures)
- Tests are free (no API costs)

---

### Edge-Triggered vs Level-Triggered Alerts

**Level-triggered**: Fires every time condition is true
```
Time:  1   2   3   4   5
Value: 0.8 0.8 0.8 0.8 0.8
Alert: 🔔  🔔  🔔  🔔  🔔  (5 alerts - annoying!)
```

**Edge-triggered**: Fires only when condition becomes true
```
Time:  1   2   3   4   5
Value: 0.5 0.8 0.8 0.8 0.8
Alert: -   🔔  -   -   -   (1 alert - useful!)
```

**We use edge-triggered** to avoid alert spam.

---

### Retry with Exponential Backoff

**What it is**: When a request fails, wait longer before each retry.

**Analogy**: Like calling a busy friend. First wait 1 minute, then 2 minutes, then 4 minutes...

```
Attempt 1: Fail → Wait 1 second
Attempt 2: Fail → Wait 2 seconds
Attempt 3: Fail → Wait 4 seconds
Attempt 4: Fail → Wait 8 seconds
Attempt 5: Success! ✅
```

**Why we use it**:
- Gives servers time to recover
- Doesn't hammer failing services
- Eventually succeeds if issue is temporary

---

## 11. Security Checklist

### Before Every Commit

- [ ] **No hardcoded secrets** — Search for API keys, tokens, passwords
- [ ] **No secrets in logs** — Check all `logger.info/warning/error` calls
- [ ] **URL parameters encoded** — Use `urllib.parse.quote()` for user input
- [ ] **Timeouts on all HTTP calls** — Never wait forever
- [ ] **Input validation** — All external data goes through Pydantic

### Sensitive Data Patterns to Watch

```python
# ❌ NEVER DO THIS
api_key = "sk-1234567890abcdef"  # Hardcoded secret!
logger.info(f"Using key: {api_key}")  # Logging secret!

# ✅ DO THIS INSTEAD
api_key = os.environ.get("API_KEY")  # From environment
logger.info("API key configured: %s", "[REDACTED]")  # Redacted
```

### Environment Variables for Secrets

All secrets must come from environment variables:
- `CPM_API_KEY` — API authentication
- `CPM_WEBHOOK_URL` — Discord webhook (contains token)

See `SECRETS.md` for the complete list.

---

## 12. Debugging Tips

### Problem: Module Not Found

```
ModuleNotFoundError: No module named 'src'
```

**Solution**: Run from project root with `-m` flag
```powershell
cd c:\Users\AbuBa\crypto_predict_monitor
python -m src.main
```

---

### Problem: Environment Variable Not Set

```
KeyError: 'CPM_WEBHOOK_URL'
```

**Solution**: Set the variable in PowerShell
```powershell
$env:CPM_WEBHOOK_URL = "https://discord.com/api/webhooks/..."
```

---

### Problem: Pydantic Validation Error

```
ValidationError: 1 validation error for Settings
probability
  value is not a valid float (type=type_error.float)
```

**Solution**: Check the input type. Pydantic is strict.
```python
# ❌ Wrong
probability = "0.5"  # String, not float

# ✅ Right
probability = 0.5  # Actual float
```

---

### Problem: HTTP Request Timeout

```
httpx.ReadTimeout: timed out
```

**Solution**: 
1. Check if the API is up
2. Increase timeout if needed
3. Check network connectivity

```powershell
# Test API manually
curl https://api.example.com/health
```

---

### Problem: Tests Failing After Changes

```powershell
# See which tests fail
pytest -v

# Run just the failing test with more detail
pytest tests/test_alerts.py::test_that_fails -v --tb=long

# Check if it's a mock issue
pytest tests/test_alerts.py::test_that_fails -v --tb=long -s
```

---

### Useful Debug Commands

```powershell
# Check Python version
python --version

# Check installed packages
pip list

# Check if module imports correctly
python -c "from src.config import load_settings; print('OK')"

# Run with debug logging
$env:CPM_LOG_LEVEL = "DEBUG"
python -m src.main
```

---

## 13. Phase Roadmap

### ✅ Phase A: Core Alert System (COMPLETE)
- Basic monitor loop
- Alert rule evaluation
- Discord webhooks
- Retry logic
- Configuration
- Logging with redaction

### ✅ Phase B: Advanced Alerts (COMPLETE)
- Cooldown support
- Once-only alerts
- Edge-triggered alerts
- Severity escalation
- Custom reason templates
- Webhook versioning

### ✅ Phase C: Multi-Upstream (COMPLETE)
- Polymarket integration
- Coinbase price feed
- Multi-mode merging
- Error handling per source

### 🔜 Phase D: Trading Execution (FUTURE)
- Trading adapter interface
- Position management
- Risk controls
- Order execution
- Trade tracking
- P&L calculation

### 🔮 Future Phases
- Web dashboard
- Historical data
- Backtesting
- Mobile notifications

---

## 14. Communication Guide

### When Reporting Progress

```
✅ GOOD:
"Completed: Added URL encoding for token_id in fetcher.py (line 168).
This prevents injection if token_id contains special characters."

❌ BAD:
"Done."
```

### When Reporting Errors

```
✅ GOOD:
"Error in src/fetcher.py line 45: `KeyError: 'price'`
The Polymarket API response doesn't have a 'price' field.
Actual response: {'bid': 0.5, 'ask': 0.6}
Suggested fix: Use 'bid' or 'ask' instead."

❌ BAD:
"It's broken."
```

### When Asking Questions

```
✅ GOOD:
"The Coinbase API returns timestamps in Unix format, but our MarketEvent
expects ISO 8601. Should I:
A) Convert in fetcher.py (keeps schema clean)
B) Accept both formats in schema (more flexible)
I recommend A because it keeps the schema simple."

❌ BAD:
"What format should I use?"
```

---

## 15. Quick Reference

### File Locations
| What | Where |
|------|-------|
| Main entry point | `src/main.py` |
| Configuration | `src/config.py` |
| Alert logic | `src/alerts.py` |
| Data fetching | `src/fetcher.py` |
| HTTP client | `src/http_client.py` |
| Tests | `tests/` |

### Key Commands
```powershell
# Run monitor
python -m src.main

# Run tests
pytest

# Run with coverage
pytest --cov=src

# Set environment variable
$env:VAR_NAME = "value"
```

### Environment Variables
| Variable | Required | Description |
|----------|----------|-------------|
| `CPM_MODE` | No | `health` or `monitor` |
| `CPM_UPSTREAM` | Yes | `dev`, `polymarket`, `price`, `multi` |
| `CPM_WEBHOOK_URL` | Yes | Discord webhook URL |
| `CPM_RULES_JSON` | Yes | Alert rules as JSON array |

### Upstream Modes
| Mode | Data Source | Required Config |
|------|-------------|-----------------|
| `dev` | Local server | `CPM_BASE_URL` |
| `polymarket` | Polymarket API | `CPM_POLYMARKET_MARKETS_JSON` |
| `price` | Coinbase API | `CPM_PRICE_SYMBOL` |
| `multi` | Both | Both above |

---

*Last updated: Phase C completion*
