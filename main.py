import asyncio
import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import config
from bot import bot, watchlist_0dte, watchlist_swing, run_full_scan
from agents.news_notifier import send_daily_news
from agents.breaking_news_monitor import check_breaking_news
from agents.longterm_notifier import run_longterm_scan
from agents.signal_filter import clear_signals
from utils.logger import logger
from datetime import datetime
import pytz

PST = pytz.timezone("America/Los_Angeles")


def _is_market_open() -> bool:
    now      = datetime.now(PST)
    open_dt  = now.replace(hour=config.MARKET_OPEN_HOUR,  minute=config.MARKET_OPEN_MINUTE,  second=0)
    close_dt = now.replace(hour=config.MARKET_CLOSE_HOUR, minute=config.MARKET_CLOSE_MINUTE, second=0)
    return open_dt <= now <= close_dt


async def scheduled_morning_scan():
    logger.info("[SCHEDULER] Morning scan triggered")
    clear_signals()
    settings_ch = bot.get_channel(config.DISCORD_SETTINGS_CHANNEL)
    if settings_ch:
        await settings_ch.send(
            "🔔 **Market is open — starting first scan of the day**\n"
            f"⏱ Rescanning every `{config.SCAN_INTERVAL_MINUTES} minutes` until 1:00pm PST"
        )
    await asyncio.gather(
        run_full_scan("0dte",  settings_ch),
        run_full_scan("swing", settings_ch),
    )


async def recurring_scan():
    from bot import scanning_paused
    if scanning_paused:
        logger.info("[SCHEDULER] Scan skipped — manually paused")
        return
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
    settings_ch = bot.get_channel(config.DISCORD_SETTINGS_CHANNEL)
    if settings_ch:
        await settings_ch.send(
            "🔕 **Market closed — scanning stopped for today.**\n"
            "Bot will resume tomorrow at 6:30am PST. 🌙"
        )
    logger.info("[SCHEDULER] Market closed")


async def scheduled_news():
    logger.info("[SCHEDULER] Morning news digest triggered")
    all_tickers = watchlist_0dte | watchlist_swing
    await send_daily_news(bot, all_tickers)


async def monitor_breaking_news():
    all_tickers = watchlist_0dte | watchlist_swing
    await check_breaking_news(bot, all_tickers)


async def scheduled_longterm_scan():
    logger.info("[SCHEDULER] Long-term scan triggered")
    await run_longterm_scan(bot)


async def run_on_startup(bot: discord.Client):
    """
    Fires once as soon as the bot is ready.
    Runs all three scans immediately without waiting for the schedule.
    """
    logger.info("[STARTUP] Running all scans immediately on startup")
    settings_ch = bot.get_channel(config.DISCORD_SETTINGS_CHANNEL)

    if settings_ch:
        await settings_ch.send(
            "🚀 **Bot just started — running all scans now...**"
        )

    # run all three at the same time
    await asyncio.gather(
       # send_daily_news(bot, watchlist_0dte | watchlist_swing),
        run_longterm_scan(bot),
    )

    # trade scans only if market is open right now
    if _is_market_open():
        clear_signals()
        await asyncio.gather(
            run_full_scan("0dte",  settings_ch),
            run_full_scan("swing", settings_ch),
        )
    else:
        if settings_ch:
            await settings_ch.send(
                "💤 Market is currently closed — trade scans will start at 6:30am PST.\n"
                "Long-term and news scans ran successfully."
            )

    logger.info("[STARTUP] All startup scans complete")


async def main():
    scheduler = AsyncIOScheduler(timezone="America/Los_Angeles")

    # 6:15am — morning news digest
    scheduler.add_job(
        scheduled_news,
        CronTrigger(day_of_week="mon-fri", hour=6, minute=15),
    )

    # 6:30am — first trade scan of the day
    scheduler.add_job(
        scheduled_morning_scan,
        CronTrigger(day_of_week="mon-fri", hour=6, minute=30),
    )

    # every 10 min — recurring trade scans
    scheduler.add_job(
        recurring_scan,
        CronTrigger(
            day_of_week="mon-fri",
            hour="6-12",
            minute=f"40-59/{config.SCAN_INTERVAL_MINUTES},0-59/{config.SCAN_INTERVAL_MINUTES}",
        ),
    )

    # 1:00pm — market close
    scheduler.add_job(
        scheduled_market_close,
        CronTrigger(day_of_week="mon-fri", hour=13, minute=0),
    )

    # 7:00am — long term scan
    scheduler.add_job(
        scheduled_longterm_scan,
        CronTrigger(day_of_week="mon-fri", hour=7, minute=0),
    )

    # every 15 min — breaking news
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

    # hook into bot's on_ready to fire startup scans
    @bot.event
    async def on_ready():
        await bot.tree.sync()
        logger.info(f"[BOT] Logged in as {bot.user}")
        print(f"✅ Bot online as {bot.user}")
        # run everything immediately
        await run_on_startup(bot)

    await bot.start(config.DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())