from pydantic import BaseModel, ValidationError
from typing import List, Optional

VALID_PAIRS = {"BTC/USDT", "ETH/USDT", "XRP/USDT"}
VALID_TIMEFRAMES = {"3m", "5m", "15m"}
MIN_CONFIDENCE = 0.6
VALID_STRATEGIES = {
    "VWAP Breakout",
    "EMA Cross (9/21)",
    "RSI Divergence",
    "Support/Resistance Break",
    "Bollinger Band Squeeze"
}
VALID_MOMENTUM = {"HIGH", "MEDIUM", "LOW"}

class Signal(BaseModel):
    pair: str
    direction: str
    strategy: str
    timeframe: str
    entry: float
    stop: float
    targets: List[float]
    confidence: float
    momentum: str
    # Optional fields for dynamic updates
    early_exit: Optional[bool] = False
    momentum_change: Optional[str] = None  # HIGH/MEDIUM/LOW
    strategy_invalidated: Optional[bool] = False

def validate_signal(signal: Signal) -> Optional[Signal]:
    # Validate pair
    if signal.pair not in VALID_PAIRS:
        return None
    # Validate timeframe
    if signal.timeframe not in VALID_TIMEFRAMES:
        return None
    # Validate confidence threshold
    if signal.confidence < MIN_CONFIDENCE:
        return None
    # Validate strategy
    if signal.strategy not in VALID_STRATEGIES:
        return None
    # Validate momentum
    if signal.momentum not in VALID_MOMENTUM:
        return None
    # Validate targets length
    if len(signal.targets) != 3:
        return None
    # Validate direction
    if signal.direction.upper() not in {"BUY", "SELL"}:
        return None
    # Validate prices positive
    if signal.entry <= 0 or signal.stop <= 0 or any(t <= 0 for t in signal.targets):
        return None
    return signal


