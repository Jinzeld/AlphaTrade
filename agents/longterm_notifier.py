import discord
import asyncio
from datetime import datetime
import config
from agents.finviz_screener  import get_oversold_stocks
from agents.longterm_analyst import analyze_longterm_stock, rank_longterm_picks
from utils.logger import logger


def _risk_bar(score_label: str) -> str:
    bars = {"LOW": "███░░░░░░░", "MEDIUM": "██████░░░░", "HIGH": "██████████"}
    return bars.get(score_label, "░░░░░░░░░░")


async def run_longterm_scan(bot: discord.Client, triggered_by: str = "auto"):
    """
    triggered_by: "auto" (scheduled) or "manual" (button press)
    Only posts to #long-term-picks if STRONG BUY stocks are found.
    """
    channel = bot.get_channel(config.DISCORD_LONGTERM_CHANNEL)
    if channel is None:
        logger.error(f"[LONGTERM] Channel {config.DISCORD_LONGTERM_CHANNEL} not found")
        return

    today    = datetime.now().strftime("%A, %B %d %Y")
    loop     = asyncio.get_event_loop()
    trigger_label = "🕐 Scheduled Daily Scan" if triggered_by == "auto" else "👆 Manual Scan"

    logger.info(f"[LONGTERM] Starting scan ({triggered_by})...")

    # notify channel that scan is running (only for manual)
    if triggered_by == "manual":
        await channel.send(
            f"🔍 **Manual scan triggered** — scanning Finviz for RSI < 30 stocks..."
        )

    stocks = await loop.run_in_executor(None, get_oversold_stocks)

    if not stocks:
        logger.info("[LONGTERM] No RSI < 30 stocks found — skipping")
        if triggered_by == "manual":
            await channel.send(
                "📭 No stocks with RSI under 30 found right now. "
                "Market may not have any deeply oversold opportunities today."
            )
        return

    logger.info(f"[LONGTERM] Analyzing {len(stocks)} stocks with NIM...")

    strong_buys  = []
    all_analyzed = []

    for stock in stocks:
        analysis = await loop.run_in_executor(
            None, lambda s=stock: analyze_longterm_stock(s)
        )

        all_analyzed.append({
            "ticker":   stock["ticker"],
            "stock":    stock,
            "analysis": analysis,
        })

        if analysis["verdict"] == "STRONG BUY":
            strong_buys.append({
                "ticker":   stock["ticker"],
                "stock":    stock,
                "analysis": analysis,
            })

        await asyncio.sleep(0.5)

    if not strong_buys:
        logger.info("[LONGTERM] No STRONG BUY found — no message sent")
        if triggered_by == "manual":
            verdicts = [a["analysis"]["verdict"] for a in all_analyzed]
            summary  = ", ".join([f"{v}" for v in verdicts])
            await channel.send(
                f"📊 Scanned {len(stocks)} RSI < 30 stocks — no STRONG BUY found today.\n"
                f"Verdicts: `{summary}`"
            )
        return

    # post the header
    await channel.send(
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 **Long-Term Strong Buy Alert — {today}**\n"
        f"📊 {trigger_label}\n"
        f"Found **{len(strong_buys)} STRONG BUY** from "
        f"{len(stocks)} stocks with RSI < 30\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    # post each strong buy card
    for item in strong_buys:
        stock    = item["stock"]
        analysis = item["analysis"]

        reasons_text = "\n".join([f"  ✅ {r}" for r in analysis.get("reasons", [])])
        red_flags    = analysis.get("red_flags", [])
        flags_text   = (
            "\n".join([f"  ⚠️ {f}" for f in red_flags])
            if red_flags else "  ✅ None"
        )

        await channel.send(
            f"\n🔥 **STRONG BUY — ${stock['ticker']}** "
            f"`{analysis['confidence']} CONFIDENCE`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 {stock['company']} | {stock['sector']}\n"
            f"💰 Price:           `${stock['price']}` ({stock['change']} today)\n"
            f"📊 RSI:             `{stock['rsi']}` ← under 30\n"
            f"📈 Analyst Target:  `${analysis['target_price']}` "
            f"({analysis['upside_pct']} upside)\n"
            f"⏱️ Hold Period:     `{analysis['time_horizon']}`\n"
            f"📐 P/E:             `{stock['pe_ratio']}` | "
            f"EPS: `{stock['eps']}` | Div: `{stock['dividend']}`\n"
            f"🏦 Market Cap:      `{stock['market_cap']}`\n"
            f"📅 Earnings Date:   `{stock['earnings_date']}`\n\n"
            f"**Why it's a strong buy:**\n{reasons_text}\n\n"
            f"**Red Flags:**\n{flags_text}\n\n"
            f"**{_risk_bar(analysis['risk_level'])} {analysis['risk_level']} RISK**\n\n"
            f"> 🤖 _{analysis['summary']}_"
        )

        await asyncio.sleep(0.5)

    # portfolio summary if multiple strong buys
    if len(strong_buys) > 1:
        summary = await loop.run_in_executor(
            None, lambda: rank_longterm_picks(all_analyzed)
        )
        await channel.send(
            f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🤖 **AI Portfolio View:**\n> {summary}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    logger.info(
        f"[LONGTERM] Done — {len(strong_buys)} STRONG BUY(s) "
        f"from {len(stocks)} scanned ({triggered_by})"
    )