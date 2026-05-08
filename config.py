from dotenv import load_dotenv
import os

load_dotenv()

# ── Credentials ───────────────────────────────────────────────────────────────
ALPACA_KEY          = os.getenv("ALPACA_KEY")
ALPACA_SECRET       = os.getenv("ALPACA_SECRET")
DISCORD_WEBHOOK     = os.getenv("DISCORD_WEBHOOK")
DISCORD_TOKEN       = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL     = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
DISCORD_NEWS_CHANNEL = int(os.getenv("DISCORD_NEWS_CHANNEL_ID", "0"))
FINNHUB_KEY         = os.getenv("FINNHUB_KEY")
IS_PAPER            = os.getenv("IS_PAPER", "True") == "True"

# ── Strategy thresholds ───────────────────────────────────────────────────────
RSI_OVERSOLD        = 35
RSI_OVERBOUGHT      = 65
EMA_FAST            = 9
EMA_SLOW            = 21
EMA_TREND           = 200

# ── Options config ────────────────────────────────────────────────────────────
OPTION_MIN_VOLUME       = 100
OPTION_MIN_OI           = 200
OPTION_0DTE_DAYS        = 1
OPTION_SWING_DAYS       = 21

# ── News config ───────────────────────────────────────────────────────────────
NEWS_MAX_ARTICLES       = 5    # how many articles per ticker
NEWS_MAX_GENERAL        = 8    # how many general market headlines

# ── Risk score weights ────────────────────────────────────────────────────────
RISK_WEIGHTS = {
    "rsi_extreme":      2,
    "no_trend_confirm": 2,
    "low_volume":       2,
    "high_iv":          2,
    "0dte":             2,
}

# ── Required env check ────────────────────────────────────────────────────────
_required = {
    "ALPACA_KEY":       ALPACA_KEY,
    "ALPACA_SECRET":    ALPACA_SECRET,
    "DISCORD_TOKEN":    DISCORD_TOKEN,
    "FINNHUB_KEY":      FINNHUB_KEY,
}
for name, val in _required.items():
    if not val:
        raise EnvironmentError(f"[CONFIG] Missing required env variable: {name}")