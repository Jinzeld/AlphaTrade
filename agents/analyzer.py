import pandas as pd
from utils.indicators import ema, rsi
from utils.logger import logger
import config


def analyze(df: pd.DataFrame) -> dict | None:
    if df.empty or len(df) < config.EMA_TREND:
        logger.warning("[ANALYZER] Not enough candle data for full analysis (need 200+ candles)")
        return None

    close = df["Close"].squeeze()

    ema_fast   = ema(close, config.EMA_FAST)
    ema_slow   = ema(close, config.EMA_SLOW)
    ema_200    = ema(close, config.EMA_TREND)
    rsi_values = rsi(close, 14)

    # current bar values
    price     = round(float(close.iloc[-1]), 2)
    curr_rsi  = round(float(rsi_values.iloc[-1]), 2)
    curr_fast = round(float(ema_fast.iloc[-1]), 2)
    curr_slow = round(float(ema_slow.iloc[-1]), 2)
    curr_200  = round(float(ema_200.iloc[-1]), 2)

    # previous bar values for crossover detection
    prev_fast = round(float(ema_fast.iloc[-2]), 2)
    prev_slow = round(float(ema_slow.iloc[-2]), 2)

    bullish_cross = prev_fast < prev_slow and curr_fast > curr_slow
    bearish_cross = prev_fast > prev_slow and curr_fast < curr_slow

    trend = "BULLISH" if price > curr_200 else "BEARISH"

    # how far price is from 200 EMA as a percentage
    ema200_distance_pct = round(((price - curr_200) / curr_200) * 100, 2)

    return {
        "price":              price,
        "rsi":                curr_rsi,
        "ema_fast":           curr_fast,
        "ema_slow":           curr_slow,
        "ema_200":            curr_200,
        "ema200_distance_pct": ema200_distance_pct,
        "bullish_cross":      bullish_cross,
        "bearish_cross":      bearish_cross,
        "trend":              trend,
    }
