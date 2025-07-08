# Deployment Instructions

## Quick Deploy to Render

### Step 1: Prepare Your Repository
1. Fork or clone this repository to your GitHub account
2. Make sure all files are in the root directory of your repository

### Step 2: Deploy to Render
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `crypto-signals-bot`
   - **Root Directory**: `/` (leave empty if files are in root)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.main:app --host 0.0.0.0 --port $PORT`

### Step 3: Set Environment Variables
In Render dashboard, add these environment variables:
- `TELEGRAM_TOKEN`: Your bot token from @BotFather
- `TELEGRAM_CHAT_ID`: Your chat ID (get from bot messages)
- `WEBHOOK_SECRET`: A secure random string

### Step 4: Deploy
Click "Create Web Service" and wait for deployment to complete.

## Uptime Robot Setup

### Step 1: Get Your Service URL
After deployment, copy your Render service URL (e.g., `https://crypto-signals-bot.onrender.com`)

### Step 2: Create Monitor
1. Go to [Uptime Robot](https://uptimerobot.com/)
2. Add New Monitor:
   - **Type**: HTTP(s)
   - **Name**: Crypto Signals Bot
   - **URL**: Your Render service URL
   - **Interval**: 5 minutes

This keeps your service awake on Render's free tier.

## TradingView Webhook Setup

### Webhook URL
Use your deployed service URL + `/webhook`:
```
https://your-service-name.onrender.com/webhook
```

### Headers
Add this header to your TradingView alert:
```
X-Webhook-Secret: YOUR_WEBHOOK_SECRET
```

### JSON Payload
Use the template in `tradingview_alert_template.json` and customize for your strategy.

## Troubleshooting

### Common Issues
1. **Service won't start**: Check environment variables are set correctly
2. **Telegram not working**: Verify bot token and chat ID
3. **Webhook fails**: Ensure webhook secret matches

### Logs
Check Render logs in the dashboard for error messages.

