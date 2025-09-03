# safety_guards.py
# Consolidated guard utilities for the trading agent (Recall competition ready)

from typing import Dict, List
import time
import math

# -------------------------
# AIGuard (Hardened)
# -------------------------
class AIGuardHardened:
    def __init__(self, min_stable_pct=0.15, max_token_pct=0.45, allowed_tokens: List[str] = None, stable_symbol="USDC"):
        self.min_stable_pct = min_stable_pct
        self.max_token_pct = max_token_pct
        self.allowed_tokens = allowed_tokens or ["USDC", "WETH", "WBTC", "SOL"]
        self.stable_symbol = stable_symbol

    def sanitize_targets(self, ai_targets: Dict[str, float]) -> Dict[str, float]:
        # 1) Keep allowed & non-negative
        clean = {t: max(0.0, ai_targets.get(t, 0.0)) for t in self.allowed_tokens if ai_targets.get(t, 0.0) > 0}

        # Ensure stable token key exists
        if self.stable_symbol not in clean:
            clean[self.stable_symbol] = 0.0

        # 2) Normalize
        s = sum(clean.values())
        if s == 0.0:
            return {t: 1.0 / len(self.allowed_tokens) for t in self.allowed_tokens}
        clean = {t: v / s for t, v in clean.items()}

        # 3) Per-token cap
        for t in list(clean.keys()):
            if clean[t] > self.max_token_pct:
                clean[t] = self.max_token_pct

        # 4) Enforce min stable
        if clean[self.stable_symbol] < self.min_stable_pct:
            need = self.min_stable_pct - clean[self.stable_symbol]
            clean[self.stable_symbol] = self.min_stable_pct
            others = [t for t in clean.keys() if t != self.stable_symbol]
            if others and need > 0:
                cut_per = need / len(others)
                for t in others:
                    clean[t] = max(0.0, clean[t] - cut_per)

        # 5) Re-normalize
        s = sum(clean.values())
        if s == 0.0:
            return {t: 1.0 / len(self.allowed_tokens) for t in self.allowed_tokens}
        clean = {t: v / s for t, v in clean.items()}
        return clean

    def validate_signal(self, ai_signal: str) -> str:
        s = (ai_signal or "").strip().upper()
        return s if s in {"BUY", "SELL", "HOLD"} else "HOLD"


# -------------------------
# Turnover limiter
# -------------------------
def limit_turnover(current: Dict[str, float], proposed: Dict[str, float], max_turnover: float = 0.20) -> Dict[str, float]:
    """
    Caps the total absolute change (L1 distance / 2) between current and proposed targets.
    max_turnover=0.20 => at most 20% of portfolio weight can move per rebalance.
    """
    keys = set(current) | set(proposed)
    cur = {k: current.get(k, 0.0) for k in keys}
    prop = {k: max(0.0, proposed.get(k, 0.0)) for k in keys}
    s = sum(prop.values())
    if s == 0:
        prop = {k: 1.0 / len(keys) for k in keys}
    else:
        prop = {k: v / s for k, v in prop.items()}

    deltas = {k: prop[k] - cur[k] for k in keys}
    up_budget = max_turnover
    down_budget = max_turnover
    ups = {k: d for k, d in deltas.items() if d > 0}
    downs = {k: -d for k, d in deltas.items() if d < 0}
    up_sum = sum(ups.values())
    down_sum = sum(downs.values())
    up_scale = min(1.0, up_budget / up_sum) if up_sum > 0 else 1.0
    down_scale = min(1.0, down_budget / down_sum) if down_sum > 0 else 1.0

    final = {}
    for k in keys:
        d = deltas[k]
        if d > 0:
            d = d * up_scale
        elif d < 0:
            d = d * down_scale
        final[k] = cur[k] + d

    total = sum(max(0.0, v) for v in final.values())
    if total == 0:
        final = {k: 1.0 / len(keys) for k in keys}
    else:
        final = {k: max(0.0, v) / total for k, v in final.items()}
    return final


# -------------------------
# Execution rate limiter (cooldown + hourly cap)
# -------------------------
class ExecutionRateLimiter:
    def __init__(self, min_seconds_between_trades: int = 30, max_trades_per_hour: int = 20):
        self.min_gap = min_seconds_between_trades
        self.max_per_hour = max_trades_per_hour
        self.window = 3600
        self._last_ts = 0.0
        self._history = []  # list of timestamps

    def allow(self) -> bool:
        now = time.time()
        if now - self._last_ts < self.min_gap:
            return False
        # purge old
        self._history = [ts for ts in self._history if now - ts <= self.window]
        if len(self._history) >= self.max_per_hour:
            return False
        return True

    def notify_executed(self):
        ts = time.time()
        self._last_ts = ts
        self._history.append(ts)


# -------------------------
# Market sanity checks
# -------------------------
def is_price_fresh(last_update_ts: float, now_ts: float, max_age_sec: int = 30) -> bool:
    return (now_ts - last_update_ts) <= max_age_sec

def within_slippage(quoted_price: float, expected_price: float, max_slippage_pct: float = 0.01) -> bool:
    if expected_price <= 0:
        return False
    slip = abs(quoted_price - expected_price) / expected_price
    return slip <= max_slippage_pct


# -------------------------
# Volatility circuit breaker
# -------------------------
def realized_vol(prices: List[float]) -> float:
    if len(prices) < 10:
        return 0.0
    rets = []
    for i in range(1, len(prices)):
        if prices[i-1] <= 0 or prices[i] <= 0:
            continue
        rets.append(math.log(prices[i] / prices[i-1]))
    if not rets:
        return 0.0
    mu = sum(rets)/len(rets)
    var = sum((r - mu)**2 for r in rets)/len(rets)
    return var**0.5

def halt_for_excess_vol(prices: List[float], vol_threshold: float = 0.05) -> bool:
    return realized_vol(prices) >= vol_threshold


# -------------------------
# Unified pre-trade checklist
# -------------------------
def pre_trade_check(
    symbol: str,
    current_targets: Dict[str, float],
    ai_targets: Dict[str, float],
    price_last_update_ts: float,
    quoted_price: float,
    reference_price: float,
    recent_prices: List[float],
    rate_limiter: ExecutionRateLimiter,
    ai_guard: AIGuardHardened,
    turnover_cap: float = 0.20,
    max_price_age_sec: int = 30,
    max_slippage_pct: float = 0.01,
    vol_threshold: float = 0.05,
):
    """
    Return (ok: bool, safe_targets: dict, reason: str)
    - Sanitizes AI targets
    - Limits turnover
    - Checks price freshness, slippage, volatility, and rate limits
    """
    # 1) AI targets → sanitize
    safe_targets = ai_guard.sanitize_targets(ai_targets)

    # 2) Limit turnover
    safe_targets = limit_turnover(current_targets, safe_targets, max_turnover=turnover_cap)

    # 3) Market sanity
    now = time.time()
    if not is_price_fresh(price_last_update_ts, now, max_age_sec=max_price_age_sec):
        return False, safe_targets, "Stale price feed"

    if not within_slippage(quoted_price, reference_price, max_slippage_pct=max_slippage_pct):
        return False, safe_targets, "Excessive slippage"

    if halt_for_excess_vol(recent_prices, vol_threshold=vol_threshold):
        return False, safe_targets, "Volatility circuit breaker"

    # 4) Rate limiting
    if not rate_limiter.allow():
        return False, safe_targets, "Cooldown / hourly limit in effect"

    return True, safe_targets, "OK"
