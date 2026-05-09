import asyncio
import discord
from datetime import datetime, time as dtime
import pytz
import config
from agents.news_fetcher import get_breaking_news, get_breaking_general_news
from agents.ai_analyst import summarize_news
from utils.logger import logger

_general_last_ts: int = 0

PST = pytz.timezone("America/Los_Angeles")

MONITOR_START = dtime(6, 0)
MONITOR_END   = dtime(17, 0)


def _is_market_hours() -> bool:
    now = datetime.now(PST).time()
    return MONITOR_START <= now <= MONITOR_END


def _importance_filter(headline: str) -> bool:
    keywords = [
        "earnings", "beats", "misses", "guidance", "fda", "approval",
        "merger", "acquisition", "buyout", "bankruptcy", "lawsuit",
        "revenue", "profit", "loss", "forecast", "upgrade", "downgrade",
        "recall", "investigation", "sec", "fed", "rate", "inflation",
        "crash", "surge", "plunge", "rally", "halt", "delisted",
        "ceo", "resign", "fired", "appointed", "partnership", "deal",
    ]
    return any(kw in headline.lower() for kw in keywords)


async def check_breaking_news(bot: discord.Client, watchlist: set[str]):
    """
    Single pass — checks every ticker + general news for new articles.
    Called on a loop from main.py every N minutes.
    """
    global _general_last_ts

    if not _is_market_hours():
        logger.info("[MONITOR] Outside market hours, skipping news check")
        return

    channel = bot.get_channel(config.DISCORD_NEWS_CHANNEL)
    if channel is None:
        logger.error("[MONITOR] News channel not found")
        return

    loop = asyncio.get_event_loop()

    # ── General market breaking news ──────────────────────────────
    general, new_ts = await loop.run_in_executor(
        None, lambda: get_breaking_general_news(_general_last_ts)
    )
    _general_last_ts = new_ts

    for a in general:
        if not _importance_filter(a["headline"]):
            continue
        related_text = f"\n  🏷️ Related: `{a['related']}`" if a["related"] else ""
        await channel.send(
            f"🚨 **BREAKING — Market News**\n"
            f"**{a['headline'][:200]}**\n"
            f"  🕐 `{a['time']}`  |  📡 {a['source']}"
            f"{related_text}\n"
            f"  🔗 {a['url']}"
        )
        await asyncio.sleep(0.5)

    # ── Per-ticker breaking news ──────────────────────────────────
    for ticker in sorted(watchlist):
        articles = await loop.run_in_executor(
            None, lambda t=ticker: get_breaking_news(t)
        )

        important = [a for a in articles if _importance_filter(a["headline"])]

        if not important:
            continue

        if len(important) > 1:
            summary = await loop.run_in_executor(
                None, lambda t=ticker, a=important: summarize_news(t, a)
            )
        else:
            summary = None

        for a in important:
            await channel.send(
                f"{a['emoji']} **${ticker} — {a['headline'][:180]}**\n"
                f"  🕐 `{a['time']}`  |  📡 {a['source']}  |  "
                f"Sentiment: `{a['sentiment']}`\n"
                f"  🔗 {a['url']}"
            )
            await asyncio.sleep(0.3)

        if summary:
            await channel.send(
                f"  🤖 **AI Summary for ${ticker}:** {summary}"
            )

        logger.info(f"[MONITOR] Sent {len(important)} breaking articles for {ticker}")