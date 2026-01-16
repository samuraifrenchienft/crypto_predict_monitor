# 🏗️ Build and Deployment Flow

> This guide walks you through setting up and running the crypto prediction monitor.
> Follow the steps in order if you're new to the project.

---

## 🚀 Quick Start (First Time Setup)

**Do this once when you first clone the project.**

### Step 1: Open PowerShell in the Project Folder

```
📁 Location: c:\Users\AbuBa\crypto_predict_monitor
⏰ When: Before anything else
```

Right-click in the project folder → "Open in Terminal" or open PowerShell and navigate:

```powershell
PS C:\Users\AbuBa> cd crypto_predict_monitor
PS C:\Users\AbuBa\crypto_predict_monitor>
```

### Step 2: Create a Virtual Environment

```
📁 Location: Project root folder
⏰ When: First time only (one-time setup)
```

```powershell
PS C:\Users\AbuBa\crypto_predict_monitor> python -m venv .venv
```

This creates a `.venv` folder that isolates your Python packages from other projects.

### Step 3: Activate the Virtual Environment

```
📁 Location: Project root folder
⏰ When: Every time you open a new terminal to work on this project
```

```powershell
PS C:\Users\AbuBa\crypto_predict_monitor> .venv\Scripts\activate
```

Your prompt should change to show `(.venv)`:
```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor>
```

> ⚠️ **Important**: If you don't see `(.venv)` at the start of your prompt, the virtual environment is NOT active. Run the activate command again.

### Step 4: Install Dependencies

```
📁 Location: Project root folder (with .venv activated)
⏰ When: First time, or after requirements.txt changes
```

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> pip install -r requirements.txt
```

### Step 5: Verify Installation

```
📁 Location: Project root folder (with .venv activated)
⏰ When: After installing dependencies
```

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> python -c "from src.config import Settings; print('✅ Setup complete!')"
```

If you see `✅ Setup complete!`, you're ready to go!

---

## 🏃 Running the Monitor

### 🩺 Health Check Mode (Default)

**What it does**: Verifies the system can start and configuration is valid. Does NOT poll for events.

**Use this when**: Testing that your setup works before running the full monitor.

```
📁 Location: Project root folder (with .venv activated)
⏰ When: To verify configuration is correct
```

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> python -m src.main
```

Or explicitly set the mode:

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_MODE = "health"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> python -m src.main
```

---

### 🔧 Dev Mode (Local Testing)

**What it does**: Fetches events from a local dev server you run yourself. Great for testing without hitting real APIs.

**Use this when**: Developing new features or testing alert rules locally.

**Step 1**: Start the dev server (in one terminal):

```
📁 Location: Project root folder (with .venv activated)
⏰ When: Before running the monitor in dev mode
```

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> python tools/dev_server.py
```

Keep this terminal open! The dev server runs on `http://localhost:8000`.

**Step 2**: Run the monitor (in a second terminal):

```
📁 Location: Project root folder (with .venv activated)
⏰ When: After the dev server is running
```

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_MODE = "monitor"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_UPSTREAM = "dev"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_BASE_URL = "http://localhost:8000"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK_HERE"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> python -m src.main
```

---

### 📊 Polymarket Mode (Real Prediction Markets)

**What it does**: Fetches real probability data from Polymarket's CLOB API. Monitors prediction market outcomes.

**Use this when**: You want to track real Polymarket prediction markets.

```
📁 Location: Project root folder (with .venv activated)
⏰ When: For production monitoring of Polymarket
```

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_MODE = "monitor"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_UPSTREAM = "polymarket"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_POLYMARKET_MARKETS_JSON = '{"btc_100k": {"token_id": "abc123", "question": "Will BTC hit 100k?"}}'
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_RULES_JSON = '[{"market_id": "btc_100k", "min_probability": 0.7}]'
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> python -m src.main
```

**Required environment variables**:
| Variable | Description | Example |
|----------|-------------|---------|
| `CPM_POLYMARKET_MARKETS_JSON` | JSON object mapping market IDs to token info | `{"btc_100k": {"token_id": "abc..."}}` |
| `CPM_RULES_JSON` | Alert rules as JSON array | `[{"market_id": "btc_100k", "min_probability": 0.7}]` |

---

### 💰 Price Mode (Crypto Prices)

**What it does**: Fetches real-time crypto prices from Coinbase. Monitors price changes and calculates deltas.

**Use this when**: You want to track crypto price movements (BTC, ETH, etc.).

```
📁 Location: Project root folder (with .venv activated)
⏰ When: For monitoring crypto prices
```

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_MODE = "monitor"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_UPSTREAM = "price"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_PRICE_PROVIDER = "coinbase"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_PRICE_SYMBOL = "BTC-USD"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_RULES_JSON = '[{"market_id": "BTC-USD", "min_delta": 0.05}]'
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> python -m src.main
```

**Required environment variables**:
| Variable | Description | Example |
|----------|-------------|---------|
| `CPM_PRICE_PROVIDER` | Price data source | `coinbase` |
| `CPM_PRICE_SYMBOL` | Trading pair to monitor | `BTC-USD`, `ETH-USD` |

**Optional**:
| Variable | Description | Default |
|----------|-------------|---------|
| `CPM_PRICE_INTERVAL_MINUTES` | How often to check prices | `15` |

---

### 🔀 Multi Mode (Combined Sources)

**What it does**: Fetches from BOTH Polymarket AND Coinbase, merging events together. Best of both worlds.

**Use this when**: You want to monitor prediction markets AND crypto prices simultaneously.

```
📁 Location: Project root folder (with .venv activated)
⏰ When: For comprehensive monitoring
```

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_MODE = "monitor"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_UPSTREAM = "multi"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_WEBHOOK_URL = "https://discord.com/api/webhooks/YOUR_WEBHOOK"

# Polymarket settings
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_POLYMARKET_MARKETS_JSON = '{"btc_100k": {"token_id": "abc123"}}'

# Price settings
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_PRICE_PROVIDER = "coinbase"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_PRICE_SYMBOL = "BTC-USD"

# Rules for both
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_RULES_JSON = '[{"market_id": "btc_100k", "min_probability": 0.7}, {"market_id": "BTC-USD", "min_delta": 0.05}]'

(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> python -m src.main
```

---

## 🧪 Testing

### Run All Tests

```
📁 Location: Project root folder (with .venv activated)
⏰ When: Before committing changes, after making edits
```

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> pytest
```

### Run Tests with Coverage Report

```
📁 Location: Project root folder (with .venv activated)
⏰ When: To check how much code is tested
```

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> pytest --cov=src
```

### Run a Specific Test File

```
📁 Location: Project root folder (with .venv activated)
⏰ When: Debugging a specific module
```

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> pytest tests/test_alerts.py
```

### Run a Specific Test Function

```
📁 Location: Project root folder (with .venv activated)
⏰ When: Debugging a specific test
```

```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> pytest tests/test_alerts.py::test_cooldown_prevents_spam -v
```

---

## ⚙️ Configuration Modes Summary

| Mode | Data Source | Best For | Required Config |
|------|-------------|----------|-----------------|
| 🔧 `dev` | Local dev server | Testing locally | `CPM_BASE_URL` |
| 📊 `polymarket` | Polymarket API | Prediction markets | `CPM_POLYMARKET_MARKETS_JSON` |
| 💰 `price` | Coinbase API | Crypto prices | `CPM_PRICE_SYMBOL` |
| 🔀 `multi` | Both APIs | Full monitoring | All of the above |

---

## 📋 Environment Variables Reference

See `SECRETS.md` for the complete list with security notes.

### Core Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CPM_MODE` | No | `health` or `monitor` (default: `health`) |
| `CPM_UPSTREAM` | Yes* | `dev`, `polymarket`, `price`, or `multi` |
| `CPM_WEBHOOK_URL` | Yes* | Discord webhook URL for alerts |
| `CPM_RULES_JSON` | Yes* | Alert rules as JSON array |

*Required for monitor mode

---

## 🚢 Deployment

### Current Status
- **Phase C**: Alerts-only monitoring ✅
- **Phase D**: Trading execution (FUTURE)

### Current Deployment
Manual deployment only. Run the monitor in a terminal or as a background process.

### Future Plans
- 🐳 Docker containerization
- ☁️ Cloud deployment (AWS/GCP)
- 🔄 CI/CD pipeline
- 🤖 Automated testing

---

## ❓ Common Issues

### Problem: `(.venv)` not showing in prompt

**Symptom**: Your prompt shows `PS C:\...>` instead of `(.venv) PS C:\...>`

**Cause**: Virtual environment is not activated.

**Solution**:
```powershell
PS C:\Users\AbuBa\crypto_predict_monitor> .venv\Scripts\activate
```

---

### Problem: `python: command not found` or `python is not recognized`

**Symptom**: PowerShell doesn't recognize the `python` command.

**Cause**: Python is not installed or not in your PATH.

**Solution**:
1. Download Python from https://python.org
2. During installation, check ✅ "Add Python to PATH"
3. Restart PowerShell

---

### Problem: `ModuleNotFoundError: No module named 'src'`

**Symptom**: Error when running `python src/main.py`

**Cause**: Running Python wrong way.

**Solution**: Use the `-m` flag:
```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> python -m src.main
```

---

### Problem: `pip install` fails with permission error

**Symptom**: `ERROR: Could not install packages due to an EnvironmentError`

**Cause**: Virtual environment not activated, or permission issues.

**Solution**:
1. Make sure `.venv` is activated (see `(.venv)` in prompt)
2. If still failing, try:
```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> pip install --user -r requirements.txt
```

---

### Problem: `KeyError: 'CPM_WEBHOOK_URL'`

**Symptom**: Error about missing environment variable.

**Cause**: Required environment variable not set.

**Solution**: Set the variable before running:
```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_WEBHOOK_URL = "https://discord.com/api/webhooks/..."
```

---

### Problem: Dev server won't start

**Symptom**: Error when running `python tools/dev_server.py`

**Cause**: Port 8000 might be in use.

**Solution**: Check if something else is using port 8000:
```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> netstat -ano | findstr :8000
```

If something is using it, either stop that process or modify the dev server to use a different port.

---

### Problem: Tests fail with import errors

**Symptom**: `pytest` fails with `ModuleNotFoundError`

**Cause**: pytest not installed or wrong Python environment.

**Solution**:
```powershell
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> pip install pytest pytest-cov
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> pytest
```

---

### Problem: Webhook not sending messages

**Symptom**: Monitor runs but no Discord messages appear.

**Possible causes**:
1. Webhook URL is incorrect
2. Alert rules never trigger
3. Network/firewall blocking

**Debug steps**:
```powershell
# Enable debug logging
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> $env:CPM_LOG_LEVEL = "DEBUG"
(.venv) PS C:\Users\AbuBa\crypto_predict_monitor> python -m src.main
```

Look for log messages about webhook calls or alert evaluations.

---

*Last updated: Phase C completion*
