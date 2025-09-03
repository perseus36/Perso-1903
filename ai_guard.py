import json
import time
from typing import Dict, Optional, Tuple

class AIGuard:
    def __init__(self, min_stable_pct=0.10, max_token_pct=0.50, allowed_tokens=None):
        """
        AI Guard system to protect portfolio from unsafe AI decisions
        
        :param min_stable_pct: Minimum stablecoin percentage in portfolio (e.g., 0.10 = 10%)
        :param max_token_pct: Maximum allocation for a single token (e.g., 0.50 = 50%)
        :param allowed_tokens: List of supported tokens (e.g., ["USDC", "WETH", "WBTC", "SOL"])
        """
        self.min_stable_pct = min_stable_pct
        self.max_token_pct = max_token_pct
        self.allowed_tokens = allowed_tokens or ["USDC", "WETH", "WBTC", "SOL"]

    def sanitize_targets(self, ai_targets: dict[str, float]) -> dict[str, float]:
        """
        Sanitize AI-generated portfolio target weights.
        """
        clean_targets = {}

        # 1. Only keep allowed tokens
        for token, weight in ai_targets.items():
            if token not in self.allowed_tokens:
                continue
            clean_targets[token] = max(0.0, weight)  # remove negatives

        # 2. Normalize to sum = 1
        total = sum(clean_targets.values())
        if total == 0:
            # fallback: equal distribution
            return {t: 1.0 / len(self.allowed_tokens) for t in self.allowed_tokens}
        for token in clean_targets:
            clean_targets[token] /= total

        # 3. Apply max % limit per token
        for token in clean_targets:
            if clean_targets[token] > self.max_token_pct:
                clean_targets[token] = self.max_token_pct

        # 4. Guarantee minimum stablecoin allocation
        if "USDC" in clean_targets:
            if clean_targets["USDC"] < self.min_stable_pct:
                diff = self.min_stable_pct - clean_targets["USDC"]
                clean_targets["USDC"] = self.min_stable_pct

                # Reduce from other tokens equally
                others = [t for t in clean_targets if t != "USDC"]
                if others:
                    for t in others:
                        clean_targets[t] -= diff / len(others)
                        if clean_targets[t] < 0:
                            clean_targets[t] = 0

        # 5. Normalize again
        total = sum(clean_targets.values())
        for token in clean_targets:
            clean_targets[token] /= total

        return clean_targets

    def validate_signal(self, ai_signal: str) -> str:
        """
        Validate AI-generated trading signals.
        Only accept BUY / SELL / HOLD. Everything else becomes HOLD.
        """
        ai_signal = ai_signal.upper().strip()
        if ai_signal not in ["BUY", "SELL", "HOLD"]:
            return "HOLD"
        return ai_signal
    
    def validate_risk_level(self, risk_level: int) -> int:
        """
        Validate AI-generated risk level (1-10 scale).
        """
        try:
            risk = int(risk_level)
            return max(1, min(10, risk))  # Clamp between 1-10
        except (ValueError, TypeError):
            return 5  # Default to medium risk
    
    def sanitize_trading_signals(self, ai_signals: dict) -> dict:
        """
        Sanitize AI-generated trading signals dictionary.
        """
        if not isinstance(ai_signals, dict):
            return {"signals": [], "overall_sentiment": "neutral", "risk_level": 5}
        
        clean_signals = {"signals": [], "overall_sentiment": "neutral", "risk_level": 5}
        
        # Validate overall sentiment
        sentiment = ai_signals.get("overall_sentiment", "neutral")
        if sentiment.lower() not in ["bullish", "bearish", "neutral"]:
            sentiment = "neutral"
        clean_signals["overall_sentiment"] = sentiment
        
        # Validate risk level
        clean_signals["risk_level"] = self.validate_risk_level(ai_signals.get("risk_level", 5))
        
        # Sanitize individual signals
        signals = ai_signals.get("signals", [])
        if isinstance(signals, list):
            for signal in signals:
                if isinstance(signal, dict):
                    clean_signal = {
                        "symbol": signal.get("symbol", ""),
                        "action": self.validate_signal(signal.get("action", "HOLD")),
                        "confidence": max(1, min(10, signal.get("confidence", 5))),
                        "reason": signal.get("reason", "AI analysis"),
                        "target_price": signal.get("target_price", ""),
                        "stop_loss": signal.get("stop_loss", "")
                    }
                    
                    # Only include signals for allowed tokens
                    if clean_signal["symbol"] in self.allowed_tokens:
                        clean_signals["signals"].append(clean_signal)
        
        return clean_signals
    
    def log_sanitization(self, original: dict, sanitized: dict, operation: str):
        """
        Log sanitization operations for transparency.
        """
        print(f"🛡️ AI Guard {operation}:")
        print(f"   Original: {json.dumps(original, indent=2)}")
        print(f"   Sanitized: {json.dumps(sanitized, indent=2)}")
        print(f"   Changes applied: {operation}")
