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

