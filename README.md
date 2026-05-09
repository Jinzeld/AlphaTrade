# 📈 AI Trading Bot

A fully automated stock & options trading signal bot powered by **NVIDIA NIM (Llama 3.1)**, **Alpaca**, **Finnhub**, and **Discord**. Scans your watchlist every 10 minutes during market hours, analyzes RSI, EMA crossovers, and the 200 EMA trend, pulls real-time news, and posts trade signals with AI analysis and risk scores directly to your Discord server.

---

## ✨ Features

- **Auto scanning** every 10 minutes from market open (6:30am PST) to close (1:00pm PST)
- **Technical analysis** — RSI oversold/overbought, EMA 9/21 crossover, 200 EMA trend direction
- **Options scanner** — finds the best call or put for 0DTE and swing trades
- **AI trade analysis** via NVIDIA NIM (Llama 3.1 70B) — plain English explanation of every setup
- **News conviction** — Finnhub news fed into NIM to confirm or contradict the technical signal
- **Risk scoring** — blended 0-10 score from technicals + news + options quality
- **Breaking news monitor** — checks for important headlines every 15 minutes during market hours
- **Persistent watchlist** — saved to disk, survives Docker restarts and bot resets
- **Separate channels** — 0DTE signals, swing signals, daily news, and settings all in their own Discord channels
- **Full Discord bot** — manage everything with slash commands from `#option-trades-settings`

---

## 🖥️ Discord Server Layout

```
Text Channels
  # general

Option Trades
  # option-trades-settings   ← manage the bot here
  # 0dte-trades              ← 0DTE signals post here
  # swing-trades             ← swing signals post here

News
  # daily-news               ← morning digest + breaking news
```

---

## 📁 Project Structure

```
trading-bot/
│
├── main.py                        # scheduler + bot entry point
├── bot.py                         # Discord bot, slash commands, watchlist UI
├── config.py                      # loads .env, all settings
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env                           # your credentials (never commit this)
├── .env.example                   # template
├── .gitignore
│
├── agents/
│   ├── data_fetcher.py            # pulls price candles (Alpaca + yfinance fallback)
│   ├── analyzer.py                # calculates RSI, EMA9, EMA21, 200 EMA
│   ├── strategy.py                # detects trade setups + conviction scoring
│   ├── options_scanner.py         # finds best call/put for 0DTE or swing
│   ├── risk_scorer.py             # blended risk score 0-10
│   ├── notifier.py                # formats and sends Discord alerts
│   ├── news_fetcher.py            # Finnhub news fetching
│   ├── news_conviction.py         # NIM analysis of news vs trade setup
│   ├── news_notifier.py           # morning digest sender
│   ├── breaking_news_monitor.py   # real-time news monitor
│   ├── ai_analyst.py              # NIM trade + news summarization
│   ├── signal_filter.py           # prevents duplicate alerts
│   └── watchlist_manager.py       # load/save watchlist to disk
│
├── utils/
│   ├── indicators.py              # EMA + RSI math
│   ├── logger.py                  # logging setup
│   └── utils.py                   # helpers
│
├── data/
│   └── watchlist.json             # persistent watchlist (auto-created)
│
└── logs/
    └── bot.log                    # saved logs
```

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/trading-bot.git
cd trading-bot
```

### 2. Set up your `.env`

```bash
cp .env.example .env
```

Fill in all values in `.env`:

```bash
# Alpaca — https://alpaca.markets (free paper trading)
ALPACA_KEY=your_alpaca_key
ALPACA_SECRET=your_alpaca_secret
IS_PAPER=True

# Discord — https://discord.com/developers/applications
DISCORD_TOKEN=your_bot_token
DISCORD_WEBHOOK=https://discord.com/api/webhooks/...
DISCORD_CHANNEL_ID=
DISCORD_NEWS_CHANNEL_ID=
DISCORD_SETTINGS_CHANNEL_ID=
DISCORD_0DTE_CHANNEL_ID=
DISCORD_SWING_CHANNEL_ID=

# Finnhub — https://finnhub.io (free tier)
FINNHUB_KEY=your_finnhub_key

# NVIDIA NIM — https://build.nvidia.com (free)
NVIDIA_NIM_KEY=nvapi-your_key
NVIDIA_NIM_MODEL=meta/llama-3.1-70b-instruct
```

### 3. Run with Docker

```bash
docker-compose up --build -d
```

View live logs:

```bash
docker-compose logs -f
```

Stop the bot:

```bash
docker-compose down
```

---

## 🔑 API Keys — Where to Get Them

| Service | Free | Link | What it's used for |
|---|---|---|---|
| Alpaca | ✅ Yes | [alpaca.markets](https://alpaca.markets) | Stock price data + paper trading |
| Finnhub | ✅ Yes | [finnhub.io](https://finnhub.io) | Real-time financial news |
| NVIDIA NIM | ✅ Yes | [build.nvidia.com](https://build.nvidia.com) | AI trade analysis (Llama 3.1) |
| Discord | ✅ Yes | [discord.com/developers](https://discord.com/developers/applications) | Bot token + webhooks |

---

## 🤖 Discord Bot Commands

All commands only work in `#option-trades-settings`.

### Watchlist
| Command | Description |
|---|---|
| `/add-0dte TICKER` | Add ticker to 0DTE watchlist |
| `/add-swing TICKER` | Add ticker to Swing watchlist |
| `/remove-0dte TICKER` | Remove from 0DTE watchlist |
| `/remove-swing TICKER` | Remove from Swing watchlist |
| `/watchlist` | Show both watchlists |

### Scanning
| Command | Description |
|---|---|
| `/scan-0dte TICKER` | Manually scan one ticker for 0DTE |
| `/scan-swing TICKER` | Manually scan one ticker for Swing |
| `/scanall-0dte` | Scan full 0DTE watchlist now |
| `/scanall-swing` | Scan full Swing watchlist now |

### Controls
| Command | Description |
|---|---|
| `/pause` | Pause all recurring scans |
| `/resume` | Resume recurring scans |
| `/reset` | Reset bot (choose to keep or clear watchlist) |
| `/news` | Pull latest news for all tickers now |
| `/set-scan-interval N` | Change scan frequency in minutes |
| `/set-news-interval N` | Change news check frequency in minutes |
| `/panel` | Show the settings panel |
| `/status` | Show bot health and current config |

---

## 📊 How a Signal Works

```
Every 10 min during market hours
         ↓
   Pull price candles (Alpaca / yfinance)
         ↓
   Calculate RSI + EMA9/21 crossover + 200 EMA trend
         ↓
   Check if setup qualifies (HIGH or MEDIUM conviction)
         ↓
   Fetch Finnhub news for that ticker
         ↓
   Feed news + technicals into NVIDIA NIM (Llama 3.1)
         ↓
   Get news conviction verdict + news risk score
         ↓
   Scan options chain for best call or put
         ↓
   Calculate blended risk score (0-10)
         ↓
   NIM writes a plain English trade explanation
         ↓
   Post full signal to #0dte-trades or #swing-trades
```

---

## 📅 Daily Schedule

| Time (PST) | Event |
|---|---|
| 6:15am | 📰 Morning news digest → `#daily-news` |
| 6:30am | 🔔 First scan of the day |
| Every 10 min | 🔄 Rescan all tickers |
| Every 15 min | 🚨 Breaking news check |
| 1:00pm | 🔕 Market closed — scanning stops |

---

## 📣 Example Discord Alert

```
🟢 BUY / CALL SIGNAL — $NVDA   🔥 HIGH CONVICTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Price:     $887.40
📊 RSI:       32.4
📈 Trend:     BULLISH (200 EMA: $801.22)
🔧 EMA Cross: Fast 881.20 | Slow 879.10

Why this setup triggered:
  ✅ RSI oversold at 32.4
  ✅ EMA9 crossed above EMA21
  ✅ Price above 200 EMA — uptrend confirmed

📋 Best CALL — Swing 📅
  • Strike:         $890.00
  • Expiry:         2026-05-23 (15 days)
  • Ask / Bid:      $4.90 / $4.70
  • Volume:         1,204
  • Open Interest:  3,841
  • Implied Vol:    38.2%

📰 News Conviction (Llama 3.1 / NIM)
  Verdict:    🔥 STRONG BUY
  News Risk:  LOW — ████░░░░░░ 4/10
  Sentiment:  🟢 3 positive  🔴 0 negative  ⚪ 1 neutral
  💬 Record earnings beat adds strong fundamental support...

🟢 Final Risk Score — LOW RISK
  ███░░░░░░░ 3/10

🤖 AI Trade Analysis
> This is one of the cleanest setups you'll see...
```

---

## ⚠️ Disclaimer

This bot is for **educational and informational purposes only**. It is not financial advice. Always do your own research before making any trades. Options trading involves significant risk and you can lose your entire investment. Start with paper trading (`IS_PAPER=True`) and never trade with money you can't afford to lose.

---

## 🛠️ Built With

- [discord.py](https://discordpy.readthedocs.io/) — Discord bot framework
- [alpaca-py](https://github.com/alpacahq/alpaca-py) — Stock data and trading API
- [yfinance](https://github.com/ranaroussi/yfinance) — Market data fallback + options chains
- [finnhub-python](https://github.com/Finnhub-Stock-API/finnhub-python) — Financial news API
- [NVIDIA NIM](https://build.nvidia.com) — Llama 3.1 70B for AI analysis
- [APScheduler](https://apscheduler.readthedocs.io/) — Job scheduling
- [Docker](https://www.docker.com/) — Containerization

---

## 📄 License

MIT License — free to use, modify, and distribute.