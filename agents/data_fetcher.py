import yfinance as yf
import pandas as pd
from utils.logger import logger


def get_candles(ticker: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Pull daily candles — 1 year so the 200 EMA has
    enough history to be accurate from day one.
    """
    try:
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        df.dropna(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        logger.info(f"[DATA] Fetched {len(df)} candles for {ticker}")
        return df
    except Exception as e:
        logger.error(f"[DATA] Failed to fetch candles for {ticker}: {e}")
        return pd.DataFrame()
