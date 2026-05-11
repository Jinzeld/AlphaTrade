import yfinance as yf
import pandas as pd
from utils.logger import logger


def get_candles(ticker: str, period: str = "5d", interval: str = "5m") -> pd.DataFrame:
    """
    5 minute candles for intraday 0DTE and swing scanning.
    5 days of history gives enough data for all indicators.
    """
    try:
        df = yf.download(
            ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
        df.dropna(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        logger.info(f"[DATA] {ticker} — {len(df)} candles ({interval})")
        return df
    except Exception as e:
        logger.error(f"[DATA] Failed to fetch {ticker}: {e}")
        return pd.DataFrame()


def get_daily_candles(ticker: str) -> pd.DataFrame:
    """
    Daily candles used only for the 200 EMA trend direction check.
    Needs 1 year of data so the 200 EMA is accurate.
    """
    try:
        df = yf.download(
            ticker,
            period="1y",
            interval="1d",
            progress=False,
            auto_adjust=True,
        )
        df.dropna(inplace=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        logger.error(f"[DATA] Failed daily candles for {ticker}: {e}")
        return pd.DataFrame()