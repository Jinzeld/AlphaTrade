_last_signals: dict[str, str] = {}


def is_new_signal(ticker: str, action: str) -> bool:
    if _last_signals.get(ticker) == action:
        return False
    _last_signals[ticker] = action
    return True


def clear_signals():
    """Call this at the start of each morning scan to reset daily state."""
    _last_signals.clear()
