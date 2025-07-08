# monitor.py
import ccxt
import time
import logging
import requests
from typing import Dict
from signal_cache import SignalCache

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('monitor')

class SignalMonitor:
    def __init__(self):
        self.exchange = ccxt.binance()  # No API keys needed for price
        self.cache = SignalCache()
        self.webhook_url = "http://localhost:8000/webhook"  # Update with your webhook URL
        self.check_interval = 120  # 2 minutes

    def get_current_price(self, pair: str) -> float:
        try:
            ticker = self.exchange.fetch_ticker(pair)
            return ticker['last']
        except Exception as e:
            logger.error(f"Error fetching price for {pair}: {str(e)}")
            return None

    def check_signal(self, signal: Dict) -> bool:
        current_price = self.get_current_price(signal['pair'])
        if current_price is None:
            return False

        # Check stop loss
        if (signal['direction'] == "BUY" and current_price <= signal['stop']) or \
           (signal['direction'] == "SELL" and current_price >= signal['stop']):
            signal['early_exit'] = True
            signal['strategy_invalidated'] = True
            signal['exit_reason'] = "STOP_HIT"
            return True

        # Check momentum (if we have the data)
        if 'data_frame' in signal and signal['data_frame'] is not None:
            from crypto_signals_bot.src.strategies import detect_momentum_change
            momentum = detect_momentum_change(signal['data_frame'])
            if momentum == "LOW":
                signal['early_exit'] = True
                signal['momentum_change'] = "LOW"
                signal['exit_reason'] = "MOMENTUM_LOW"
                return True

        return False

    def process_signals(self):
        active_signals = self.cache.get_active_signals()
        for signal in active_signals:
            if self.check_signal(signal):
                try:
                    response = requests.post(
                        self.webhook_url,
                        json=signal,
                        timeout=5
                    )
                    if response.status_code == 200:
                        self.cache.remove_signal(signal['id'])
                        logger.info(f"Sent exit signal: {signal['strategy']} {signal['direction']} {signal['pair']} {signal['timeframe']}")
                    else:
                        logger.error(f"Webhook failed: {response.status_code} {response.text}")
                except Exception as e:
                    logger.error(f"Error sending webhook: {str(e)}")

    def run(self):
        logger.info("Starting Signal Monitor")
        while True:
            try:
                self.process_signals()
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                logger.info("Stopping Signal Monitor")
                break
            except Exception as e:
                logger.error(f"Monitor error: {str(e)}")
                time.sleep(60)  # Wait before retrying

if __name__ == "__main__":
    monitor = SignalMonitor()
    monitor.run()