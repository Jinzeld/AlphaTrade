import yfinance as yf
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from config import ALPACA_KEY, ALPACA_SECRET

_alpaca_client = StockHistoricalDataClient(ALPACA_KEY, ALPACA_SECRET)

def get_candles(ticker: str, period="5d", interval="1h") -> pd.DataFrame:
    try:
        request = StockBarsRequest(
            symbol_or_symbols=ticker,
            timeframe=TimeFrame.Hour,
            limit=120
        )
        bars = _alpaca_client.get_stock_bars(request).df
        bars = bars.reset_index(level=0, drop=True)  # drop symbol from index
        bars.columns = [c.capitalize() for c in bars.columns]
        return bars
    except Exception as e:
        print(f"[WARN] Alpaca fetch failed for {ticker}, falling back to yfinance: {e}")
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        df.dropna(inplace=True)
        return df