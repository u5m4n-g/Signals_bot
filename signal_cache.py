# signal_cache.py
import json
import os
import uuid
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from crypto_signals_bot.src.strategies import Signal

class SignalCache:
    def __init__(self, file_path: str = "signal_cache.json"):
        self.file_path = file_path
        self.cache = self._load_cache()
        self.next_slno = self._get_next_slno()

    def _load_cache(self) -> List[Dict]:
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return []
        return []

    def _save_cache(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.cache, f)

    def _generate_id(self) -> str:
        return str(uuid.uuid4())

    def add_signal(self, signal: Signal):
        signal_data = signal.dict(exclude={'data_frame'})
        signal_data["id"] = self._generate_id()
        signal_data["slno"] = f"#{self.next_slno:03d}"
        self.next_slno += 1
        signal_data['timestamp'] = datetime.now().isoformat()
        signal_data['active'] = True
        self.cache.append(signal_data)
        self._save_cache()

    def remove_signal(self, signal_id: str):
        self.cache = [s for s in self.cache if s.get('id') != signal_id]
        self._save_cache()

    def signal_exists(self, signal: Signal) -> bool:
        # Check if similar signal exists (same pair, strategy, direction)
        for s in self.cache:
            if (s['pair'] == signal.pair and
                s['strategy'] == signal.strategy and
                s['direction'] == signal.direction and
                s["timeframe"] == signal.timeframe and
                s["active"] is True):
                return True
        return False

    def get_active_signals(self) -> List[Dict]:
        # Clean up old signals (>24 hours)
        now = datetime.now()
        self.cache = [
            s for s in self.cache
            if datetime.fromisoformat(s["timestamp"]) > now - timedelta(hours=24) and
            s["timeframe"] in ["3m", "5m", "15m"]
        ]
        self._save_cache()
        return [s for s in self.cache if s.get('active', False)]

    def clear_cache(self):
        self.cache = []
        self._save_cache()



    def _get_next_slno(self) -> int:
        max_slno = 0
        for s in self.cache:
            if 'slno' in s and s['slno'] is not None:
                try:
                    max_slno = max(max_slno, int(s['slno'].lstrip('#')))
                except ValueError:
                    pass
        return max_slno + 1


