# order_guards.py
# Per-order safety checks for execution

from dataclasses import dataclass
from typing import Optional, Tuple, Callable, Dict, Any, List
import time
import math

@dataclass
class Order:
    side: str           # "BUY" or "SELL"
    base: str           # e.g., "WETH"
    quote: str          # e.g., "USDC"
    amount: float       # base amount for BUY/SELL (or quote for BUY if your router uses quote-based)
    use_quote_amount: bool = False  # True if 'amount' is in quote units for BUY

@dataclass
class Quote:
    price: float        # expected price base/quote
    ts: float           # timestamp of quote
    venue: str          # dex/route name
    expected_slippage_pct: float    # quoted slippage expectation
    route_liquidity: float          # rough liquidity score (0-1)

@dataclass
class OrderPolicy:
    max_slippage_pct: float = 0.01          # 1%
    max_price_age_sec: int = 30
    min_notional_quote: float = 10.0        # don't trade < $10
    min_base_amount: float = 1e-8           # dust threshold
    max_price_impact_pct: float = 0.02      # 2% price impact vs reference
    split_threshold_quote: float = 2000.0   # split if order size (quote) > this
    split_parts: int = 3                    # how many pieces to split
    max_retries: int = 3
    backoff_seconds: float = 1.5
    max_consecutive_failures: int = 3

class ConsecutiveFailureBreaker:
    def __init__(self, max_consecutive_failures: int = 3, cooloff_sec: int = 60):
        self.max_fails = max_consecutive_failures
        self.cooloff_sec = cooloff_sec
        self.counter = 0
        self.block_until = 0.0

    def record(self, ok: bool):
        now = time.time()
        if now < self.block_until:
            return
        if ok:
            self.counter = 0
        else:
            self.counter += 1
            if self.counter >= self.max_fails:
                self.block_until = now + self.cooloff_sec
                self.counter = 0

    def allowed(self) -> bool:
        return time.time() >= self.block_until

def is_price_fresh(quote: Quote, policy: OrderPolicy) -> bool:
    return (time.time() - quote.ts) <= policy.max_price_age_sec

def within_slippage(quoted_price: float, exec_price: float, max_slippage_pct: float) -> bool:
    if quoted_price <= 0 or exec_price <= 0:
        return False
    slip = abs(exec_price - quoted_price) / quoted_price
    return slip <= max_slippage_pct

def within_price_impact(exec_price: float, reference_price: float, max_impact_pct: float) -> bool:
    if reference_price <= 0 or exec_price <= 0:
        return False
    impact = abs(exec_price - reference_price) / reference_price
    return impact <= max_impact_pct

def has_sufficient_balance(balance_lookup: Callable[[str], float], token: str, needed: float) -> bool:
    return balance_lookup(token) >= max(0.0, needed)

def has_allowance(allowance_lookup: Callable[[str, str], float], token: str, spender: str, needed: float) -> bool:
    return allowance_lookup(token, spender) >= max(0.0, needed)

def estimate_quote_notional(order: Order, price: float) -> float:
    # If order.amount is base and BUY/SELL in base terms
    if order.use_quote_amount:
        return order.amount
    return order.amount * price

def split_order(order: Order, parts: int) -> List[Order]:
    per = order.amount / parts
    return [Order(side=order.side, base=order.base, quote=order.quote, amount=per, use_quote_amount=order.use_quote_amount) for _ in range(parts)]

def validate_order(
    order: Order,
    quote: Quote,
    policy: OrderPolicy,
    balance_lookup: Callable[[str], float],
    allowance_lookup: Callable[[str, str], float],
    reference_price: float,
    spender: str,
) -> Tuple[bool, str, List[Order]]:
    # freshness
    if not is_price_fresh(quote, policy):
        return False, "Stale quote", []

    # min notional
    notional = estimate_quote_notional(order, quote.price)
    if notional < policy.min_notional_quote:
        return False, "Below min notional", []

    # dust
    if (not order.use_quote_amount) and order.amount < policy.min_base_amount:
        return False, "Dust amount", []

    # balance
    if order.side == "BUY":
        needed_quote = notional
        if not has_sufficient_balance(balance_lookup, order.quote, needed_quote):
            return False, "Insufficient quote balance", []
        if not has_allowance(allowance_lookup, order.quote, spender, needed_quote):
            return False, "Insufficient quote allowance", []
    else:  # SELL
        needed_base = order.amount if not order.use_quote_amount else (order.amount / quote.price)
        if not has_sufficient_balance(balance_lookup, order.base, needed_base):
            return False, "Insufficient base balance", []
        if not has_allowance(allowance_lookup, order.base, spender, needed_base):
            return False, "Insufficient base allowance", []

    # price impact guard (vs reference oracle)
    if not within_price_impact(quote.price, reference_price, policy.max_price_impact_pct):
        return False, "Excessive price impact vs reference", []

    # split large orders
    if notional > policy.split_threshold_quote and policy.split_parts > 1:
        return True, "Split order", split_order(order, policy.split_parts)

    return True, "OK", [order]

def execute_with_guards(
    order: Order,
    get_best_quote: Callable[[Order], Quote],
    send_order: Callable[[Order], Dict[str, Any]],
    get_exec_price: Callable[[Dict[str, Any]], float],
    policy: OrderPolicy,
    balance_lookup: Callable[[str], float],
    allowance_lookup: Callable[[str, str], float],
    reference_price_lookup: Callable[[str, str], float],
    spender: str,
    breaker: ConsecutiveFailureBreaker,
    logger: Callable[[str], None],
) -> Optional[List[Dict[str, Any]]]:
    """
    High-level guarded execution: quote -> validate -> (maybe split) -> send (retry/backoff) -> slippage check vs quote
    """
    if not breaker.allowed():
        logger("[SKIP] breaker active")
        return None

    quote = get_best_quote(order)
    ref_price = reference_price_lookup(order.base, order.quote)

    ok, reason, batch = validate_order(
        order, quote, policy, balance_lookup, allowance_lookup, ref_price, spender
    )
    if not ok:
        logger(f"[REJECT] {reason}")
        breaker.record(False)
        return None

    receipts = []
    for i, part in enumerate(batch):
        tries = 0
        while tries < policy.max_retries:
            q = get_best_quote(part)  # refresh quote per try
            tx = send_order(part)
            exec_price = get_exec_price(tx)

            # post-trade slippage guard vs quote used for THIS try
            if within_slippage(q.price, exec_price, policy.max_slippage_pct):
                receipts.append(tx)
                breaker.record(True)
                logger(f"[OK] part={i+1}/{len(batch)} filled at {exec_price}")
                break
            else:
                tries += 1
                logger(f"[RETRY] slippage too high (quoted={q.price}) (exec={exec_price}) try={tries}")
                time.sleep(policy.backoff_seconds)

        if tries >= policy.max_retries:
            logger(f"[FAIL] part={i+1}/{len(batch)} aborted after retries")
            breaker.record(False)
            return receipts if receipts else None

    return receipts
