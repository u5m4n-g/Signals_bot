# Updated runner.py (Final Production Version)

import ccxt
import time
import logging
import requests
import pandas as pd
from typing import List, Dict
from crypto_signals_bot.src.strategies import calculate_all_strategies
from signal_cache import SignalCache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('runner.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('runner')

class SignalRunner:
    def __init__(self):
        self.exchange = ccxt.binance()  # No API keys needed for OHLCV
        self.cache = SignalCache()
        self.webhook_url = "http://localhost:8000/webhook"  # Update with your webhook URL
        self.pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]  # Top liquid pairs
        self.timeframes = ["3m", "5m", "15m"]
        self.ohlcv_limit = 100  # Number of candles to fetch

    def fetch_ohlcv(self, pair: str, timeframe: str) -> pd.DataFrame:
        try:
            ohlcv = self.exchange.fetch_ohlcv(pair, timeframe, limit=self.ohlcv_limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {pair} {timeframe}: {str(e)}")
            return None

    def process_pair(self, pair: str):
        for timeframe in self.timeframes:
            df = self.fetch_ohlcv(pair, timeframe)
            if df is not None and len(df) > 20:  # Minimum data requirement
                signals = calculate_all_strategies(df, pair, timeframe)
                for signal in signals:
                    if not self.cache.signal_exists(signal):
                        try:
                            signal_dict = signal.dict(exclude={"data_frame"})
                            if hasattr(signal, 'data_frame') and signal.data_frame is not None:
                                signal_dict["data_frame"] = signal.data_frame.to_dict(orient="records")

                            response = requests.post(
                                self.webhook_url,
                                json=signal_dict,
                                timeout=5
                            )
                            if response.status_code == 200:
                                self.cache.add_signal(signal)
                                logger.info(f"✅ Sent new signal: {signal.strategy} {signal.direction} {signal.pair} {signal.timeframe} @ {signal.entry}")
                            else:
                                logger.error(f"❌ Webhook failed: {response.status_code} {response.text}")
                        except Exception as e:
                            logger.error(f"🔥 Error sending webhook: {str(e)}")

    def run(self):
        logger.info("🚀 Starting Signal Runner in PRODUCTION mode")
        while True:
            try:
                for pair in self.pairs:
                    self.process_pair(pair)
                time.sleep(300)  # Run every 5 minutes
            except KeyboardInterrupt:
                logger.info("🛑 Stopping Signal Runner")
                break
            except Exception as e:
                logger.error(f"⚠️ Runner error: {str(e)}")
                time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    runner = SignalRunner()
    runner.run()
