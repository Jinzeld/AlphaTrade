import config
from utils.logger import logger


def calculate_risk(
    analysis:         dict,
    setup:            dict,
    option:           dict | None,
    trade_type:       str,
    news_conviction:  dict | None = None,   # ← new
) -> dict:
    score   = 0
    factors = []

    # ── RSI extremes ──────────────────────────────────────────────
    r = analysis["rsi"]
    if r < 25 or r > 75:
        score += config.RISK_WEIGHTS["rsi_extreme"]
        factors.append(f"RSI very extreme at {r} — high chance of snap reversal")

    # ── 200 EMA trend alignment ───────────────────────────────────
    trend  = analysis["trend"]
    action = setup["action"]
    if ("BUY" in action and trend != "BULLISH") or ("SELL" in action and trend != "BEARISH"):
        score += config.RISK_WEIGHTS["no_trend_confirm"]
        factors.append("Trade direction is against the 200 EMA trend — counter-trend risk")

    # ── Option quality ────────────────────────────────────────────
    if option and "error" not in option:
        if option["volume"] < config.OPTION_MIN_VOLUME:
            score += config.RISK_WEIGHTS["low_volume"]
            factors.append(f"Low option volume ({option['volume']}) — hard to exit quickly")

        iv = float(option["implied_vol"].replace("%", ""))
        if iv > 60:
            score += config.RISK_WEIGHTS["high_iv"]
            factors.append(f"High implied volatility at {option['implied_vol']} — premium is expensive")
    else:
        score += 2
        factors.append("No valid option found — position sizing risk unknown")

    # ── Trade type ────────────────────────────────────────────────
    if trade_type == "0dte":
        score += config.RISK_WEIGHTS["0dte"]
        factors.append("0DTE options decay fast — needs an immediate price move")

    # ── Conviction adjustment ─────────────────────────────────────
    conviction = setup.get("conviction", "LOW")
    if conviction == "HIGH":
        score = max(0, score - 1)
    elif conviction == "LOW":
        score = min(10, score + 2)

    # ── News risk blending (new) ──────────────────────────────────
    if news_conviction:
        news_score = news_conviction.get("news_risk_score", 5)
        news_level = news_conviction.get("news_risk", "UNKNOWN")

        # blend news risk at 40% weight into overall score
        score = round((score * 0.6) + (news_score * 0.4))

        if news_level == "HIGH":
            factors.append(f"News analysis flagged HIGH risk — news contradicts trade direction")
        elif news_level == "LOW":
            factors.append(f"News supports the trade direction — risk reduced")

        # if news conviction flips direction, warn loudly
        news_conv = news_conviction.get("conviction", "NEUTRAL")
        if "BUY" in action and "SELL" in news_conv:
            score = min(10, score + 2)
            factors.append("⚠️ NEWS CONTRADICTS SETUP — news says bearish, technicals say bullish")
        elif "SELL" in action and "BUY" in news_conv:
            score = min(10, score + 2)
            factors.append("⚠️ NEWS CONTRADICTS SETUP — news says bullish, technicals say bearish")

    score = min(10, max(0, score))

    if score <= 3:
        label, emoji = "LOW RISK",    "🟢"
    elif score <= 6:
        label, emoji = "MEDIUM RISK", "🟡"
    else:
        label, emoji = "HIGH RISK",   "🔴"

    return {
        "score":   score,
        "label":   label,
        "emoji":   emoji,
        "factors": factors,
    }