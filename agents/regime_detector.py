import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
from utils.logger import logger
import warnings
warnings.filterwarnings("ignore")

# ── Regime labels ─────────────────────────────────────────────────────────────
REGIME_BULL_TREND      = "BULL TREND"
REGIME_BEAR_TREND      = "BEAR TREND"
REGIME_RANGING         = "RANGING"
REGIME_HIGH_VOLATILITY = "HIGH VOLATILITY"
REGIME_LOW_VOLATILITY  = "LOW VOLATILITY"

# which strategies work best in each regime
REGIME_STRATEGY_MAP = {
    REGIME_BULL_TREND:      ["TREND FOLLOWING", "MOMENTUM BREAKOUT"],
    REGIME_BEAR_TREND:      ["TREND FOLLOWING", "MOMENTUM BREAKOUT"],
    REGIME_RANGING:         ["MEAN REVERSION"],
    REGIME_HIGH_VOLATILITY: [],   # no strategies — too risky
    REGIME_LOW_VOLATILITY:  ["MEAN REVERSION"],
}

# risk multiplier per regime — feeds into risk scorer
REGIME_RISK_SCORES = {
    REGIME_BULL_TREND:      -1,   # reduces risk score
    REGIME_BEAR_TREND:      +1,   # slightly higher risk
    REGIME_RANGING:         0,
    REGIME_HIGH_VOLATILITY: +3,   # dangerous for options
    REGIME_LOW_VOLATILITY:  +1,   # signals may be weak
}


def _get_vix() -> float | None:
    """Pulls current VIX level as a fear gauge."""
    try:
        vix = yf.download("^VIX", period="5d", interval="1d", progress=False)
        if isinstance(vix.columns, pd.MultiIndex):
            vix.columns = vix.columns.get_level_values(0)
        return float(vix["Close"].iloc[-1])
    except Exception as e:
        logger.warning(f"[REGIME] Could not fetch VIX: {e}")
        return None


def _get_spy_data() -> pd.DataFrame | None:
    """SPY daily data used to detect the broad market regime."""
    try:
        df = yf.download("SPY", period="1y", interval="1d", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except Exception as e:
        logger.error(f"[REGIME] Could not fetch SPY: {e}")
        return None


def _build_features(df: pd.DataFrame) -> np.ndarray:
    """
    Builds the feature matrix for HMM:
    - log returns
    - rolling 5-day volatility
    - normalized volume
    """
    close   = df["Close"].squeeze()
    volume  = df["Volume"].squeeze()

    log_returns = np.log(close / close.shift(1)).fillna(0)
    volatility  = log_returns.rolling(5).std().fillna(0)
    norm_vol    = (volume - volume.mean()) / (volume.std() + 1e-9)

    features = np.column_stack([
        log_returns.values,
        volatility.values,
        norm_vol.values,
    ])
    return features


def detect_regime(ticker_df: pd.DataFrame | None = None) -> dict:
    """
    Detects the current market regime using:
    1. HMM on SPY daily data (macro regime)
    2. VIX level (fear gauge)
    3. SPY trend vs 50/200 EMA

    Returns:
      - regime:           one of the 5 regime constants
      - vix:              current VIX level
      - regime_emoji:     visual indicator
      - allowed_strategies: list of strategies that work in this regime
      - risk_adjustment:  integer to add to risk score
      - description:      plain English explanation
      - confidence:       HIGH / MEDIUM / LOW
    """
    logger.info("[REGIME] Detecting market regime...")

    vix    = _get_vix()
    spy_df = _get_spy_data()

    # ── VIX-based override ────────────────────────────────────────
    # if VIX is extreme just call it high volatility immediately
    if vix is not None:
        if vix >= 30:
            logger.info(f"[REGIME] VIX at {vix} — HIGH VOLATILITY override")
            return _build_result(
                regime      = REGIME_HIGH_VOLATILITY,
                vix         = vix,
                confidence  = "HIGH",
                description = (
                    f"VIX is at {vix:.1f} — market fear is elevated. "
                    f"Options are expensive and moves are unpredictable. "
                    f"Avoiding most signals to protect capital."
                ),
            )
        if vix <= 13:
            logger.info(f"[REGIME] VIX at {vix} — LOW VOLATILITY")
            return _build_result(
                regime      = REGIME_LOW_VOLATILITY,
                vix         = vix,
                confidence  = "HIGH",
                description = (
                    f"VIX is at {vix:.1f} — market is extremely calm. "
                    f"Options premiums are low, small moves expected. "
                    f"Only mean reversion setups worth trading."
                ),
            )

    if spy_df is None or len(spy_df) < 200:
        logger.warning("[REGIME] Not enough SPY data — defaulting to RANGING")
        return _build_result(
            regime      = REGIME_RANGING,
            vix         = vix,
            confidence  = "LOW",
            description = "Could not determine regime — treating as ranging market.",
        )

    # ── SPY trend check ───────────────────────────────────────────
    spy_close  = spy_df["Close"].squeeze()
    ema50      = spy_close.ewm(span=50,  adjust=False).mean()
    ema200     = spy_close.ewm(span=200, adjust=False).mean()
    curr_price = float(spy_close.iloc[-1])
    curr_ema50 = float(ema50.iloc[-1])
    curr_ema200= float(ema200.iloc[-1])

    # ── HMM regime detection ──────────────────────────────────────
    try:
        features = _build_features(spy_df)
        model    = GaussianHMM(
            n_components=3,
            covariance_type="full",
            n_iter=100,
            random_state=42,
        )
        model.fit(features)
        hidden_states = model.predict(features)
        current_state = hidden_states[-1]

        # characterize each HMM state by its mean return
        state_means = {}
        for state in range(3):
            mask = hidden_states == state
            if mask.sum() > 0:
                mean_ret = float(np.log(
                    spy_close / spy_close.shift(1)
                ).fillna(0).values[mask].mean())
                state_means[state] = mean_ret

        current_mean = state_means.get(current_state, 0)

    except Exception as e:
        logger.warning(f"[REGIME] HMM failed: {e} — falling back to trend check")
        current_mean = 0

    # ── Final regime classification ───────────────────────────────
    above_ema50  = curr_price > curr_ema50
    above_ema200 = curr_price > curr_ema200
    vix_moderate = vix is not None and 13 < vix < 30

    if above_ema50 and above_ema200 and current_mean >= 0:
        regime = REGIME_BULL_TREND
        desc   = (
            f"SPY is above both 50 EMA (${curr_ema50:.2f}) and "
            f"200 EMA (${curr_ema200:.2f}). "
            f"Market is in a healthy uptrend. "
            f"{'VIX at ' + str(round(vix, 1)) + ' — calm conditions.' if vix else ''}"
        )
        confidence = "HIGH" if above_ema50 and above_ema200 else "MEDIUM"

    elif not above_ema50 and not above_ema200 and current_mean < 0:
        regime = REGIME_BEAR_TREND
        desc   = (
            f"SPY is below both 50 EMA (${curr_ema50:.2f}) and "
            f"200 EMA (${curr_ema200:.2f}). "
            f"Market is in a downtrend — favor puts and short setups. "
            f"{'VIX at ' + str(round(vix, 1)) + ' — fear elevated.' if vix else ''}"
        )
        confidence = "HIGH"

    else:
        regime = REGIME_RANGING
        desc   = (
            f"SPY is between key EMAs — no clear trend direction. "
            f"Market is chopping. Mean reversion plays only. "
            f"{'VIX at ' + str(round(vix, 1)) + '.' if vix else ''}"
        )
        confidence = "MEDIUM"

    logger.info(f"[REGIME] Detected: {regime} (VIX: {vix})")
    return _build_result(
        regime     = regime,
        vix        = vix,
        confidence = confidence,
        description= desc,
    )


def _build_result(
    regime:      str,
    vix:         float | None,
    confidence:  str,
    description: str,
) -> dict:
    emoji_map = {
        REGIME_BULL_TREND:      "🟢",
        REGIME_BEAR_TREND:      "🔴",
        REGIME_RANGING:         "🟡",
        REGIME_HIGH_VOLATILITY: "⚡",
        REGIME_LOW_VOLATILITY:  "😴",
    }
    return {
        "regime":               regime,
        "vix":                  round(vix, 1) if vix else None,
        "regime_emoji":         emoji_map.get(regime, "⚪"),
        "allowed_strategies":   REGIME_STRATEGY_MAP.get(regime, []),
        "risk_adjustment":      REGIME_RISK_SCORES.get(regime, 0),
        "description":          description,
        "confidence":           confidence,
    }