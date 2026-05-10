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


async def run_longterm_scan(bot: discord.Client):
    """
    Runs automatically every morning at 7:00am PST.
    Only posts to #long-term-picks if a STRONG BUY is found.
    No message at all if nothing qualifies — keeps the channel clean.
    """
    channel = bot.get_channel(config.DISCORD_LONGTERM_CHANNEL)
    if channel is None:
        logger.error(f"[LONGTERM] Channel {config.DISCORD_LONGTERM_CHANNEL} not found")
        return

    today = datetime.now().strftime("%A, %B %d %Y")
    loop  = asyncio.get_event_loop()

    logger.info("[LONGTERM] Starting oversold scan...")

    # step 1 — pull oversold stocks from finviz
    stocks = await loop.run_in_executor(None, get_oversold_stocks)

    if not stocks:
        logger.info("[LONGTERM] No oversold stocks found today — skipping")
        return

    logger.info(f"[LONGTERM] Analyzing {len(stocks)} stocks with NIM...")

    strong_buys = []
    all_analyzed = []

    # step 2 — analyze every stock silently in the background
    for stock in stocks:
        analysis = await loop.run_in_executor(
            None, lambda s=stock: analyze_longterm_stock(s)
        )

        all_analyzed.append({
            "ticker":   stock["ticker"],
            "stock":    stock,
            "analysis": analysis,
        })

        # collect only strong buys
        if analysis["verdict"] == "STRONG BUY":
            strong_buys.append({
                "ticker":   stock["ticker"],
                "stock":    stock,
                "analysis": analysis,
            })

        await asyncio.sleep(0.5)

    # step 3 — if nothing is a strong buy, stay silent
    if not strong_buys:
        logger.info("[LONGTERM] No STRONG BUY stocks found today — no message sent")
        return

    # step 4 — only now post to Discord since we have something worth sending
    await channel.send(
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 **Long-Term Strong Buy Alert — {today}**\n"
        f"Found **{len(strong_buys)}** STRONG BUY stock(s) "
        f"from {len(stocks)} oversold today\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    # step 5 — post each strong buy card
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
            f"📊 RSI:             `{stock['rsi']}` ← oversold\n"
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

    # step 6 — post portfolio summary only if multiple strong buys
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
        f"[LONGTERM] Done — {len(strong_buys)} STRONG BUY(s) posted "
        f"out of {len(stocks)} scanned"
    )