from finvizfinance.screener.overview import Overview
from finvizfinance.screener.technical import Technical
from finvizfinance.quote import finvizfinance
import pandas as pd
import time
from utils.logger import logger
import config


# maps config label to finviz filter string
_CAP_MAP = {
    "Small": "cap_small",
    "Mid":   "cap_mid",
    "Large": "cap_large",
    "Mega":  "cap_mega",
}


def get_oversold_stocks() -> list[dict]:
    """
    Pulls the Finviz oversold screener — RSI(14) oversold signal.
    Filters by minimum market cap and returns the top N stocks
    with their full fundamental + technical data.
    """
    try:
        logger.info("[FINVIZ] Running oversold screener...")

        tech = Technical()
        tech.set_filter(signal="ta_oversold", filters_dict={
            "Market Cap":    config.FINVIZ_MIN_MARKET_CAP,
            "Country":       "USA",
        })

        df = tech.screener_view()

        if df is None or df.empty:
            logger.warning("[FINVIZ] No oversold stocks found")
            return []

        # sort by RSI ascending so most oversold comes first
        if "RSI" in df.columns:
            df["RSI"] = pd.to_numeric(df["RSI"], errors="coerce")
            df = df.sort_values("RSI", ascending=True)

        df = df.head(config.FINVIZ_TOP_N)

        results = []
        for _, row in df.iterrows():
            ticker = str(row.get("Ticker", "")).strip()
            if not ticker:
                continue

            # pull deeper fundamentals per ticker
            try:
                stock_data = finvizfinance(ticker).ticker_fundament()
            except Exception:
                stock_data = {}

            time.sleep(0.5)  # be polite to finviz

            results.append({
                "ticker":        ticker,
                "company":       str(row.get("Company", "N/A")),
                "sector":        str(row.get("Sector",  "N/A")),
                "industry":      str(row.get("Industry","N/A")),
                "price":         str(row.get("Price",   "N/A")),
                "change":        str(row.get("Change",  "N/A")),
                "volume":        str(row.get("Volume",  "N/A")),
                "rsi":           str(row.get("RSI",     "N/A")),
                "sma20":         str(row.get("SMA20",   "N/A")),
                "sma50":         str(row.get("SMA50",   "N/A")),
                "sma200":        str(row.get("SMA200",  "N/A")),
                "market_cap":    stock_data.get("Market Cap",       "N/A"),
                "pe_ratio":      stock_data.get("P/E",              "N/A"),
                "eps":           stock_data.get("EPS (ttm)",        "N/A"),
                "dividend":      stock_data.get("Dividend %",       "N/A"),
                "analyst_target":stock_data.get("Target Price",     "N/A"),
                "analyst_rec":   stock_data.get("Recom",            "N/A"),
                "debt_equity":   stock_data.get("Debt/Eq",          "N/A"),
                "roe":           stock_data.get("ROE",              "N/A"),
                "revenue":       stock_data.get("Revenue",          "N/A"),
                "earnings_date": stock_data.get("Earnings",         "N/A"),
            })

        logger.info(f"[FINVIZ] Found {len(results)} oversold stocks")
        return results

    except Exception as e:
        logger.error(f"[FINVIZ] Screener failed: {e}")
        return []