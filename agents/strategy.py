import config
from utils.logger import logger


def check_setup(data: dict) -> dict | None:
    """
    Scores conviction based on how many conditions align.
    Returns a setup dict with action, conviction level, and reasons.

    Conviction levels:
      HIGH   — all 3 conditions met (RSI + EMA cross + 200 EMA trend)
      MEDIUM — RSI + 200 EMA trend (no fresh crossover yet)
      LOW    — only one condition met (informational only)
    """
    if data is None:
        return None

    price = data["price"]
    r     = data["rsi"]
    trend = data["trend"]

    bull_signals = []
    bear_signals = []

    # ── Bullish conditions ────────────────────────────────────────
    if r <= config.RSI_OVERSOLD:
        bull_signals.append(f"RSI oversold at {r} (buyers likely stepping in)")

    if data["bullish_cross"]:
        bull_signals.append(
            f"EMA{config.EMA_FAST} just crossed above EMA{config.EMA_SLOW} (momentum shift up)"
        )

    if trend == "BULLISH":
        bull_signals.append(
            f"Price ${price} is above 200 EMA ${data['ema_200']} — uptrend confirmed"
        )

    # ── Bearish conditions ────────────────────────────────────────
    if r >= config.RSI_OVERBOUGHT:
        bear_signals.append(f"RSI overbought at {r} (sellers likely stepping in)")

    if data["bearish_cross"]:
        bear_signals.append(
            f"EMA{config.EMA_FAST} just crossed below EMA{config.EMA_SLOW} (momentum shift down)"
        )

    if trend == "BEARISH":
        bear_signals.append(
            f"Price ${price} is below 200 EMA ${data['ema_200']} — downtrend confirmed"
        )

    # ── Determine conviction ──────────────────────────────────────
    def score_conviction(signals: list) -> str:
        if len(signals) == 3:
            return "HIGH"
        elif len(signals) == 2:
            return "MEDIUM"
        elif len(signals) == 1:
            return "LOW"
        return "NONE"

    bull_conv = score_conviction(bull_signals)
    bear_conv = score_conviction(bear_signals)

    # ignore LOW conviction setups — not strong enough to alert
    if bull_conv in ("HIGH", "MEDIUM") and bull_conv != "NONE":
        return {
            "action":      "BUY / CALL",
            "option_type": "call",
            "conviction":  bull_conv,
            "reasons":     bull_signals,
        }

    if bear_conv in ("HIGH", "MEDIUM") and bear_conv != "NONE":
        return {
            "action":      "SELL / PUT",
            "option_type": "put",
            "conviction":  bear_conv,
            "reasons":     bear_signals,
        }

    logger.info(f"[STRATEGY] No qualifying setup (bull={bull_conv}, bear={bear_conv})")
    return None
