import os
import time
import threading
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from typing import List, Optional, Dict
import uvicorn
import pandas as pd

from crypto_signals_bot.src.bot import send_telegram_alert
from crypto_signals_bot.src.strategies import validate_signal, Signal
app = FastAPI()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID or not WEBHOOK_SECRET:
    raise RuntimeError("Missing TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, or WEBHOOK_SECRET")

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
async def webhook(request: Request, x_webhook_secret: Optional[str] = Header(None, alias="X-Webhook-Secret")):
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid webhook secret")
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

    try:
        webhook_signal = WebhookSignal(**payload)
        signal = Signal(**webhook_signal.dict(), data_frame=None)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=f"Signal validation error: {e}")

    validated = validate_signal(signal)
    if not validated:
        raise HTTPException(status_code=400, detail="Signal failed validation")

    if can_send_alert(signal.pair):
        try:
            await send_telegram_alert(signal)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Telegram error: {str(e)}")

    return JSONResponse(content={"message": "✅ Signal processed"}, status_code=200)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


