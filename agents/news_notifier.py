import discord
import asyncio
from datetime import datetime
import config
from agents.news_fetcher import get_ticker_news, get_general_market_news
from utils.logger import logger
from agents.ai_analyst import summarize_news


def _truncate(text: str, limit: int = 100) -> str:
    return text if len(text) <= limit else text[:limit] + "..."


async def send_daily_news(bot: discord.Client, watchlist: set[str]):
    """
    Sends the full daily news digest to the news channel.
    Sections:
      1. General market headlines
      2. Per-ticker news with sentiment
    """
    channel = bot.get_channel(config.DISCORD_NEWS_CHANNEL)
    if channel is None:
        logger.error(f"[NEWS] Could not find news channel ID {config.DISCORD_NEWS_CHANNEL}")
        return

    today = datetime.now().strftime("%A, %B %d %Y")
    loop  = asyncio.get_event_loop()

    # ── Header ────────────────────────────────────────────────────
    await channel.send(
        f"📰 **Daily Market News Digest**\n"
        f"📅 {today}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    # ── Section 1: General market headlines ───────────────────────
    await channel.send("**🌍 General Market Headlines**")

    general = await loop.run_in_executor(None, get_general_market_news)

    if general:
        for a in general:
            related_text = f"  🏷️ Related: `{a['related']}`\n" if a["related"] else ""
            await channel.send(
                f"**{_truncate(a['headline'], 120)}**\n"
                f"  🕐 `{a['time']}`  |  📡 {a['source']}\n"
                f"{related_text}"
                f"  🔗 {a['url']}"
            )
            await asyncio.sleep(0.5)
    else:
        await channel.send("⚠️ Could not fetch general headlines right now.")

    # ── Section 2: Per-ticker news ────────────────────────────────
    if watchlist:
        await channel.send(
            f"\n**📊 Watchlist News** — "
            f"`{'`, `'.join(sorted(watchlist))}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

        for ticker in sorted(watchlist):
            articles = await loop.run_in_executor(None, lambda t=ticker: get_ticker_news(t))

            if not articles:
                await channel.send(f"**${ticker}** — No news found today.")
                continue
            
            # get AI summary
            summary = await loop.run_in_executor(
                None, lambda t=ticker, a=articles: summarize_news(t, a)
            )
            
            # header for this ticker
            await channel.send(f"\n**${ticker}** — {len(articles)} article(s)")

            for a in articles:
                await channel.send(
                    f"{a['emoji']} **{_truncate(a['headline'], 120)}**\n"
                    f"  🕐 `{a['time']}`  |  📡 {a['source']}  |  "
                    f"Sentiment: `{a['sentiment']}`\n"
                    f"  🔗 {a['url']}"
                )
                await asyncio.sleep(0.3)

    # ── Footer ────────────────────────────────────────────────────
    await channel.send(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ **News digest complete.** Trade signals post in <#signals> when setups trigger."
    )
    logger.info("[NEWS] Daily news digest sent")