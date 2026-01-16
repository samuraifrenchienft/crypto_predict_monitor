# Crypto Predict Monitor

**Advanced crypto prediction market monitoring system** with P&L tracking, multi-venue support, and comprehensive alerting.

## 🚀 Overview
A production-ready monitoring system that tracks crypto prediction markets across multiple venues, provides real-time alerts, and includes sophisticated P&L analytics with social sharing capabilities.

## ✨ Key Features
- **Multi-venue support**: Dev server, Polymarket CLOB, Coinbase price feeds
- **P&L Tracking**: Comprehensive profit/loss analytics with visual card generation
- **Social Sharing**: Auto-generated P&L cards for Twitter/Discord
- **Advanced Alerting**: Thresholds, cooldowns, severity escalation, custom templates
- **Database Integration**: Supabase backend with migrations and RLS
- **Web Dashboard**: React-based real-time monitoring interface
- **API Layer**: RESTful endpoints for all system functions
- **Reliable Delivery**: Automatic retries, idempotency, schema versioning
- **Security**: JWT auth, rate limiting, input validation, log redaction
- **Performance Monitoring**: Metrics, error tracking, and health checks
- **Production Deployment**: Docker, CI/CD, monitoring stack

## 🎯 What's New in v2.0.0

### Major Features
- **🎨 P&L Card System**: Generate beautiful visual cards for social sharing
- **🌐 Modern Dashboard**: React-based interface with real-time WebSocket updates
- **🗄️ Database Layer**: Full Supabase integration with migrations and RLS
- **🐳 Production Ready**: Complete Docker setup with multi-stage builds
- **📊 Monitoring Stack**: Prometheus, Grafana, and Loki integration
- **🔒 Enhanced Security**: JWT authentication, rate limiting, input validation

### Technical Improvements
- **API Documentation**: Complete OpenAPI reference with examples
- **CI/CD Pipeline**: Automated testing, building, and deployment
- **Quality Assurance**: 80% test coverage with comprehensive QA suite
- **Performance Optimization**: Connection pooling, caching, and monitoring
- **Error Handling**: Structured logging and error tracking
- **Scalability**: Horizontal scaling support with load balancing

## 🏗️ Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│   Monitor Core  │───▶│   Alert System  │
│                 │    │                 │    │                 │
│ • Polymarket    │    │ • Event Loop    │    │ • Discord       │
│ • Coinbase      │    │ • Rules Engine  │    │ • Webhooks      │
│ • Dev Server    │    │ • State Mgmt    │    │ • Escalation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HTTP Client   │    │   Database      │    │   P&L System    │
│                 │    │                 │    │                 │
│ • Retries       │    │ • Supabase      │    │ • Card Generator│
│ • Rate Limits   │    │ • Migrations    │    │ • Social Share  │
│ • Error Handling│    │ • RLS Policies  │    │ • Analytics     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (for production)
- Supabase account (for database)

### Installation

1. **Clone and setup**
```bash
git clone <repository-url>
cd crypto_predict_monitor
python -m venv .venv
.venv\Scripts\activate  # Windows
# or: source .venv/bin/activate  # Unix
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
pip install -r pnl_requirements.txt
cd frontend && npm install && cd ..
```

3. **Environment setup**
```bash
cp config/staging.env .env
# Edit .env with your configuration
```

4. **Database setup**
```bash
# Run Supabase migrations
python -c "from src.database.migrate import run_supabase_migrations; run_supabase_migrations()"
```

### Running the System

**Development Mode:**
```bash
# Start backend
python -m src.main_enhanced

# Start dashboard (separate terminal)
python run_dashboard.py

# Start frontend (separate terminal)
cd frontend && npm start
```

**Docker Mode:**
```bash
# Staging
docker-compose up -d

# Production
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 P&L Card System

The system includes a sophisticated P&L tracking and social sharing system:

### Features
- **Real-time P&L calculation** from prediction market data
- **Visual card generation** with customizable themes
- **Social media integration** for Twitter/Discord sharing
- **Performance metrics** including win rates and volume tracking

### API Endpoints
```bash
# Generate P&L card
GET /api/pnl-card/{user_id}

# Get shareable metadata
GET /api/pnl-card/{user_id}/share

# Health check
GET /api/pnl-card/health
```

### Card Customization
```python
# Customize card appearance
pnl_service = PnLCardService(
    background_image_path="assets/custom_bg.png",
    theme="dark",  # or "light"
    show_volume=True,
    show_win_rate=True
)
```

## 🔧 Configuration

### Environment Variables
```bash
# Core Configuration
CPM_MODE=monitor                    # health, monitor, api
CPM_UPSTREAM=dev                    # dev, polymarket, price, multi
CPM_BASE_URL=http://localhost:8000  # API base URL

# Database
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Webhooks
CPM_WEBHOOK_URL=discord_webhook_url
DISCORD_HEALTH_WEBHOOK_URL=health_webhook_url

# Security
JWT_SECRET_KEY=your_jwt_secret
API_RATE_LIMIT=100                  # requests per hour

# P&L Cards
S3_BUCKET=your_s3_bucket           # for card storage
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
```

### Alert Rules Configuration
```yaml
rules:
  - market_id: "0x123..."
    threshold_price: 0.75
    cooldown_minutes: 15
    severity: "high"
    template: "price_alert"
    
  - market_id: "0x456..."
    threshold_volume: 1000000
    cooldown_minutes: 30
    severity: "medium"
```

## 🌐 Web Dashboard

Access the dashboard at `http://localhost:3000`

### Features
- **Real-time market monitoring** with WebSocket updates
- **P&L visualization** and analytics
- **Alert management** and configuration
- **User authentication** with JWT tokens
- **Responsive design** for mobile/desktop

### Components
- **Market Overview**: Live price feeds and market data
- **P&L Tracker**: Personal profit/loss analytics
- **Alert Center**: Configure and manage alert rules
- **Settings**: System configuration and preferences

## 📡 API Documentation

### Core Endpoints

#### Monitoring
```bash
GET  /health                         # System health check
GET  /markets                        # List all markets
GET  /markets/{id}                   # Market details
POST /alerts                         # Create alert rule
GET  /alerts                         # List alert rules
```

#### P&L System
```bash
GET  /api/pnl-card/{user_id}         # Download P&L card
GET  /api/pnl-card/{user_id}/share   # Get shareable metadata
GET  /api/pnl-card/health            # P&L service health
```

#### Database
```bash
GET  /api/pnl/snapshots              # P&L snapshots
GET  /api/pnl/analytics              # P&L analytics
POST /api/pnl/import                 # Import P&L data
```

### Authentication
All protected endpoints require JWT authentication:
```bash
Authorization: Bearer <your_jwt_token>
```

## 🐳 Docker Deployment

### Development
```bash
docker-compose -f docker-compose.yml up
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Services
- **app**: Main monitoring application
- **dashboard**: Web dashboard
- **database**: Supabase/PostgreSQL
- **nginx**: Reverse proxy and SSL termination
- **redis**: Caching and session storage
- **prometheus**: Metrics collection
- **grafana**: Monitoring dashboards
- **loki**: Log aggregation

## 🧪 Testing

### QA Validation
```bash
python scripts/qa_validation.py
```

### Unit Tests
```bash
pytest tests/unit/
pytest tests/unit/ --cov=src --cov-report=html
```

### Integration Tests
```bash
pytest tests/integration/
pytest tests/integration/ --cov=src
```

### Performance Tests
```bash
python test_load_performance.py
python test_api_comprehensive.py
```

### Security Tests
```bash
python test_security.py
bandit -r src/
```

## 🔒 Security Features

- **JWT Authentication**: Secure token-based auth
- **Rate Limiting**: Configurable per-user limits
- **Input Validation**: Pydantic models throughout
- **SQL Injection Protection**: Parameterized queries
- **CORS Protection**: Configurable origin policies
- **Log Redaction**: Automatic sensitive data masking
- **HTTPS Only**: SSL/TLS enforcement in production

## 📈 Performance Monitoring

### Metrics Collection
- **Response times**: API endpoint performance
- **Error rates**: Failure tracking and alerting
- **Resource usage**: CPU, memory, and disk monitoring
- **Database performance**: Query optimization metrics

### Health Checks
```bash
# System health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/api/health/db

# P&L service health
curl http://localhost:8000/api/pnl-card/health
```

### Monitoring Stack
- **Grafana Dashboard**: http://localhost:3001
- **Prometheus**: http://localhost:9090
- **Loki Logs**: http://localhost:3100

## 🚀 Deployment

### Automated Deployment
```bash
# Staging
./deploy.sh staging

# Production
./deploy.sh production
```

### Manual Deployment
```bash
# Build and tag images
docker build -f Dockerfile.prod -t crypto-monitor:latest .

# Run production compose
docker-compose -f docker-compose.prod.yml up -d
```

### Environment-Specific Configs
- **Development**: Local SQLite, debug logging
- **Staging**: Supabase staging, comprehensive logging
- **Production**: Supabase prod, structured logging, monitoring

## 📚 Documentation

- **[API Reference](docs/api.md)**: Complete API documentation
- **[Release Notes](RELEASE_NOTES.md)**: v2.0.0 changelog and migration guide
- **[QA Report](qa_report.md)**: Latest validation results
- **[Deployment Guide](docs/deployment.md)**: Production deployment
- **[Troubleshooting](docs/troubleshooting.md)**: Common issues and solutions

## 🔄 Release Management

### Create Release
```bash
python scripts/create_release.py
```

### Release Artifacts
- Source archive (`crypto-predict-monitor-2.0.0-src.tar.gz`)
- Docker images (`crypto-predict-monitor/app:latest`)
- Release manifest (`manifest-2.0.0.json`)
- Checksums file (`checksums-2.0.0.txt`)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run QA validation: `python scripts/qa_validation.py`
6. Ensure all tests pass
7. Submit a pull request

## 📄 License

Proprietary - All rights reserved.

## 🆘 Support

For issues and questions:
- **Documentation**: Check the `/docs` folder
- **Issues**: Create an issue in the repository
- **Emergency**: Use the health webhook for critical alerts
- **Monitoring**: Check Grafana dashboards for system status

## 🎯 Version History

### v2.0.0 (Current) - January 13, 2026
- ✅ Production-ready release
- ✅ P&L card system with social sharing
- ✅ Modern React dashboard
- ✅ Complete Docker deployment
- ✅ Comprehensive monitoring stack
- ✅ Enhanced security features
- ✅ 80% QA test coverage

### v1.0.0 - January 1, 2026
- ✅ Basic monitoring functionality
- ✅ Multi-venue support
- ✅ Discord webhook alerts
- ✅ Configuration management

---

**Version**: 2.0.0  
**Last Updated**: 2025-01-13  
**Status**: Production Ready ✅  
**QA Success Rate**: 80%  
**Build**: 202601130536
