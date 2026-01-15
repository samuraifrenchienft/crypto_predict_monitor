# Deploy Arbitrage Bot to Render for 24/7 Operation

## Quick Setup

1. **Replace your current render.yaml** with `render_arbitrage.yaml`:
   ```bash
   cp render_arbitrage.yaml render.yaml
   ```

2. **Push to GitHub** (Render auto-deploys from your repo)

3. **Set Environment Variables** in Render Dashboard:
   - `SUPABASE_URL`: Your Supabase URL
   - `SUPABASE_SERVICE_KEY`: Your Supabase service key
   - `ALCHEMY_API_KEY`: Your Alchemy API key
   - `DISCORD_WEBHOOK_URL`: Your working Discord webhook
   - `CPM_WEBHOOK_URL`: Your working Discord webhook (same as above)
   - `CPM_HEALTH_WEBHOOK_URL`: Your health Discord webhook

## What Gets Deployed

### Services:
1. **Arbitrage Bot** (`crypto-arbitrage-bot.onrender.com`)
   - Runs 24/7 scanning every 5 minutes
   - Sends Discord alerts for opportunities
   - Health check at `/health`

2. **Dashboard** (`crypto-prediction-dashboard.onrender.com`)
   - Web interface for monitoring
   - Statistics and tracking

## Features

✅ **24/7 Operation**: Bot runs continuously on Render's free tier
✅ **Automatic Alerts**: Discord notifications for arbitrage opportunities  
✅ **Health Monitoring**: Render monitors bot health automatically
✅ **Continuous Scanning**: Checks markets every 5 minutes
✅ **Production Mode**: Optimized for cloud deployment

## Bot Behavior

- **Scans**: Every 5 minutes (300 seconds)
- **Alerts**: Only quality opportunities (>7.0/10 score)
- **Markets**: Currently 3 test markets (expandable)
- **Discord**: Professional embeds with full details

## Monitoring

- **Health Endpoint**: `https://crypto-arbitrage-bot.onrender.com/health`
- **Bot Status**: `https://crypto-arbitrage-bot.onrender.com/`
- **Dashboard**: `https://crypto-prediction-dashboard.onrender.com/`

## Cost

- **Free Tier**: Both services run on Render's free plan
- **No Credit Card Required**: For basic usage
- **Limits**: 750 hours/month (plenty for 24/7 operation)

## Troubleshooting

If bot stops working:
1. Check Render logs for errors
2. Verify Discord webhooks are working
3. Ensure environment variables are set correctly
4. Check if free tier hours are exhausted

## Next Steps

After deployment:
1. Test Discord alerts are working
2. Monitor bot performance in dashboard
3. Add more markets for better coverage
4. Customize alert thresholds if needed
