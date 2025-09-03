# technical_analysis.py
# Competition-ready technical analysis module for Perso-1903
# Optimized for 1-week competition with quick signal generation

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import time

class CompetitionTechnicalAnalyzer:
    """
    Ultra-fast technical analysis for Recall competition
    Focus: Quick signals, momentum detection, volatility opportunities
    Timeframes: 1h, 4h, 12h (competition-optimized)
    """
    
    def __init__(self, price_history: Dict[str, List[float]] = None):
        self.price_history = price_history or {}
        self.signal_cache = {}  # Cache signals to avoid recalculation
        self.last_update = {}
        
        # Competition-optimized parameters
        self.rsi_period = 14
        self.macd_fast = 12
        self.macd_slow = 26
        self.macd_signal = 9
        self.bb_period = 20
        self.bb_std = 2
        
        # Signal thresholds (competition-tuned)
        self.rsi_oversold = 30
        self.rsi_overbought = 70
        self.macd_threshold = 0.001  # Small threshold for quick signals
        self.volatility_threshold = 0.02  # 2% volatility trigger
        
    def update_price_history(self, symbol: str, price: float):
        """Update price history for a symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append(price)
        self.last_update[symbol] = time.time()
        
        # Keep only last 100 prices for competition efficiency
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
        
        # Clear signal cache for this symbol
        if symbol in self.signal_cache:
            del self.signal_cache[symbol]
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI (Relative Strength Index)"""
        if len(prices) < period + 1:
            return 50.0  # Neutral if insufficient data
        
        prices = np.array(prices)
        deltas = np.diff(prices)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    def calculate_macd(self, prices: List[float]) -> Dict[str, float]:
        """Calculate MACD (Moving Average Convergence Divergence)"""
        if len(prices) < self.macd_slow:
            return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
        
        prices = np.array(prices)
        
        # Calculate EMAs
        ema_fast = self._calculate_ema(prices, self.macd_fast)
        ema_slow = self._calculate_ema(prices, self.macd_slow)
        
        # MACD line
        macd_line = ema_fast - ema_slow
        
        # Signal line (EMA of MACD)
        macd_values = []
        for i in range(len(prices)):
            if i >= self.macd_slow - 1:
                ema_f = self._calculate_ema(prices[:i+1], self.macd_fast)
                ema_s = self._calculate_ema(prices[:i+1], self.macd_slow)
                macd_values.append(ema_f - ema_s)
        
        if len(macd_values) >= self.macd_signal:
            signal_line = self._calculate_ema(np.array(macd_values), self.macd_signal)
        else:
            signal_line = macd_line
        
        histogram = macd_line - signal_line
        
        return {
            "macd": float(macd_line),
            "signal": float(signal_line),
            "histogram": float(histogram)
        }
    
    def _calculate_ema(self, prices: np.ndarray, period: int) -> float:
        """Calculate Exponential Moving Average"""
        if len(prices) < period:
            return float(prices[-1])
        
        alpha = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return ema
    
    def calculate_bollinger_bands(self, prices: List[float]) -> Dict[str, float]:
        """Calculate Bollinger Bands"""
        if len(prices) < self.bb_period:
            current_price = prices[-1] if prices else 0
            return {
                "upper": current_price * 1.02,
                "middle": current_price,
                "lower": current_price * 0.98,
                "width": 0.04
            }
        
        prices = np.array(prices[-self.bb_period:])
        sma = np.mean(prices)
        std = np.std(prices)
        
        upper = sma + (self.bb_std * std)
        lower = sma - (self.bb_std * std)
        width = (upper - lower) / sma
        
        return {
            "upper": float(upper),
            "middle": float(sma),
            "lower": float(lower),
            "width": float(width)
        }
    
    def calculate_volatility(self, prices: List[float], period: int = 20) -> float:
        """Calculate price volatility"""
        if len(prices) < period:
            return 0.0
        
        prices = np.array(prices[-period:])
        returns = np.diff(prices) / prices[:-1]
        volatility = np.std(returns)
        
        return float(volatility)
    
    def generate_quick_signals(self, symbol: str) -> Dict[str, any]:
        """Generate quick trading signals for competition"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
            return {"signal": "HOLD", "strength": 0, "confidence": 0.5}
        
        # Check cache first
        if symbol in self.signal_cache:
            cache_age = time.time() - self.last_update.get(symbol, 0)
            if cache_age < 300:  # 5 minutes cache
                return self.signal_cache[symbol]
        
        prices = self.price_history[symbol]
        current_price = prices[-1]
        
        # Calculate indicators
        rsi = self.calculate_rsi(prices, self.rsi_period)
        macd_data = self.calculate_macd(prices)
        bb_data = self.calculate_bollinger_bands(prices)
        volatility = self.calculate_volatility(prices)
        
        # Generate signals
        signal, strength, confidence = self._combine_signals(
            rsi, macd_data, bb_data, volatility, current_price
        )
        
        result = {
            "signal": signal,
            "strength": strength,
            "confidence": confidence,
            "indicators": {
                "rsi": rsi,
                "macd": macd_data,
                "bollinger_bands": bb_data,
                "volatility": volatility
            },
            "timestamp": time.time()
        }
        
        # Cache the result
        self.signal_cache[symbol] = result
        return result
    
    def _combine_signals(self, rsi: float, macd: Dict, bb: Dict, 
                        volatility: float, current_price: float) -> Tuple[str, int, float]:
        """Combine all indicators into a single signal"""
        
        # Initialize scores
        buy_score = 0
        sell_score = 0
        total_confidence = 0
        
        # RSI Analysis
        if rsi < self.rsi_oversold:
            buy_score += 2
            total_confidence += 0.8
        elif rsi > self.rsi_overbought:
            sell_score += 2
            total_confidence += 0.8
        elif rsi < 45:
            buy_score += 1
            total_confidence += 0.6
        elif rsi > 55:
            sell_score += 1
            total_confidence += 0.6
        
        # MACD Analysis
        macd_line = macd["macd"]
        signal_line = macd["signal"]
        histogram = macd["histogram"]
        
        if macd_line > signal_line and histogram > self.macd_threshold:
            buy_score += 2
            total_confidence += 0.7
        elif macd_line < signal_line and histogram < -self.macd_threshold:
            sell_score += 2
            total_confidence += 0.7
        
        # Bollinger Bands Analysis
        bb_upper = bb["upper"]
        bb_lower = bb["lower"]
        bb_width = bb["width"]
        
        if current_price < bb_lower:
            buy_score += 1
            total_confidence += 0.6
        elif current_price > bb_upper:
            sell_score += 1
            total_confidence += 0.6
        
        # Volatility Analysis
        if volatility > self.volatility_threshold:
            # High volatility - more aggressive signals
            buy_score *= 1.2
            sell_score *= 1.2
            total_confidence += 0.3
        
        # Determine final signal
        signal_strength = abs(buy_score - sell_score)
        
        if buy_score > sell_score and signal_strength >= 2:
            signal = "BUY"
            strength = min(signal_strength, 5)
        elif sell_score > buy_score and signal_strength >= 2:
            signal = "SELL"
            strength = min(signal_strength, 5)
        else:
            signal = "HOLD"
            strength = 0
        
        # Calculate confidence (0-1)
        confidence = min(total_confidence / 4, 1.0)
        
        return signal, strength, confidence
    
    def get_momentum_direction(self, symbol: str) -> str:
        """Get momentum direction (BULLISH/BEARISH/NEUTRAL)"""
        signals = self.generate_quick_signals(symbol)
        
        if signals["signal"] == "BUY" and signals["strength"] >= 3:
            return "BULLISH"
        elif signals["signal"] == "SELL" and signals["strength"] >= 3:
            return "BEARISH"
        else:
            return "NEUTRAL"
    
    def detect_volatility_opportunity(self, symbol: str) -> bool:
        """Detect if there's a volatility opportunity"""
        if symbol not in self.price_history:
            return False
        
        volatility = self.calculate_volatility(self.price_history[symbol])
        return volatility > self.volatility_threshold
    
    def get_support_resistance(self, symbol: str) -> Dict[str, float]:
        """Get support and resistance levels"""
        if symbol not in self.price_history or len(self.price_history[symbol]) < 20:
            current_price = self.price_history.get(symbol, [0])[-1]
            return {
                "support": current_price * 0.95,
                "resistance": current_price * 1.05
            }
        
        prices = np.array(self.price_history[symbol])
        
        # Simple support/resistance calculation
        recent_prices = prices[-20:]
        support = np.percentile(recent_prices, 25)
        resistance = np.percentile(recent_prices, 75)
        
        return {
            "support": float(support),
            "resistance": float(resistance)
        }
    
    def get_competition_summary(self, symbol: str) -> Dict[str, any]:
        """Get comprehensive technical analysis summary for competition"""
        signals = self.generate_quick_signals(symbol)
        momentum = self.get_momentum_direction(symbol)
        volatility_opp = self.detect_volatility_opportunity(symbol)
        levels = self.get_support_resistance(symbol)
        
        return {
            "symbol": symbol,
            "signal": signals.get("signal", "HOLD"),
            "strength": signals.get("strength", 0),
            "confidence": signals.get("confidence", 0.5),
            "momentum": momentum,
            "volatility_opportunity": volatility_opp,
            "support_resistance": levels,
            "indicators": signals.get("indicators", {}),
            "recommendation": self._generate_recommendation(signals, momentum, volatility_opp)
        }
    
    def _generate_recommendation(self, signals: Dict, momentum: str, volatility_opp: bool) -> str:
        """Generate trading recommendation"""
        signal = signals["signal"]
        strength = signals["strength"]
        confidence = signals["confidence"]
        
        if signal == "BUY" and strength >= 3 and confidence >= 0.7:
            if volatility_opp:
                return "STRONG_BUY_VOLATILITY"
            else:
                return "STRONG_BUY"
        elif signal == "SELL" and strength >= 3 and confidence >= 0.7:
            if volatility_opp:
                return "STRONG_SELL_VOLATILITY"
            else:
                return "STRONG_SELL"
        elif signal == "BUY" and strength >= 2:
            return "BUY"
        elif signal == "SELL" and strength >= 2:
            return "SELL"
        else:
            return "HOLD"

# Global instance for easy access
TECHNICAL_ANALYZER = CompetitionTechnicalAnalyzer()
