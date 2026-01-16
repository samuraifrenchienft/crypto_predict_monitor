# Discord Bot Setup Guide

## Quick Setup

### 1. Create Discord Webhook URLs

You need two Discord webhooks:

1. **Main Alert Webhook** - For arbitrage opportunities
2. **Health Webhook** - For system health alerts

#### Creating Webhooks:

1. Go to your Discord server
2. Click on a channel where you want alerts
3. Click "Edit Channel" → "Integrations" → "Webhooks"
4. Click "New Webhook"
5. Name it "Arbitrage Alerts" or "Health Monitor"
6. Copy the webhook URL

### 2. Configure Environment Variables

Add these to your `.env` file:

```bash
# Main arbitrage alerts webhook
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN

# Health/system alerts webhook (optional, can be same as above)
DISCORD_HEALTH_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_HEALTH_WEBHOOK_ID/YOUR_HEALTH_WEBHOOK_TOKEN
```

### 3. Start the Bot

Run the deployment script:

```bash
python deploy_discord_bot.py
```

Or start the main integration directly:

```bash
python main_integration.py
```

## Features

✅ **Real-time Arbitrage Alerts**
- Cross-market arbitrage detection
- Rich Discord embeds with profit margins
- Color-coded alerts (Green/Yellow/Red)
- Rating system (🎯🎯🎯)

✅ **System Health Monitoring**
- Bot startup/shutdown notifications
- Error alerts
- Performance metrics

✅ **P&L Tracking**
- Automated profit/loss tracking
- Alert matching system
- Database integration

## Alert Types

### Arbitrage Alerts
- Market question and source
- YES/NO price spreads
- Estimated profit and margin
- Expiration time
- Liquidity information

### Health Alerts
- System status changes
- Error notifications
- Performance warnings

## Deployment Options

### Option 1: Local Development
```bash
# Set environment variables
export DISCORD_WEBHOOK_URL="your_webhook_url"

# Start bot
python deploy_discord_bot.py
```

### Option 2: Server Deployment
```bash
# Create .env file on server
echo "DISCORD_WEBHOOK_URL=your_webhook_url" > .env

# Run with process manager
pm2 start deploy_discord_bot.py --name crypto-bot
```

### Option 3: Docker Deployment
```bash
# Build and run
docker-compose up -d
```

## Testing

Test your Discord setup:

```python
python -c "
import asyncio
from utils.discord_alerts import DiscordAlerter, AlertData
from datetime import datetime, timedelta

async def test():
    async with DiscordAlerter() as alerter:
        alert = AlertData(
            market_question='Test Alert: Is this working?',
            yes_bid=0.5, yes_ask=0.52,
            no_bid=0.48, no_ask=0.5,
            spread=0.02, est_profit=2.0,
            profit_margin=2.0,
            market_link='https://example.com',
            expires_at=datetime.utcnow() + timedelta(hours=1),
            liquidity='Test', market_source='test'
        )
        await alerter.send_alert(alert)

asyncio.run(test())
"
```

## Troubleshooting

### Webhook Not Working
- Check URL format: `https://discord.com/api/webhooks/ID/TOKEN`
- Verify webhook permissions in Discord
- Check if channel allows webhooks

### Bot Not Starting
- Check Python dependencies: `pip install -r requirements.txt`
- Verify environment variables are loaded
- Check logs for error messages

### No Alerts Being Sent
- Verify arbitrage detection is running
- Check minimum spread thresholds
- Monitor logs for detection activity

## Production Tips

1. **Use separate webhooks** for different alert types
2. **Set up rate limiting** to avoid Discord spam
3. **Monitor webhook health** regularly
4. **Use environment variables** for all secrets
5. **Set up logging** for debugging

## Support

If you need help:
1. Check the logs: `logs/bot.log`
2. Test webhook manually
3. Verify environment variables
4. Check Discord server permissions
