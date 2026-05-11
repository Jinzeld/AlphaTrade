import config
from utils.logger import logger


def _momentum_breakout(data: dict) -> dict | None:
    """
    Momentum breakout strategy.
    Looks for: EMA cross + MACD confirmation + volume surge + VWAP alignment
    Best for: strong trending moves, earnings reactions, news-driven spikes
    """
    bull = []
    bear = []

    # EMA 9/21 cross
    if data["bullish_cross"]:
        bull.append(f"EMA9 crossed above EMA21 — momentum shift up")
    if data["bearish_cross"]:
        bear.append(f"EMA9 crossed below EMA21 — momentum shift down")

    # MACD histogram flip
    if data["macd_bull_cross"]:
        bull.append(f"MACD histogram flipped positive — buyers taking control")
    if data["macd_bear_cross"]:
        bear.append(f"MACD histogram flipped negative — sellers taking control")

    # volume surge confirms the move
    if data["vol_surge"]:
        if bull:
            bull.append(f"Volume surge {int(data['curr_volume']):,} vs avg {int(data['avg_volume']):,} — institutional buying")
        if bear:
            bear.append(f"Volume surge {int(data['curr_volume']):,} vs avg {int(data['avg_volume']):,} — institutional selling")

    # VWAP alignment
    if data["above_vwap"] is True and bull:
        bull.append(f"Price ${data['price']} above VWAP ${data['vwap']} — bullish intraday bias")
    if data["above_vwap"] is False and bear:
        bear.append(f"Price ${data['price']} below VWAP ${data['vwap']} — bearish intraday bias")

    # need at least 2 signals
    if len(bull) >= 2:
        return {
            "strategy":    "MOMENTUM BREAKOUT",
            "action":      "BUY / CALL",
            "option_type": "call",
            "conviction":  "HIGH" if len(bull) >= 3 else "MEDIUM",
            "reasons":     bull,
        }
    if len(bear) >= 2:
        return {
            "strategy":    "MOMENTUM BREAKOUT",
            "action":      "SELL / PUT",
            "option_type": "put",
            "conviction":  "HIGH" if len(bear) >= 3 else "MEDIUM",
            "reasons":     bear,
        }
    return None


def _mean_reversion(data: dict) -> dict | None:
    """
    Mean reversion / bounce strategy.
    Looks for: RSI extremes + Bollinger Band touch + VWAP deviation
    Best for: oversold bounces, overbought fades, range-bound stocks
    """
    bull = []
    bear = []

    # RSI oversold
    if data["rsi"] <= config.RSI_OVERSOLD:
        bull.append(f"RSI oversold at {data['rsi']} — sellers exhausted")
    # RSI overbought
    if data["rsi"] >= config.RSI_OVERBOUGHT:
        bear.append(f"RSI overbought at {data['rsi']} — buyers exhausted")

    # Bollinger Band touch
    if data["near_bb_lower"]:
        bull.append(f"Price touching lower Bollinger Band ${data['bb_lower']} — mean reversion likely")
    if data["near_bb_upper"]:
        bear.append(f"Price touching upper Bollinger Band ${data['bb_upper']} — fade likely")

    # MACD divergence helps confirm
    if data["macd_hist"] > 0 and bull:
        bull.append(f"MACD histogram turning positive — reversal momentum building")
    if data["macd_hist"] < 0 and bear:
        bear.append(f"MACD histogram negative — downside momentum building")

    # need at least 2 signals
    if len(bull) >= 2:
        return {
            "strategy":    "MEAN REVERSION",
            "action":      "BUY / CALL",
            "option_type": "call",
            "conviction":  "HIGH" if len(bull) >= 3 else "MEDIUM",
            "reasons":     bull,
        }
    if len(bear) >= 2:
        return {
            "strategy":    "MEAN REVERSION",
            "action":      "SELL / PUT",
            "option_type": "put",
            "conviction":  "HIGH" if len(bear) >= 3 else "MEDIUM",
            "reasons":     bear,
        }
    return None


def _trend_following(data: dict) -> dict | None:
    """
    Trend following strategy.
    Looks for: price above/below key EMAs + daily 200 EMA trend + VWAP alignment
    Best for: strong trending days, sector momentum
    """
    bull = []
    bear = []

    price  = data["price"]
    ema9   = data["ema9"]
    ema21  = data["ema21"]
    ema50  = data["ema50"]
    trend  = data["daily_trend"]

    # price stacked above all EMAs
    if price > ema9 > ema21 > ema50:
        bull.append(f"Price stacked above EMA9 > EMA21 > EMA50 — strong uptrend")
    if price < ema9 < ema21 < ema50:
        bear.append(f"Price stacked below EMA9 < EMA21 < EMA50 — strong downtrend")

    # daily 200 EMA trend confirmation
    if trend == "BULLISH":
        bull.append(f"Daily 200 EMA trend is BULLISH — trading with the macro trend")
    if trend == "BEARISH":
        bear.append(f"Daily 200 EMA trend is BEARISH — trading with the macro trend")

    # VWAP above/below
    if data["above_vwap"] is True:
        bull.append(f"Price above VWAP ${data['vwap']} — intraday buyers in control")
    if data["above_vwap"] is False:
        bear.append(f"Price below VWAP ${data['vwap']} — intraday sellers in control")

    # RSI in healthy trend zone (not overbought/oversold)
    r = data["rsi"]
    if 50 < r < 70 and bull:
        bull.append(f"RSI at {r} — trending up with room to run")
    if 30 < r < 50 and bear:
        bear.append(f"RSI at {r} — trending down with room to fall")

    # need at least 2 signals
    if len(bull) >= 2:
        return {
            "strategy":    "TREND FOLLOWING",
            "action":      "BUY / CALL",
            "option_type": "call",
            "conviction":  "HIGH" if len(bull) >= 3 else "MEDIUM",
            "reasons":     bull,
        }
    if len(bear) >= 2:
        return {
            "strategy":    "TREND FOLLOWING",
            "action":      "SELL / PUT",
            "option_type": "put",
            "conviction":  "HIGH" if len(bear) >= 3 else "MEDIUM",
            "reasons":     bear,
        }
    return None


def check_setup(data: dict) -> dict | None:
    """
    Runs all 3 strategies. Returns the strongest signal found.
    Priority: HIGH conviction > MEDIUM conviction
    If multiple HIGH signals exist, picks the one with most reasons.
    """
    if data is None:
        return None

    results = []

    for strategy_fn in [_momentum_breakout, _mean_reversion, _trend_following]:
        result = strategy_fn(data)
        if result:
            results.append(result)

    if not results:
        logger.info(f"[STRATEGY] No setup found at ${data['price']}")
        return None

    # sort by conviction then number of reasons
    def score(r):
        conv_score = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}.get(r["conviction"], 0)
        return (conv_score, len(r["reasons"]))

    results.sort(key=score, reverse=True)
    best = results[0]

    # if multiple strategies agree on direction, boost conviction
    bull_count = sum(1 for r in results if "BUY" in r["action"])
    bear_count = sum(1 for r in results if "SELL" in r["action"])

    if bull_count >= 2 and "BUY" in best["action"]:
        best["conviction"]  = "VERY HIGH"
        other_strategies    = [r["strategy"] for r in results if "BUY" in r["action"] and r != best]
        best["reasons"].append(f"Confirmed by {', '.join(other_strategies)} strategy")

    if bear_count >= 2 and "SELL" in best["action"]:
        best["conviction"]  = "VERY HIGH"
        other_strategies    = [r["strategy"] for r in results if "SELL" in r["action"] and r != best]
        best["reasons"].append(f"Confirmed by {', '.join(other_strategies)} strategy")

    logger.info(
        f"[STRATEGY] {best['strategy']} — {best['action']} "
        f"({best['conviction']}) at ${data['price']}"
    )
    return best