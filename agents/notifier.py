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
    news_conviction: dict | None = None,   # ← new
):
    action     = setup["action"]
    conviction = setup["conviction"]
    emoji_action     = "🟢" if "BUY" in action else "🔴"
    conviction_emoji = {"HIGH": "🔥", "MEDIUM": "⚡", "LOW": "💤"}.get(conviction, "")
    trade_label      = "0DTE ⚡" if trade_type == "0dte" else "Swing 📅"
    reasons_text     = "\n".join([f"  ✅ {r}" for r in setup["reasons"]])

    # ── Options block ──────────────────────────────────────────────
    if option and "error" not in option:
        itm_label = "✅ Yes" if option["in_the_money"] else "❌ No"
        opt_block = (
            f"\n**📋 Best {option['type']} — {trade_label}**\n"
            f"  • Strike:         `${option['strike']}`\n"
            f"  • Expiry:         `{option['expiry']}` ({option['days_to_exp']} days)\n"
            f"  • Ask / Bid:      `${option['ask']} / ${option['bid']}`\n"
            f"  • Last Price:     `${option['last_price']}` per contract\n"
            f"  • Volume:         `{option['volume']:,}`\n"
            f"  • Open Interest:  `{option['open_interest']:,}`\n"
            f"  • Implied Vol:    `{option['implied_vol']}`\n"
            f"  • In The Money:   {itm_label}"
        )
    else:
        err = option.get("error", "unknown") if option else "not scanned"
        opt_block = f"\n⚠️ **Options:** {err}"

    # ── News conviction block (new) ────────────────────────────────
    if news_conviction and news_conviction.get("conviction") != "NEUTRAL":
        nc        = news_conviction
        sb        = nc.get("sentiment_breakdown", {})
        pos       = sb.get("positive", 0)
        neg       = sb.get("negative", 0)
        neu       = sb.get("neutral", 0)
        kf_text   = "\n".join([f"  📌 {f}" for f in nc.get("key_factors", [])])
        conv_map  = {
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

    # ── Risk block ─────────────────────────────────────────────────
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

    message = {
        "content": (
            f"{emoji_action} **{action} SIGNAL — ${ticker}**   "
            f"{conviction_emoji} `{conviction} CONVICTION`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Price:     `${analysis['price']}`\n"
            f"📊 RSI:       `{analysis['rsi']}`\n"
            f"📈 Trend:     `{analysis['trend']}` (200 EMA: `${analysis['ema_200']}`)\n"
            f"🔧 EMA Cross: Fast `{analysis['ema_fast']}` | Slow `{analysis['ema_slow']}`\n\n"
            f"**Why this setup triggered:**\n{reasons_text}"
            f"{opt_block}"
            f"{news_block}"
            f"{risk_block}"
            f"{ai_block}"
        )
    }

    try:
        r = requests.post(config.DISCORD_WEBHOOK, json=message)
        if r.status_code != 204:
            logger.warning(f"[NOTIFY] Discord returned {r.status_code}")
        else:
            logger.info(f"[NOTIFY] Alert sent for {ticker}")
    except Exception as e:
        logger.error(f"[NOTIFY] Failed to send alert: {e}")