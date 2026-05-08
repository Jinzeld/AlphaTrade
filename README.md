# AlphaTrade
AI agent powered trade bot 


## Framework and structure layout
```
    trading-bot/
    │
    ├── main.py                  # runs everything on a schedule
    ├── config.py                # all your API keys and settings
    ├── requirements.txt
    │
    ├── agents/
    │   ├── data_fetcher.py      # pulls price data from APIs
    │   ├── analyzer.py          # calculates indicators (RSI, EMA, etc.)
    │   ├── strategy.py          # decides if a trade setup is valid
    │   ├── signal_filter.py     # stops duplicate alerts from spamming
    │   └── notifier.py          # sends the message to Discord
    │
    ├── utils/
    │   ├── indicators.py        # reusable indicator functions
    │   ├── logger.py            # logs everything so you can debug
    │   └── utils.py             # small helper functions
    │
    └── logs/
        └── bot.log              # saved logs
```
## Structure Visual Diagram

<img width="729" height="615" alt="image" src="https://github.com/user-attachments/assets/bbcacd5a-c398-4b0b-aff5-02fb4e344194" />
