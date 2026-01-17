# Crypto Prediction Market Arbitrage Bot

A **spread-only** arbitrage detection system for crypto prediction markets. The bot identifies cross-platform arbitrage opportunities based purely on spread percentages, filtering out noise and focusing on profitable trades.

## 🎯 Core Strategy: Spread-Only Arbitrage

**NO volume tracking • NO liquidity metrics • NO complex scoring**

Just pure spread-based arbitrage detection with a 6-tier system:

| Tier | Spread Range | Action | Priority |
|------|-------------|--------|----------|
| 🔵 **Exceptional** | 3.0%+ | IMMEDIATE ATTENTION | 1 |
| 🟢 **Excellent** | 2.51-3.0% | ACT QUICKLY | 2 |
| 💛 **Very Good** | 2.01-2.5% | STRONG YES | 3 |
| 🟠 **Good** | 1.5-2.0% | **YOUR STRATEGY** | 4 |
| ⚪ **Fair** | 1.0-1.5% | Filtered out | 5 |
| ⚫ **Poor** | <1.0% | Filtered out | 6 |

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL (for dashboard)
- Discord webhook URLs

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/samuraifrenchienft/crypto_predict_monitor.git
cd crypto_predict_monitor
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment**
```bash
cp env.example .env
# Edit .env with your Discord webhook URLs and database URL
```

4. **Configure the bot**
```bash
# Edit config.yaml to adjust settings if needed
# Default: 1.5% minimum spread, all platforms enabled
```

5. **Run the bot**
```bash
python main.py
```

## 📁 Project Structure

```
crypto-arbitrage-bot/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── config.yaml                        # Single configuration file
├── env.example                        # Environment variables template
│
├── bot/                               # Bot core (arbitrage detection)
│   ├── __init__.py
│   ├── config.py                      # Configuration loader
│   ├── models.py                      # Data models (Market, Quote, etc.)
│   │
│   ├── adapters/                      # Platform adapters
│   │   ├── __init__.py
│   │   ├── base.py                    # Base adapter class
│   │   ├── polymarket.py
│   │   ├── azuro.py
│   │   ├── manifold.py
│   │   └── limitless.py
│   │
│   ├── detection/                     # Arbitrage detection logic
│   │   ├── __init__.py
│   │   ├── arbitrage.py               # Arbitrage calculation
│   │   └── filter.py                  # Tiered filtering (spread-only)
│   │
│   ├── scoring/                       # Quality scoring
│   │   ├── __init__.py
│   │   └── spread_scorer.py           # Spread-only quality scores
│   │
│   └── alerts/                        # Alert system
│       ├── __init__.py
│       └── discord.py                 # Discord webhook alerts
│
├── dashboard/                         # Web dashboard
│   ├── __init__.py
│   ├── app.py                         # Flask app
│   ├── auth.py                        # Authentication
│   ├── db.py                          # Database connection
│   ├── models.py                      # Database models
│   └── templates/
│       ├── index.html                 # Main dashboard
│       └── leaderboard.html           # Leaderboard page
│
├── shared/                            # Shared utilities
│   ├── __init__.py
│   ├── logger.py                      # Centralized logging
│   ├── http_client.py                 # HTTP utilities
│   └── utils.py                       # Common helpers
│
├── scripts/                           # Utility scripts
│   ├── verify_config.py               # Config validation
│   ├── test_adapters.py               # Adapter testing
│   └── migrate_db.py                  # Database migrations
│
├── tests/                             # Test suite
│   ├── __init__.py
│   ├── test_filter.py
│   ├── test_scoring.py
│   └── test_adapters.py
│
└── data/                              # Runtime data
    ├── logs/                          # Application logs
    └── snapshots/                     # Debug snapshots
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Required
CPM_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_TOKEN
DISCORD_HEALTH_WEBHOOK_URL=https://discord.com/api/webhooks/HEALTH_WEBHOOK_ID/HEALTH_TOKEN
DATABASE_URL=postgresql://user:pass@localhost:5432/cpm_arbitrage
FLASK_SECRET_KEY=your_secret_key_here

# Optional
DISCORD_BOT_TOKEN=your_discord_bot_token
DEBUG_MODE=false
```

### Bot Configuration (config.yaml)

Key settings in `config.yaml`:

```yaml
strategy:
  min_spread: 0.015  # 1.5% minimum spread

tiers:
  good:
    min_spread: 1.5    # Your strategy threshold
    emoji: "🟠"
    action: "YOUR STRATEGY"

platforms:
  polymarket:
    enabled: true
    rate_limit: 100
```

## 🔧 Supported Platforms

- **Polymarket** - https://polymarket.com
- **Azuro** - https://bookmaker.xyz
- **Manifold** - https://manifold.markets
- **Limitless** - https://limitless.exchange

## 📊 Features

### ✅ What's Included
- **Spread-only filtering** - Clean, simple arbitrage detection
- **6-tier system** - Clear opportunity categorization
- **Real-time alerts** - Discord notifications for GOOD tier and above
- **Web dashboard** - Monitor opportunities and performance
- **Quality scoring** - 0-10 scale based on spread percentage
- **Health monitoring** - System status and error tracking
- **Structured logging** - JSON logs for production monitoring

### ❌ What's Removed (Intentionally)
- Volume tracking metrics
- Liquidity analysis
- Complex scoring algorithms
- Mock data/demo modes
- Deprecated features
- Duplicate filtering logic

## 🚨 Discord Alerts

The bot sends tiered Discord alerts:

- **🔵 Exceptional** (3.0%+) - Immediate attention
- **🟢 Excellent** (2.51-3.0%) - Act quickly
- **💛 Very Good** (2.01-2.5%) - Strong opportunity
- **🟠 Good** (1.5-2.0%) - Your strategy threshold
- **⚪ Fair/Poor** - Filtered out, no alerts

Each alert includes:
- Spread percentage and quality score
- Direct links to both markets
- Tier-specific color coding
- Market details and timestamps

## 📈 Dashboard

Web dashboard provides:
- Live arbitrage opportunities
- Tier breakdown statistics
- Historical performance
- Market links and details
- Quality score distribution

Access at: `http://localhost:5000`

## 🧪 Testing

Run the test suite:

```bash
# Test tiered filtering
python -m pytest tests/test_filter.py

# Test quality scoring
python -m pytest tests/test_scoring.py

# Test platform adapters
python -m pytest tests/test_adapters.py

# Run all tests
python -m pytest tests/
```

## 🔍 Monitoring & Logging

### Logs
- **Location**: `data/logs/cpm.log`
- **Format**: Structured JSON (production) or simple text
- **Rotation**: 10MB max, 5 backups

### Health Checks
- Platform API status monitoring
- Error rate tracking
- Performance metrics
- Discord health alerts

## 🛠️ Development

### Adding New Platforms

1. Create adapter in `bot/adapters/new_platform.py`
2. Inherit from `BaseAdapter`
3. Implement required methods:
   - `fetch_markets()`
   - `fetch_quotes()`
   - `get_market_url()`
   - `normalize_market_title()`

4. Add platform config to `config.yaml`
5. Update `Platform` enum in `models.py`

### Customizing Tiers

Edit `tiers` section in `config.yaml`:

```yaml
tiers:
  custom_tier:
    min_spread: 2.0
    emoji: "🎯"
    color: "#ff00ff"
    action: "CUSTOM ACTION"
    priority: 3
    alert: true
```

## 📋 Requirements

See `requirements.txt` for full list. Key dependencies:

- `aiohttp` - Async HTTP client
- `flask` - Web dashboard
- `sqlalchemy` - Database ORM
- `pyyaml` - Configuration parsing
- `requests` - HTTP client
- `pytest` - Testing framework

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

- **Issues**: Create GitHub issue
- **Discord**: Join our community
- **Documentation**: See `/docs` folder

---

**Built with ❤️ for crypto arbitrage traders**
