# signal_cache.py
import json
import os
import uuid
from typing import List, Dict, Optional
from datetime import datetime, timedelta

class SignalCache:
    def __init__(self, file_path: str = "signal_cache.json"):
        self.file_path = file_path
        self.cache = self._load_cache()

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

    def add_signal(self, signal: Dict):
        signal_data = signal.copy()
        signal_data['id'] = self._generate_id()
        signal_data['timestamp'] = datetime.now().isoformat()
        signal_data['active'] = True
        self.cache.append(signal_data)
        self._save_cache()

    def remove_signal(self, signal_id: str):
        self.cache = [s for s in self.cache if s.get('id') != signal_id]
        self._save_cache()

    def signal_exists(self, signal: Dict) -> bool:
        # Check if similar signal exists (same pair, strategy, direction)
        for s in self.cache:
            if (s['pair'] == signal.pair and
                s['strategy'] == signal.strategy and
                s['direction'] == signal.direction and
                s['timeframe'] == signal.timeframe and
                s['active'] is True):
                return True
        return False

    def get_active_signals(self) -> List[Dict]:
        # Clean up old signals (>24 hours)
        now = datetime.now()
        self.cache = [
            s for s in self.cache
            if datetime.fromisoformat(s['timestamp']) > now - timedelta(hours=24)
        ]
        self._save_cache()
        return [s for s in self.cache if s.get('active', False)]

    def clear_cache(self):
        self.cache = []
        self._save_cache()