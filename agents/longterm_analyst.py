from openai import OpenAI
import config
from utils.logger import logger
import json

_client = OpenAI(
    api_key=config.NVIDIA_NIM_KEY,
    base_url=config.NVIDIA_NIM_URL,
)


def analyze_longterm_stock(stock: dict) -> dict:
    """
    Feeds full Finviz fundamentals + technicals into NIM Llama 3.1
    and gets back a structured long term investment verdict.

    Returns:
      - verdict:       STRONG BUY / BUY / HOLD / AVOID
      - confidence:    HIGH / MEDIUM / LOW
      - target_price:  AI estimated fair value
      - time_horizon:  suggested hold period
      - risk_level:    LOW / MEDIUM / HIGH
      - reasons:       list of bullet points
      - summary:       2-3 sentence plain English verdict
      - red_flags:     list of concerns if any
    """

    prompt = f"""
You are a professional long-term stock analyst and value investor.
Analyze this stock and give a clear long-term investment verdict.
Focus on whether this oversold stock is a genuine buying opportunity
or a value trap. Consider both technical and fundamental factors.

STOCK: {stock['ticker']} — {stock['company']}
SECTOR: {stock['sector']} | INDUSTRY: {stock['industry']}

TECHNICAL DATA:
- Current Price:   ${stock['price']}
- Today's Change:  {stock['change']}
- RSI(14):         {stock['rsi']}  ← flagged as oversold
- SMA20:           {stock['sma20']}
- SMA50:           {stock['sma50']}
- SMA200:          {stock['sma200']}
- Volume:          {stock['volume']}

FUNDAMENTAL DATA:
- Market Cap:      {stock['market_cap']}
- P/E Ratio:       {stock['pe_ratio']}
- EPS (TTM):       {stock['eps']}
- Revenue:         {stock['revenue']}
- ROE:             {stock['roe']}
- Debt/Equity:     {stock['debt_equity']}
- Dividend Yield:  {stock['dividend']}
- Analyst Target:  {stock['analyst_target']}
- Analyst Rating:  {stock['analyst_rec']}
- Earnings Date:   {stock['earnings_date']}

Your job:
1. Is this stock oversold for a GOOD reason (bad fundamentals) or a BAD reason (market overreaction)?
2. Does the fundamental data support a long-term buy?
3. What is the risk level?

Respond ONLY in this exact JSON format, no markdown, no extra text:
{{
  "verdict": "STRONG BUY or BUY or HOLD or AVOID",
  "confidence": "HIGH or MEDIUM or LOW",
  "target_price": "your estimated fair value as a number string e.g. 145.00",
  "upside_pct": "estimated % upside from current price e.g. +23.5%",
  "time_horizon": "suggested hold period e.g. 6-12 months",
  "risk_level": "LOW or MEDIUM or HIGH",
  "summary": "2-3 sentence plain English explanation of the verdict",
  "reasons": ["reason 1", "reason 2", "reason 3"],
  "red_flags": ["flag 1"] or []
}}
"""

    try:
        response = _client.chat.completions.create(
            model=config.NVIDIA_NIM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.2,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

        logger.info(f"[LONGTERM] {stock['ticker']} → {result['verdict']} ({result['confidence']})")
        return result

    except Exception as e:
        logger.error(f"[LONGTERM] NIM analysis failed for {stock['ticker']}: {e}")
        return {
            "verdict":      "HOLD",
            "confidence":   "LOW",
            "target_price": "N/A",
            "upside_pct":   "N/A",
            "time_horizon": "N/A",
            "risk_level":   "UNKNOWN",
            "summary":      "AI analysis unavailable right now.",
            "reasons":      [],
            "red_flags":    [],
        }


def rank_longterm_picks(analyzed_stocks: list[dict]) -> str:
    """
    After all stocks are analyzed individually, asks NIM to rank
    the top 3 picks and give an overall portfolio summary.
    """
    if not analyzed_stocks:
        return "No stocks to rank."

    stocks_summary = "\n".join([
        f"- {s['ticker']}: {s['analysis']['verdict']} | "
        f"Target ${s['analysis']['target_price']} | "
        f"Upside {s['analysis']['upside_pct']} | "
        f"Risk {s['analysis']['risk_level']}"
        for s in analyzed_stocks
        if s.get("analysis")
    ])

    prompt = f"""
You are a portfolio manager reviewing a list of oversold stocks
that have been individually analyzed for long-term investment potential.

Here are today's analyzed picks:
{stocks_summary}

Give a brief 3-4 sentence portfolio summary:
1. Which 3 are the strongest buys and why
2. What sectors look most attractive today
3. Any overall market observations based on how many stocks are oversold

Keep it direct and plain English. No bullet points. No JSON. Just a paragraph.
"""

    try:
        response = _client.chat.completions.create(
            model=config.NVIDIA_NIM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"[LONGTERM] Ranking failed: {e}")
        return "Portfolio summary unavailable."