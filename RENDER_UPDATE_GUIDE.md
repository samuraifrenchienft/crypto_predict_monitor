# Render Dashboard Update Guide

## Quick Setup Steps

### 1. Update Supabase Credentials in Render Dashboard
Go to your Render dashboard and update these environment variables:

```
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_KEY=your-supabase-anon-key  
SUPABASE_SERVICE_KEY=your-supabase-service-key
```

### 2. Trigger Manual Deployment (Optional)
If you want to force an update immediately:
1. Go to your Render dashboard
2. Click on your "crypto-prediction-dashboard" service
3. Click "Manual Deploy" → "Deploy Latest Commit"

### 3. Verify Auto-Deployment is Working
Your `render.yaml` already has `autoDeploy: true`, so:
- Any push to your main branch will trigger automatic deployment
- The dashboard should update within 2-5 minutes after each commit

### 4. Test the Deployment
Check these endpoints to verify everything works:
- Health Check: `https://crypto-prediction-dashboard.onrender.com/api/health`
- Database Metrics: `https://crypto-prediction-dashboard.onrender.com/api/database/metrics`
- Main Dashboard: `https://crypto-prediction-dashboard.onrender.com/`

## What's Already Configured ✅

- **Auto-deployment**: Enabled for all commits
- **Database**: PostgreSQL (Render) + Supabase integration  
- **Health checks**: `/api/health` endpoint
- **Error handling**: Comprehensive logging and monitoring
- **Connection pooling**: Optimized database connections

## Troubleshooting

### If Dashboard Doesn't Update:
1. Check Render logs for deployment errors
2. Verify Supabase credentials are correct
3. Test health endpoint - should return "healthy" status
4. Check if DATABASE_URL is properly connected

### Common Issues:
- **Supabase credentials**: Must be actual values, not placeholders
- **Database connection**: Health endpoint will show database status
- **Build failures**: Check Render build logs for dependency issues

## Next Steps

1. Update Supabase credentials in Render dashboard
2. Push a test commit to verify auto-deployment
3. Monitor the deployment logs
4. Test the updated dashboard

Your dashboard should now automatically update after each commit! 🚀
