from typing import Optional, List, Tuple
import pandas as pd
from pydantic import BaseModel, Field, ConfigDict
from ta.trend import EMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.momentum import RSIIndicator
from ta.volume import VolumeWeightedAveragePrice
import logging

# Configure logging
strategy_logger = logging.getLogger("strategies")
strategy_logger.setLevel(logging.INFO)
handler = logging.FileHandler("strategies.log")
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
strategy_logger.addHandler(handler)

class Signal(BaseModel):
    pair: str
    direction: str  # "BUY" or "SELL"
    strategy: str
    timeframe: str
    entry: float
    stop: float
    targets: List[float]
    confidence: float  # 0.60 to 1.0
    momentum: str  # "LOW", "MEDIUM", "HIGH"
    early_exit: bool = False
    momentum_change: Optional[str] = None
    strategy_invalidated: bool = False
    exit_reason: Optional[str] = None
    slno: Optional[str] = None
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        extra="ignore"
    )

def check_trend_reversal(signal: Signal, df: pd.DataFrame) -> bool:
    """Check for trend reversal conditions"""
    if df.empty or "close" not in df.columns:
        return False # Cannot perform check without data
    ema9 = EMAIndicator(df["close"], window=9).ema_indicator().iloc[-1]
    ema21 = EMAIndicator(df["close"], window=21).ema_indicator().iloc[-1]
    
    if signal.direction == "BUY" and ema9 < ema21:
        strategy_logger.warning(f"Trend reversal detected for {signal.pair} {signal.strategy}")
        return True
    elif signal.direction == "SELL" and ema9 > ema21:
        strategy_logger.warning(f"Trend reversal detected for {signal.pair} {signal.strategy}")
        return True
    return False

def check_momentum_crash(signal: Signal, df: pd.DataFrame) -> bool:
    """Check for momentum crash conditions"""
    if df.empty or "close" not in df.columns:
        return False # Cannot perform check without data
    rsi = RSIIndicator(df["close"], window=14).rsi().iloc[-1]
    
    if signal.direction == "BUY" and rsi < 45:
        strategy_logger.warning(f"Momentum crash (RSI={rsi:.1f}) for {signal.pair}")
        return True
    elif signal.direction == "SELL" and rsi > 55:
        strategy_logger.warning(f"Momentum crash (RSI={rsi:.1f}) for {signal.pair}")
        return True
    return False

def check_vwap_rejection(signal: Signal, df: pd.DataFrame) -> bool:
    """Check for VWAP rejection (for VWAP strategy only)"""
    if df.empty or "close" not in df.columns or "high" not in df.columns or "low" not in df.columns or "volume" not in df.columns:
        return False # Cannot perform check without data
    if signal.strategy != "VWAP Breakout":
        return False
        
    vwap = VolumeWeightedAveragePrice(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        volume=df["volume"],
        window=20
    ).volume_weighted_average_price().iloc[-1]
    
    current_price = df["close"].iloc[-1]
    
    if signal.direction == "BUY" and current_price < vwap:
        strategy_logger.warning(f"VWAP rejection for {signal.pair}")
        return True
    elif signal.direction == "SELL" and current_price > vwap:
        strategy_logger.warning(f"VWAP rejection for {signal.pair}")
        return True
    return False

def validate_signal(signal: Signal, df: Optional[pd.DataFrame] = None) -> Optional[Signal]:
    """Enhanced signal validation with safety checks"""
    if signal.confidence < 0.6:
        strategy_logger.info(f"Signal rejected: Confidence {signal.confidence} < 0.6")
        return None
    if len(signal.targets) != 3:
        strategy_logger.info(f"Signal rejected: Invalid targets count {len(signal.targets)}")
        return None
    if signal.direction not in ["BUY", "SELL"]:
        strategy_logger.info(f"Signal rejected: Invalid direction {signal.direction}")
        return None
    if signal.entry <= 0 or signal.stop <= 0:
        strategy_logger.info(f"Signal rejected: Invalid entry/stop {signal.entry}/{signal.stop}")
        return None
        
    # Apply safety checks only if DataFrame is provided and not empty
    if df is not None and not df.empty:
        if check_trend_reversal(signal, df):
            signal.early_exit = True
            signal.strategy_invalidated = True
            signal.exit_reason = "TREND_REVERSAL"
            
        if check_momentum_crash(signal, df):
            signal.early_exit = True
            signal.momentum_change = "LOW"
            signal.exit_reason = "MOMENTUM_CRASH"
            
        if check_vwap_rejection(signal, df):
            signal.early_exit = True
            signal.strategy_invalidated = True
            signal.exit_reason = "VWAP_REJECTION"
        
    return signal

def calculate_vwap_breakout(df: pd.DataFrame, pair: str, timeframe: str) -> Optional[Signal]:
    """VWAP Breakout with volume confirmation"""
    vwap = VolumeWeightedAveragePrice(
        high=df["high"],
        low=df["low"],
        close=df["close"],
        volume=df["volume"],
        window=20
    ).volume_weighted_average_price()
    
    current_price = df["close"].iloc[-1]
    prev_price = df["close"].iloc[-2]
    current_volume = df["volume"].iloc[-1]
    avg_volume = df["volume"].rolling(20).mean().iloc[-1]
    
    # Breakout conditions
    bullish = (prev_price < vwap.iloc[-2]) and (current_price > vwap.iloc[-1])
    bearish = (prev_price > vwap.iloc[-2]) and (current_price < vwap.iloc[-1])
    vol_confirmed = current_volume > avg_volume * 1.5
    
    if bullish and vol_confirmed:
        atr = _calculate_atr(df)
        stop = round(current_price - 1.5 * atr, 2)
        targets = [round(current_price + r * atr, 2) for r in [1, 1.5, 2]]
        signal = Signal(
            pair=pair,
            direction="BUY",
            strategy="VWAP Breakout",
            timeframe=timeframe,
            entry=current_price,
            stop=stop,
            targets=targets,
            confidence=min(0.75 + (current_volume/avg_volume - 1.5)/3, 0.95),
            momentum="HIGH" if current_volume > avg_volume * 2 else "MEDIUM",
        )
        return validate_signal(signal, df)
    
    elif bearish and vol_confirmed:
        atr = _calculate_atr(df)
        stop = round(current_price + 1.5 * atr, 2)
        targets = [round(current_price - r * atr, 2) for r in [1, 1.5, 2]]
        signal = Signal(
            pair=pair,
            direction="SELL",
            strategy="VWAP Breakout",
            timeframe=timeframe,
            entry=current_price,
            stop=stop,
            targets=targets,
            confidence=min(0.75 + (current_volume/avg_volume - 1.5)/3, 0.95),
            momentum="HIGH" if current_volume > avg_volume * 2 else "MEDIUM",
        )
        return validate_signal(signal, df)    
    strategy_logger.info(f"VWAP Breakout: No valid signal for {pair} {timeframe}")
    return None

def calculate_ema_cross(df: pd.DataFrame, pair: str, timeframe: str) -> Optional[Signal]:
    """EMA 9/21 Crossover Strategy"""
    ema9 = EMAIndicator(close=df["close"], window=9).ema_indicator()
    ema21 = EMAIndicator(close=df["close"], window=21).ema_indicator()
    
    current_price = df["close"].iloc[-1]
    bullish = (ema9.iloc[-2] <= ema21.iloc[-2]) and (ema9.iloc[-1] > ema21.iloc[-1])
    bearish = (ema9.iloc[-2] >= ema21.iloc[-2]) and (ema9.iloc[-1] < ema21.iloc[-1])
    
    if bullish:
        atr = _calculate_atr(df)
        stop = round(current_price - 1.5 * atr, 2)
        targets = [round(current_price + r * atr, 2) for r in [1, 1.5, 2]]
        angle = (ema9.iloc[-1] - ema9.iloc[-3]) / (ema9.iloc[-3] or 1)
        signal = Signal(
            pair=pair,
            direction="BUY",
            strategy="EMA Cross",
            timeframe=timeframe,
            entry=current_price,
            stop=stop,
            targets=targets,
            confidence=min(0.65 + angle*100, 0.90),
            momentum="HIGH" if angle > 0.01 else "MEDIUM",
        )
        return validate_signal(signal, df)
    
    elif bearish:
        atr = _calculate_atr(df)
        stop = round(current_price + 1.5 * atr, 2)
        targets = [round(current_price - r * atr, 2) for r in [1, 1.5, 2]]
        angle = (ema9.iloc[-3] - ema9.iloc[-1]) / (ema9.iloc[-3] or 1)
        signal = Signal(
            pair=pair,
            direction="SELL",
            strategy="EMA Cross",
            timeframe=timeframe,
            entry=current_price,
            stop=stop,
            targets=targets,
            confidence=min(0.65 + angle*100, 0.90),
            momentum="HIGH" if angle > 0.01 else "MEDIUM",
        )
        return validate_signal(signal, df)
    
    strategy_logger.info(f"EMA Cross: No valid signal for {pair} {timeframe}")
    return None

def calculate_rsi_divergence(df: pd.DataFrame, pair: str, timeframe: str) -> Optional[Signal]:
    """RSI Divergence Detection"""
    rsi = RSIIndicator(close=df["close"], window=14).rsi()
    current_rsi = rsi.iloc[-1]
    
    if len(df) < 15:
        strategy_logger.info(f"RSI Divergence: Not enough data for {pair} {timeframe}")
        return None
    
    # Bullish divergence detection
    lows = df["low"].rolling(5, center=True).min() == df["low"]
    if sum(lows[-10:]) >= 2:
        idx = lows[lows].index[-2:]
        price_low1, price_low2 = df["low"].loc[idx[0]], df["low"].loc[idx[1]]
        rsi_low1, rsi_low2 = rsi.loc[idx[0]], rsi.loc[idx[1]]
        
        if (price_low2 < price_low1) and (rsi_low2 > rsi_low1) and (current_rsi > 30):
            current_price = df["close"].iloc[-1]
            atr = _calculate_atr(df)
            stop = round(current_price - 1.5 * atr, 2)
            targets = [round(current_price + r * atr, 2) for r in [1, 1.5, 2]]
            signal = Signal(
                pair=pair,
                direction="BUY",
                strategy="RSI Divergence",
                timeframe=timeframe,
                entry=current_price,
                stop=stop,
                targets=targets,
                confidence=min(0.70 + (rsi_low2 - rsi_low1)/10, 0.85),
                momentum="HIGH" if current_rsi > 50 else "MEDIUM",
            )
            return validate_signal(signal, df)
    
    # Bearish divergence detection
    highs = df["high"].rolling(5, center=True).max() == df["high"]
    if sum(highs[-10:]) >= 2:
        idx = highs[highs].index[-2:]
        price_high1, price_high2 = df["high"].loc[idx[0]], df["high"].loc[idx[1]]
        rsi_high1, rsi_high2 = rsi.loc[idx[0]], rsi.loc[idx[1]]
        
        if (price_high2 > price_high1) and (rsi_high2 < rsi_high1) and (current_rsi < 70):
            current_price = df["close"].iloc[-1]
            atr = _calculate_atr(df)
            stop = round(current_price + 1.5 * atr, 2)
            targets = [round(current_price - r * atr, 2) for r in [1, 1.5, 2]]
            signal = Signal(
                pair=pair,
                direction="SELL",
                strategy="RSI Divergence",
                timeframe=timeframe,
                entry=current_price,
                stop=stop,
                targets=targets,
                confidence=min(0.70 + (rsi_high1 - rsi_high2)/10, 0.85),
                momentum="HIGH" if current_rsi < 50 else "MEDIUM",
            )
            return validate_signal(signal, df)
    
    strategy_logger.info(f"RSI Divergence: No valid signal for {pair} {timeframe}")
    return None

def calculate_support_resistance_break(df: pd.DataFrame, pair: str, timeframe: str) -> Optional[Signal]:
    """Support/Resistance Breakout Strategy"""
    current_price = df["close"].iloc[-1]
    current_volume = df["volume"].iloc[-1]
    avg_volume = df["volume"].rolling(20).mean().iloc[-1]
    
    # Identify key levels
    pivot_range = 8
    resistance = df["high"].rolling(pivot_range).max().iloc[-1]
    support = df["low"].rolling(pivot_range).min().iloc[-1]
    
    # Breakout conditions
    res_touches = sum(df["high"][-15:] >= resistance * 0.995)
    sup_touches = sum(df["low"][-15:] <= support * 1.005)
    
    # Bullish breakout
    if (res_touches >= 2 and current_price > resistance 
        and df["close"].iloc[-2] <= resistance and current_volume > avg_volume * 1.2):
        atr = _calculate_atr(df)
        stop = round(current_price - 1.5 * atr, 2)
        targets = [round(current_price + r * atr, 2) for r in [1, 1.5, 2]]
        signal = Signal(
            pair=pair,
            direction="BUY",
            strategy="Support/Resistance Break",
            timeframe=timeframe,
            entry=current_price,
            stop=stop,
            targets=targets,
            momentum="HIGH" if current_volume > avg_volume * 1.5 else "MEDIUM",
        )
        return validate_signal(signal, df)
    
    # Bearish breakout
    elif (sup_touches >= 2 and current_price < support 
          and df["close"].iloc[-2] >= support and current_volume > avg_volume * 1.2):
        atr = _calculate_atr(df)
        stop = round(current_price + 1.5 * atr, 2)
        targets = [round(current_price - r * atr, 2) for r in [1, 1.5, 2]]
        signal = Signal(
            pair=pair,
            direction="SELL",
            strategy="Support/Resistance Break",
            timeframe=timeframe,
            entry=current_price,
            stop=stop,
            targets=targets,
            momentum="HIGH" if current_volume > avg_volume * 1.5 else "MEDIUM",
        )
        return validate_signal(signal, df)
    
    strategy_logger.info(f"Support/Resistance Break: No valid signal for {pair} {timeframe}")
    return None

def calculate_bollinger_squeeze(df: pd.DataFrame, pair: str, timeframe: str) -> Optional[Signal]:
    """Bollinger Band Squeeze Breakout"""
    bb = BollingerBands(close=df["close"], window=20, window_dev=2)
    upper = bb.bollinger_hband()
    lower = bb.bollinger_lband()
    bandwidth = (upper - lower) / bb.bollinger_mavg()
    
    current_price = df["close"].iloc[-1]
    prev_price = df["close"].iloc[-2]
    current_volume = df["volume"].iloc[-1]
    avg_volume = df["volume"].rolling(20).mean().iloc[-1]
    
    squeeze_thresh = bandwidth.rolling(50).quantile(0.2).iloc[-1]
    is_squeeze = bandwidth.iloc[-1] < squeeze_thresh
    
    if is_squeeze:
        # Bullish breakout
        if (prev_price <= upper.iloc[-2]) and (current_price > upper.iloc[-1]):
            atr = _calculate_atr(df)
            stop = round(current_price - 1.5 * atr, 2)
            targets = [round(current_price + r * atr, 2) for r in [1, 1.5, 2]]
            signal = Signal(
                pair=pair,
                direction="BUY",
                strategy="Bollinger Band Squeeze",
                timeframe=timeframe,
                entry=current_price,
                stop=stop,
                targets=targets,
                confidence=min(0.75 + (1 - bandwidth.iloc[-1]/squeeze_thresh), 0.95),
                momentum="HIGH" if current_volume > avg_volume * 1.5 else "MEDIUM",
            )
            return validate_signal(signal, df)
        
        # Bearish breakout
        elif (prev_price >= lower.iloc[-2]) and (current_price < lower.iloc[-1]):
            atr = _calculate_atr(df)
            stop = round(current_price + 1.5 * atr, 2)
            targets = [round(current_price - r * atr, 2) for r in [1, 1.5, 2]]
            signal = Signal(
                pair=pair,
                direction="SELL",
                strategy="Bollinger Band Squeeze",
                timeframe=timeframe,
                entry=current_price,
                stop=stop,
                targets=targets,
                confidence=min(0.75 + (1 - bandwidth.iloc[-1]/squeeze_thresh), 0.95),
                momentum="HIGH" if current_volume > avg_volume * 1.5 else "MEDIUM",
            )
            return validate_signal(signal, df)
    
    strategy_logger.info(f"Bollinger Squeeze: No valid signal for {pair} {timeframe}")
    return None

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
    for strategy_func in strategies:
        if signal := strategy_func(df.copy(), pair, timeframe):
            signals.append(signal)
            strategy_logger.info(f"Generated {signal.strategy} signal for {pair} {timeframe}")
        else:
            strategy_logger.debug(f"No signal from {strategy_func.__name__} for {pair} {timeframe}")
    
    return signals

def should_exit_early(current_price: float, signal: Signal, df: pd.DataFrame) -> Tuple[bool, Optional[str]]:
    """Determine if early exit conditions are met"""
    # Stop loss hit
    if (signal.direction == "BUY" and current_price <= signal.stop) or \
       (signal.direction == "SELL" and current_price >= signal.stop):
        return True, "STOP_LOSS_HIT"
    
    # Technical exits
    if signal.strategy_invalidated:
        return True, signal.exit_reason or "STRATEGY_INVALIDATED"
    
    if signal.early_exit:
        return True, signal.exit_reason or "EARLY_EXIT_TRIGGERED"
    
    # Early Profit Booking (e.g., if first target is hit)
    if signal.direction == "BUY" and current_price >= signal.targets[0]:
        return True, "EARLY_PROFIT_BOOKING"
    elif signal.direction == "SELL" and current_price <= signal.targets[0]:
        return True, "EARLY_PROFIT_BOOKING"

    # Cost-to-Cost Exit (Breakeven)
    if (signal.direction == "BUY" and current_price <= signal.entry) or \
       (signal.direction == "SELL" and current_price >= signal.entry):
        return True, "COST_TO_COST_EXIT"

    return False, None





def _calculate_atr(df: pd.DataFrame) -> float:
    """Helper to calculate Average True Range"""
    atr = AverageTrueRange(high=df["high"], low=df["low"], close=df["close"], window=14).average_true_range()
    return atr.iloc[-1]


