"""
Short-horizon forecasting for simulation metrics.

This is deliberately NOT reinforcement learning -- RL (the agents package)
answers "what should I do next"; this answers "where is this number
headed". For a handful of rounds ahead on a smooth-ish bounded metric
(0-100 stability/tension scores), a lightweight linear-trend projection
with an exponential-smoothing blend is a much better fit than a heavy
model: it's instant to compute every poll cycle (no training step, no
GPU, no framework dependency beyond numpy which is already a
requirement), and its uncertainty band is honest about how little data
justifies a longer-range prediction. If richer accuracy is ever needed
this is the seam to swap in statsmodels/ARIMA or a small torch LSTM
without touching the API contract.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence

import numpy as np

# Metrics the dashboard cares about forecasting. Keep this list in sync
# with what the frontend's ForecastPanel renders.
FORECAST_METRICS: List[str] = [
    'economic_stability',
    'strategic_tension',
    'technology_independence',
    'public_sentiment',
]


def _linear_forecast(values: Sequence[float], horizon: int) -> Dict[str, Any]:
    """Fit y = a*x + b by least squares over the recent window and project
    `horizon` steps forward, clamped to the metric's natural 0-100 range
    (public_sentiment is roughly -1..1 and is clamped by the caller instead).
    Returns predicted points plus a residual-based confidence band that
    widens with distance into the future.
    """
    n = len(values)
    if n < 2:
        last = values[-1] if values else 50.0
        return {
            'predicted': [round(last, 2)] * horizon,
            'lower': [round(last, 2)] * horizon,
            'upper': [round(last, 2)] * horizon,
            'trend': 'flat',
            'slope_per_round': 0.0,
        }

    x = np.arange(n, dtype=float)
    y = np.asarray(values, dtype=float)
    slope, intercept = np.polyfit(x, y, 1)

    fitted = slope * x + intercept
    residual_std = float(np.std(y - fitted)) if n > 2 else max(1.0, float(np.std(y)) * 0.5)
    residual_std = max(residual_std, 0.4)  # never claim false precision

    future_x = np.arange(n, n + horizon, dtype=float)
    predicted = slope * future_x + intercept

    # Confidence band widens the further out we project -- honest about
    # compounding uncertainty rather than a constant-width band.
    widen = np.sqrt(np.arange(1, horizon + 1))
    lower = predicted - residual_std * 1.28 * widen  # ~80% band
    upper = predicted + residual_std * 1.28 * widen

    trend = 'flat'
    if slope > 0.15:
        trend = 'rising'
    elif slope < -0.15:
        trend = 'falling'

    return {
        'predicted': [round(float(v), 2) for v in predicted],
        'lower': [round(float(v), 2) for v in lower],
        'upper': [round(float(v), 2) for v in upper],
        'trend': trend,
        'slope_per_round': round(float(slope), 4),
    }


def forecast_metrics(
    history: List[Dict[str, Any]],
    horizon: int = 8,
    window: int = 30,
) -> Dict[str, Any]:
    """
    history: list of {'round': int, 'state': {...}} entries, oldest first
             (matches the shape returned by /api/state/history).
    horizon: rounds to project into the future.
    window:  how many recent rounds feed the trend fit -- recent-only so a
             regime shift (e.g. a strategy escalation) isn't dragged down
             by stale early-game data.
    """
    if not history:
        return {'available': False, 'reason': 'no_history', 'metrics': {}}

    recent = history[-window:]
    last_round = recent[-1].get('round', len(recent) - 1)

    # Prefer the fast multivariate model for realtime dashboards; retain the
    # original linear implementation as a deterministic fallback.
    multi = _multivariate_forecast(recent, horizon=horizon, window=window)
    if multi.get('available'):
        return {
            'available': True,
            'horizon': horizon,
            'window_used': len(recent),
            'last_round': last_round,
            'future_rounds': [last_round + i for i in range(1, horizon + 1)],
            'model': 'multivariate_ridge_ar',
            'metrics': multi['metrics'],
        }

    metrics: Dict[str, Any] = {}
    for key in FORECAST_METRICS:
        series = [float(h.get('state', {}).get(key, 50.0)) for h in recent]
        result = _linear_forecast(series, horizon)

        clamp_lo, clamp_hi = (-1.0, 1.0) if key == 'public_sentiment' else (0.0, 100.0)
        for field in ('predicted', 'lower', 'upper'):
            result[field] = [round(min(clamp_hi, max(clamp_lo, v)), 3) for v in result[field]]

        result['history'] = [round(v, 3) for v in series[-window:]]
        metrics[key] = result

    return {
        'available': True,
        'horizon': horizon,
        'window_used': len(recent),
        'last_round': last_round,
        'future_rounds': [last_round + i for i in range(1, horizon + 1)],
        'metrics': metrics,
    }


def _multivariate_forecast(history: List[Dict[str, Any]], horizon: int, window: int = 30) -> Dict[str, Any]:
    """Fast multivariate autoregression with ridge regularization.

    Uses lag-1 values of all dashboard metrics as predictors. It is a
    practical realtime alternative to retraining an LSTM on every poll.
    """
    keys = FORECAST_METRICS
    rows = []
    for h in history[-window:]:
        state = h.get("state", {})
        rows.append([
            float(state.get(k, 0.0) or 0.0) for k in keys
        ])
    if len(rows) < 4:
        return {"available": False, "reason": "insufficient_history"}
    X = np.asarray(rows, dtype=float)
    # Convert sentiment to a common 0..100 scale for regression.
    X[:, keys.index("public_sentiment")] = (X[:, keys.index("public_sentiment")] + 1) * 50
    if len(X) < 6:
        return {"available": False, "reason": "insufficient_history"}

    # Ridge fit: y[t] ~= b + A*y[t-1]. Avoid sklearn here for tiny realtime work.
    x0, y0 = X[:-1], X[1:]
    lam = 1.0
    design = np.column_stack([np.ones(len(x0)), x0])
    reg = np.eye(design.shape[1]); reg[0,0] = 0.0
    coef = np.linalg.solve(design.T @ design + lam * reg, design.T @ y0)
    pred = []
    cur = X[-1].copy()
    for _ in range(horizon):
        nxt = np.r_[1.0, cur] @ coef
        nxt = np.clip(nxt, 0, 100)
        pred.append(nxt)
        cur = nxt
    arr = np.asarray(pred)
    residual = y0 - design @ coef
    std = np.maximum(np.std(residual, axis=0), 0.5)
    out = {}
    for i,k in enumerate(keys):
        vals = arr[:,i]
        band = std[i] * 1.28 * np.sqrt(np.arange(1, horizon+1))
        trend = "rising" if vals[-1] > vals[0] + .15 else "falling" if vals[-1] < vals[0] - .15 else "flat"
        if k == "public_sentiment":
            vals = np.clip(vals / 50 - 1, -1, 1)
            lo = np.clip((arr[:,i] - band) / 50 - 1, -1, 1)
            hi = np.clip((arr[:,i] + band) / 50 - 1, -1, 1)
        else:
            lo, hi = np.clip(arr[:,i]-band,0,100), np.clip(arr[:,i]+band,0,100)
        out[k] = {
            "predicted":[round(float(v),3) for v in vals],
            "lower":[round(float(v),3) for v in lo],
            "upper":[round(float(v),3) for v in hi],
            "trend":trend,
            "model":"multivariate_ridge_ar"
        }
    return {"available": True, "metrics": out}
