import finnhub
import time
from datetime import datetime
import config
from utils.logger import logger

_client = finnhub.Client(api_key=config.FINNHUB_KEY)

SENTIMENT_EMOJI = {
    "positive": "🟢",
    "negative": "🔴",
    "neutral":  "⚪",
}


def _sentiment_label(score: float) -> tuple[str, str]:
    """Converts a sentiment score (-1 to 1) to a label and emoji."""
    if score >= 0.15:
        return "Positive", "🟢"
    elif score <= -0.15:
        return "Negative", "🔴"
    else:
        return "Neutral", "⚪"


def get_ticker_news(ticker: str) -> list[dict]:
    """
    Fetches latest news articles for a specific ticker.
    Returns a cleaned list of article dicts.
    """
    try:
        today     = datetime.now().strftime("%Y-%m-%d")
        articles  = _client.company_news(ticker, _from="2024-01-01", to=today)
        # sort by newest first and cap it
        articles  = sorted(articles, key=lambda x: x.get("datetime", 0), reverse=True)
        articles  = articles[:config.NEWS_MAX_ARTICLES]

        results = []
        for a in articles:
            sentiment_score = a.get("sentiment", {}).get("score", 0) if isinstance(a.get("sentiment"), dict) else 0
            label, emoji    = _sentiment_label(sentiment_score)
            results.append({
                "ticker":    ticker,
                "headline":  a.get("headline", "No headline"),
                "source":    a.get("source", "Unknown"),
                "url":       a.get("url", ""),
                "sentiment": label,
                "emoji":     emoji,
                "time":      datetime.fromtimestamp(a.get("datetime", 0)).strftime("%I:%M %p"),
            })
        return results

    except Exception as e:
        logger.error(f"[NEWS] Failed to fetch news for {ticker}: {e}")
        return []


def get_general_market_news() -> list[dict]:
    """
    Fetches top general market news headlines (not ticker-specific).
    """
    try:
        articles = _client.general_news("general", min_id=0)
        articles = sorted(articles, key=lambda x: x.get("datetime", 0), reverse=True)
        articles = articles[:config.NEWS_MAX_GENERAL]

        results = []
        for a in articles:
            results.append({
                "headline": a.get("headline", "No headline"),
                "source":   a.get("source", "Unknown"),
                "url":      a.get("url", ""),
                "summary":  a.get("summary", "")[:200] + "..." if a.get("summary") else "",
                "time":     datetime.fromtimestamp(a.get("datetime", 0)).strftime("%I:%M %p"),
                "related":  ", ".join(a.get("related", "").split(",")[:3]) if a.get("related") else "",
            })
            time.sleep(0.1)  # small delay to respect rate limits

        return results

    except Exception as e:
        logger.error(f"[NEWS] Failed to fetch general news: {e}")
        return []