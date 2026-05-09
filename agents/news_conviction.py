from openai import OpenAI
import config
from utils.logger import logger

_client = OpenAI(
    api_key=config.NVIDIA_NIM_KEY,
    base_url=config.NVIDIA_NIM_URL,
)


def analyze_news_conviction(
    ticker:     str,
    articles:   list[dict],
    setup:      dict,
    analysis:   dict,
    trade_type: str,
) -> dict:
    """
    Feeds news articles + technical setup into NIM (Llama 3.1).
    Returns a conviction verdict and news-based risk level.

    Returns dict:
      - conviction:     STRONG BUY / WEAK BUY / NEUTRAL / WEAK SELL / STRONG SELL
      - news_risk:      LOW / MEDIUM / HIGH
      - news_risk_score: 0-10
      - summary:        2-3 sentence plain English explanation
      - key_factors:    list of bullet points NIM pulled from the news
      - sentiment_breakdown: positive/negative/neutral counts
    """

    if not articles:
        return {
            "conviction":        "NEUTRAL",
            "news_risk":         "UNKNOWN",
            "news_risk_score":   5,
            "summary":           "No news available to analyze.",
            "key_factors":       [],
            "sentiment_breakdown": {"positive": 0, "negative": 0, "neutral": 0},
        }

    # count raw sentiments
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    for a in articles:
        s = a.get("sentiment", "neutral").lower()
        if s in sentiment_counts:
            sentiment_counts[s] += 1

    # build the news block for the prompt
    news_block = "\n".join([
        f"{i+1}. [{a['sentiment'].upper()}] \"{a['headline']}\" — {a['source']} at {a['time']}"
        for i, a in enumerate(articles)
    ])

    action     = setup.get("action", "UNKNOWN")
    conviction = setup.get("conviction", "LOW")

    prompt = f"""
You are a professional financial analyst and options trader.

Your job is to analyze recent news for {ticker} and determine:
1. Whether the news SUPPORTS, CONTRADICTS, or is NEUTRAL to this technical trade setup
2. A final conviction level for the trade combining both news and technicals
3. The news-based risk level for this trade

TECHNICAL SETUP:
- Action: {action}
- Technical conviction: {conviction}
- Price: ${analysis['price']}
- RSI: {analysis['rsi']}
- Trend: {analysis['trend']}
- EMA cross: Bullish={analysis['bullish_cross']}, Bearish={analysis['bearish_cross']}
- Trade type: {trade_type.upper()}

RECENT NEWS ({len(articles)} articles):
{news_block}

SENTIMENT COUNT:
- Positive: {sentiment_counts['positive']}
- Negative: {sentiment_counts['negative']}
- Neutral:  {sentiment_counts['neutral']}

Respond ONLY in this exact JSON format with no extra text, no markdown, no code blocks:
{{
  "conviction": "STRONG BUY or WEAK BUY or NEUTRAL or WEAK SELL or STRONG SELL",
  "news_risk": "LOW or MEDIUM or HIGH",
  "news_risk_score": number between 0 and 10,
  "summary": "2-3 sentences explaining what the news means for this trade in plain English",
  "key_factors": ["factor 1", "factor 2", "factor 3"]
}}

Rules:
- If news strongly supports the technical direction → lower risk, higher conviction
- If news contradicts the technical direction → higher risk, lower conviction
- If mixed or neutral news → medium risk, keep technical conviction as-is
- For 0DTE trades, any negative news = HIGH risk automatically
- Be specific about what in the news matters for the trade
- key_factors must be exactly 3 items
"""

    try:
        response = _client.chat.completions.create(
            model=config.NVIDIA_NIM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.2,  # low temp for consistent structured output
        )

        raw = response.choices[0].message.content.strip()

        # strip any accidental markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()

        import json
        result = json.loads(raw)

        # validate required keys exist
        required = ["conviction", "news_risk", "news_risk_score", "summary", "key_factors"]
        for key in required:
            if key not in result:
                raise ValueError(f"Missing key in NIM response: {key}")

        result["sentiment_breakdown"] = sentiment_counts
        logger.info(f"[NEWS CONVICTION] {ticker} → {result['conviction']} | Risk: {result['news_risk']}")
        return result

    except Exception as e:
        logger.error(f"[NEWS CONVICTION] NIM call failed for {ticker}: {e}")
        return {
            "conviction":        "NEUTRAL",
            "news_risk":         "UNKNOWN",
            "news_risk_score":   5,
            "summary":           "AI news analysis unavailable right now.",
            "key_factors":       [],
            "sentiment_breakdown": sentiment_counts,
        }