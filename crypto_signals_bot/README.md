# Crypto Signals Bot

This project implements a Python-based crypto signals bot that receives webhook alerts from TradingView, validates them, and sends formatted alerts to a Telegram chat.

## Features

- **FastAPI Webhook:** Receives TradingView alerts via a secure webhook.
- **Signal Validation:** Ensures signals meet predefined criteria (e.g., valid pairs, timeframes, confidence levels, strategies).
- **Telegram Integration:** Sends well-formatted alerts to a specified Telegram chat.
- **Rate Limiting:** Prevents alert spamming by limiting alerts per trading pair.
- **Dynamic Updates:** Supports early exit, momentum change, and strategy invalidation notices.
- **Free Deployment:** Designed for single-click deployment on Render with Uptime Robot for continuous monitoring.

## Getting Started

Follow these instructions to set up and deploy your crypto signals bot.

### Prerequisites

- A Telegram Bot Token (from BotFather)
- Your Telegram Chat ID (you can get this by sending a message to your bot and then visiting `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`)
- A webhook secret for securing your TradingView alerts.
- A GitHub account for deploying to Render.
- A Render account (free tier).
- An Uptime Robot account (free tier).

### Local Setup (for development/testing)

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/crypto-signals-bot.git
    cd crypto-signals-bot
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Set environment variables:**
    Create a `.env` file in the root directory or set them directly in your shell:
    ```
    TELEGRAM_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHAT_ID="YOUR_TELEGRAM_CHAT_ID"
    WEBHOOK_SECRET="YOUR_SECURE_WEBHOOK_SECRET"
    ```

4.  **Run the application:**
    ```bash
    uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    ```
    The API will be accessible at `http://0.0.0.0:8000`.

### Deployment on Render

1.  **Push your code to GitHub:**
    Create a new private GitHub repository and push your project to it.

2.  **Connect Render to your GitHub repository:**
    - Go to your Render Dashboard.
    - Click `New Web Service`.
    - Select `Build and deploy from a Git repository`.
    - Connect your GitHub account and select the repository you just created.

3.  **Configure the web service:**
    - **Name:** `crypto-signals-bot` (or your preferred name)
    - **Root Directory:** `/` (or the directory containing `render.yaml` if different)
    - **Runtime:** `Python 3`
    - **Build Command:** `pip install -r requirements.txt`
    - **Start Command:** `uvicorn src.main:app --host 0.0.0.0 --port $PORT`
    - **Environment Variables:** Add `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`, and `WEBHOOK_SECRET` with their respective values.
    - **Plan:** Select `Free`.

4.  **Deploy:** Click `Create Web Service`. Render will automatically build and deploy your application.

### Uptime Robot Setup Guide

Uptime Robot will monitor your Render service and keep it awake, preventing it from sleeping on the free tier.

1.  **Get your Render service URL:** After successful deployment on Render, copy the URL of your web service (e.g., `https://crypto-signals-bot.onrender.com`).

2.  **Add a new monitor in Uptime Robot:**
    - Log in to your Uptime Robot account.
    - Click `Add New Monitor`.
    - **Monitor Type:** `HTTP(s)`
    - **Friendly Name:** `Crypto Signals Bot Uptime`
    - **URL (or IP):** Paste your Render service URL.
    - **Monitoring Interval:** `5 minutes` (or your preferred interval)
    - **Alert Contacts:** Select your preferred alert method (e.g., email).
    - Click `Create Monitor`.

### TradingView Alert Template

Use this JSON payload in your TradingView webhook alerts. Replace `YOUR_DIRECTION`, `YOUR_STRATEGY`, etc., with dynamic TradingView variables.

**Webhook URL:** Your Render service URL + `/webhook` (e.g., `https://crypto-signals-bot.onrender.com/webhook`)

**HTTP Method:** `POST`

**HTTP Header:**
- Key: `X-Webhook-Secret`
- Value: `YOUR_SECURE_WEBHOOK_SECRET`

**JSON Payload:**

```json
{
  "pair": "{{ticker}}",
  "direction": "YOUR_DIRECTION",
  "strategy": "YOUR_STRATEGY",
  "timeframe": "{{interval}}",
  "entry": {{close}},
  "stop": YOUR_STOP_LOSS_PRICE,
  "targets": [YOUR_TARGET_1_PRICE, YOUR_TARGET_2_PRICE, YOUR_TARGET_3_PRICE],
  "confidence": YOUR_CONFIDENCE_LEVEL,
  "momentum": "YOUR_MOMENTUM_LEVEL",
  "early_exit": false,
  "momentum_change": null,
  "strategy_invalidated": false
}
```

**Example TradingView Variables for Payload:**

- `{{ticker}}`: Trading pair (e.g., `BTCUSDT` - you might need to format this to `BTC/USDT` in TradingView's alert message if your broker uses a different format)
- `{{interval}}`: Timeframe (e.g., `5` for 5 minutes, `15` for 15 minutes - you might need to map this to `3m`, `5m`, `15m` in TradingView's alert message)
- `{{close}}`: Current closing price (can be used for entry)

**Important Notes for TradingView:**

- **Pair Formatting:** TradingView's `{{ticker}}` variable might output `BTCUSDT` instead of `BTC/USDT`. You may need to adjust your TradingView alert message to explicitly send `BTC/USDT` or handle the formatting in your bot if necessary.
- **Timeframe Formatting:** Similarly, `{{interval}}` might output `5` instead of `5m`. You might need to add 'm' in your TradingView alert message or handle the mapping in your bot.
- **Dynamic Values:** For `YOUR_DIRECTION`, `YOUR_STRATEGY`, `YOUR_STOP_LOSS_PRICE`, `YOUR_TARGET_X_PRICE`, `YOUR_CONFIDENCE_LEVEL`, and `YOUR_MOMENTUM_LEVEL`, you will need to use specific TradingView variables or hardcode values based on your alert logic. For example, you might use `{{strategy.order.action}}` for direction if your strategy outputs buy/sell orders.

## Contributing

Feel free to fork the repository and submit pull requests.

## License

This project is open-source and available under the MIT License.


