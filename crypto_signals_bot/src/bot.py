import os
from dotenv import load_dotenv  # ✅ This is missing
from telegram import Bot
from telegram.error import TelegramError

load_dotenv()  # ✅ This loads your .env file

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TELEGRAM_TOKEN)

def format_alert(signal) -> str:
    base = (
        f"[{signal.pair}] [{signal.direction.upper()}] [{signal.strategy}]\n"
        f"🕒 Timeframe: {signal.timeframe}\n"
        f"🎯 Entry: {signal.entry}\n"
        f"🛑 Stop: {signal.stop}\n"
        f"📈 Targets: {signal.targets[0]} → {signal.targets[1]} → {signal.targets[2]}\n"
        f"🧠 Confidence: {int(signal.confidence * 100)}%\n"
        f"⚡ Momentum: {signal.momentum}"
    )
    updates = []
    if signal.early_exit:
        updates.append("⚠️ Early Exit Alert")
    if signal.momentum_change:
        updates.append(f"⚡ Momentum Change: {signal.momentum_change}")
    if signal.strategy_invalidated:
        updates.append("❌ Strategy Invalidation Notice")
    if updates:
        base += "\n" + "\n".join(updates)
    return base

async def await send_telegram_alert(signal) -> None:
    text = format_alert(signal)
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text)
    except TelegramError as e:
        print(f"Telegram error: {e}")
