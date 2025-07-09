import os
import time
import threading
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError, Field
from typing import List, Optional, Dict
import uvicorn
import pandas as pd

from src.bot import send_telegram_alert
from src.strategies import validate_signal, Signal

app = FastAPI()

# Load environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID or not WEBHOOK_SECRET:
    raise RuntimeError("Missing required environment variables: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, or WEBHOOK_SECRET")

# Rate limiting: prevent too many alerts per pair
rate_limit_lock = threading.Lock()
last_alert_time: Dict[str, float] = {
    "BTC/USDT": 0,
    "ETH/USDT": 0,
    "SOL/USDT": 0,
}

class WebhookSignal(BaseModel):
    pair: str
    direction: str
    strategy: str
    timeframe: str
    entry: float
    stop: float
    targets: List[float]
    confidence: float
    momentum: str
    early_exit: bool = False
    momentum_change: Optional[str] = None
    strategy_invalidated: bool = False
    exit_reason: Optional[str] = None

    class Config:
        extra = "ignore"

def can_send_alert(pair: str) -> bool:
    with rate_limit_lock:
        now = time.time()
        if now - last_alert_time.get(pair, 0) >= 120:
            last_alert_time[pair] = now
            return True
        return False

@app.post("/webhook")
async def webhook(
    request: Request,
    x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret")
):
    # 🔒 Verify webhook secret
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid webhook secret")

    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    try:
        # Step 1: parse input ignoring data_frame
        webhook_signal = WebhookSignal(**payload)

        # Step 2: convert to full Signal model with None data_frame
        signal_data = webhook_signal.model_dump()
        signal_data["data_frame"] = None
        signal = Signal(**signal_data)

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Signal validation error: {e}")

    # Step 3: run custom strategy validation
    validated = validate_signal(signal)
    if not validated:
        raise HTTPException(status_code=400, detail="Signal failed logic validation")

    # Step 4: rate limit
    if can_send_alert(validated.pair):
        try:
            await send_telegram_alert(validated)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Telegram error: {str(e)}")

    return JSONResponse(content={"message": "✅ Signal processed successfully"}, status_code=200)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
