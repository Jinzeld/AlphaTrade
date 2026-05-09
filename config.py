from dotenv import load_dotenv
import os

load_dotenv()

# ── Credentials ───────────────────────────────────────────────────────────
ALPACA_KEY            = os.getenv("ALPACA_KEY")
ALPACA_SECRET         = os.getenv("ALPACA_SECRET")
DISCORD_WEBHOOK       = os.getenv("DISCORD_WEBHOOK")
DISCORD_TOKEN         = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL       = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
DISCORD_NEWS_CHANNEL  = int(os.getenv("DISCORD_NEWS_CHANNEL_ID", "0"))
FINNHUB_KEY           = os.getenv("FINNHUB_KEY")
NVIDIA_NIM_KEY        = os.getenv("NVIDIA_NIM_KEY")
NVIDIA_NIM_MODEL      = os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.1-70b-instruct")
NVIDIA_NIM_URL        = "https://integrate.api.nvidia.com/v1"
IS_PAPER              = os.getenv("IS_PAPER", "True") == "True"

# ── Option trade channels ─────────────────────────────────────────────────
DISCORD_0DTE_CHANNEL     = int(os.getenv("DISCORD_0DTE_CHANNEL_ID", "0"))
DISCORD_SWING_CHANNEL    = int(os.getenv("DISCORD_SWING_CHANNEL_ID", "0"))
DISCORD_SETTINGS_CHANNEL = int(os.getenv("DISCORD_SETTINGS_CHANNEL_ID", "0"))

# ── Scan schedule ─────────────────────────────────────────────────────────────
SCAN_INTERVAL_MINUTES = 10       # rescan every 10 minutes
MARKET_OPEN_HOUR      = 6        # 6:30am PST (NYSE opens 9:30am EST = 6:30am PST)
MARKET_OPEN_MINUTE    = 30
MARKET_CLOSE_HOUR     = 13       # 1:00pm PST (NYSE closes 4:00pm EST = 1:00pm PST)
MARKET_CLOSE_MINUTE   = 0

# ── Strategy thresholds ───────────────────────────────────────────────────
RSI_OVERSOLD          = 35
RSI_OVERBOUGHT        = 65
EMA_FAST              = 9
EMA_SLOW              = 21
EMA_TREND             = 200

# ── Options config ────────────────────────────────────────────────────────
OPTION_MIN_VOLUME     = 100
OPTION_MIN_OI         = 200
OPTION_0DTE_DAYS      = 1
OPTION_SWING_DAYS     = 21

# ── News config ───────────────────────────────────────────────────────────
NEWS_MAX_ARTICLES     = 5
NEWS_MAX_GENERAL      = 8

# ── Risk weights ──────────────────────────────────────────────────────────
RISK_WEIGHTS = {
    "rsi_extreme":      2,
    "no_trend_confirm": 2,
    "low_volume":       2,
    "high_iv":          2,
    "0dte":             2,
}

# ── Required env check ────────────────────────────────────────────────────
_required = {
    "ALPACA_KEY":      ALPACA_KEY,
    "ALPACA_SECRET":   ALPACA_SECRET,
    "DISCORD_TOKEN":   DISCORD_TOKEN,
    "FINNHUB_KEY":     FINNHUB_KEY,
    "NVIDIA_NIM_KEY":  NVIDIA_NIM_KEY,
}
for name, val in _required.items():
    if not val:
        raise EnvironmentError(f"[CONFIG] Missing required env variable: {name}")