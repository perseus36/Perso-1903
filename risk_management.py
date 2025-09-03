import json
import time
from typing import Dict, Optional, Tuple

class RiskManager:
    def __init__(self, stop_loss_pct=-0.07, take_profit_pct=0.10, trailing_stop_pct=0.05, max_position_pct=0.10):
        """
        Risk management system for Perso-1903 trading agent
        
        :param stop_loss_pct: Stop loss threshold (e.g., -0.07 = 7% loss)
        :param take_profit_pct: Take profit threshold (e.g., 0.10 = 10% profit)
        :param trailing_stop_pct: Trailing stop percentage when in profit (e.g., 0.05 = 5%)
        :param max_position_pct: Maximum portfolio percentage for a single trade
        """
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.max_position_pct = max_position_pct
        
        # Track active positions
        self.active_positions = {}  # {symbol: {entry_price, entry_time, highest_price, amount}}
        
    def calculate_position_size(self, portfolio_value: float, price: float) -> float:
        """
        Calculate maximum position size based on portfolio value and risk parameters
        
        :param portfolio_value: Total portfolio value in USD
        :param price: Current token price
        :return: Maximum position size in token units
        """
        max_position_value = portfolio_value * self.max_position_pct
        size = max_position_value / price
        return size
    
    def check_exit_conditions(self, entry_price: float, current_price: float, highest_price: Optional[float] = None) -> Optional[str]:
        """
        Check if a position should be closed based on risk management rules
        
        :param entry_price: Entry price of the position
        :param current_price: Current market price
        :param highest_price: Highest price seen since entry (for trailing stop)
        :return: "STOP_LOSS", "TAKE_PROFIT", "TRAILING_STOP" or None
        """
        change = (current_price - entry_price) / entry_price
        
        # Stop loss check
        if change <= self.stop_loss_pct:
            return "STOP_LOSS"
        
        # Take profit check
        if change >= self.take_profit_pct:
            return "TAKE_PROFIT"
        
        # Trailing stop check
        if highest_price is not None:
            drawdown = (current_price - highest_price) / highest_price
            if drawdown <= -self.trailing_stop_pct:
                return "TRAILING_STOP"
        
        return None
    
    def open_position(self, symbol: str, entry_price: float, amount: float):
        """
        Record a new position opening
        
        :param symbol: Token symbol
        :param entry_price: Entry price
        :param amount: Position size
        """
        self.active_positions[symbol] = {
            'entry_price': entry_price,
            'entry_time': time.time(),
            'highest_price': entry_price,
            'amount': amount
        }
        print(f"📈 Position opened: {symbol} at ${entry_price:.4f}, amount: {amount:.4f}")
    
    def update_position(self, symbol: str, current_price: float):
        """
        Update position tracking with current price
        
        :param symbol: Token symbol
        :param current_price: Current market price
        :return: Exit condition if triggered, None otherwise
        """
        if symbol not in self.active_positions:
            return None
        
        position = self.active_positions[symbol]
        entry_price = position['entry_price']
        
        # Update highest price if current price is higher
        if current_price > position['highest_price']:
            position['highest_price'] = current_price
        
        # Check exit conditions
        exit_condition = self.check_exit_conditions(
            entry_price, 
            current_price, 
            position['highest_price']
        )
        
        if exit_condition:
            print(f"🚨 Exit condition triggered for {symbol}: {exit_condition}")
            print(f"   Entry: ${entry_price:.4f}, Current: ${current_price:.4f}")
            print(f"   Change: {((current_price - entry_price) / entry_price) * 100:.2f}%")
        
        return exit_condition
    
    def close_position(self, symbol: str, exit_price: float, reason: str):
        """
        Close a position and record the trade
        
        :param symbol: Token symbol
        :param exit_price: Exit price
        :param reason: Reason for closing (STOP_LOSS, TAKE_PROFIT, etc.)
        """
        if symbol not in self.active_positions:
            return None
        
        position = self.active_positions[symbol]
        entry_price = position['entry_price']
        amount = position['amount']
        
        # Calculate P&L
        pnl = (exit_price - entry_price) * amount
        pnl_pct = (exit_price - entry_price) / entry_price * 100
        
        # Record trade
        trade_record = {
            'symbol': symbol,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'amount': amount,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'reason': reason,
            'entry_time': position['entry_time'],
            'exit_time': time.time(),
            'duration': time.time() - position['entry_time']
        }
        
        # Remove from active positions
        del self.active_positions[symbol]
        
        print(f"📉 Position closed: {symbol}")
        print(f"   Entry: ${entry_price:.4f}, Exit: ${exit_price:.4f}")
        print(f"   P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")
        print(f"   Reason: {reason}")
        
        return trade_record
    
    def get_active_positions(self) -> Dict:
        """
        Get all currently active positions
        
        :return: Dictionary of active positions
        """
        return self.active_positions.copy()
    
    def get_position_summary(self) -> Dict:
        """
        Get summary of all active positions
        
        :return: Summary statistics
        """
        if not self.active_positions:
            return {'total_positions': 0, 'total_value': 0}
        
        total_positions = len(self.active_positions)
        total_value = sum(pos['amount'] * pos['entry_price'] for pos in self.active_positions.values())
        
        return {
            'total_positions': total_positions,
            'total_value': total_value,
            'positions': self.active_positions
        }
    
    def save_positions(self, filename: str = 'positions.json'):
        """
        Save active positions to file
        
        :param filename: Output filename
        """
        try:
            with open(filename, 'w') as f:
                json.dump(self.active_positions, f, indent=2)
            print(f"💾 Positions saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving positions: {e}")
    
    def load_positions(self, filename: str = 'positions.json'):
        """
        Load active positions from file
        
        :param filename: Input filename
        """
        try:
            with open(filename, 'r') as f:
                self.active_positions = json.load(f)
            print(f"📂 Positions loaded from {filename}")
        except Exception as e:
            print(f"❌ Error loading positions: {e}")
            self.active_positions = {}
