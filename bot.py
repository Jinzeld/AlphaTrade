import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import config
from utils.logger import logger
from agents.data_fetcher      import get_candles
from agents.analyzer          import analyze
from agents.strategy          import check_setup
from agents.options_scanner   import get_best_option
from agents.risk_scorer       import calculate_risk
from agents.notifier          import send_alert
from agents.news_fetcher      import get_ticker_news
from agents.news_conviction   import analyze_news_conviction
from agents.ai_analyst        import analyze_trade
from agents.signal_filter     import is_new_signal, clear_signals
from agents.watchlist_manager import load_watchlists, save_watchlists, clear_watchlists
from agents.longterm_notifier import run_longterm_scan

# ── Shared state — loaded from disk on startup ─────────────────────────────
watchlist_0dte,  watchlist_swing = load_watchlists()
scanning_paused: bool = False

# ── Bot setup ──────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def is_settings_channel(interaction: discord.Interaction) -> bool:
    return interaction.channel_id == config.DISCORD_SETTINGS_CHANNEL


async def wrong_channel_reply(interaction: discord.Interaction):
    await interaction.response.send_message(
        f"⚙️ Please use <#{config.DISCORD_SETTINGS_CHANNEL}> to manage the bot.",
        ephemeral=True
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Core scan
# ══════════════════════════════════════════════════════════════════════════════

async def run_scan_for_ticker(
    ticker:      str,
    trade_type:  str,
    log_channel: discord.TextChannel | None = None,
):
    ticker = ticker.upper()

    out_channel = bot.get_channel(
        config.DISCORD_0DTE_CHANNEL if trade_type == "0dte" else config.DISCORD_SWING_CHANNEL
    )
    if out_channel is None:
        logger.error(f"[BOT] Output channel not found for {trade_type}")
        return

    status_ch = log_channel or out_channel
    await status_ch.send(f"🔍 Scanning **{ticker}** for `{trade_type.upper()}` setup...")
    loop = asyncio.get_event_loop()

    df       = await loop.run_in_executor(None, lambda: get_candles(ticker))
    analysis = await loop.run_in_executor(None, lambda: analyze(df))
    setup    = await loop.run_in_executor(None, lambda: check_setup(analysis))

    if setup is None:
        await status_ch.send(
            f"📭 **{ticker}** — No qualifying setup found.\n"
            f"> RSI: `{analysis['rsi'] if analysis else 'N/A'}` | "
            f"Trend: `{analysis['trend'] if analysis else 'N/A'}`"
        )
        return

    await status_ch.send(f"📰 Fetching & analyzing news for **{ticker}**...")
    news = await loop.run_in_executor(None, lambda: get_ticker_news(ticker))

    news_conviction = await loop.run_in_executor(
        None, lambda: analyze_news_conviction(ticker, news, setup, analysis, trade_type)
    )

    option = await loop.run_in_executor(
        None, lambda: get_best_option(ticker, setup["option_type"], trade_type)
    )

    risk = calculate_risk(analysis, setup, option, trade_type, news_conviction)

    await status_ch.send(f"🤖 Building AI analysis for **{ticker}**...")
    ai_analysis = await loop.run_in_executor(
        None, lambda: analyze_trade(ticker, analysis, setup, option, risk, trade_type, news)
    )

    send_alert(ticker, setup, analysis, option, risk, trade_type, ai_analysis, news_conviction)
    await status_ch.send(f"✅ Signal posted to <#{out_channel.id}> for **{ticker}**")


async def run_full_scan(trade_type: str, log_channel: discord.TextChannel):
    watchlist = watchlist_0dte if trade_type == "0dte" else watchlist_swing

    if not watchlist:
        await log_channel.send(
            f"⚠️ No tickers in `{trade_type.upper()}` watchlist.\n"
            f"Add some with `/add-0dte AAPL` or `/add-swing AAPL`"
        )
        return

    out_id = config.DISCORD_0DTE_CHANNEL if trade_type == "0dte" else config.DISCORD_SWING_CHANNEL
    await log_channel.send(
        f"🌅 **Scanning {len(watchlist)} tickers for `{trade_type.upper()}`** → "
        f"results in <#{out_id}>\n"
        f"Tickers: `{'`, `'.join(sorted(watchlist))}`"
    )

    for ticker in sorted(watchlist):
        await run_scan_for_ticker(ticker, trade_type, log_channel)
        await asyncio.sleep(1)

    await log_channel.send(f"✅ `{trade_type.upper()}` scan complete.")
    
@tree.command(name="set-market-cap", description="Set minimum market cap filter for long-term scan")
@app_commands.choices(size=[
    app_commands.Choice(name="Small", value="Small"),
    app_commands.Choice(name="Mid",   value="Mid"),
    app_commands.Choice(name="Large", value="Large"),
    app_commands.Choice(name="Mega",  value="Mega"),
])
async def set_market_cap(interaction: discord.Interaction, size: str):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    config.FINVIZ_MIN_MARKET_CAP = size
    await interaction.response.send_message(
        f"✅ Long-term scan market cap set to **{size} Cap**.\n"
        f"Applies automatically at next 7:00am scan."
    )
# ══════════════════════════════════════════════════════════════════════════════
#  Settings panel
# ══════════════════════════════════════════════════════════════════════════════

async def post_settings_panel():
    channel = bot.get_channel(config.DISCORD_SETTINGS_CHANNEL)
    if channel is None:
        return

    dte_tickers   = ", ".join(sorted(watchlist_0dte))  or "None"
    swing_tickers = ", ".join(sorted(watchlist_swing)) or "None"

    await channel.send(
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚙️  **TRADING BOT — SETTINGS PANEL**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**📋 Watchlists** *(saved automatically)*\n"
        f"  ⚡ 0DTE:   `{dte_tickers}`\n"
        f"  📅 Swing:  `{swing_tickers}`\n\n"
        "**⏰ Auto Schedule**\n"
        "  • 6:15am PST — News digest → `#daily-news`\n"
        "  • 6:30am PST — First scan → `#0dte-trades` & `#swing-trades`\n"
        f"  • Every {config.SCAN_INTERVAL_MINUTES}min — Rescan until 1:00pm PST\n"
        "  • 1:00pm PST — Market close\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "**🛠️ Commands** *(use in this channel only)*\n\n"
        "`/add-0dte TICKER`        — Add to 0DTE watchlist\n"
        "`/add-swing TICKER`       — Add to Swing watchlist\n"
        "`/remove-0dte TICKER`     — Remove from 0DTE watchlist\n"
        "`/remove-swing TICKER`    — Remove from Swing watchlist\n"
        "`/watchlist`              — Show both watchlists\n\n"
        "`/scan-0dte TICKER`       — Scan one ticker for 0DTE now\n"
        "`/scan-swing TICKER`      — Scan one ticker for Swing now\n"
        "`/scanall-0dte`           — Scan full 0DTE watchlist now\n"
        "`/scanall-swing`          — Scan full Swing watchlist now\n\n"
        "`/news`                   — Pull latest news now\n"
        "`/pause`                  — Pause all recurring scans\n"
        "`/resume`                 — Resume recurring scans\n"
        "`/reset`                  — Reset bot (keeps watchlist by default)\n"
        "`/set-scan-interval N`    — Change scan frequency (minutes)\n"
        "`/set-news-interval N`    — Change news check frequency\n"
        "`/panel`                  — Show this panel again\n"
        "`/status`                 — Show bot health\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Watchlist commands
# ══════════════════════════════════════════════════════════════════════════════

@tree.command(name="add-0dte", description="Add a ticker to the 0DTE watchlist")
@app_commands.describe(ticker="e.g. AAPL, TSLA, NVDA, SPY")
async def add_0dte(interaction: discord.Interaction, ticker: str):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    ticker = ticker.upper().strip()
    watchlist_0dte.add(ticker)
    save_watchlists(watchlist_0dte, watchlist_swing)
    await interaction.response.send_message(
        f"⚡ **{ticker}** added to `0DTE` watchlist and saved.\n"
        f"Current 0DTE: `{'`, `'.join(sorted(watchlist_0dte))}`"
    )


@tree.command(name="add-swing", description="Add a ticker to the Swing watchlist")
@app_commands.describe(ticker="e.g. AAPL, TSLA, NVDA, SPY")
async def add_swing(interaction: discord.Interaction, ticker: str):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    ticker = ticker.upper().strip()
    watchlist_swing.add(ticker)
    save_watchlists(watchlist_0dte, watchlist_swing)
    await interaction.response.send_message(
        f"📅 **{ticker}** added to `Swing` watchlist and saved.\n"
        f"Current Swing: `{'`, `'.join(sorted(watchlist_swing))}`"
    )


@tree.command(name="remove-0dte", description="Remove a ticker from the 0DTE watchlist")
@app_commands.describe(ticker="Ticker to remove")
async def remove_0dte(interaction: discord.Interaction, ticker: str):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    ticker = ticker.upper().strip()
    if ticker in watchlist_0dte:
        watchlist_0dte.remove(ticker)
        save_watchlists(watchlist_0dte, watchlist_swing)
        await interaction.response.send_message(
            f"🗑️ **{ticker}** removed from `0DTE` watchlist and saved."
        )
    else:
        await interaction.response.send_message(
            f"❓ **{ticker}** is not in the 0DTE watchlist.", ephemeral=True
        )


@tree.command(name="remove-swing", description="Remove a ticker from the Swing watchlist")
@app_commands.describe(ticker="Ticker to remove")
async def remove_swing(interaction: discord.Interaction, ticker: str):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    ticker = ticker.upper().strip()
    if ticker in watchlist_swing:
        watchlist_swing.remove(ticker)
        save_watchlists(watchlist_0dte, watchlist_swing)
        await interaction.response.send_message(
            f"🗑️ **{ticker}** removed from `Swing` watchlist and saved."
        )
    else:
        await interaction.response.send_message(
            f"❓ **{ticker}** is not in the Swing watchlist.", ephemeral=True
        )


@tree.command(name="watchlist", description="Show both watchlists")
async def show_watchlist(interaction: discord.Interaction):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    dte   = ", ".join(sorted(watchlist_0dte))  or "Empty"
    swing = ", ".join(sorted(watchlist_swing)) or "Empty"
    await interaction.response.send_message(
        f"**📋 Current Watchlists** *(auto-saved)*\n"
        f"  ⚡ 0DTE:  `{dte}`\n"
        f"  📅 Swing: `{swing}`"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Scan commands
# ══════════════════════════════════════════════════════════════════════════════

@tree.command(name="scan-0dte", description="Scan one ticker for 0DTE now")
@app_commands.describe(ticker="Ticker to scan")
async def scan_0dte(interaction: discord.Interaction, ticker: str):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    await interaction.response.send_message(f"⚡ Starting 0DTE scan for **{ticker.upper()}**...")
    await run_scan_for_ticker(ticker, "0dte", interaction.channel)


@tree.command(name="scan-swing", description="Scan one ticker for Swing now")
@app_commands.describe(ticker="Ticker to scan")
async def scan_swing(interaction: discord.Interaction, ticker: str):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    await interaction.response.send_message(f"📅 Starting Swing scan for **{ticker.upper()}**...")
    await run_scan_for_ticker(ticker, "swing", interaction.channel)


@tree.command(name="scanall-0dte", description="Scan full 0DTE watchlist now")
async def scanall_0dte(interaction: discord.Interaction):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    await interaction.response.send_message("⚡ Running full 0DTE scan...")
    await run_full_scan("0dte", interaction.channel)


@tree.command(name="scanall-swing", description="Scan full Swing watchlist now")
async def scanall_swing(interaction: discord.Interaction):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    await interaction.response.send_message("📅 Running full Swing scan...")
    await run_full_scan("swing", interaction.channel)


# ══════════════════════════════════════════════════════════════════════════════
#  Reset — keeps watchlist unless user explicitly wipes it
# ══════════════════════════════════════════════════════════════════════════════

@tree.command(name="reset", description="Reset the bot — choose whether to keep or clear your watchlist")
async def reset_bot(interaction: discord.Interaction):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)

    class ResetView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=30)
            self.choice = None

        @discord.ui.button(
            label="🔄 Reset bot only (keep watchlist)",
            style=discord.ButtonStyle.primary
        )
        async def reset_only(self, i: discord.Interaction, b: discord.ui.Button):
            self.choice = "signals_only"
            self.stop()
            await i.response.defer()

        @discord.ui.button(
            label="🗑️ Reset everything (clear watchlist too)",
            style=discord.ButtonStyle.danger
        )
        async def reset_all(self, i: discord.Interaction, b: discord.ui.Button):
            self.choice = "full_reset"
            self.stop()
            await i.response.defer()

        @discord.ui.button(
            label="❌ Cancel",
            style=discord.ButtonStyle.secondary
        )
        async def cancel(self, i: discord.Interaction, b: discord.ui.Button):
            self.choice = "cancel"
            self.stop()
            await i.response.send_message("Reset cancelled.", ephemeral=True)

    view = ResetView()
    await interaction.response.send_message(
        "**🔄 Reset Options**\n\n"
        "What do you want to reset?\n\n"
        "• **Reset bot only** — clears signal history so alerts can fire again, "
        "but keeps your watchlist exactly as is\n"
        "• **Reset everything** — clears signal history AND wipes both watchlists",
        view=view
    )
    await view.wait()

    if view.choice == "cancel" or view.choice is None:
        return

    channel = interaction.channel

    if view.choice == "signals_only":
        clear_signals()
        dte   = ", ".join(sorted(watchlist_0dte))  or "None"
        swing = ", ".join(sorted(watchlist_swing)) or "None"
        await channel.send(
            "🔄 **Bot reset — signal history cleared.**\n"
            "Your watchlist was kept:\n"
            f"  ⚡ 0DTE:  `{dte}`\n"
            f"  📅 Swing: `{swing}`"
        )

    elif view.choice == "full_reset":
        # second confirmation before wiping the watchlist
        class ConfirmWipe(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=20)
                self.confirmed = False

            @discord.ui.button(label="✅ Yes wipe everything", style=discord.ButtonStyle.danger)
            async def confirm(self, i: discord.Interaction, b: discord.ui.Button):
                self.confirmed = True
                self.stop()
                await i.response.defer()

            @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, i: discord.Interaction, b: discord.ui.Button):
                self.stop()
                await i.response.send_message("Cancelled.", ephemeral=True)

        confirm_view = ConfirmWipe()
        await channel.send(
            "⚠️ **Are you sure?** This will permanently delete both watchlists.",
            view=confirm_view
        )
        await confirm_view.wait()

        if confirm_view.confirmed:
            watchlist_0dte.clear()
            watchlist_swing.clear()
            clear_signals()
            clear_watchlists()
            await channel.send(
                "🗑️ **Full reset complete.**\n"
                "Both watchlists cleared and signal history wiped.\n"
                "Add tickers with `/add-0dte` or `/add-swing`"
            )
            await post_settings_panel()


# ══════════════════════════════════════════════════════════════════════════════
#  Other commands
# ══════════════════════════════════════════════════════════════════════════════

@tree.command(name="news", description="Pull latest news for all watchlist tickers now")
async def news_cmd(interaction: discord.Interaction):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    from agents.news_notifier import send_daily_news
    all_tickers = watchlist_0dte | watchlist_swing
    await interaction.response.send_message(
        f"📰 Fetching news for {len(all_tickers)} tickers..."
    )
    await send_daily_news(bot, all_tickers)


@tree.command(name="pause", description="Pause all recurring scans")
async def pause_scans(interaction: discord.Interaction):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    global scanning_paused
    scanning_paused = True
    await interaction.response.send_message(
        "⏸️ **Scanning paused.** Use `/resume` to start again."
    )


@tree.command(name="resume", description="Resume recurring scans")
async def resume_scans(interaction: discord.Interaction):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    global scanning_paused
    scanning_paused = False
    await interaction.response.send_message(
        "▶️ **Scanning resumed.**"
    )


@tree.command(name="set-scan-interval", description="Change how often the bot rescans during market hours")
@app_commands.describe(minutes="Rescan interval in minutes e.g. 5, 10, 15, 30")
async def set_scan_interval(interaction: discord.Interaction, minutes: int):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    if minutes < 5 or minutes > 60:
        await interaction.response.send_message(
            "⚠️ Must be between 5 and 60 minutes.", ephemeral=True
        )
        return
    config.SCAN_INTERVAL_MINUTES = minutes
    await interaction.response.send_message(
        f"✅ Scan interval set to every **{minutes} minutes**.\n"
        f"⚠️ Restart with `docker-compose restart` to apply."
    )


@tree.command(name="set-news-interval", description="Change how often breaking news is checked")
@app_commands.describe(minutes="Check interval in minutes e.g. 5, 10, 15")
async def set_news_interval(interaction: discord.Interaction, minutes: int):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    if minutes < 5 or minutes > 60:
        await interaction.response.send_message(
            "⚠️ Must be between 5 and 60 minutes.", ephemeral=True
        )
        return
    config.NEWS_MONITOR_INTERVAL_MINUTES = minutes
    await interaction.response.send_message(
        f"✅ News check interval set to every **{minutes} minutes**.\n"
        f"⚠️ Restart with `docker-compose restart` to apply."
    )


@tree.command(name="panel", description="Show the settings panel")
async def panel_cmd(interaction: discord.Interaction):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    await interaction.response.send_message("Refreshing panel...")
    await post_settings_panel()


@tree.command(name="status", description="Show bot health and config")
async def status_cmd(interaction: discord.Interaction):
    if not is_settings_channel(interaction):
        return await wrong_channel_reply(interaction)
    dte_ch   = bot.get_channel(config.DISCORD_0DTE_CHANNEL)
    swing_ch = bot.get_channel(config.DISCORD_SWING_CHANNEL)
    news_ch  = bot.get_channel(config.DISCORD_NEWS_CHANNEL)
    await interaction.response.send_message(
        "**🟢 Bot Status — Online**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"  ⚡ 0DTE channel:    {dte_ch.mention if dte_ch else '❌ Not found'}\n"
        f"  📅 Swing channel:   {swing_ch.mention if swing_ch else '❌ Not found'}\n"
        f"  📰 News channel:    {news_ch.mention if news_ch else '❌ Not found'}\n\n"
        f"  ⚡ 0DTE tickers:    `{', '.join(sorted(watchlist_0dte)) or 'Empty'}`\n"
        f"  📅 Swing tickers:   `{', '.join(sorted(watchlist_swing)) or 'Empty'}`\n\n"
        f"  ⏸️ Scanning paused: `{scanning_paused}`\n"
        f"  🔄 Scan interval:   every `{config.SCAN_INTERVAL_MINUTES} min`\n"
        f"  📰 News interval:   every `{config.NEWS_MONITOR_INTERVAL_MINUTES} min`\n"
        f"  🤖 NIM Model:       `{config.NVIDIA_NIM_MODEL}`\n"
        f"  💼 Alpaca mode:     `{'Paper' if config.IS_PAPER else 'LIVE'}`\n"
        f"  💾 Watchlist file:  `data/watchlist.json`"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Bot events
# ══════════════════════════════════════════════════════════════════════════════

@bot.event
async def on_ready():
    await tree.sync()
    logger.info(f"[BOT] Logged in as {bot.user}")
    print(f"✅ Bot online as {bot.user}")
    print(f"   0DTE watchlist:  {watchlist_0dte}")
    print(f"   Swing watchlist: {watchlist_swing}")
    await post_settings_panel()