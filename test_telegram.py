from dotenv import load_dotenv
load_dotenv()

import os
import asyncio
from telegram import Bot

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_test():
    bot = Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text="✅ Telegram test message from signal bot!")

if __name__ == "__main__":
    asyncio.run(send_test())


