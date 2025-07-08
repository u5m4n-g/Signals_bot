# main.py
import os
import time
import threading
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError
from typing import List, Optional
import uvicorn

from src.bot import send_telegram_alert
from src.strategies import validate_signal, Signal
app = FastAPI()

# Environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID or not WEBHOOK_SECRET:
    raise RuntimeError("Missing required environment variables: TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, WEBHOOK_SECRET")

# Rate limiting: max 1 alert per 2 minutes per pair
rate_limit_lock = threading.Lock()
last_alert_time = {
    "BTC/USDT": 0,
    "ETH/USDT": 0,
    "XRP/USDT": 0,
}

def can_send_alert(pair: str) -> bool:
    with rate_limit_lock:
        now = time.time()
        if now - last_alert_time.get(pair, 0) >= 120:
            last_alert_time[pair] = now
            return True
        return False

@app.post("/webhook")
async def webhook(request: Request, x_webhook_secret: Optional[str] = Header(None)):
    if x_webhook_secret != WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid webhook secret")
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    try:
        signal = Signal(**payload)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail="Validation error: " + str(e))

    validated = validate_signal(signal)
    if not validated:
        raise HTTPException(status_code=400, detail="Signal validation failed")

    if can_send_alert(validated.pair):
        await send_telegram_alert(validated)
    
    return JSONResponse(content={"message": "Signal processed successfully"}, status_code=200)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


