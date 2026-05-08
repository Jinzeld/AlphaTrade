from dotenv import load_dotenv
import os

load_dotenv()

# ── Credentials ───────────────────────────────────────────────────────────────
ALPACA_KEY       = os.getenv("ALPACA_KEY")
ALPACA_SECRET    = os.getenv("ALPACA_SECRET")
DISCORD_WEBHOOK  = os.getenv("DISCORD_WEBHOOK")
DISCORD_TOKEN    = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL  = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
IS_PAPER         = os.getenv("IS_PAPER", "True") == "True"

# ── Strategy thresholds ───────────────────────────────────────────────────────
RSI_OVERSOLD     = 35
RSI_OVERBOUGHT   = 65
EMA_FAST         = 9
EMA_SLOW         = 21
EMA_TREND        = 200

# ── Options config ────────────────────────────────────────────────────────────
OPTION_MIN_VOLUME      = 100
OPTION_MIN_OI          = 200
OPTION_0DTE_DAYS       = 1     # same-day expiry
OPTION_SWING_DAYS      = 21    # up to 3 weeks out for swing

# ── Risk score weights ────────────────────────────────────────────────────────
# Each factor adds to the risk score (0 = safest, 10 = riskiest)
RISK_WEIGHTS = {
    "rsi_extreme":      2,   # RSI very extreme (below 25 or above 75)
    "no_trend_confirm": 2,   # price not clearly above/below 200 EMA
    "low_volume":       2,   # option volume below threshold
    "high_iv":          2,   # implied volatility above 60%
    "0dte":             2,   # zero DTE is inherently higher risk
}

# ── Required env check ────────────────────────────────────────────────────────
_required = {
    "ALPACA_KEY":      ALPACA_KEY,
    "ALPACA_SECRET":   ALPACA_SECRET,
    "DISCORD_TOKEN":   DISCORD_TOKEN,
}
for name, val in _required.items():
    if not val:
        raise EnvironmentError(f"[CONFIG] Missing required env variable: {name}")
