import pandas as pd
import numpy as np
from utils.indicators import ema, rsi
from utils.logger import logger
import config


def _vwap(df: pd.DataFrame) -> pd.Series:
    """VWAP — resets each day, key intraday level."""
    df = df.copy()
    df["date"] = pd.to_datetime(df.index).date
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    vwap_vals = []
    for date, group in df.groupby("date"):
        tp   = (group["High"] + group["Low"] + group["Close"]) / 3
        vol  = group["Volume"]
        cumvp = (tp * vol).cumsum()
        cumv  = vol.cumsum()
        vwap_vals.extend((cumvp / cumv).tolist())
    return pd.Series(vwap_vals, index=df.index)


def _macd(series: pd.Series):
    """MACD line, signal, histogram."""
    fast    = series.ewm(span=12, adjust=False).mean()
    slow    = series.ewm(span=26, adjust=False).mean()
    macd    = fast - slow
    signal  = macd.ewm(span=9, adjust=False).mean()
    hist    = macd - signal
    return macd, signal, hist


def _bollinger(series: pd.Series, period: int = 20, std: float = 2.0):
    """Upper, middle, lower Bollinger Bands."""
    middle = series.rolling(period).mean()
    stddev = series.rolling(period).std()
    upper  = middle + std * stddev
    lower  = middle - std * stddev
    return upper, middle, lower


def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range — measures volatility."""
    high  = df["High"]
    low   = df["Low"]
    close = df["Close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def analyze(df: pd.DataFrame, daily_df: pd.DataFrame | None = None) -> dict | None:
    if df.empty or len(df) < 50:
        logger.warning("[ANALYZER] Not enough candle data")
        return None

    close  = df["Close"].squeeze()
    high   = df["High"].squeeze()
    low    = df["Low"].squeeze()
    volume = df["Volume"].squeeze()

    # ── Core EMAs (5 min) ─────────────────────────────────────────
    ema9   = ema(close, 9)
    ema21  = ema(close, 21)
    ema50  = ema(close, 50)

    # ── 200 EMA trend from daily chart ────────────────────────────
    daily_trend = "UNKNOWN"
    ema200_val  = None
    if daily_df is not None and len(daily_df) >= 200:
        daily_close = daily_df["Close"].squeeze()
        ema200      = ema(daily_close, 200)
        ema200_val  = round(float(ema200.iloc[-1]), 2)
        daily_price = float(daily_close.iloc[-1])
        daily_trend = "BULLISH" if daily_price > ema200_val else "BEARISH"

    # ── RSI ───────────────────────────────────────────────────────
    rsi_vals   = rsi(close, 14)
    curr_rsi   = round(float(rsi_vals.iloc[-1]), 2)

    # ── MACD ─────────────────────────────────────────────────────
    macd_line, macd_signal, macd_hist = _macd(close)
    curr_macd   = round(float(macd_line.iloc[-1]),   4)
    curr_signal = round(float(macd_signal.iloc[-1]), 4)
    curr_hist   = round(float(macd_hist.iloc[-1]),   4)
    prev_hist   = round(float(macd_hist.iloc[-2]),   4)
    macd_bull_cross = prev_hist < 0 and curr_hist > 0
    macd_bear_cross = prev_hist > 0 and curr_hist < 0

    # ── Bollinger Bands ───────────────────────────────────────────
    bb_upper, bb_mid, bb_lower = _bollinger(close, 20)
    curr_bb_upper = round(float(bb_upper.iloc[-1]), 4)
    curr_bb_lower = round(float(bb_lower.iloc[-1]), 4)
    curr_bb_mid   = round(float(bb_mid.iloc[-1]),   4)
    bb_width_pct  = round(((curr_bb_upper - curr_bb_lower) / curr_bb_mid) * 100, 2)

    # ── VWAP ─────────────────────────────────────────────────────
    try:
        vwap_series = _vwap(df)
        curr_vwap   = round(float(vwap_series.iloc[-1]), 4)
    except Exception:
        curr_vwap = None

    # ── ATR (volatility) ─────────────────────────────────────────
    atr_series = _atr(df)
    curr_atr   = round(float(atr_series.iloc[-1]), 4)

    # ── EMA crossovers ────────────────────────────────────────────
    prev_ema9  = float(ema9.iloc[-2])
    prev_ema21 = float(ema21.iloc[-2])
    curr_ema9  = float(ema9.iloc[-1])
    curr_ema21 = float(ema21.iloc[-1])
    bullish_cross = prev_ema9 < prev_ema21 and curr_ema9 > curr_ema21
    bearish_cross = prev_ema9 > prev_ema21 and curr_ema9 < curr_ema21

    # ── Volume surge ─────────────────────────────────────────────
    avg_vol    = float(volume.rolling(20).mean().iloc[-1])
    curr_vol   = float(volume.iloc[-1])
    vol_surge  = curr_vol > avg_vol * 1.5  # 50% above average

    price = round(float(close.iloc[-1]), 2)

    return {
        "price":          price,
        "rsi":            curr_rsi,
        "ema9":           round(curr_ema9,  2),
        "ema21":          round(curr_ema21, 2),
        "ema50":          round(float(ema50.iloc[-1]), 2),
        "ema200":         ema200_val,
        "daily_trend":    daily_trend,
        "macd":           curr_macd,
        "macd_signal":    curr_signal,
        "macd_hist":      curr_hist,
        "macd_bull_cross": macd_bull_cross,
        "macd_bear_cross": macd_bear_cross,
        "bb_upper":       curr_bb_upper,
        "bb_lower":       curr_bb_lower,
        "bb_mid":         curr_bb_mid,
        "bb_width_pct":   bb_width_pct,
        "vwap":           curr_vwap,
        "atr":            curr_atr,
        "bullish_cross":  bullish_cross,
        "bearish_cross":  bearish_cross,
        "vol_surge":      vol_surge,
        "avg_volume":     round(avg_vol, 0),
        "curr_volume":    round(curr_vol, 0),
        "above_vwap":     price > curr_vwap if curr_vwap else None,
        "near_bb_lower":  price <= curr_bb_lower * 1.002,
        "near_bb_upper":  price >= curr_bb_upper * 0.998,
    }