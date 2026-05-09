import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from utils.logger import logger
import config


def get_best_option(ticker: str, option_type: str, trade_type: str = "swing") -> dict | None:
    """
    Scans for the best call or put based on trade type:
      - 0dte:  same day expiry only
      - swing: up to OPTION_SWING_DAYS out
    Picks the contract closest to at-the-money with healthy volume.
    """
    try:
        tk    = yf.Ticker(ticker)
        price = tk.fast_info["last_price"]
        exps  = tk.options

        today   = datetime.now().date()
        max_days = config.OPTION_0DTE_DAYS if trade_type == "0dte" else config.OPTION_SWING_DAYS
        cutoff  = today + timedelta(days=max_days)

        valid = [
            e for e in exps
            if today <= datetime.strptime(e, "%Y-%m-%d").date() <= cutoff
        ]

        if not valid:
            return {"error": f"No {'same-day' if trade_type == '0dte' else f'{max_days}-day'} options found for {ticker}"}

        best_option = None
        best_score  = float("inf")

        for exp in valid:
            chain = tk.option_chain(exp)
            df    = chain.calls if option_type == "call" else chain.puts

            df = df[
                (df["volume"]       >= config.OPTION_MIN_VOLUME) &
                (df["openInterest"] >= config.OPTION_MIN_OI)
            ].copy()

            if df.empty:
                continue

            df["distance"] = abs(df["strike"] - price)
            row = df.loc[df["distance"].idxmin()]

            if row["distance"] < best_score:
                best_score  = row["distance"]
                days_to_exp = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days
                best_option = {
                    "type":          option_type.upper(),
                    "expiry":        exp,
                    "days_to_exp":   days_to_exp,
                    "strike":        round(float(row["strike"]), 2),
                    "last_price":    round(float(row["lastPrice"]), 2),
                    "bid":           round(float(row["bid"]), 2),
                    "ask":           round(float(row["ask"]), 2),
                    "volume":        int(row["volume"]),
                    "open_interest": int(row["openInterest"]),
                    "implied_vol":   f"{round(float(row['impliedVolatility']) * 100, 1)}%",
                    "in_the_money":  bool(row["inTheMoney"]),
                    "underlying":    round(float(price), 2),
                }

        return best_option or {"error": "No options passed the volume/OI filter"}

    except Exception as e:
        logger.error(f"[OPTIONS] Error scanning {ticker}: {e}")
        return {"error": str(e)}
