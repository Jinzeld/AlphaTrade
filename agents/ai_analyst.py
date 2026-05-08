from openai import OpenAI
import config
from utils.logger import logger

_client = OpenAI(
    api_key=config.NVIDIA_NIM_KEY,
    base_url=config.NVIDIA_NIM_URL,
)


def analyze_trade(
    ticker:     str,
    analysis:   dict,
    setup:      dict,
    option:     dict | None,
    risk:       dict,
    trade_type: str,
    news:       list[dict],
) -> str:
    """
    Sends all trade data to the NIM model and gets back a
    plain-English analysis of the trade setup.
    """

    # build a news summary string
    news_lines = ""
    if news:
        news_lines = "\n".join([
            f"- [{a['sentiment']}] {a['headline']} ({a['source']})"
            for a in news[:3]
        ])
    else:
        news_lines = "No recent news available."

    # build option string
    if option and "error" not in option:
        option_text = (
            f"{option['type']} | Strike ${option['strike']} | "
            f"Expiry {option['expiry']} ({option['days_to_exp']} days) | "
            f"Price ${option['last_price']} | IV {option['implied_vol']} | "
            f"Volume {option['volume']} | OI {option['open_interest']}"
        )
    else:
        option_text = "No valid option found."

    prompt = f"""
You are a professional stock trader and technical analyst assistant.
Analyze the following trade setup and give a concise, clear assessment.
Write in plain English like you're explaining it to a smart beginner trader.
Keep your response under 200 words. Be direct and specific. Do not use bullet points.

TICKER: {ticker}
TRADE TYPE: {trade_type.upper()}
ACTION: {setup['action']}
CONVICTION: {setup['conviction']}

TECHNICAL DATA:
- Price: ${analysis['price']}
- RSI: {analysis['rsi']} (oversold <35, overbought >65)
- EMA9: {analysis['ema_fast']} | EMA21: {analysis['ema_slow']}
- 200 EMA: {analysis['ema_200']} (trend direction)
- Overall trend: {analysis['trend']}
- Bullish cross detected: {analysis['bullish_cross']}
- Bearish cross detected: {analysis['bearish_cross']}

OPTION SUGGESTION:
{option_text}

RISK SCORE: {risk['score']}/10 — {risk['label']}
RISK FACTORS: {', '.join(risk['factors']) if risk['factors'] else 'None'}

RECENT NEWS:
{news_lines}

Write your analysis now. Start with whether this is a strong or weak setup and why.
Then comment on the option. End with one sentence of caution if risk is medium or high.
"""

    try:
        response = _client.chat.completions.create(
            model=config.NVIDIA_NIM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"[AI] NIM analysis failed for {ticker}: {e}")
        return "⚠️ AI analysis unavailable right now."


def summarize_news(ticker: str, articles: list[dict]) -> str:
    """
    Asks NIM to summarize multiple news articles into one
    clean paragraph for the news digest channel.
    """
    if not articles:
        return "No news to summarize."

    headlines = "\n".join([
        f"- {a['headline']} (Sentiment: {a['sentiment']}, Source: {a['source']})"
        for a in articles
    ])

    prompt = f"""
You are a financial news analyst. Summarize the following headlines about {ticker}
into a single short paragraph (3-4 sentences max). 
Focus on what matters most for a trader watching this stock today.
Be factual, neutral, and concise. Do not add opinions or predictions beyond what the news says.

HEADLINES:
{headlines}
"""

    try:
        response = _client.chat.completions.create(
            model=config.NVIDIA_NIM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"[AI] NIM news summary failed for {ticker}: {e}")
        return "⚠️ AI summary unavailable."