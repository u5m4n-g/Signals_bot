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
from src.strategies import validate_signal

app = FastAPI()

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID or not WEBHOOK_SECRET:
    raise RuntimeError("Missing required environment variables: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, WEBHOOK_SECRET")

# Rate limiting: max 1 alert per 2 minutes per pair
rate_limit_lock = threading.Lock()
last_alert_time: Dict[str, float] = {
    "BTC/USDT": 0,
    "ETH/USDT": 0,
    "XRP/USDT": 0,
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
        extra = "ignore"  # Ignore extra fields during validation

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
    # Verify webhook secret
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: Invalid webhook secret"
        )

    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON payload: {str(e)}"
        )

    try:
        # First validate as WebhookSignal (without data_frame)
        webhook_signal = WebhookSignal(**payload)
        
        # Then convert to full Signal with empty data_frame
        signal_data = webhook_signal.model_dump()
        signal_data["data_frame"] = None
        signal = Signal(**signal_data)
    except ValidationError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Signal validation error: {str(e)}"
        )

    # Validate signal logic
    validated = validate_signal(signal)
    if not validated:
        raise HTTPException(
            status_code=400,
            detail="Signal validation failed - check confidence, targets, etc."
        )

    # Rate limit and send alert
    if can_send_alert(validated.pair):
        try:
            await send_telegram_alert(validated)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send Telegram alert: {str(e)}"
            )
    
    return JSONResponse(
        content={"message": "Signal processed successfully"},
        status_code=200
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )