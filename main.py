import time
import config
from agents.data_fetcher import get_candles
from agents.analyzer     import analyze
from agents.strategy     import check_setup
from agents.signal_filter import is_new_signal
from agents.notifier     import send_alert

def run():
    for ticker in config.WATCHLIST:
        try:
            df     = get_candles(ticker)
            data   = analyze(df)
            setup  = check_setup(data)

            if setup and is_new_signal(ticker, setup["action"]):
                send_alert(ticker, setup["action"], data["price"], setup["reason"])
                print(f"[ALERT] {ticker} → {setup['action']}")
            else:
                print(f"[OK] {ticker} — no setup")

        except Exception as e:
            print(f"[ERROR] {ticker}: {e}")

if __name__ == "__main__":
    print("Bot running...")
    while True:
        run()
        time.sleep(config.CHECK_INTERVAL_SECONDS)