# Deploy to Render (Free)

This guide will help you deploy your crypto prediction dashboard to Render for free hosting.

## Prerequisites

1. GitHub account
2. Your code pushed to GitHub
3. Render account (free)

## Step 1: Push to GitHub

```bash
# Add all files to git
git add .
git commit -m "Add dashboard for Render deployment"
git push origin main
```

## Step 2: Deploy to Render

### Option A: Use render.yaml (Recommended)

1. Go to https://render.com
2. Sign up for a free account
3. Click "New" → "Web Service"
4. Connect your GitHub repository
5. Render will automatically detect `render.yaml`
6. Click "Create Web Service"

### Option B: Manual Setup

1. Go to https://render.com
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: crypto-prediction-dashboard
   - **Environment**: Python 3
   - **Build Command**: 
     ```
     pip install -r requirements.txt && pip install -r dashboard/requirements.txt
     ```
   - **Start Command**: 
     ```
     gunicorn -c dashboard/gunicorn_config.py dashboard.app:app
     ```
   - **Health Check Path**: `/api/stats`
   - **Plan**: Free

## Step 3: Configure Environment

Add these environment variables in Render:

```
FLASK_ENV=production
PYTHON_VERSION=3.10
```

## Step 4: Deploy

1. Click "Create Web Service"
2. Wait for the build to complete (2-3 minutes)
3. Your dashboard will be live at: `https://crypto-prediction-dashboard.onrender.com`

## Step 5: Custom Domain (Optional)

1. In Render dashboard, go to "Custom Domains"
2. Add your domain (e.g., dashboard.yourdomain.com)
3. Update DNS records as instructed
4. Render will automatically issue SSL certificate

## Troubleshooting

### Build Fails
- Check that all requirements are in `requirements.txt`
- Make sure `render.yaml` is in the root directory
- Check Render build logs

### Health Check Fails
- The `/api/stats` endpoint should return JSON
- Check that the app starts correctly
- Verify the port is set to 5000

### App Not Loading
- Check Render logs
- Make sure adapters are enabled in `config.yaml`
- Verify API endpoints are working

## Features on Render

✅ **Free Tier Benefits**:
- 750 hours/month runtime
- SSL certificate
- Custom domain support
- Automatic deployments
- Health monitoring
- Logs

✅ **Your Dashboard**:
- Real-time market data
- All 5 prediction market sources
- Rate limiting respected
- Auto-refresh every 30 seconds
- Mobile responsive

## Limits

- **Runtime**: 750 hours/month (plenty for a dashboard)
- **Bandwidth**: 100GB/month
- **Sleeps**: After 15 minutes inactivity
- **Cold Starts**: ~30 seconds to wake up

## Keep Your App Awake

To prevent the app from sleeping, you can:
1. Add a cron job to ping `/api/stats` every 10 minutes
2. Use the "Always On" plan ($7/month) if needed
3. Set up external monitoring

## Alternative Free Options

If Render doesn't work for you:

1. **PythonAnywhere** (Free)
   - Upload files via web interface
   - No GitHub required
   - Limited bandwidth

2. **Home Hosting** (Free)
   - Use your computer
   - Dynamic DNS (duckdns.org)
   - Cloudflare Tunnel for HTTPS

3. **Static + API** (Free)
   - Frontend on Netlify/Vercel
   - Backend on AWS Lambda free tier
   - More complex setup

## Success!

Once deployed, your dashboard will be permanently accessible at:
`https://crypto-prediction-dashboard.onrender.com`

Share the link with others to view your prediction market data!
