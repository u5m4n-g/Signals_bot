import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from crypto_signals_bot.src.strategies import Signal
from signal_cache import SignalCache
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Configure logging for bot
bot_logger = logging.getLogger("bot")
bot_logger.setLevel(logging.INFO)
handler = logging.FileHandler("bot.log")
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
bot_logger.addHandler(handler)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    bot_logger.error("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID environment variables.")
    raise RuntimeError("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")

async def send_telegram_alert(signal: Signal):
    message = (
        f"🚨 New Signal: {signal.pair} ({signal.timeframe}) 🚨\n\n"
        f"Direction: {signal.direction}\n"
        f"Strategy: {signal.strategy}\n"
        f"Entry: {signal.entry}\n"
        f"Stop Loss: {signal.stop}\n"
        f"Targets: {', '.join(map(str, signal.targets))}\n"
        f"Confidence: {signal.confidence:.2f}\n"
        f"Momentum: {signal.momentum}\n"
        f"SLNO: {signal.slno or 'N/A'}\n"
    )
    bot_logger.info(f"Sending Telegram alert for {signal.pair}: {message}")
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        await application.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        bot_logger.info(f"Telegram alert sent successfully for {signal.pair}")
    except Exception as e:
        bot_logger.error(f"Failed to send Telegram alert for {signal.pair}: {e}")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a summary of all currently active trades."""
    cache: SignalCache = context.bot_data["signal_cache"]
    active_signals = cache.get_active_signals()

    if not active_signals:
        await update.message.reply_text("No active trades at the moment.")
        return

    response_message = "📊 Active Trades Summary 📊\n\n"
    for signal_data in active_signals:
        response_message += (
            f"Pair: {signal_data['pair']}\n"
            f"Direction: {signal_data['direction']}\n"
            f"Entry Price: {signal_data['entry']}\n"
            f"SL: {signal_data['stop']}\n"
            f"TP List: {', '.join(map(str, signal_data['targets']))}\n"
            f"Momentum: {signal_data['momentum']}\n"
            f"SLNO: {signal_data['slno'] or 'N/A'}\n"
            f"---\n"
        )
    await update.message.reply_text(response_message)

def setup_telegram_bot(signal_cache: SignalCache):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.bot_data["signal_cache"] = signal_cache
    application.add_handler(CommandHandler("status", status_command))
    application.run_polling(drop_pending_updates=True)
    bot_logger.info("Telegram bot polling started.")


