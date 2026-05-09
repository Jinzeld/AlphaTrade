import finnhub
import time
from datetime import datetime
import config
from utils.logger import logger

_client = finnhub.Client(api_key=config.FINNHUB_KEY)

# tracks latest article timestamp per ticker so we never re-send old news
_last_seen: dict[str, int] = {}


def _sentiment_label(score: float) -> tuple[str, str]:
    if score >= 0.15:
        return "Positive", "🟢"
    elif score <= -0.15:
        return "Negative", "🔴"
    else:
        return "Neutral", "⚪"


def get_ticker_news(ticker: str) -> list[dict]:
    """Full news fetch — used for morning digest and trade analysis."""
    try:
        today    = datetime.now().strftime("%Y-%m-%d")
        articles = _client.company_news(ticker, _from="2024-01-01", to=today)
        articles = sorted(articles, key=lambda x: x.get("datetime", 0), reverse=True)
        articles = articles[:config.NEWS_MAX_ARTICLES]

        results = []
        for a in articles:
            score        = a.get("sentiment", {}).get("score", 0) if isinstance(a.get("sentiment"), dict) else 0
            label, emoji = _sentiment_label(score)
            results.append({
                "ticker":    ticker,
                "headline":  a.get("headline", "No headline"),
                "source":    a.get("source", "Unknown"),
                "url":       a.get("url", ""),
                "sentiment": label,
                "emoji":     emoji,
                "time":      datetime.fromtimestamp(a.get("datetime", 0)).strftime("%I:%M %p"),
                "timestamp": a.get("datetime", 0),
            })
        return results
    except Exception as e:
        logger.error(f"[NEWS] Failed to fetch news for {ticker}: {e}")
        return []


def get_breaking_news(ticker: str) -> list[dict]:
    """
    Only returns articles we haven't sent before for this ticker.
    Uses _last_seen to track the latest timestamp per ticker.
    """
    try:
        today    = datetime.now().strftime("%Y-%m-%d")
        articles = _client.company_news(ticker, _from=today, to=today)
        articles = sorted(articles, key=lambda x: x.get("datetime", 0), reverse=True)

        last_ts  = _last_seen.get(ticker, 0)
        new_ones = [a for a in articles if a.get("datetime", 0) > last_ts]

        if new_ones:
            _last_seen[ticker] = max(a.get("datetime", 0) for a in new_ones)

        results = []
        for a in new_ones:
            score        = a.get("sentiment", {}).get("score", 0) if isinstance(a.get("sentiment"), dict) else 0
            label, emoji = _sentiment_label(score)
            results.append({
                "ticker":    ticker,
                "headline":  a.get("headline", "No headline"),
                "source":    a.get("source", "Unknown"),
                "url":       a.get("url", ""),
                "sentiment": label,
                "emoji":     emoji,
                "time":      datetime.fromtimestamp(a.get("datetime", 0)).strftime("%I:%M %p"),
                "timestamp": a.get("datetime", 0),
            })
        return results

    except Exception as e:
        logger.error(f"[BREAKING NEWS] Failed for {ticker}: {e}")
        return []


def get_general_market_news() -> list[dict]:
    """General market headlines — used for morning digest."""
    try:
        articles = _client.general_news("general", min_id=0)
        articles = sorted(articles, key=lambda x: x.get("datetime", 0), reverse=True)
        articles = articles[:config.NEWS_MAX_GENERAL]

        results = []
        for a in articles:
            results.append({
                "headline":  a.get("headline", "No headline"),
                "source":    a.get("source", "Unknown"),
                "url":       a.get("url", ""),
                "summary":   a.get("summary", "")[:200] + "..." if a.get("summary") else "",
                "time":      datetime.fromtimestamp(a.get("datetime", 0)).strftime("%I:%M %p"),
                "related":   ", ".join(a.get("related", "").split(",")[:3]) if a.get("related") else "",
                "timestamp": a.get("datetime", 0),
            })
            time.sleep(0.1)
        return results
    except Exception as e:
        logger.error(f"[NEWS] Failed to fetch general news: {e}")
        return []


def get_breaking_general_news(last_ts: int = 0) -> tuple[list[dict], int]:
    """
    General breaking news — only returns articles newer than last_ts.
    Returns (articles, new_last_ts)
    """
    try:
        articles = _client.general_news("general", min_id=0)
        articles = sorted(articles, key=lambda x: x.get("datetime", 0), reverse=True)
        new_ones = [a for a in articles if a.get("datetime", 0) > last_ts]

        new_ts = max((a.get("datetime", 0) for a in new_ones), default=last_ts)

        results = []
        for a in new_ones[:5]:  # cap at 5 per check so it doesn't flood
            results.append({
                "headline":  a.get("headline", "No headline"),
                "source":    a.get("source", "Unknown"),
                "url":       a.get("url", ""),
                "time":      datetime.fromtimestamp(a.get("datetime", 0)).strftime("%I:%M %p"),
                "related":   ", ".join(a.get("related", "").split(",")[:3]) if a.get("related") else "",
                "timestamp": a.get("datetime", 0),
            })
        return results, new_ts

    except Exception as e:
        logger.error(f"[BREAKING GENERAL] Failed: {e}")
        return [], last_ts