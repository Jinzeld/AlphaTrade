import json
import os
from utils.logger import logger

WATCHLIST_FILE = "data/watchlist.json"


def _ensure_file():
    """Creates the data folder and file if they don't exist yet."""
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(WATCHLIST_FILE):
        with open(WATCHLIST_FILE, "w") as f:
            json.dump({"0dte": [], "swing": []}, f, indent=2)
        logger.info("[WATCHLIST] Created new watchlist.json")


def load_watchlists() -> tuple[set[str], set[str]]:
    """Loads both watchlists from disk. Returns (0dte_set, swing_set)."""
    _ensure_file()
    try:
        with open(WATCHLIST_FILE, "r") as f:
            data = json.load(f)
        dte   = set(data.get("0dte",  []))
        swing = set(data.get("swing", []))
        logger.info(f"[WATCHLIST] Loaded — 0DTE: {dte} | Swing: {swing}")
        return dte, swing
    except Exception as e:
        logger.error(f"[WATCHLIST] Failed to load: {e}")
        return set(), set()


def save_watchlists(dte: set[str], swing: set[str]):
    """Saves both watchlists to disk."""
    _ensure_file()
    try:
        with open(WATCHLIST_FILE, "w") as f:
            json.dump({
                "0dte":  sorted(list(dte)),
                "swing": sorted(list(swing)),
            }, f, indent=2)
        logger.info(f"[WATCHLIST] Saved — 0DTE: {dte} | Swing: {swing}")
    except Exception as e:
        logger.error(f"[WATCHLIST] Failed to save: {e}")


def clear_watchlists():
    """Wipes both watchlists from disk."""
    save_watchlists(set(), set())
    logger.info("[WATCHLIST] Watchlists cleared from disk")