# Trade Execution Tracking System

A comprehensive system for tracking user trade executions on Polymarket and Kalshi using Alchemy webhooks for real-time monitoring.

## Architecture Overview

### Tier 1 - Real-Time Monitoring (Primary)
- **Alchemy Webhooks**: Instant push notifications for wallet transactions
- **Address Activity Monitoring**: Tracks all transactions from connected wallets
- **Immediate Processing**: Real-time trade detection and P&L calculation

### Tier 2 - Historical Fallback
- **Alchemy Transfers API**: Retrieves missed transactions
- **Batch Processing**: Ensures no trades are missed
- **Data Recovery**: Failsafe for webhook downtime

### Tier 3 - Portfolio Enrichment (Optional)
- **Zerion API**: Enhanced portfolio data across chains
- **Normalized Data**: Consistent formatting from multiple sources
- **Additional Webhooks**: Extra monitoring layers

## Features

- ✅ **Real-time Trade Detection**: Instant notification of trades
- ✅ **Automatic P&L Calculation**: Tracks profit/loss in real-time
- ✅ **Multi-Market Support**: Polymarket and Kalshi integration
- ✅ **Dashboard Analytics**: Visual trading performance metrics
- ✅ **Leaderboard System**: User ranking by P&L
- ✅ **Gas Cost Tracking**: Complete cost analysis
- ✅ **Position Management**: Track open and closed positions

## Quick Start

### 1. Database Setup

Run the SQL schema in `database/schema/executions.sql` in your Supabase project.

### 2. Environment Variables

Create `.env` file with:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-key

# Alchemy Configuration
ALCHEMY_API_KEY=your-alchemy-api-key
ALCHEMY_WEBHOOK_SECRET=your-webhook-secret

# Webhook Configuration
WEBHOOK_URL=https://your-domain.com/api/webhooks/wallet-activity

# API Configuration
API_BASE_URL=https://your-api-domain.com
```

### 3. Install Dependencies

```bash
pip install -r requirements_tracking.txt
```

### 4. Run the API

```bash
uvicorn api.webhooks.alchemy_handler:app --reload
```

### 5. Run the Dashboard

```bash
streamlit run dashboard/trading_dashboard.py
```

## Database Schema

### Executions Table
- Stores all trade executions (entries and exits)
- Automatically calculates P&L on exit
- Supports both Polymarket and Kalshi trades

### Webhook Logs Table
- Debugging and monitoring webhook deliveries
- Tracks processing status and errors

### User P&L Summary View
- Aggregated trading statistics
- Leaderboard data
- Performance metrics

## API Endpoints

### Webhook Endpoints
- `POST /api/webhooks/wallet-activity` - Receive Alchemy webhooks
- `POST /api/webhooks/create/{user_id}` - Create webhook for user

### Data Endpoints
- `GET /api/executions/{user_id}` - Get user's trade history
- `GET /api/pnl/{user_id}` - Get user's P&L summary

## Integration Guide

### 1. User Connects Wallet

```javascript
import { useWalletManager } from './components/WalletManager';

function TradingApp() {
  const { connectWallet, isConnected, address } = useWalletManager();
  
  const handleConnect = async () => {
    await connectWallet();
    // Webhook automatically created
  };
  
  return (
    <button onClick={handleConnect}>
      Connect Wallet
    </button>
  );
}
```

### 2. Real-Time Trade Detection

When a user executes a trade:
1. Alchemy webhook fires
2. System detects market (Polymarket/Kalshi)
3. Fetches trade details via API
4. Stores execution in database
5. Updates P&L in real-time

### 3. Display P&L

```javascript
import { UserPnLDisplay } from './components/WalletManager';

function Dashboard({ userId }) {
  return (
    <UserPnLDisplay userId={userId} />
  );
}
```

## Market Integration

### Polymarket
- **Contract Address**: `0x4bF53B9B888197B09A09e6dC3fea0837eBBdF5aB`
- **API**: GraphQL endpoint for trade details
- **Data Fields**: Market ID, side, price, quantity

### Kalshi
- **Contract Address**: TBD (add when available)
- **API**: REST API for trade details
- **Data Fields**: Market ticker, side, price, quantity

## Deployment

### Render Deployment

1. Fork/clone the repository
2. Update environment variables in Render dashboard
3. Connect GitHub repository
4. Deploy both services:
   - `trade-tracking-api` (FastAPI webhook handler)
   - `trading-dashboard` (Streamlit dashboard)

### Manual Deployment

```bash
# API Server
uvicorn api.webhooks.alchemy_handler:app --host 0.0.0.0 --port 8000

# Dashboard
streamlit run dashboard/trading_dashboard.py --server.port 8501
```

## Security Considerations

- **Webhook Verification**: HMAC signature verification
- **Rate Limiting**: Prevent webhook abuse
- **Data Privacy**: User data isolation
- **API Keys**: Secure storage of credentials

## Monitoring

### Webhook Health
- Check webhook logs table
- Monitor processing status
- Alert on failed webhooks

### Performance Metrics
- API response times
- Database query performance
- Webhook processing lag

## Troubleshooting

### Common Issues

1. **Webhook Not Firing**
   - Check Alchemy webhook configuration
   - Verify webhook URL is accessible
   - Check webhook secret

2. **Trades Not Detected**
   - Verify contract addresses
   - Check transaction parsing logic
   - Review market detection rules

3. **P&L Calculation Errors**
   - Check entry/exit price matching
   - Verify quantity calculations
   - Review gas cost inclusion

### Debug Mode

Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

- [ ] Support for more prediction markets
- [ ] Mobile app integration
- [ ] Advanced analytics dashboard
- [ ] Social trading features
- [ ] Automated trading alerts

## Contributing

1. Fork the repository
2. Create feature branch
3. Make your changes
4. Add tests
5. Submit pull request

## License

MIT License - see LICENSE file for details

## Support

For support and questions:
- Create an issue on GitHub
- Join our Discord community
- Email: support@yourdomain.com
