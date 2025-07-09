import os
import asyncio
from telegram import Bot

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or "7773093247:AAEHYC48CqkF7J9n2e-Xu3dlvXuv2DlK8Is"
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID") or "7915749117"

async def send_test():
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="✅ Telegram test message from signal bot!")

if __name__ == "__main__":
    asyncio.run(send_test())
