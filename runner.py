from crypto_signals_bot.src.strategies import calculate_all_strategies

# runner.py
import os
import ccxt
import time
import logging
import requests
import pandas as pd
from typing import List, Dict

from signal_cache import SignalCache

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format=r'%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('runner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('runner')

class SignalRunner:
    def __init__(self):
        self.exchange = ccxt.kraken()  # Changed from binance to kraken
        self.cache = SignalCache()
        self.webhook_url = "https://signals-bot-zely.onrender.com/webhook"
        self.pairs = ["BTC/USDT", "ETH/USDT", "DOGE/USDT"]
        self.timeframes = ["5m", "15m"]
        self.ohlcv_limit = 100

    def fetch_ohlcv(self, pair: str, timeframe: str) -> pd.DataFrame:
        try:
            ohlcv = self.exchange.fetch_ohlcv(pair, timeframe, limit=self.ohlcv_limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {pair} {timeframe}: {str(e)}")
            return None

    def send_to_webhook(self, signal) -> bool:
        try:
            signal_data = signal.dict() # data_frame is already excluded in Signal model

            # Convert all Timestamp objects to string
            for k, v in signal_data.items():
                if isinstance(v, pd.Timestamp):
                    signal_data[k] = v.isoformat()

            response = requests.post(
    self.webhook_url,
    json=signal_data,
    headers={"X-Webhook-Secret": os.getenv("WEBHOOK_SECRET")},
    timeout=5
)


            if response.status_code == 200:
                logger.info(f"✅ Sent signal: {signal.strategy} {signal.direction} {signal.pair} {signal.timeframe}")
                return True
            else:
                logger.error(f"❌ Webhook failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"🚨 Failed to send webhook: {str(e)}")
            return False

    def process_pair(self, pair: str):
        self.cache.get_active_signals() # Clean up stale signals and update active list
        active_signals_count = len(self.cache.get_active_signals())
        if active_signals_count >= 3:
            logger.info(f"Max active trades (3) reached. Skipping new signals.")
            return

        for timeframe in self.timeframes:
            df = self.fetch_ohlcv(pair, timeframe)
            if df is not None and len(df) > 20:
                signals = calculate_all_strategies(df, pair, timeframe)
                for signal in signals:
                    if not self.cache.signal_exists(signal):
                        if self.send_to_webhook(signal):
                            self.cache.add_signal(signal)
    def run(self):
        logger.info("🚀 Starting Signal Runner")
        while True:
            try:
                for pair in self.pairs:
                    self.process_pair(pair)
                time.sleep(180)  # Run every 3 minutes
            except KeyboardInterrupt:
                logger.info("🛑 Signal Runner stopped by user")
                break
            except Exception as e:
                logger.error(f"🔥 Runner error: {str(e)}")
                time.sleep(60)

if __name__ == "__main__":
    runner = SignalRunner()
    runner.run()



from crypto_signals_bot.src.strategies import calculate_all_strategies

