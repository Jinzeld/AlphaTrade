from dotenv import load_dotenv
import os

load_dotenv()

ALPACA_KEY      = os.getenv("ALPACA_KEY")
ALPACA_SECRET   = os.getenv("ALPACA_SECRET")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
IS_PAPER        = os.getenv("IS_PAPER", "True") == "True"

# tickers you want scanned every morning
WATCHLIST = ["AAPL", "TSLA", "NVDA", "SPY", "AMD"]

TIMEFRAME                = "1h"
CHECK_INTERVAL_SECONDS   = 300

# strategy thresholds
RSI_OVERSOLD    = 35
RSI_OVERBOUGHT  = 65
EMA_FAST        = 9
EMA_SLOW        = 21
EMA_TREND       = 200

# options config
OPTION_MIN_VOLUME       = 100     # ignore options with low volume
OPTION_MIN_OI           = 200     # open interest minimum
OPTION_MAX_EXPIRY_DAYS  = 14      # only look at options expiring within 14 days

_required = {
    "ALPACA_KEY":      ALPACA_KEY,
    "ALPACA_SECRET":   ALPACA_SECRET,
    "DISCORD_WEBHOOK": DISCORD_WEBHOOK,
}
for name, val in _required.items():
    if not val:
        raise EnvironmentError(f"Missing required env variable: {name}")