import requests
from utils.logger import logger
import config


def _risk_bar(score: int) -> str:
    filled = round(score)
    empty  = 10 - filled
    return f"{'█' * filled}{'░' * empty} {score}/10"


def send_alert(
    ticker:          str,
    setup:           dict,
    analysis:        dict,
    option:          dict | None,
    risk:            dict,
    trade_type:      str,
    ai_analysis:     str  = "",
    news_conviction: dict | None = None,
    regime:          dict | None = None
):
    action     = setup["action"]
    conviction = setup["conviction"]
    strategy   = setup.get("strategy", "")

    emoji_action     = "🟢" if "BUY" in action else "🔴"
    conviction_emoji = {
        "VERY HIGH": "🔥🔥",
        "HIGH":      "🔥",
        "MEDIUM":    "⚡",
        "LOW":       "💤",
    }.get(conviction, "")
    trade_label = "0DTE ⚡" if trade_type == "0dte" else "Swing 📅"

    reasons_text = "\n".join([f"  ✅ {r}" for r in setup["reasons"]])

    # ── Volume label ──────────────────────────────────────────────
    vol_surge_label = " 🚀 SURGE" if analysis.get("vol_surge") else ""

    # ── VWAP label ────────────────────────────────────────────────
    vwap_val    = analysis.get("vwap")
    vwap_text   = f"`${vwap_val}`" if vwap_val else "`N/A`"
    above_vwap  = analysis.get("above_vwap")
    vwap_arrow  = " ↑ above" if above_vwap is True else " ↓ below" if above_vwap is False else ""

    # ── 200 EMA / daily trend ─────────────────────────────────────
    ema200_val   = analysis.get("ema200")
    ema200_text  = f"`${ema200_val}`" if ema200_val else "`N/A`"
    daily_trend  = analysis.get("daily_trend", "UNKNOWN")
    trend_emoji  = "📈" if daily_trend == "BULLISH" else "📉" if daily_trend == "BEARISH" else "➡️"

    # ── MACD label ────────────────────────────────────────────────
    macd_hist   = analysis.get("macd_hist", 0)
    macd_arrow  = "↑" if macd_hist > 0 else "↓"
    macd_color  = "🟢" if macd_hist > 0 else "🔴"

    # ── regime block ─────────────────────────────────────────────
    if regime:
        regime_block = (
            f"\n{regime['regime_emoji']} **Market Regime: `{regime['regime']}`** "
            f"| VIX: `{regime['vix'] or 'N/A'}`\n"
        )
    else:
        regime_block = ""

    # ── Options block ─────────────────────────────────────────────
    if option and "error" not in option:
        itm_label = "✅ Yes" if option["in_the_money"] else "❌ No"
        opt_block = (
            f"\n**📋 Best {option['type']} — {trade_label}**\n"
            f"  • Strike:          `${option['strike']}`\n"
            f"  • Expiry:          `{option['expiry']}` ({option['days_to_exp']} days)\n"
            f"  • Ask / Bid:       `${option['ask']} / ${option['bid']}`\n"
            f"  • Last Price:      `${option['last_price']}` per contract\n"
            f"  • Volume:          `{option['volume']:,}`\n"
            f"  • Open Interest:   `{option['open_interest']:,}`\n"
            f"  • Implied Vol:     `{option['implied_vol']}`\n"
            f"  • In The Money:    {itm_label}"
        )
    else:
        err = option.get("error", "unknown") if option else "not scanned"
        opt_block = f"\n⚠️ **Options:** {err}"

    # ── News conviction block ─────────────────────────────────────
    if news_conviction and news_conviction.get("conviction") not in ("NEUTRAL", None):
        nc       = news_conviction
        sb       = nc.get("sentiment_breakdown", {})
        pos      = sb.get("positive", 0)
        neg      = sb.get("negative", 0)
        neu      = sb.get("neutral",  0)
        kf_text  = "\n".join([f"  📌 {f}" for f in nc.get("key_factors", [])])
        conv_map = {
            "STRONG BUY":  "🔥 STRONG BUY",
            "WEAK BUY":    "⚡ WEAK BUY",
            "NEUTRAL":     "⚪ NEUTRAL",
            "WEAK SELL":   "🟠 WEAK SELL",
            "STRONG SELL": "🔴 STRONG SELL",
        }
        nc_label = conv_map.get(nc["conviction"], nc["conviction"])

        news_block = (
            f"\n\n**📰 News Conviction Analysis (Llama 3.1 / NIM)**\n"
            f"  Verdict:    `{nc_label}`\n"
            f"  News Risk:  `{nc['news_risk']}` — `{_risk_bar(nc['news_risk_score'])}`\n"
            f"  Sentiment:  🟢 {pos} positive  🔴 {neg} negative  ⚪ {neu} neutral\n\n"
            f"  💬 _{nc['summary']}_\n\n"
            f"**Key News Factors:**\n{kf_text}"
        )
    else:
        news_block = "\n\n📰 **News:** No significant news signals found."

    # ── Risk block ────────────────────────────────────────────────
    risk_factors_text = (
        "\n".join([f"  ⚠️ {f}" for f in risk["factors"]])
        if risk["factors"]
        else "  ✅ No major risk flags"
    )
    risk_block = (
        f"\n\n**{risk['emoji']} Final Risk Score — {risk['label']}**\n"
        f"  `{_risk_bar(risk['score'])}`\n"
        f"{risk_factors_text}"
    )

    # ── AI analysis block ─────────────────────────────────────────
    ai_block = (
        f"\n\n**🤖 AI Trade Analysis**\n> {ai_analysis}"
    ) if ai_analysis else ""

    # ── Full message ──────────────────────────────────────────────
    message = {
        "content": (
            f"{emoji_action} **{action} SIGNAL — ${ticker}**   "
            f"{conviction_emoji} `{conviction} CONVICTION`\n"
            f"📐 Strategy: `{strategy}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Price:      `${analysis['price']}`\n"
            f"📊 RSI:        `{analysis['rsi']}`\n"
            f"{trend_emoji} Trend:     `{daily_trend}` "
            f"(200 EMA: {ema200_text})\n"
            f"🔧 EMA:        9: `{analysis['ema9']}` | "
            f"21: `{analysis['ema21']}` | "
            f"50: `{analysis['ema50']}`\n"
            f"{macd_color} MACD Hist: `{macd_hist}` {macd_arrow}\n"
            f"💧 VWAP:       {vwap_text}{vwap_arrow}\n"
            f"📊 BB Bands:   `{analysis['bb_lower']}` ← price → "
            f"`{analysis['bb_upper']}`\n"
            f"🔊 Volume:     `{int(analysis['curr_volume']):,}` "
            f"(avg `{int(analysis['avg_volume']):,}`)"
            f"{vol_surge_label}\n"
            f"📏 ATR:        `{analysis['atr']}`\n\n"
            f"**Why this setup triggered:**\n{reasons_text}"
            f"{opt_block}"
            f"{news_block}"
            f"{risk_block}"
            f"{ai_block}"
        )
    }

    # Discord has a 2000 char limit per message — split if needed
    content = message["content"]
    if len(content) <= 2000:
        try:
            r = requests.post(config.DISCORD_WEBHOOK, json={"content": content})
            if r.status_code != 204:
                logger.warning(f"[NOTIFY] Discord returned {r.status_code}")
            else:
                logger.info(f"[NOTIFY] Alert sent for {ticker}")
        except Exception as e:
            logger.error(f"[NOTIFY] Failed to send alert: {e}")
    else:
        # split into chunks at 2000 chars on newline boundaries
        chunks = []
        current = ""
        for line in content.split("\n"):
            if len(current) + len(line) + 1 > 1990:
                chunks.append(current)
                current = line + "\n"
            else:
                current += line + "\n"
        if current:
            chunks.append(current)

        for i, chunk in enumerate(chunks):
            try:
                r = requests.post(config.DISCORD_WEBHOOK, json={"content": chunk})
                if r.status_code != 204:
                    logger.warning(f"[NOTIFY] Chunk {i+1} returned {r.status_code}")
            except Exception as e:
                logger.error(f"[NOTIFY] Failed to send chunk {i+1}: {e}")