from typing import Optional, List, Tuple
import numpy as np
import pandas as pd
from pydantic import BaseModel
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice

from pydantic import Field
import pandas as pd
class Signal(BaseModel):
    data_frame: Optional[pd.DataFrame] = Field(exclude=True)
    pair: str
    direction: str  # "BUY" or "SELL"
    strategy: str
    timeframe: str
    entry: float
    stop: float
    targets: List[float]
    confidence: float  # 0.60 to 1.0
    momentum: str  # "LOW", "MEDIUM", "HIGH"
    data_frame: Optional[pd.DataFrame] = None  # Raw OHLCV data for monitoring
    early_exit: bool = False
    momentum_change: Optional[str] = None
    strategy_invalidated: bool = False

    class Config:
        arbitrary_types_allowed = True  # For DataFrame field

# --------------------------
# STRATEGY IMPLEMENTATIONS
# --------------------------

def calculate_vwap_breakout(df: pd.DataFrame, pair: str, timeframe: str) -> Optional[Signal]:
    """VWAP Breakout with volume confirmation"""
    vwap = VolumeWeightedAveragePrice(
        high=df['high'],
        low=df['low'],
        close=df['close'],
        volume=df['volume'],
        window=20
    ).volume_weighted_average_price()
    
    current_price = df['close'].iloc[-1]
    prev_price = df['close'].iloc[-2]
    current_volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].rolling(20).mean().iloc[-1]
    
    # Breakout conditions
    bullish = (prev_price < vwap.iloc[-2]) and (current_price > vwap.iloc[-1])
    bearish = (prev_price > vwap.iloc[-2]) and (current_price < vwap.iloc[-1])
    vol_confirmed = current_volume > avg_volume * 1.5
    
    if bullish and vol_confirmed:
        stop = min(df['low'].iloc[-5:])
        risk = current_price - stop
        signal = Signal(
            pair=pair,
            direction="BUY",
            strategy="VWAP Breakout",
            timeframe=timeframe,
            entry=current_price,
            stop=stop,
            targets=[round(current_price + r*risk, 2) for r in [1, 2, 3]],
            confidence=min(0.75 + (current_volume/avg_volume - 1.5)/3, 0.95),
            momentum="HIGH" if current_volume > avg_volume * 2 else "MEDIUM",
            data_frame=df
        )
        return validate_signal(signal)
    
    elif bearish and vol_confirmed:
        stop = max(df['high'].iloc[-5:])
        risk = stop - current_price
        signal = Signal(
            pair=pair,
            direction="SELL",
            strategy="VWAP Breakout",
            timeframe=timeframe,
            entry=current_price,
            stop=stop,
            targets=[round(current_price - r*risk, 2) for r in [1, 2, 3]],
            confidence=min(0.75 + (current_volume/avg_volume - 1.5)/3, 0.95),
            momentum="HIGH" if current_volume > avg_volume * 2 else "MEDIUM",
            data_frame=df
        )
        return validate_signal(signal)
    
    return None

def calculate_ema_cross(df: pd.DataFrame, pair: str, timeframe: str) -> Optional[Signal]:
    """EMA 9/21 Crossover Strategy"""
    ema9 = EMAIndicator(close=df['close'], window=9).ema_indicator()
    ema21 = EMAIndicator(close=df['close'], window=21).ema_indicator()
    
    current_price = df['close'].iloc[-1]
    bullish = (ema9.iloc[-2] <= ema21.iloc[-2]) and (ema9.iloc[-1] > ema21.iloc[-1])
    bearish = (ema9.iloc[-2] >= ema21.iloc[-2]) and (ema9.iloc[-1] < ema21.iloc[-1])
    
    if bullish:
        stop = min(df['low'].iloc[-8:])
        risk = current_price - stop
        angle = (ema9.iloc[-1] - ema9.iloc[-3]) / (ema9.iloc[-3] or 1)
        signal = Signal(
            pair=pair,
            direction="BUY",
            strategy="EMA Cross",
            timeframe=timeframe,
            entry=current_price,
            stop=stop,
            targets=[round(current_price + r*risk, 2) for r in [1, 2, 3]],
            confidence=min(0.65 + angle*100, 0.90),
            momentum="HIGH" if angle > 0.01 else "MEDIUM",
            data_frame=df
        )
        return validate_signal(signal)
    
    elif bearish:
        stop = max(df['high'].iloc[-8:])
        risk = stop - current_price
        angle = (ema9.iloc[-3] - ema9.iloc[-1]) / (ema9.iloc[-3] or 1)
        signal = Signal(
            pair=pair,
            direction="SELL",
            strategy="EMA Cross",
            timeframe=timeframe,
            entry=current_price,
            stop=stop,
            targets=[round(current_price - r*risk, 2) for r in [1, 2, 3]],
            confidence=min(0.65 + angle*100, 0.90),
            momentum="HIGH" if angle > 0.01 else "MEDIUM",
            data_frame=df
        )
        return validate_signal(signal)
    
    return None

def calculate_rsi_divergence(df: pd.DataFrame, pair: str, timeframe: str) -> Optional[Signal]:
    """RSI Divergence Detection"""
    rsi = RSIIndicator(close=df['close'], window=14).rsi()
    current_rsi = rsi.iloc[-1]
    
    if len(df) < 15:
        return None
    
    # Bullish divergence detection
    lows = df['low'].rolling(5, center=True).min() == df['low']
    if sum(lows[-10:]) >= 2:
        idx = lows[lows].index[-2:]
        price_low1, price_low2 = df['low'].loc[idx[0]], df['low'].loc[idx[1]]
        rsi_low1, rsi_low2 = rsi.loc[idx[0]], rsi.loc[idx[1]]
        
        if (price_low2 < price_low1) and (rsi_low2 > rsi_low1) and (current_rsi > 30):
            current_price = df['close'].iloc[-1]
            stop = price_low2 * 0.995
            risk = current_price - stop
            signal = Signal(
                pair=pair,
                direction="BUY",
                strategy="RSI Divergence",
                timeframe=timeframe,
                entry=current_price,
                stop=stop,
                targets=[round(current_price + r*risk, 2) for r in [1, 2, 3]],
                confidence=min(0.70 + (rsi_low2 - rsi_low1)/10, 0.85),
                momentum="HIGH" if current_rsi > 50 else "MEDIUM",
                data_frame=df
            )
            return validate_signal(signal)
    
    # Bearish divergence detection
    highs = df['high'].rolling(5, center=True).max() == df['high']
    if sum(highs[-10:]) >= 2:
        idx = highs[highs].index[-2:]
        price_high1, price_high2 = df['high'].loc[idx[0]], df['high'].loc[idx[1]]
        rsi_high1, rsi_high2 = rsi.loc[idx[0]], rsi.loc[idx[1]]
        
        if (price_high2 > price_high1) and (rsi_high2 < rsi_high1) and (current_rsi < 70):
            current_price = df['close'].iloc[-1]
            stop = price_high2 * 1.005
            risk = stop - current_price
            signal = Signal(
                pair=pair,
                direction="SELL",
                strategy="RSI Divergence",
                timeframe=timeframe,
                entry=current_price,
                stop=stop,
                targets=[round(current_price - r*risk, 2) for r in [1, 2, 3]],
                confidence=min(0.70 + (rsi_high1 - rsi_high2)/10, 0.85),
                momentum="HIGH" if current_rsi < 50 else "MEDIUM",
                data_frame=df
            )
            return validate_signal(signal)
    
    return None

def calculate_support_resistance_break(df: pd.DataFrame, pair: str, timeframe: str) -> Optional[Signal]:
    """Support/Resistance Breakout Strategy"""
    current_price = df['close'].iloc[-1]
    current_volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].rolling(20).mean().iloc[-1]
    
    # Identify key levels
    pivot_range = 8
    resistance = df['high'].rolling(pivot_range).max().iloc[-1]
    support = df['low'].rolling(pivot_range).min().iloc[-1]
    
    # Breakout conditions
    res_touches = sum(df['high'][-15:] >= resistance * 0.995)
    sup_touches = sum(df['low'][-15:] <= support * 1.005)
    
    # Bullish breakout
    if (res_touches >= 2 and current_price > resistance 
        and df['close'].iloc[-2] <= resistance and current_volume > avg_volume * 1.2):
        stop = support
        risk = current_price - stop
        signal = Signal(
            pair=pair,
            direction="BUY",
            strategy="Support/Resistance Break",
            timeframe=timeframe,
            entry=current_price,
            stop=stop,
            targets=[round(current_price + r*risk, 2) for r in [1, 1.5, 2]],
            confidence=min(0.70 + (res_touches-2)*0.05 + (current_volume/avg_volume - 1.2)/5, 0.90),
            momentum="HIGH" if current_volume > avg_volume * 1.5 else "MEDIUM",
            data_frame=df
        )
        return validate_signal(signal)
    
    # Bearish breakout
    elif (sup_touches >= 2 and current_price < support 
          and df['close'].iloc[-2] >= support and current_volume > avg_volume * 1.2):
        stop = resistance
        risk = stop - current_price
        signal = Signal(
            pair=pair,
            direction="SELL",
            strategy="Support/Resistance Break",
            timeframe=timeframe,
            entry=current_price,
            stop=stop,
            targets=[round(current_price - r*risk, 2) for r in [1, 1.5, 2]],
            confidence=min(0.70 + (sup_touches-2)*0.05 + (current_volume/avg_volume - 1.2)/5, 0.90),
            momentum="HIGH" if current_volume > avg_volume * 1.5 else "MEDIUM",
            data_frame=df
        )
        return validate_signal(signal)
    
    return None

def calculate_bollinger_squeeze(df: pd.DataFrame, pair: str, timeframe: str) -> Optional[Signal]:
    """Bollinger Band Squeeze Breakout"""
    bb = BollingerBands(close=df['close'], window=20, window_dev=2)
    upper = bb.bollinger_hband()
    lower = bb.bollinger_lband()
    bandwidth = (upper - lower) / bb.bollinger_mavg()
    
    current_price = df['close'].iloc[-1]
    prev_price = df['close'].iloc[-2]
    current_volume = df['volume'].iloc[-1]
    avg_volume = df['volume'].rolling(20).mean().iloc[-1]
    
    squeeze_thresh = bandwidth.rolling(50).quantile(0.2).iloc[-1]
    is_squeeze = bandwidth.iloc[-1] < squeeze_thresh
    
    if is_squeeze:
        # Bullish breakout
        if (prev_price <= upper.iloc[-2]) and (current_price > upper.iloc[-1]):
            stop = lower.iloc[-1]
            risk = current_price - stop
            signal = Signal(
                pair=pair,
                direction="BUY",
                strategy="Bollinger Band Squeeze",
                timeframe=timeframe,
                entry=current_price,
                stop=stop,
                targets=[round(current_price + r*risk, 2) for r in [1, 1.5, 2]],
                confidence=min(0.75 + (1 - bandwidth.iloc[-1]/squeeze_thresh), 0.95),
                momentum="HIGH" if current_volume > avg_volume * 1.5 else "MEDIUM",
                data_frame=df
            )
            return validate_signal(signal)
        
        # Bearish breakout
        elif (prev_price >= lower.iloc[-2]) and (current_price < lower.iloc[-1]):
            stop = upper.iloc[-1]
            risk = stop - current_price
            signal = Signal(
                pair=pair,
                direction="SELL",
                strategy="Bollinger Band Squeeze",
                timeframe=timeframe,
                entry=current_price,
                stop=stop,
                targets=[round(current_price - r*risk, 2) for r in [1, 1.5, 2]],
                confidence=min(0.75 + (1 - bandwidth.iloc[-1]/squeeze_thresh), 0.95),
                momentum="HIGH" if current_volume > avg_volume * 1.5 else "MEDIUM",
                data_frame=df
            )
            return validate_signal(signal)
    
    return None

# --------------------------
# CORE UTILITIES
# --------------------------

def validate_signal(signal: Signal) -> Optional[Signal]:
    """Validate signal meets all requirements"""
    if signal.confidence < 0.6:
        return None
    if len(signal.targets) != 3:
        return None
    if signal.direction not in ["BUY", "SELL"]:
        return None
    if signal.entry <= 0 or signal.stop <= 0:
        return None
    return signal

def detect_momentum_change(df: pd.DataFrame) -> Optional[str]:
    """Detect momentum loss based on volume/price action"""
    if len(df) < 3:
        return None
    
    vol_decrease = df['volume'].iloc[-1] < df['volume'].iloc[-2] * 0.8
    price_stagnant = abs(df['close'].iloc[-1] - df['close'].iloc[-2]) < 0.001 * df['close'].iloc[-1]
    
    if vol_decrease and price_stagnant:
        return "LOW"
    return None

def should_exit_early(current_price: float, signal: Signal) -> Tuple[bool, Optional[str]]:
    """Determine if early exit conditions are met"""
    # Stop loss hit
    if (signal.direction == "BUY" and current_price <= signal.stop) or \
       (signal.direction == "SELL" and current_price >= signal.stop):
        return True, "STOP_HIT"
    
    # Momentum loss
    if signal.data_frame is not None:
        momentum = detect_momentum_change(signal.data_frame)
        if momentum == "LOW":
            return True, "MOMENTUM_LOW"
    
    return False, None

def calculate_all_strategies(df: pd.DataFrame, pair: str, timeframe: str) -> List[Signal]:
    """Run all strategies and return validated signals"""
    strategies = [
        calculate_vwap_breakout,
        calculate_ema_cross,
        calculate_rsi_divergence,
        calculate_support_resistance_break,
        calculate_bollinger_squeeze
    ]
    
    signals = []
    for strategy in strategies:
        if signal := strategy(df.copy(), pair, timeframe):
            signals.append(signal)
    
    return signals