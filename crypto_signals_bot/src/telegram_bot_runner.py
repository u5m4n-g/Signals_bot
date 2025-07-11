import asyncio
from crypto_signals_bot.src.bot import setup_telegram_bot
from signal_cache import SignalCache

if __name__ == "__main__":
    cache = SignalCache()
    asyncio.run(setup_telegram_bot(cache))


