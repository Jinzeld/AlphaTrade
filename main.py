import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import config
from bot import bot, watchlist_0dte, watchlist_swing, run_full_scan
from agents.news_notifier import send_daily_news
from agents.breaking_news_monitor import check_breaking_news
from agents.signal_filter import clear_signals
from utils.logger import logger
from datetime import datetime
import pytz

PST = pytz.timezone("America/Los_Angeles")


def _is_market_open() -> bool:
    """Returns True if current PST time is within market hours."""
    now       = datetime.now(PST)
    open_dt   = now.replace(hour=config.MARKET_OPEN_HOUR,  minute=config.MARKET_OPEN_MINUTE,  second=0)
    close_dt  = now.replace(hour=config.MARKET_CLOSE_HOUR, minute=config.MARKET_CLOSE_MINUTE, second=0)
    return open_dt <= now <= close_dt


async def scheduled_morning_scan():
    """
    First scan of the day at 6:30am.
    Clears signal filter so everything is fresh.
    """
    logger.info("[SCHEDULER] Market open — first scan of the day")
    clear_signals()

    settings_ch = bot.get_channel(config.DISCORD_SETTINGS_CHANNEL)
    if settings_ch:
        await settings_ch.send(
            "🔔 **Market is open — starting first scan of the day**\n"
            f"⏱ Will rescan every `{config.SCAN_INTERVAL_MINUTES} minutes` until market close at 1:00pm PST"
        )

    await asyncio.gather(
        run_full_scan("0dte",  settings_ch),
        run_full_scan("swing", settings_ch),
    )


async def recurring_scan():
    """
    Runs every 10 minutes during market hours after the first scan.
    Skips if market is closed so weekend/overnight jobs do nothing.
    """
    if not _is_market_open():
        logger.info("[SCHEDULER] Recurring scan skipped — market closed")
        return

    logger.info("[SCHEDULER] Recurring scan triggered")

    settings_ch = bot.get_channel(config.DISCORD_SETTINGS_CHANNEL)
    if settings_ch:
        now = datetime.now(PST).strftime("%I:%M %p")
        await settings_ch.send(f"🔄 **Rescanning all tickers** — `{now} PST`")

    await asyncio.gather(
        run_full_scan("0dte",  settings_ch),
        run_full_scan("swing", settings_ch),
    )


async def scheduled_market_close():
    """Fires at market close — sends a summary and stops scanning."""
    settings_ch = bot.get_channel(config.DISCORD_SETTINGS_CHANNEL)
    if settings_ch:
        await settings_ch.send(
            "🔕 **Market closed — scanning stopped for today.**\n"
            "Bot will resume tomorrow at 6:30am PST. 🌙"
        )
    logger.info("[SCHEDULER] Market closed — scans paused until tomorrow")


async def scheduled_news():
    logger.info("[SCHEDULER] Morning news digest triggered")
    all_tickers = watchlist_0dte | watchlist_swing
    await send_daily_news(bot, all_tickers)


async def monitor_breaking_news():
    all_tickers = watchlist_0dte | watchlist_swing
    await check_breaking_news(bot, all_tickers)


async def main():
    scheduler = AsyncIOScheduler(timezone="America/Los_Angeles")

    # 6:15am — morning news digest
    scheduler.add_job(
        scheduled_news,
        CronTrigger(day_of_week="mon-fri", hour=6, minute=15),
    )

    # 6:30am — first scan of the day (also clears signal filter)
    scheduler.add_job(
        scheduled_morning_scan,
        CronTrigger(day_of_week="mon-fri", hour=6, minute=30),
    )

    # every 10 min from 6:40am to 12:50pm — recurring scans
    # starts at 6:40 so it doesn't overlap the 6:30 first scan
    scheduler.add_job(
        recurring_scan,
        CronTrigger(
            day_of_week="mon-fri",
            hour="6-12",
            minute=f"40-59/{config.SCAN_INTERVAL_MINUTES},0-59/{config.SCAN_INTERVAL_MINUTES}",
        ),
    )

    # 1:00pm — market close notification
    scheduler.add_job(
        scheduled_market_close,
        CronTrigger(day_of_week="mon-fri", hour=13, minute=0),
    )

    # every 15 min 6am-5pm — breaking news monitor
    scheduler.add_job(
        monitor_breaking_news,
        CronTrigger(
            day_of_week="mon-fri",
            hour="6-17",
            minute=f"*/{config.NEWS_MONITOR_INTERVAL_MINUTES}",
        ),
    )

    scheduler.start()
    logger.info("[SCHEDULER] All jobs scheduled")
    print("⏰ Schedule:")
    print("   6:15am PST  — Morning news digest")
    print("   6:30am PST  — First scan (market open)")
    print("   Every 10min — Recurring scans until 1:00pm")
    print("   Every 15min — Breaking news monitor")
    print("   1:00pm PST  — Market close notification")

    await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())