from dotenv import load_dotenv
import os

load_dotenv()

ALPACA_KEY      = os.getenv("ALPACA_KEY")
ALPACA_SECRET   = os.getenv("ALPACA_SECRET")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
BINANCE_KEY     = os.getenv("BINANCE_KEY")
IS_PAPER        = os.getenv("IS_PAPER", "True") == "True"

WATCHLIST                = ["AAPL", "TSLA", "BTC/USDT"]
TIMEFRAME                = "1h"
CHECK_INTERVAL_SECONDS   = 300

# quick sanity check so you know immediately if something is missing
_required = {
    "ALPACA_KEY":      ALPACA_KEY,
    "ALPACA_SECRET":   ALPACA_SECRET,
    "DISCORD_WEBHOOK": DISCORD_WEBHOOK,
}
for name, val in _required.items():
    if not val:
        raise EnvironmentError(f"Missing required env variable: {name}")