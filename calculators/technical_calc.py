from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from common import safe_div, to_float


def calculate_technical_indicators(price_df: pd.DataFrame, nifty500_df: pd.DataFrame | None = None) -> dict[str, Any]:
    if price_df.empty:
        return {}
    frame = price_df.copy()
    frame.columns = [str(column).lower() for column in frame.columns]
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["high"] = pd.to_numeric(frame.get("high", frame["close"]), errors="coerce")
    frame["low"] = pd.to_numeric(frame.get("low", frame["close"]), errors="coerce")
    frame["volume"] = pd.to_numeric(frame.get("volume", 0), errors="coerce").fillna(0)
    close = frame["close"].dropna()
    if close.empty:
        return {}
    latest = close.iloc[-1]
    sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else None
    sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
    rsi = _rsi(close)
    macd, macd_signal = _macd(close)
    high_52 = close.tail(252).max()
    low_52 = close.tail(252).min()
    returns = close.pct_change().dropna()
    atr = _atr(frame)
    support = float(frame["low"].tail(min(60, len(frame))).min())
    return {
        "sma50": float(sma50) if sma50 is not None and not np.isnan(sma50) else None,
        "sma200": float(sma200) if sma200 is not None and not np.isnan(sma200) else None,
        "golden_cross": bool(sma50 is not None and sma200 is not None and sma50 > sma200),
        "death_cross": bool(sma50 is not None and sma200 is not None and sma50 < sma200),
        "rsi_14": rsi,
        "macd": macd,
        "macd_signal": macd_signal,
        "roc_20_pct": _pct(close, 20),
        "historical_volatility_pct": float(returns.std() * np.sqrt(252) * 100) if not returns.empty else None,
        "atr_14": atr,
        "distance_from_52w_low_pct": safe_div(latest - low_52, low_52, 0) * 100 if low_52 else None,
        "drawdown_from_52w_high_pct": safe_div(latest - high_52, high_52, 0) * 100 if high_52 else None,
        "year_high": float(high_52),
        "year_low": float(low_52),
        "support_level": support,
        "suggested_stop_loss": round(support * 0.97, 2),
        "potential_return_to_52w_high_pct": safe_div(high_52 - latest, latest, 0) * 100 if latest else None,
        "volume_ratio_20d": _volume_ratio(frame),
        "relative_strength_6m_pct": _relative_strength(close, nifty500_df),
    }


def _rsi(close: pd.Series, period: int = 14) -> float | None:
    if len(close) <= period:
        return None
    delta = close.diff()
    gains = delta.clip(lower=0).rolling(period).mean()
    losses = -delta.clip(upper=0).rolling(period).mean()
    rs = gains / losses.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    value = rsi.iloc[-1]
    return float(value) if not np.isnan(value) else 100.0


def _macd(close: pd.Series) -> tuple[float | None, float | None]:
    if len(close) < 35:
        return None, None
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    return float(macd.iloc[-1]), float(signal.iloc[-1])


def _atr(frame: pd.DataFrame, period: int = 14) -> float | None:
    if len(frame) <= period:
        return None
    high_low = frame["high"] - frame["low"]
    high_close = (frame["high"] - frame["close"].shift()).abs()
    low_close = (frame["low"] - frame["close"].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    value = ranges.rolling(period).mean().iloc[-1]
    return float(value) if not np.isnan(value) else None


def _pct(close: pd.Series, days: int) -> float | None:
    if len(close) <= days:
        return None
    start = to_float(close.iloc[-days])
    end = to_float(close.iloc[-1])
    if start in (None, 0) or end is None:
        return None
    return (end / start - 1) * 100


def _volume_ratio(frame: pd.DataFrame) -> float | None:
    if len(frame) < 20:
        return None
    avg = frame["volume"].tail(20).mean()
    if avg == 0:
        return None
    return float(frame["volume"].iloc[-1] / avg)


def _relative_strength(close: pd.Series, nifty500_df: pd.DataFrame | None) -> float | None:
    if nifty500_df is None or nifty500_df.empty or len(close) < 126:
        return None
    index_frame = nifty500_df.copy()
    index_frame.columns = [str(c).lower() for c in index_frame.columns]
    if "close" not in index_frame or len(index_frame["close"].dropna()) < 126:
        return None
    stock_return = close.iloc[-1] / close.iloc[-126] - 1
    index_close = pd.to_numeric(index_frame["close"], errors="coerce").dropna()
    index_return = index_close.iloc[-1] / index_close.iloc[-126] - 1
    return float((stock_return - index_return) * 100)
