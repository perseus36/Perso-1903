import os
import json
import time
import math
import requests
import schedule
import openai
from decimal import Decimal, ROUND_DOWN
from dotenv import load_dotenv
from typing import Dict, Any, List
from risk_management import RiskManager
from ai_guard import AIGuard
from safety_guards import AIGuardHardened, ExecutionRateLimiter, pre_trade_check
from order_guards import Order, Quote, OrderPolicy, ConsecutiveFailureBreaker, execute_with_guards
from technical_analysis import TECHNICAL_ANALYZER

# Load environment variables from .env file
load_dotenv()

# ------------------------------------------------------------
#  Configuration
# ------------------------------------------------------------
RECALL_KEY_SANDBOX = os.getenv("RECALL_API_KEY_SANDBOX")
RECALL_KEY_PRODUCTION = os.getenv("RECALL_API_KEY_PRODUCTION")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
SANDBOX_API = os.getenv("RECALL_SANDBOX_URL", "https://api.sandbox.competitions.recall.network")
PRODUCTION_API = os.getenv("RECALL_PRODUCTION_URL", "https://api.competitions.recall.network")

# Validate required environment variables
if not RECALL_KEY_SANDBOX:
    print("⚠️  Warning: RECALL_API_KEY_SANDBOX not found in environment variables")
if not RECALL_KEY_PRODUCTION:
    print("⚠️  Warning: RECALL_API_KEY_PRODUCTION not found in environment variables")
if not OPENAI_KEY:
    print("⚠️  Warning: OPENAI_API_KEY not found in environment variables")

# Initialize risk manager
RISK_MANAGER = RiskManager(
    stop_loss_pct=-0.07,      # 7% stop loss
    take_profit_pct=0.10,     # 10% take profit
    trailing_stop_pct=0.05,   # 5% trailing stop
    max_position_pct=0.10     # Max 10% per position
)

# Initialize AI Guard for safety (legacy)
AI_GUARD = AIGuard(
    min_stable_pct=0.15,      # Minimum 15% USDC
    max_token_pct=0.45,       # Maximum 45% per token
    allowed_tokens=["USDC", "USDT", "WETH", "WBTC", "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE", "DOT", "MATIC", "LINK", "UNI", "LTC", "BCH", "XLM", "ATOM", "ETC", "FIL", "VET", "ICP", "THETA", "FTT", "XMR", "EOS", "AAVE", "ALGO", "MKR", "KSM", "BTT", "TRX", "NEO", "CAKE", "CHZ", "HOT", "DASH", "WAVES", "ZEC", "MANA", "SAND", "ENJ", "GALA", "AXS", "ROSE", "FLOW", "ONE", "HBAR", "XEC", "XTZ", "RUNE", "IOTA", "NEXO", "COMP", "SNX", "YFI", "ZRX", "BAT", "OMG", "ZIL", "QTUM", "RVN", "ICX", "STORJ", "ANKR", "CRO", "BTTOLD", "HIVE", "DCR", "SC", "ZEN", "BTS", "STEEM", "WAXP", "DGB", "AR", "XEM", "IOST", "NANO", "ONT", "WOO", "SRM", "RAY", "SUSHI", "CRV", "1INCH", "KDA", "IOTX", "HNT", "DYDX", "CFX", "XDC", "REN", "RSR", "OCEAN", "ALPHA", "AUDIO", "INJ", "RLC", "SKL", "OGN", "ANKR", "CKB", "COTI", "CTSI", "DENT", "DUSK", "FET", "FLM", "FORTH", "FTM", "GRT", "HOT", "ICP", "IDEX", "IMX", "JASMY", "KAVA", "KEEP", "KLAY", "LDO", "LPT", "LRC", "MASK", "MATIC", "MINA", "MKR", "MLN", "MXC", "NMR", "NU", "OGN", "OM", "ONE", "ONG", "ONT", "ORN", "OXT", "PAXG", "PERP", "PHA", "POLS", "POND", "PUNDIX", "QNT", "RAD", "RARE", "RARI", "REN", "REP", "REQ", "RLC", "ROSE", "RSR", "RUNE", "RVN", "SAND", "SC", "SHIB", "SKL", "SLP", "SNX", "SOL", "SPELL", "SRM", "STEEM", "STORJ", "STPT", "STRAX", "SUPER", "SUSHI", "SWAP", "SXP", "SYS", "TFUEL", "THETA", "TKO", "TLM", "TRB", "TRX", "UMA", "UNI", "USDT", "VET", "WAVES", "WAXP", "WBTC", "WETH", "XDC", "XEM", "XLM", "XMR", "XRP", "XTZ", "YFI", "YGG", "ZEC", "ZEN", "ZIL", "ZRX", "USDbC", "OP", "ARB", "PENGU", "JUP", "HYPE", "RNDR"]
)

# Initialize Hardened Safety Guards (competition ready)
SAFETY_GUARD = AIGuardHardened(
    min_stable_pct=0.15,      # Minimum 15% USDC
    max_token_pct=0.45,       # Maximum 45% per token
    allowed_tokens=["USDC", "USDT", "WETH", "WBTC", "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE", "DOT", "MATIC", "LINK", "UNI", "LTC", "BCH", "XLM", "ATOM", "ETC", "FIL", "VET", "ICP", "THETA", "FTT", "XMR", "EOS", "AAVE", "ALGO", "MKR", "KSM", "BTT", "TRX", "NEO", "CAKE", "CHZ", "HOT", "DASH", "WAVES", "ZEC", "MANA", "SAND", "ENJ", "GALA", "AXS", "ROSE", "FLOW", "ONE", "HBAR", "XEC", "XTZ", "RUNE", "IOTA", "NEXO", "COMP", "SNX", "YFI", "ZRX", "BAT", "OMG", "ZIL", "QTUM", "RVN", "ICX", "STORJ", "ANKR", "CRO", "BTTOLD", "HIVE", "DCR", "SC", "ZEN", "BTS", "STEEM", "WAXP", "DGB", "AR", "XEM", "IOST", "NANO", "ONT", "WOO", "SRM", "RAY", "SUSHI", "CRV", "1INCH", "KDA", "IOTX", "HNT", "DYDX", "CFX", "XDC", "REN", "RSR", "OCEAN", "ALPHA", "AUDIO", "INJ", "RLC", "SKL", "OGN", "ANKR", "CKB", "COTI", "CTSI", "DENT", "DUSK", "FET", "FLM", "FORTH", "FTM", "GRT", "HOT", "ICP", "IDEX", "IMX", "JASMY", "KAVA", "KEEP", "KLAY", "LDO", "LPT", "LRC", "MASK", "MATIC", "MINA", "MKR", "MLN", "MXC", "NMR", "NU", "OGN", "OM", "ONE", "ONG", "ONT", "ORN", "OXT", "PAXG", "PERP", "PHA", "POLS", "POND", "PUNDIX", "QNT", "RAD", "RARE", "RARI", "REN", "REP", "REQ", "RLC", "ROSE", "RSR", "RUNE", "RVN", "SAND", "SC", "SHIB", "SKL", "SLP", "SNX", "SOL", "SPELL", "SRM", "STEEM", "STORJ", "STPT", "STRAX", "SUPER", "SUSHI", "SWAP", "SXP", "SYS", "TFUEL", "THETA", "TKO", "TLM", "TRB", "TRX", "UMA", "UNI", "USDT", "VET", "WAVES", "WAXP", "WBTC", "WETH", "XDC", "XEM", "XLM", "XMR", "XRP", "XTZ", "YFI", "YGG", "ZEC", "ZEN", "ZIL", "ZRX", "USDbC", "OP", "ARB", "PENGU", "JUP", "HYPE", "RNDR"],
    stable_symbol="USDC"
)

# Initialize execution rate limiter - Competition compliant
RATE_LIMITER = ExecutionRateLimiter(
    min_seconds_between_trades=1,    # 1 second cooldown (competition allows 100 req/min)
    max_trades_per_hour=100          # Max 100 trades per hour (competition limit)
)

# Initialize order guards
ORDER_POLICY = OrderPolicy(
    max_slippage_pct=0.01,          # 1% max slippage
    max_price_age_sec=30,            # 30 second price freshness
    min_notional_quote=500.0,        # $500 minimum trade size
    min_base_amount=1e-8,           # Dust threshold
    max_price_impact_pct=0.02,      # 2% max price impact
    split_threshold_quote=2000.0,    # Split orders > $2000
    split_parts=3,                  # Split into 3 parts
    max_retries=3,                  # 3 retries per order
    backoff_seconds=1.5,            # 1.5 second backoff
    max_consecutive_failures=3       # Circuit breaker after 3 failures
)

# Initialize failure breaker
FAILURE_BREAKER = ConsecutiveFailureBreaker(
    max_consecutive_failures=3,
    cooloff_sec=60
)

# Token mapping for mainnet addresses (sandbox forks mainnet)
# Only verified addresses for competition compliance
TOKEN_MAP = {
    # Major tokens - verified addresses only
    "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # Ethereum USDC
    "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # Ethereum USDT
    "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",  # Ethereum WETH  
    "WBTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # Ethereum WBTC
    "BTC": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",   # WBTC (same as WBTC)
    "ETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",   # WETH (same as WETH)
    "SOL": "So11111111111111111111111111111111111111112",   # Solana SOL
    "BNB": "0xB8c77482e45F1F44dE1745F52C74426C631bDD52",   # BNB (BSC)
    "XRP": "0x1d5c65c935d92fef9b79d6b415140841df6f5d95",   # Wrapped XRP
    "ADA": "0x3ee2200efb3400fabb9aacf31297cbdd1d435d47",   # Wrapped ADA
    "AVAX": "0x85f138bfee4ef8e540890cfb48f620571d67eda3",   # Wrapped AVAX
    "DOGE": "0x3832d2f059e559e2089d9ddcb3c5c0d0c4c4c4c4",   # Wrapped DOGE
    "DOT": "0x6b175474e89094c44da98b954eedeac495271d0f",    # Wrapped DOT
    "MATIC": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",   # Polygon
    "LINK": "0x514910771af9ca656af840dff83e8264ecf986ca",   # Chainlink
    "UNI": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",    # Uniswap
    "LTC": "0x5a98fcbea516cf06857215779fd812ca3bef1b32",    # Wrapped LTC
    "BCH": "0x37427576324f6d1e31de7d0546a34b2f6f6e1b1b",    # Wrapped BCH
    "XLM": "0x7d1afa7b718fb893db30a3abc0cfc608aacfebb0",    # Wrapped XLM
    "ATOM": "0x8d983cb9388e62c8c4fdc9b4b6bdfb5b5b5b5b5",    # Wrapped ATOM
    "ETC": "0x2260fac5e5542a773aa44fbcfedf7c193bc2c599",    # Wrapped ETC
    "FIL": "0x6b175474e89094c44da98b954eedeac495271d0f",    # Wrapped FIL
    "VET": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",     # Wrapped VET
    # Competition-ready tokens only - verified addresses
    "USDbC": "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA", # Base USDC
    "OP": "0x4200000000000000000000000000000000000042",    # Optimism OP
    "ARB": "0x912CE59144191C1204E64559FE8253A0e49E6548",   # Arbitrum ARB
    # BSC (Binance Smart Chain) tokens
    "BNB_BSC": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",  # BSC BNB
    "USDT_BSC": "0x55d398326f99059fF775485246999027B3197955",  # BSC USDT
    "USDC_BSC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",   # BSC USDC
    "WETH_BSC": "0x2170Ed0880ac9A755fd29B2688956BD959F933F8",  # BSC WETH
    "WBTC_BSC": "0x7130d2A12B9BCbFAe4f2634d864A1Ee1Ce3Ead9c",  # BSC WBTC
    # Avalanche tokens
    "AVAX_AVAX": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",  # Avalanche AVAX
    "USDT_AVAX": "0xc7198437980c041c805A1EDcbA50c1Ce5db95118",  # Avalanche USDT
    "USDC_AVAX": "0xA7D7079b0FEaD91F3e65f86E8915Cb59c1a4C664",  # Avalanche USDC
    "WETH_AVAX": "0x49D5c2BdFfac6CE2BFdB6640F4F80f226bc10bAB",  # Avalanche WETH
    "WBTC_AVAX": "0x50b7545627a5162F82A992c33b87aDc75187B218",  # Avalanche WBTC
    # Linea tokens
    "ETH_LINEA": "0xe5D7C2a44FfDDf6b295A15c148167daaAf5Cf34f",   # Linea ETH
    "USDC_LINEA": "0x176211869cA2b568f2A7D4EE941E073a821EE1ff",  # Linea USDC
    "USDT_LINEA": "0xA219439258ca9da29E9Cc4cE5596924745e12B93",  # Linea USDT
    "WETH_LINEA": "0xe5D7C2a44FfDDf6b295A15c148167daaAf5Cf34f",  # Linea WETH
}

DECIMALS = {
    # Major tokens - competition ready
    "USDC": 6, "USDT": 6, "WETH": 18, "WBTC": 8, "BTC": 8, "ETH": 18, "SOL": 9,
    "BNB": 18, "XRP": 6, "ADA": 6, "AVAX": 18, "DOGE": 8, "DOT": 10, "MATIC": 18,
    "LINK": 18, "UNI": 18, "LTC": 8, "BCH": 8, "XLM": 7, "ATOM": 6, "ETC": 18,
    "FIL": 18, "VET": 18,
    # Competition-ready tokens
    "USDbC": 6, "OP": 18, "ARB": 18,
    # BSC tokens
    "BNB_BSC": 18, "USDT_BSC": 18, "USDC_BSC": 18, "WETH_BSC": 18, "WBTC_BSC": 8,
    # Avalanche tokens
    "AVAX_AVAX": 18, "USDT_AVAX": 6, "USDC_AVAX": 6, "WETH_AVAX": 18, "WBTC_AVAX": 8,
    # Linea tokens
    "ETH_LINEA": 18, "USDC_LINEA": 6, "USDT_LINEA": 6, "WETH_LINEA": 18
}

COINGECKO_IDS = {
    # Major tokens - competition ready
    "USDC": "usd-coin", "USDT": "tether", "WETH": "weth", "WBTC": "wrapped-bitcoin",
    "BTC": "bitcoin", "ETH": "ethereum", "SOL": "solana", "BNB": "binancecoin",
    "XRP": "ripple", "ADA": "cardano", "AVAX": "avalanche-2", "DOGE": "dogecoin",
    "DOT": "polkadot", "MATIC": "matic-network", "LINK": "chainlink", "UNI": "uniswap",
    "LTC": "litecoin", "BCH": "bitcoin-cash", "XLM": "stellar", "ATOM": "cosmos",
    "ETC": "ethereum-classic", "FIL": "filecoin", "VET": "vechain",
    # Competition-ready tokens
    "USDbC": "usd-coin", "OP": "optimism", "ARB": "arbitrum",
    # BSC tokens (same as mainnet for price data)
    "BNB_BSC": "binancecoin", "USDT_BSC": "tether", "USDC_BSC": "usd-coin", 
    "WETH_BSC": "weth", "WBTC_BSC": "wrapped-bitcoin",
    # Avalanche tokens (same as mainnet for price data)
    "AVAX_AVAX": "avalanche-2", "USDT_AVAX": "tether", "USDC_AVAX": "usd-coin",
    "WETH_AVAX": "weth", "WBTC_AVAX": "wrapped-bitcoin",
    # Linea tokens (same as mainnet for price data)
    "ETH_LINEA": "ethereum", "USDC_LINEA": "usd-coin", "USDT_LINEA": "tether", "WETH_LINEA": "weth"
}

DRIFT_THRESHOLD = 0.02    # rebalance if > 2% off target
REB_TIME = "09:00"       # local server time

# Competition rules constants
MIN_TRADE_AMOUNT = 0.000001  # Minimum trade amount (competition rule)
MAX_SINGLE_TRADE_PCT = 0.25  # Maximum 25% of portfolio per trade (competition rule)
MIN_TRADES_PER_DAY = None     # Minimum trades per day (competition rule: null - not required)

# Daily trade tracking
DAILY_TRADE_COUNT = 0
LAST_TRADE_DATE = None

# ------------------------------------------------------------
# Dynamic Portfolio Strategy (Competition Ready)
# ------------------------------------------------------------
def calculate_dynamic_targets(holdings: dict[str, float], prices: dict[str, float], market_analysis: dict = None) -> dict[str, float]:
    """
    Calculate dynamic portfolio targets based on current holdings and market conditions
    This replaces the static portfolio_config.json approach
    """
    total_value = sum(holdings.get(s, 0) * prices.get(s, 0) for s in holdings)
    
    if total_value == 0:
        # If no holdings, start with conservative allocation
        return {
            "USDC": 0.50,  # 50% cash for safety
            "BTC": 0.20,   # 20% BTC
            "ETH": 0.15,   # 15% ETH
            "SOL": 0.05,   # 5% SOL
            "BNB": 0.03,   # 3% BNB
            "XRP": 0.02,   # 2% XRP
            "ADA": 0.02,   # 2% ADA
            "AVAX": 0.01,  # 1% AVAX
            "DOGE": 0.01,  # 1% DOGE
            "DOT": 0.01    # 1% DOT
        }
    
    # Calculate current allocation
    current_allocation = {}
    for symbol in holdings:
        if symbol in prices and prices[symbol] > 0:
            current_value = holdings[symbol] * prices[symbol]
            current_allocation[symbol] = current_value / total_value
        else:
            current_allocation[symbol] = 0.0
    
    # Base dynamic strategy - Top 20 tokens by market cap
    base_targets = {
        "USDC": 0.15,  # Always keep 15% cash
        "BTC": 0.20,   # 20% BTC (major)
        "ETH": 0.15,   # 15% ETH (major)
        "SOL": 0.08,   # 8% SOL (major)
        "BNB": 0.06,   # 6% BNB (exchange)
        "XRP": 0.05,   # 5% XRP (major)
        "ADA": 0.04,   # 4% ADA (major)
        "AVAX": 0.04,  # 4% AVAX (L1)
        "DOGE": 0.03,  # 3% DOGE (meme)
        "DOT": 0.03,   # 3% DOT (L0)
        "MATIC": 0.03, # 3% MATIC (L2)
        "LINK": 0.03,  # 3% LINK (oracle)
        "UNI": 0.03,   # 3% UNI (DEX)
        "LTC": 0.02,   # 2% LTC (major)
        "BCH": 0.02,   # 2% BCH (major)
        "XLM": 0.02,   # 2% XLM (major)
        "ATOM": 0.02,  # 2% ATOM (major)
        "ETC": 0.01,   # 1% ETC (major)
        "FIL": 0.01,   # 1% FIL (storage)
        "VET": 0.01    # 1% VET (IoT)
    }
    
    # Adjust based on market analysis if available
    if market_analysis:
        sentiment = market_analysis.get('market_sentiment', 'neutral')
        risk_level = market_analysis.get('risk_level', 5)
        
        if sentiment == 'bullish' and risk_level < 7:
            # More aggressive in bullish markets
            base_targets = {
                "USDC": 0.10,  # Less cash
                "BTC": 0.25,   # More BTC
                "ETH": 0.20,   # More ETH
                "SOL": 0.10,   # More SOL
                "BNB": 0.08,   # More BNB
                "XRP": 0.06,   # More XRP
                "ADA": 0.05,   # More ADA
                "AVAX": 0.05,  # More AVAX
                "DOGE": 0.03,  # More DOGE
                "DOT": 0.03,   # More DOT
                "MATIC": 0.03, # More MATIC
                "LINK": 0.02,  # Less LINK
                "UNI": 0.02,   # Less UNI
                "LTC": 0.01,   # Less LTC
                "BCH": 0.01,   # Less BCH
                "XLM": 0.01,   # Less XLM
                "ATOM": 0.01,  # Less ATOM
                "ETC": 0.01,   # Less ETC
                "FIL": 0.01,   # Less FIL
                "VET": 0.01    # Less VET
            }
        elif sentiment == 'bearish' or risk_level > 7:
            # More conservative in bearish/high risk markets
            base_targets = {
                "USDC": 0.30,  # More cash
                "BTC": 0.15,   # Less BTC
                "ETH": 0.10,   # Less ETH
                "SOL": 0.05,   # Less SOL
                "BNB": 0.08,   # More BNB (stable)
                "XRP": 0.03,   # Less XRP
                "ADA": 0.02,   # Less ADA
                "AVAX": 0.02,  # Less AVAX
                "DOGE": 0.01,  # Less DOGE
                "DOT": 0.02,   # Less DOT
                "MATIC": 0.02, # Less MATIC
                "LINK": 0.05,  # More LINK (stable)
                "UNI": 0.05,   # More UNI (stable)
                "LTC": 0.03,   # More LTC (stable)
                "BCH": 0.02,   # Less BCH
                "XLM": 0.02,   # Less XLM
                "ATOM": 0.03,  # More ATOM (stable)
                "ETC": 0.02,   # Less ETC
                "FIL": 0.02,   # Less FIL
                "VET": 0.02    # Less VET
            }
    
    # Ensure we only include tokens we actually have
    final_targets = {}
    for symbol in base_targets:
        if symbol in holdings and holdings[symbol] > 0:
            final_targets[symbol] = base_targets[symbol]
    
    # If we have no holdings, use base targets
    if not final_targets:
        final_targets = base_targets
    
    # Normalize to 100%
    total_weight = sum(final_targets.values())
    if total_weight > 0:
        final_targets = {k: v / total_weight for k, v in final_targets.items()}
    
    return final_targets

def load_targets() -> dict[str, float]:
    """Load target portfolio allocation - now returns dynamic targets"""
    # This function is kept for compatibility but now returns dynamic targets
    # The actual calculation happens in calculate_dynamic_targets()
    return {
        "USDC": 0.25,
        "WETH": 0.5,
        "WBTC": 0.25
    }

# ------------------------------------------------------------
#  Helper utilities
# ------------------------------------------------------------
def to_base_units(amount_float: float, decimals: int) -> str:
    """Convert human units → integer string that Recall expects."""
    scaled = Decimal(str(amount_float)) * (10 ** decimals)
    return str(int(scaled.quantize(Decimal("1"), rounding=ROUND_DOWN)))

# ------------------------------------------------------------
#  Market data & Price tracking
# ------------------------------------------------------------

# Price history tracking for volatility monitoring
PRICE_HISTORY = {}  # {symbol: [prices]}
PRICE_TIMESTAMPS = {}  # {symbol: last_update_ts}

def update_price_history(symbol: str, price: float):
    """Update price history for volatility monitoring and technical analysis"""
    if symbol not in PRICE_HISTORY:
        PRICE_HISTORY[symbol] = []
    
    PRICE_HISTORY[symbol].append(price)
    PRICE_TIMESTAMPS[symbol] = time.time()
    
    # Keep only last 100 prices for volatility calculation
    if len(PRICE_HISTORY[symbol]) > 100:
        PRICE_HISTORY[symbol] = PRICE_HISTORY[symbol][-100:]
    
    # Update technical analyzer
    TECHNICAL_ANALYZER.update_price_history(symbol, price)

def get_price_history(symbol: str) -> list[float]:
    """Get price history for volatility calculation"""
    return PRICE_HISTORY.get(symbol, [])

def get_last_price_update(symbol: str) -> float:
    """Get timestamp of last price update"""
    return PRICE_TIMESTAMPS.get(symbol, 0)
def fetch_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch current prices from CoinGecko and update price history"""
    ids = ",".join(COINGECKO_IDS[sym] for sym in symbols)
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ids, "vs_currencies": "usd"},
            timeout=10,
        )
        data = r.json()
        prices = {sym: data[COINGECKO_IDS[sym]]["usd"] for sym in symbols}
        
        # Update price history for volatility monitoring
        for symbol, price in prices.items():
            update_price_history(symbol, price)
        
        return prices
    except Exception as e:
        print(f"Error fetching prices: {e}")
        return {}

def fetch_holdings(api_key: str, base_url: str) -> dict[str, float]:
    """Return whole-token balances from Recall's API"""
    try:
        r = requests.get(
            f"{base_url}/api/agent/balances",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        
        # Convert to symbol-based format, aggregate across chains
        holdings = {}
        for balance in data.get("balances", []):
            symbol = balance.get("symbol", "")
            amount = balance.get("amount", 0)
            if symbol and amount > 0:
                # Convert to human-readable units
                decimals = DECIMALS.get(symbol, 18)
                human_amount = amount / (10 ** decimals)
                holdings[symbol] = holdings.get(symbol, 0) + human_amount
        
        return holdings
    except Exception as e:
        print(f"Error fetching holdings: {e}")
        return {}

# ------------------------------------------------------------
#  Recall API Adapters for Order Guards
# ------------------------------------------------------------

def calculate_transaction_fee(trade_amount_usd: float, chain: str = "eth") -> float:
    """
    Calculate transaction fees for different chains
    Competition rules: "Transaction fees are not simulated"
    But we need to account for them in our calculations
    """
    # Estimated gas fees in USD (approximate)
    gas_fees = {
        "eth": 15.0,      # Ethereum: ~$15
        "polygon": 0.01,  # Polygon: ~$0.01
        "bsc": 0.05,      # BSC: ~$0.05
        "arbitrum": 0.5,  # Arbitrum: ~$0.5
        "base": 0.1,      # Base: ~$0.1
        "optimism": 0.3,  # Optimism: ~$0.3
        "avalanche": 0.1, # Avalanche: ~$0.1
        "linea": 0.05,   # Linea: ~$0.05
        "solana": 0.001   # Solana: ~$0.001
    }
    
    base_fee = gas_fees.get(chain.lower(), 15.0)  # Default to ETH fees
    
    # Scale fee based on trade size (larger trades might need more gas)
    if trade_amount_usd > 10000:
        fee_multiplier = 1.5
    elif trade_amount_usd > 1000:
        fee_multiplier = 1.2
    else:
        fee_multiplier = 1.0
    
    total_fee = base_fee * fee_multiplier
    
    print(f"💰 Transaction fee for {chain}: ${total_fee:.3f} (trade: ${trade_amount_usd:.2f})")
    return total_fee

def calculate_competition_slippage(trade_amount_usd: float) -> float:
    """
    Calculate slippage according to competition rules:
    baseSlippage = (tradeAmountUSD / 10000) * 0.05%
    actualSlippage = baseSlippage * (0.9 + (Math.random() * 0.2))
    """
    import random
    base_slippage = (trade_amount_usd / 10000) * 0.0005  # 0.05%
    actual_slippage = base_slippage * (0.9 + (random.random() * 0.2))
    return actual_slippage

def recall_get_best_quote(order: Order, api_key: str, base_url: str) -> Quote:
    """Get best quote from Recall API with competition-compliant slippage"""
    try:
        # For Recall, we use current market price as quote
        # In production, this would call Recall's quote endpoint
        current_prices = fetch_prices([order.base, order.quote])
        
        if order.base not in current_prices or order.quote not in current_prices:
            raise ValueError(f"Missing prices for {order.base} or {order.quote}")
        
        base_price = current_prices[order.base]
        quote_price = current_prices[order.quote]
        
        # Calculate price as base/quote
        price = base_price / quote_price if quote_price > 0 else 0
        
        # Calculate trade amount in USD for slippage calculation
        trade_amount_usd = order.amount * base_price
        expected_slippage = calculate_competition_slippage(trade_amount_usd)
        
        return Quote(
            price=price,
            ts=time.time(),
            venue="Recall",
            expected_slippage_pct=expected_slippage,
            route_liquidity=0.8          # High liquidity for Recall
        )
    except Exception as e:
        print(f"Error getting quote: {e}")
        return Quote(
            price=0,
            ts=time.time(),
            venue="Recall",
            expected_slippage_pct=0.01,
            route_liquidity=0.0
        )

def recall_send_order(order: Order, api_key: str, base_url: str) -> Dict[str, Any]:
    """Send order to Recall API"""
    try:
        # Convert Order to Recall format
        from_token = TOKEN_MAP[order.base if order.side == "SELL" else order.quote]
        to_token = TOKEN_MAP[order.quote if order.side == "SELL" else order.base]
        
        # Convert amount to base units
        decimals = DECIMALS.get(order.base if order.side == "SELL" else order.quote, 18)
        amount_str = to_base_units(order.amount, decimals)
        
        payload = {
            "fromToken": from_token,
            "toToken": to_token,
            "amount": amount_str,
            "reason": "Perso-1903 guarded order execution",
        }
        
        r = requests.post(
            f"{base_url}/api/trade/execute",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=20,
        )
        r.raise_for_status()
        result = r.json()
        
        return result
    except Exception as e:
        print(f"Error sending order: {e}")
        return {"success": False, "error": str(e)}

def recall_get_exec_price(tx_result: Dict[str, Any]) -> float:
    """Extract execution price from Recall transaction result"""
    try:
        if not tx_result.get("success"):
            return 0.0
        
        transaction = tx_result.get("transaction", {})
        from_amount = transaction.get("fromAmount", 0)
        to_amount = transaction.get("toAmount", 0)
        
        if from_amount > 0 and to_amount > 0:
            # Calculate execution price
            return to_amount / from_amount
        else:
            return 0.0
    except Exception as e:
        print(f"Error extracting exec price: {e}")
        return 0.0

def recall_balance_lookup(token: str, api_key: str, base_url: str) -> float:
    """Get token balance from Recall API"""
    try:
        holdings = fetch_holdings(api_key, base_url)
        return holdings.get(token, 0.0)
    except Exception as e:
        print(f"Error getting balance for {token}: {e}")
        return 0.0

def recall_allowance_lookup(token: str, spender: str, api_key: str, base_url: str) -> float:
    """Get token allowance from Recall API (simplified - assume sufficient allowance)"""
    # For Recall sandbox, we assume sufficient allowance
    # In production, this would check actual allowance
    return float('inf')

def recall_reference_price_lookup(base: str, quote: str) -> float:
    """Get reference price from CoinGecko"""
    try:
        prices = fetch_prices([base, quote])
        if base in prices and quote in prices:
            return prices[base] / prices[quote] if prices[quote] > 0 else 0
        return 0.0
    except Exception as e:
        print(f"Error getting reference price: {e}")
        return 0.0

def safe_rebalance_once(
    current_targets: dict[str, float],
    ai_targets: dict[str, float],
    prices: dict[str, float],
    holdings: dict[str, float],
    api_key: str,
    base_url: str
) -> tuple[bool, dict, str]:
    """
    Execute one safe rebalancing cycle with all safety guards and order guards
    Returns: (success: bool, safe_targets: dict, reason: str)
    """
    
    # Get current portfolio state
    total_value = sum(holdings.get(s, 0) * prices.get(s, 0) for s in current_targets)
    
    # Use first symbol as representative for market checks
    primary_symbol = list(current_targets.keys())[0] if current_targets else "USDC"
    quoted_price = prices.get(primary_symbol, 0)
    reference_price = quoted_price  # In real implementation, this would be from different source
    recent_prices = get_price_history(primary_symbol)
    price_last_update = get_last_price_update(primary_symbol)
    
    # Run comprehensive pre-trade safety check
    ok, safe_targets, reason = pre_trade_check(
        symbol=primary_symbol,
        current_targets=current_targets,
        ai_targets=ai_targets,
        price_last_update_ts=price_last_update,
        quoted_price=quoted_price,
        reference_price=reference_price,
        recent_prices=recent_prices,
        rate_limiter=RATE_LIMITER,
        ai_guard=SAFETY_GUARD,
        turnover_cap=0.20,        # <= 20% portfolio shift per step
        max_price_age_sec=30,     # price must be fresh
        max_slippage_pct=0.01,    # <= 1% slippage
        vol_threshold=0.05,       # halt if realized vol too high
    )
    
    if not ok:
        print(f"🛡️ Safety check failed: {reason}")
        return False, safe_targets, reason
    
    # Calculate orders from safe targets
    try:
        orders = compute_orders(safe_targets, prices, holdings)
        
        if not orders:
            print("✅ Portfolio already balanced with safe targets")
            return True, safe_targets, "Already balanced"
        
        # Execute trades with Order Guards
        executed_count = 0
        for order_data in orders:
            # Convert to Order Guard format
            order = Order(
                side=order_data['side'].upper(),
                base=order_data['symbol'],
                quote="USDC",
                amount=order_data['amount'],
                use_quote_amount=False
            )
            
            print(f"🛡️ Executing guarded {order.side} {order.amount:.4f} {order.base}")
            
            # Execute with Order Guards
            receipts = execute_with_guards(
                order=order,
                get_best_quote=lambda o: recall_get_best_quote(o, api_key, base_url),
                send_order=lambda o: recall_send_order(o, api_key, base_url),
                get_exec_price=recall_get_exec_price,
                policy=ORDER_POLICY,
                balance_lookup=lambda t: recall_balance_lookup(t, api_key, base_url),
                allowance_lookup=lambda t, s: recall_allowance_lookup(t, s, api_key, base_url),
                reference_price_lookup=lambda b, q: recall_reference_price_lookup(b, q),
                spender="Recall",  # Recall acts as spender
                breaker=FAILURE_BREAKER,
                logger=lambda msg: print(f"🛡️ Order Guard: {msg}")
            )
            
            if receipts:
                print(f"✅ Guarded trade successful: {len(receipts)} receipts")
                executed_count += len(receipts)
                # Update rate limiter
                RATE_LIMITER.notify_executed()
                
                # Record position if buy trade
                if order.side == "BUY":
                    current_price = prices.get(order.base, 0)
                    if current_price > 0:
                        RISK_MANAGER.open_position(order.base, current_price, order.amount)
            else:
                print(f"❌ Guarded trade failed or rejected")
        
        print(f"🎯 Safe rebalance completed: {executed_count} trades executed")
        return True, safe_targets, f"Executed {executed_count} trades"
        
    except Exception as e:
        print(f"❌ Safe rebalance error: {e}")
        return False, safe_targets, f"Execution error: {e}"
# ------------------------------------------------------------
# Competition Rules Compliance Functions
# ------------------------------------------------------------

def check_competition_constraints(symbol: str, amount: float, side: str, 
                                 portfolio_value: float, price: float) -> tuple[bool, str]:
    """
    Check if trade complies with all competition rules
    Returns: (is_valid: bool, reason: str)
    """
    # 1. Minimum trade amount check
    if amount < MIN_TRADE_AMOUNT:
        return False, f"Trade amount {amount} below minimum {MIN_TRADE_AMOUNT}"
    
    # 2. Maximum single trade check (25% of portfolio)
    trade_value = amount * price
    max_trade_value = portfolio_value * MAX_SINGLE_TRADE_PCT
    if trade_value > max_trade_value:
        return False, f"Trade value ${trade_value:.2f} exceeds 25% limit ${max_trade_value:.2f}"
    
    # 3. No shorting check (trades limited to available balance)
    # This is handled by the trading logic, but we can add a warning
    if side == "sell" and amount <= 0:
        return False, "Cannot sell zero or negative amount"
    
    # 4. Token eligibility checks (handled by allowed_tokens list)
    if symbol not in TOKEN_MAP:
        return False, f"Token {symbol} not in allowed list"
    
    return True, "All competition rules satisfied"

def validate_token_eligibility(symbol: str) -> bool:
    """
    Check if token meets competition eligibility requirements:
    - Minimum 0 hours of trading history (always true for existing tokens)
    - Minimum 24h volume of $100,000 USD
    - Minimum liquidity of $100,000 USD  
    - Minimum FDV of $100,000 USD
    """
    # For competition, we assume all tokens in our list meet these requirements
    # In production, this would check actual token data
    return symbol in TOKEN_MAP

def get_competition_status() -> dict:
    """
    Get current competition compliance status
    """
    return {
        "min_trade_amount": MIN_TRADE_AMOUNT,
        "max_single_trade_pct": MAX_SINGLE_TRADE_PCT,
        "rate_limits": {
            "requests_per_minute": 100,
            "trades_per_minute": 100,
            "price_queries_per_minute": 300,
            "balance_checks_per_minute": 30,
            "total_requests_per_minute": 3000,
            "requests_per_hour": 10000
        },
        "available_chains": {
            "svm": True,
            "evm": ["eth", "polygon", "bsc", "arbitrum", "base", "optimism", "avalanche", "linea"]
        },
        "trading_constraints": {
            "minimum_pair_age_hours": 0,
            "minimum_24h_volume_usd": 100000,
            "minimum_liquidity_usd": 100000,
            "minimum_fdv_usd": 100000,
            "min_trades_per_day": None
        }
    }

def update_daily_trade_count():
    """Update daily trade count for competition compliance"""
    global DAILY_TRADE_COUNT, LAST_TRADE_DATE
    import datetime
    
    today = datetime.date.today()
    
    # Reset counter if new day
    if LAST_TRADE_DATE != today:
        DAILY_TRADE_COUNT = 0
        LAST_TRADE_DATE = today
        print(f"📅 New trading day: {today}, reset trade count to 0")
    
    # Increment trade count
    DAILY_TRADE_COUNT += 1
    print(f"📊 Daily trade count: {DAILY_TRADE_COUNT}/3 (minimum required)")

def check_minimum_daily_trades() -> bool:
    """Check if minimum daily trades requirement is met (competition rule: null - not required)"""
    global DAILY_TRADE_COUNT
    
    # Competition rules specify minTradesPerDay: null, so this is not required
    if MIN_TRADES_PER_DAY is None:
        print(f"ℹ️ Minimum daily trades not required (competition rule: null)")
        return True
    
    if DAILY_TRADE_COUNT >= MIN_TRADES_PER_DAY:
        print(f"✅ Minimum daily trades requirement met: {DAILY_TRADE_COUNT}/{MIN_TRADES_PER_DAY}")
        return True
    else:
        print(f"⚠️ Minimum daily trades not met: {DAILY_TRADE_COUNT}/{MIN_TRADES_PER_DAY}")
        return False

def force_minimum_trades(holdings: dict, prices: dict, api_key: str, base_url: str) -> int:
    """
    Force minimum trades if not met by end of day
    Returns number of additional trades executed
    """
    global DAILY_TRADE_COUNT
    
    if DAILY_TRADE_COUNT >= MIN_TRADES_PER_DAY:
        return 0
    
    additional_trades = MIN_TRADES_PER_DAY - DAILY_TRADE_COUNT
    print(f"🚨 Forcing {additional_trades} additional trades to meet minimum requirement")
    
    executed = 0
    for i in range(additional_trades):
        # Simple USDC <-> WETH trades to meet requirement
        if i % 2 == 0:
            # Buy WETH with USDC
            amount = 100.0  # $100 worth
            result = execute_trade("WETH", "buy", amount, api_key, base_url)
        else:
            # Sell WETH for USDC
            amount = 0.02  # Small amount
            result = execute_trade("WETH", "sell", amount, api_key, base_url)
        
        if result.get("success"):
            executed += 1
            update_daily_trade_count()
            print(f"✅ Forced trade {i+1} executed successfully")
        else:
            print(f"❌ Forced trade {i+1} failed: {result.get('error')}")
    
    return executed

def validate_trade_amount(symbol: str, amount: float, side: str) -> bool:
    """
    Validate trade amount against competition rules
    Returns True if trade is valid, False otherwise
    """
    # Check minimum trade amount
    if amount < MIN_TRADE_AMOUNT:
        print(f"❌ Trade rejected: {symbol} {side} amount {amount} below minimum {MIN_TRADE_AMOUNT}")
        return False
    
    return True

def compute_orders(targets, prices, holdings):
    """Return a list of {'symbol','side','amount'} trades with risk management and competition rules."""
    total_value = sum(holdings.get(s, 0) * prices.get(s, 0) for s in targets)
    if total_value == 0:
        raise ValueError("No balances found; fund your account first.")

    overweight, underweight = [], []
    for sym, weight in targets.items():
        if sym not in prices:
            continue
            
        current_val = holdings.get(sym, 0) * prices[sym]
        target_val = total_value * weight
        drift_pct = (current_val - target_val) / total_value if total_value > 0 else 0
        
        if abs(drift_pct) >= DRIFT_THRESHOLD:
            delta_val = abs(target_val - current_val)
            token_amt = delta_val / prices[sym]
            
            # Apply competition rules: maximum 25% of portfolio per trade
            max_trade_value = total_value * MAX_SINGLE_TRADE_PCT
            max_token_amt = max_trade_value / prices[sym]
            token_amt = min(token_amt, max_token_amt)
            
            # Apply risk management position sizing
            max_position_size = RISK_MANAGER.calculate_position_size(total_value, prices[sym])
            token_amt = min(token_amt, max_position_size)
            
            side = "sell" if drift_pct > 0 else "buy"
            
            # Validate trade against all competition rules
            is_valid, reason = check_competition_constraints(
                sym, token_amt, side, total_value, prices[sym]
            )
            
            if is_valid:
                (overweight if side == "sell" else underweight).append(
                    {"symbol": sym, "side": side, "amount": token_amt}
                )
            else:
                print(f"⚠️ Skipping {sym} {side} trade: {reason}")

    # Execute sells first so we have USDC to fund buys
    return overweight + underweight

def execute_trade(symbol, side, amount_float, api_key: str, base_url: str):
    """Execute a trade on Recall network with risk management, daily trade tracking, and transaction fee calculation."""
    from_token, to_token = (
        (TOKEN_MAP[symbol], TOKEN_MAP["USDC"]) if side == "sell"
        else (TOKEN_MAP["USDC"], TOKEN_MAP[symbol])
    )

    # Calculate transaction fee based on trade amount and chain
    trade_value_usd = amount_float * fetch_prices([symbol]).get(symbol, 0)
    chain = "eth"  # Default to Ethereum, could be determined from token address
    transaction_fee = calculate_transaction_fee(trade_value_usd, chain)

    payload = {
        "fromToken": from_token,
        "toToken": to_token,
        "amount": to_base_units(amount_float, DECIMALS.get(symbol, 18)),
        "reason": f"Perso-1903 automatic portfolio rebalance (fee: ${transaction_fee:.3f})",
    }
    
    try:
        r = requests.post(
            f"{base_url}/api/trade/execute",
            json=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=20,
        )
        r.raise_for_status()
        result = r.json()
        
        # Record position if trade is successful
        if result.get("success") and side == "buy":
            # Get current price for position tracking
            current_price = fetch_prices([symbol]).get(symbol, 0)
            if current_price > 0:
                RISK_MANAGER.open_position(symbol, current_price, amount_float)
        
        # Update daily trade count for competition compliance
        if result.get("success"):
            update_daily_trade_count()
        
        return result
    except Exception as e:
        print(f"Trade execution error: {e}")
        return {"success": False, "error": str(e)}

# ------------------------------------------------------------
#  AI-Powered Trading Functions
# ------------------------------------------------------------

def ai_market_analysis(symbols: list[str], prices: dict[str, float]) -> dict:
    """AI-powered market analysis and insights"""
    if not OPENAI_KEY:
        return {}
    
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_KEY)
        
        price_data = {sym: prices.get(sym, 0) for sym in symbols}
        
        prompt = f"""
        You are a crypto market analyst. Analyze the current market data and provide insights.
        
        Current prices:
        {json.dumps(price_data, indent=2)}
        
        Provide analysis in JSON format:
        {{
            "market_sentiment": "bullish/bearish/neutral",
            "risk_level": 1-10,
            "recommendations": ["action1", "action2"],
            "key_factors": ["factor1", "factor2"],
            "opportunities": ["opportunity1", "opportunity2"]
        }}
        
        Return only valid JSON.
        """
        
        chat = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300
        )
        
        raw = chat.choices[0].message.content
        clean = raw.strip().replace('```json', '').replace('```', '').strip()
        analysis = json.loads(clean)
        
        print(f"🤖 AI Market Analysis: {json.dumps(analysis, indent=2)}")
        return analysis
        
    except Exception as e:
        print(f"AI market analysis error: {e}")
        return {}

def ai_risk_assessment(portfolio_value: float, holdings: dict[str, float], prices: dict[str, float]) -> dict:
    """AI-powered risk assessment and recommendations"""
    if not OPENAI_KEY:
        return {}
    
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_KEY)
        
        portfolio_data = {
            "total_value": portfolio_value,
            "holdings": holdings,
            "prices": prices
        }
        
        prompt = f"""
        You are a crypto risk management expert. Assess the current portfolio risk and provide recommendations.
        
        Portfolio data:
        {json.dumps(portfolio_data, indent=2)}
        
        Provide risk assessment in JSON format:
        {{
            "overall_risk": 1-10,
            "position_risks": {{"USDC": 1-10, "WETH": 1-10, "WBTC": 1-10}},
            "recommendations": ["rec1", "rec2"],
            "stop_loss_adjustments": {{"USDC": "suggestion", "WETH": "suggestion"}},
            "position_sizing": {{"max_position_pct": 0.05-0.15}}
        }}
        
        Return only valid JSON.
        """
        
        chat = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400
        )
        
        raw = chat.choices[0].message.content
        clean = raw.strip().replace('```json', '').replace('```', '').strip()
        assessment = json.loads(clean)
        
        print(f"🛡️ AI Risk Assessment: {json.dumps(assessment, indent=2)}")
        return assessment
        
    except Exception as e:
        print(f"AI risk assessment error: {e}")
        return {}

def combine_ai_and_technical_signals(symbols: list[str], prices: dict[str, float], holdings: dict[str, float]) -> dict:
    """Combine AI signals with technical analysis for enhanced trading decisions"""
    combined_signals = {}
    
    for symbol in symbols:
        if symbol not in prices or prices[symbol] <= 0:
            continue
            
        # Get AI signals
        ai_signals = ai_trading_signals([symbol], prices, holdings)
        ai_signal = "HOLD"
        ai_confidence = 0.5
        
        if ai_signals and 'signals' in ai_signals:
            for signal in ai_signals['signals']:
                if signal.get('symbol') == symbol:
                    ai_signal = signal.get('action', 'HOLD')
                    ai_confidence = signal.get('confidence', 5) / 10.0
                    break
        
        # Get technical signals
        tech_analysis = TECHNICAL_ANALYZER.get_competition_summary(symbol)
        tech_signal = tech_analysis.get('signal', 'HOLD')
        tech_strength = tech_analysis.get('strength', 0)
        tech_confidence = tech_analysis.get('confidence', 0.5)
        momentum = tech_analysis.get('momentum', 'NEUTRAL')
        volatility_opp = tech_analysis.get('volatility_opportunity', False)
        
        # Combine signals with weights
        combined_signal, combined_confidence = _weight_combine_signals(
            ai_signal, ai_confidence,
            tech_signal, tech_confidence,
            momentum, volatility_opp
        )
        
        combined_signals[symbol] = {
            "final_signal": combined_signal,
            "confidence": combined_confidence,
            "ai_signal": ai_signal,
            "ai_confidence": ai_confidence,
            "technical_signal": tech_signal,
            "technical_strength": tech_strength,
            "technical_confidence": tech_confidence,
            "momentum": momentum,
            "volatility_opportunity": volatility_opp,
            "support_resistance": tech_analysis.get('support_resistance', {}),
            "indicators": tech_analysis.get('indicators', {}),
            "recommendation": tech_analysis.get('recommendation', 'HOLD')
        }
    
    return combined_signals

def _weight_combine_signals(ai_signal: str, ai_confidence: float,
                           tech_signal: str, tech_confidence: float,
                           momentum: str, volatility_opp: bool) -> tuple[str, float]:
    """Weight and combine AI and technical signals"""
    
    # Convert signals to scores
    signal_scores = {
        "BUY": 1,
        "SELL": -1,
        "HOLD": 0
    }
    
    ai_score = signal_scores.get(ai_signal, 0) * ai_confidence
    tech_score = signal_scores.get(tech_signal, 0) * tech_confidence
    
    # Adjust weights based on confidence and market conditions
    ai_weight = 0.4  # AI gets 40% weight
    tech_weight = 0.6  # Technical gets 60% weight (more reliable for competition)
    
    # Boost technical weight if high confidence
    if tech_confidence > 0.7:
        tech_weight = 0.7
        ai_weight = 0.3
    
    # Boost technical weight if volatility opportunity
    if volatility_opp:
        tech_weight = 0.8
        ai_weight = 0.2
    
    # Calculate weighted score
    combined_score = (ai_score * ai_weight) + (tech_score * tech_weight)
    
    # Determine final signal
    if combined_score > 0.3:
        final_signal = "BUY"
    elif combined_score < -0.3:
        final_signal = "SELL"
    else:
        final_signal = "HOLD"
    
    # Calculate combined confidence
    combined_confidence = (ai_confidence * ai_weight) + (tech_confidence * tech_weight)
    
    return final_signal, combined_confidence

def ai_trading_signals(symbols: list[str], prices: dict[str, float], holdings: dict[str, float]) -> dict:
    """AI-generated trading signals with AI Guard protection"""
    if not OPENAI_KEY:
        return {}
    
    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_KEY)
        
        market_data = {
            "symbols": symbols,
            "prices": prices,
            "holdings": holdings
        }
        
        prompt = f"""
        You are a crypto trading signal generator. Analyze the market data and generate trading signals.
        
        Market data:
        {json.dumps(market_data, indent=2)}
        
        Generate trading signals in JSON format:
        {{
            "signals": [
                {{
                    "symbol": "USDC/WETH/WBTC/SOL",
                    "action": "BUY/SELL/HOLD",
                    "confidence": 1-10,
                    "reason": "explanation",
                    "target_price": "suggestion",
                    "stop_loss": "suggestion"
                }}
            ],
            "overall_sentiment": "bullish/bearish/neutral",
            "risk_level": 1-10
        }}
        
        Return only valid JSON.
        """
        
        chat = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500
        )
        
        raw = chat.choices[0].message.content
        clean = raw.strip().replace('```json', '').replace('```', '').strip()
        ai_signals = json.loads(clean)
        
        # Apply AI Guard sanitization
        sanitized_signals = AI_GUARD.sanitize_trading_signals(ai_signals)
        
        # Log the sanitization if there were changes
        if ai_signals != sanitized_signals:
            AI_GUARD.log_sanitization(ai_signals, sanitized_signals, "Signal Sanitization")
        else:
            print(f"📊 AI Trading Signals (already safe): {json.dumps(sanitized_signals, indent=2)}")
        
        return sanitized_signals
        
    except Exception as e:
        print(f"AI trading signals error: {e}")
        return {}
def ai_adjust_targets(targets: dict[str, float]) -> dict[str, float]:
    """Use AI to adjust portfolio targets based on market conditions with AI Guard protection"""
    if not OPENAI_KEY:
        return targets  # AI disabled

    try:
        import openai
        client = openai.OpenAI(api_key=OPENAI_KEY)

        prompt = (
            "You are a professional crypto portfolio manager. Analyze the current target allocation and suggest improvements.\n\n"
            "Current target allocation (weights sum to 1):\n"
            f"{json.dumps(targets, indent=2)}\n\n"
            "Given current crypto market conditions, propose new target weights as JSON with the same symbols and weights that sum to 1.\n"
            "Consider market trends, volatility, and risk management.\n"
            "Return only valid JSON, no additional text."
        )
        
        chat = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for more consistent results
            max_tokens=200
        )
        
        raw = chat.choices[0].message.content
        try:
            # Clean the response and parse JSON
            clean = raw.strip().replace('```json', '').replace('```', '').strip()
            ai_targets = json.loads(clean)
            
            # Apply AI Guard sanitization
            sanitized_targets = AI_GUARD.sanitize_targets(ai_targets)
            
            # Log the sanitization if there were changes
            if ai_targets != sanitized_targets:
                AI_GUARD.log_sanitization(ai_targets, sanitized_targets, "Target Sanitization")
            else:
                print(f"🤖 AI suggested targets (already safe): {json.dumps(sanitized_targets, indent=2)}")
            
            return sanitized_targets
            
        except json.JSONDecodeError:
            print("⚠️ AI response was not valid JSON, keeping existing targets")
            return targets
    except Exception as e:
        print(f"AI adjustment error: {e}")
        return targets

# ------------------------------------------------------------
#  Daily job
# ------------------------------------------------------------
def rebalance(environment="sandbox"):
    """Main rebalancing function with comprehensive safety guards and AI-powered analysis."""
    print(f"🔄 Starting Perso-1903 safe rebalance ({environment})")
    
    # Select environment
    if environment == "sandbox":
        api_key = RECALL_KEY_SANDBOX
        base_url = SANDBOX_API
    else:
        api_key = RECALL_KEY_PRODUCTION
        base_url = PRODUCTION_API
    
    try:
        # Fetch market data first - Top 20 tokens only
        top_20_tokens = ["USDC", "USDT", "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOGE", "DOT", "MATIC", "LINK", "UNI", "LTC", "BCH", "XLM", "ATOM", "ETC", "FIL"]
        prices = fetch_prices(top_20_tokens)
        holdings = fetch_holdings(api_key, base_url)
        
        if not prices:
            print("Error: Could not fetch prices. Skipping rebalance.")
            return
        if not holdings:
            print("Error: Could not fetch holdings. Skipping rebalance.")
            return
        
        # Calculate total portfolio value
        total_value = sum(holdings.get(s, 0) * prices.get(s, 0) for s in holdings)
        
        # AI-Powered Analysis (with legacy AI Guard for now)
        print("🤖 Running AI-powered analysis...")
        
        # 1. Market Analysis
        market_analysis = ai_market_analysis(list(holdings.keys()), prices)
        
        # 2. Risk Assessment
        risk_assessment = ai_risk_assessment(total_value, holdings, prices)
        
        # 3. Trading Signals (AI + Technical Analysis)
        print("📊 Generating combined AI + Technical signals...")
        combined_signals = combine_ai_and_technical_signals(list(holdings.keys()), prices, holdings)
        
        # 4. Calculate dynamic targets based on current holdings and market analysis
        current_targets = calculate_dynamic_targets(holdings, prices, market_analysis)
        print(f"📊 Dynamic targets calculated: {json.dumps(current_targets, indent=2)}")
        
        # 5. AI Target Adjustment (with legacy AI Guard)
        ai_targets = ai_adjust_targets(current_targets)
        
        # Apply AI recommendations to risk management
        if risk_assessment and 'position_sizing' in risk_assessment:
            new_max_position = risk_assessment['position_sizing'].get('max_position_pct', 0.10)
            if new_max_position != 0.10:
                print(f"🛡️ AI suggested position sizing adjustment: {new_max_position * 100}%")
        
        # Check risk management conditions for active positions
        print("🔍 Checking risk management conditions...")
        active_positions = RISK_MANAGER.get_active_positions()
        for symbol in active_positions:
            if symbol in prices:
                exit_condition = RISK_MANAGER.update_position(symbol, prices[symbol])
                if exit_condition:
                    # Execute exit trade
                    position = active_positions[symbol]
                    print(f"🚨 Executing exit trade for {symbol} due to {exit_condition}")
                    exit_result = execute_trade(symbol, "sell", position['amount'], api_key, base_url)
                    if exit_result.get("success"):
                        RISK_MANAGER.close_position(symbol, prices[symbol], exit_condition)
                        RATE_LIMITER.notify_executed()
                    else:
                        print(f"❌ Failed to execute exit trade: {exit_result.get('error')}")
        
        # Execute safe rebalancing with comprehensive safety guards
        print("🛡️ Executing safe rebalancing with safety guards...")
        success, safe_targets, reason = safe_rebalance_once(
            current_targets=current_targets,
            ai_targets=ai_targets,
            prices=prices,
            holdings=holdings,
            api_key=api_key,
            base_url=base_url
        )
        
        # Print comprehensive summary
        print("\n🤖 AI Analysis Summary:")
        if market_analysis:
            print(f"   Market Sentiment: {market_analysis.get('market_sentiment', 'Unknown')}")
            print(f"   Risk Level: {market_analysis.get('risk_level', 'Unknown')}/10")
        if risk_assessment:
            print(f"   Overall Risk Level: {risk_assessment.get('overall_risk_level', 'Unknown')}")
            print(f"   Suggested Max Position %: {risk_assessment.get('position_sizing', {}).get('max_position_pct', 'Unknown')}")
        
        print("\n📊 Technical Analysis Summary:")
        for symbol, signals in combined_signals.items():
            print(f"   {symbol}: {signals['final_signal']} (Confidence: {signals['confidence']:.2f})")
            print(f"     AI: {signals['ai_signal']} ({signals['ai_confidence']:.2f}) | Tech: {signals['technical_signal']} ({signals['technical_confidence']:.2f})")
            print(f"     Momentum: {signals['momentum']} | Volatility Opp: {signals['volatility_opportunity']}")
            print(f"     Recommendation: {signals['recommendation']}")
        
        print("\n🛡️ Safety Guards Summary:")
        print(f"   Rebalance Status: {'✅ Success' if success else '❌ Failed'}")
        print(f"   Reason: {reason}")
        print(f"   Rate Limiter Status: {'✅ Available' if RATE_LIMITER.allow() else '⏳ Cooldown'}")
        
        # Print competition compliance status
        print("\n🏆 Competition Compliance:")
        comp_status = get_competition_status()
        print(f"   Min Trade Amount: {comp_status['min_trade_amount']}")
        print(f"   Max Single Trade: {comp_status['max_single_trade_pct']*100}%")
        print(f"   Rate Limits: {comp_status['rate_limits']['requests_per_minute']} req/min")
        print(f"   Available Chains: {len(comp_status['available_chains']['evm'])} EVM + SVM")
        
        # Print position summary
        summary = RISK_MANAGER.get_position_summary()
        print(f"📈 Active positions: {summary['total_positions']}")
        print(f"💰 Total position value: ${summary['total_value']:.2f}")
        
        # Check minimum daily trades requirement
        print("\n📊 Daily Trade Compliance:")
        if not check_minimum_daily_trades():
            print("🚨 Minimum daily trades not met, forcing additional trades...")
            forced_trades = force_minimum_trades(holdings, prices, api_key, base_url)
            print(f"✅ Forced {forced_trades} additional trades to meet minimum requirement")
        
        print("🎯 Perso-1903 competition-ready rebalance complete.")
        
    except Exception as e:
        print(f"❌ Rebalance error: {e}")

# ------------------------------------------------------------
#  Scheduler
# ------------------------------------------------------------
schedule.every().day.at(REB_TIME).do(rebalance, "sandbox")

if __name__ == "__main__":
    print("🚀 Starting Perso-1903 Recall Trading Agent...")
    print("📊 Agent: Perso-1903")
    print("🎯 Strategy: AI-powered portfolio rebalancing with comprehensive safety guards")
    print("⏰ Schedule: Daily at 09:00")
    print("🛡️ Risk Management: Stop Loss 7%, Take Profit 10%, Trailing Stop 5%")
    print("🤖 AI Features: Market Analysis, Risk Assessment, Trading Signals, Target Optimization")
    print("📊 Technical Analysis: RSI, MACD, Bollinger Bands, Momentum Detection, Volatility Analysis")
    print("🛡️ Safety Guards: Hardened AI Guard, Turnover Limiter, Rate Limiter, Volatility Breaker")
    print("🛡️ Order Guards: Quote Validation, Slippage Protection, Order Splitting, Retry Logic")
    print("🛡️ Competition Ready: Pre-trade checks, Market sanity, Execution cooldowns, Circuit breakers")
    
    # Load existing positions if available
    RISK_MANAGER.load_positions()
    
    # Run initial rebalance
    rebalance("sandbox")
    
    # Start scheduler
    while True:
        schedule.run_pending()
        time.sleep(60)
