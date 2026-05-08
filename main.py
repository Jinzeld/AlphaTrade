from apscheduler.schedulers.blocking import BlockingScheduler
import config
from agents.data_fetcher    import get_candles
from agents.analyzer        import analyze
from agents.strategy        import check_setup
from agents.signal_filter   import is_new_signal
from agents.notifier        import send_alert
from agents.options_scanner import get_best_option

def morning_scan():
    print(f"\n{'='*50}")
    print(f"🔍 Morning scan started — {len(config.WATCHLIST)} tickers")
    print(f"{'='*50}")

    for ticker in config.WATCHLIST:
        try:
            print(f"\n[SCANNING] {ticker}...")

            df       = get_candles(ticker)
            analysis = analyze(df)
            setup    = check_setup(analysis)

            if setup is None:
                print(f"  → No setup found for {ticker}")
                continue

            if not is_new_signal(ticker, setup["action"]):
                print(f"  → Duplicate signal skipped for {ticker}")
                continue

            # scan options only if setup is confirmed
            option = get_best_option(ticker, setup["option_type"])

            send_alert(ticker, setup, analysis, option)
            print(f"  ✅ Alert sent for {ticker} — {setup['action']}")

        except Exception as e:
            print(f"  ❌ Error on {ticker}: {e}")

    print(f"\n✔ Scan complete")


if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="America/Los_Angeles")

    # runs every weekday at 6:30am PST (market open)
    scheduler.add_job(
        morning_scan,
        trigger="cron",
        day_of_week="mon-fri",
        hour=6,
        minute=30
    )

    print("⏰ Scheduler running — bot will scan at 6:30am PST on weekdays")
    print(f"📋 Watching: {', '.join(config.WATCHLIST)}")

    # run once right away when you first start it so you can test it
    morning_scan()

    scheduler.start()