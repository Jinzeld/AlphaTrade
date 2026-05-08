import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import config
from bot import bot, watchlist, run_full_watchlist_scan
from agents.news_notifier import send_daily_news
from agents.signal_filter import clear_signals
from utils.logger import logger


async def scheduled_morning_scan():
    logger.info("[SCHEDULER] Morning scan triggered")
    clear_signals()
    channel = bot.get_channel(config.DISCORD_CHANNEL)
    if channel is None:
        logger.error(f"[SCHEDULER] Could not find signals channel {config.DISCORD_CHANNEL}")
        return
    await run_full_watchlist_scan(channel, trade_type="swing")


async def scheduled_news():
    logger.info("[SCHEDULER] Daily news digest triggered")
    await send_daily_news(bot, watchlist)


async def main():
    scheduler = AsyncIOScheduler(timezone="America/Los_Angeles")

    # 6:30am — trade signal scan
    scheduler.add_job(
        scheduled_morning_scan,
        trigger="cron",
        day_of_week="mon-fri",
        hour=6,
        minute=30,
    )

    # 6:15am — news digest drops 15 min BEFORE market open
    scheduler.add_job(
        scheduled_news,
        trigger="cron",
        day_of_week="mon-fri",
        hour=6,
        minute=15,
    )

    scheduler.start()
    logger.info("[SCHEDULER] Both jobs scheduled")
    await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())