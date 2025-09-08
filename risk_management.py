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
        
        # Double down strategy tracking
        self.stop_loss_history = {}  # {symbol: {stop_price, stop_time, original_entry_price}}
        self.double_down_positions = {}  # {symbol: {entry_price, entry_time, amount, is_double_down}}
        
        # Scalping strategy tracking
        self.scalping_positions = {}  # {symbol: {entry_price, entry_time, amount, partial_sold, stop_price}}
        self.scalping_sell_history = {}  # {symbol: {sell_price, sell_time, amount_sold}}
        
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
    
    def check_exit_conditions(self, entry_price: float, current_price: float, highest_price: Optional[float] = None, symbol: str = None) -> Optional[str]:
        """
        Check if a position should be closed based on risk management rules
        
        :param entry_price: Entry price of the position
        :param current_price: Current market price
        :param highest_price: Highest price seen since entry (for trailing stop)
        :param symbol: Token symbol (for double down logic)
        :return: "STOP_LOSS", "TAKE_PROFIT", "TRAILING_STOP" or None
        """
        change = (current_price - entry_price) / entry_price
        
        # Check if this is a double down position (no stop loss)
        if symbol and symbol in self.double_down_positions:
            is_double_down = self.double_down_positions[symbol].get('is_double_down', False)
            if is_double_down:
                # Only check take profit for double down positions
                if change >= self.take_profit_pct:
                    return "TAKE_PROFIT"
                return None
        
        # Stop loss check (only for regular positions)
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
            position['highest_price'],
            symbol
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
        
        # Track stop loss events for double down strategy
        if reason == "STOP_LOSS":
            self.stop_loss_history[symbol] = {
                'stop_price': exit_price,
                'stop_time': time.time(),
                'original_entry_price': entry_price
            }
            print(f"📝 Stop loss recorded for {symbol}: ${exit_price:.4f}")
        
        # Remove from active positions
        del self.active_positions[symbol]
        
        print(f"📉 Position closed: {symbol}")
        print(f"   Entry: ${entry_price:.4f}, Exit: ${exit_price:.4f}")
        print(f"   P&L: ${pnl:.2f} ({pnl_pct:.2f}%)")
        print(f"   Reason: {reason}")
        
        return trade_record
    
    def check_double_down_opportunity(self, symbol: str, current_price: float) -> bool:
        """
        Check if a token qualifies for double down strategy
        Token must have had a stop loss and dropped 5% more from stop price
        
        :param symbol: Token symbol
        :param current_price: Current market price
        :return: True if double down opportunity exists
        """
        if symbol not in self.stop_loss_history:
            return False
        
        stop_data = self.stop_loss_history[symbol]
        stop_price = stop_data['stop_price']
        
        # Check if current price is 5% below stop price
        drop_from_stop = (stop_price - current_price) / stop_price
        if drop_from_stop >= 0.05:  # 5% drop from stop price
            print(f"🎯 Double down opportunity for {symbol}:")
            print(f"   Stop price: ${stop_price:.4f}")
            print(f"   Current price: ${current_price:.4f}")
            print(f"   Drop from stop: {drop_from_stop * 100:.2f}%")
            return True
        
        return False
    
    def open_double_down_position(self, symbol: str, entry_price: float, amount: float):
        """
        Open a double down position (no stop loss)
        
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
        
        # Mark as double down position
        self.double_down_positions[symbol] = {
            'entry_price': entry_price,
            'entry_time': time.time(),
            'amount': amount,
            'is_double_down': True
        }
        
        print(f"🔄 Double down position opened: {symbol} at ${entry_price:.4f}, amount: {amount:.4f}")
        print(f"   ⚠️  No stop loss for this position - only take profit at {self.take_profit_pct * 100:.1f}%")
        
        # Remove from stop loss history since we're re-entering
        if symbol in self.stop_loss_history:
            del self.stop_loss_history[symbol]
    
    def check_scalping_opportunities(self, symbol: str, current_price: float) -> dict:
        """
        Check for scalping strategy opportunities
        Returns dict with action type and details
        """
        if symbol not in self.scalping_positions:
            return {"action": None}
        
        position = self.scalping_positions[symbol]
        entry_price = position['entry_price']
        current_amount = position['amount'] - position.get('partial_sold', 0)
        
        # Calculate price changes
        rise_2_pct = entry_price * 1.02
        rise_5_pct = entry_price * 1.05
        drop_2_pct = entry_price * 0.98
        
        # Check for %5 rise -> full sell (priority over partial sell)
        if current_price >= (rise_5_pct - 0.01) and current_amount > 0:  # Small tolerance for floating point
            return {
                "action": "FULL_SELL",
                "amount": current_amount,
                "reason": "5% rise - full sell"
            }
        
        # Check for %2 rise -> %50 sell + stop loss
        if current_price >= (rise_2_pct - 0.01) and position.get('partial_sold', 0) == 0:  # Small tolerance
            return {
                "action": "PARTIAL_SELL",
                "amount": current_amount * 0.5,  # Sell 50%
                "stop_price": entry_price,
                "reason": "2% rise - partial sell + stop loss"
            }
        
        # Check for %2 drop -> rebuy (if partially sold)
        if current_price <= (drop_2_pct + 0.01) and position.get('partial_sold', 0) > 0:  # Small tolerance
            return {
                "action": "REBUY",
                "amount": position['partial_sold'],  # Rebuy the sold amount
                "reason": "2% drop - rebuy"
            }
        
        # Check for stop loss trigger
        if position.get('stop_price') and current_price <= position['stop_price']:
            return {
                "action": "STOP_LOSS",
                "amount": current_amount,
                "reason": "Stop loss triggered"
            }
        
        return {"action": None}
    
    def check_scalping_rebuy_opportunity(self, symbol: str, current_price: float) -> dict:
        """
        Check for rebuy opportunity after full sell (2% drop from sell price)
        """
        if symbol not in self.scalping_sell_history:
            return {"action": None}
        
        sell_data = self.scalping_sell_history[symbol]
        sell_price = sell_data['sell_price']
        
        # Check for 2% drop from sell price
        rebuy_price = sell_price * 0.98
        if current_price <= (rebuy_price + 0.01):  # Small tolerance for floating point
            return {
                "action": "REBUY_FROM_SELL",
                "amount": sell_data['amount_sold'],
                "reason": "2% drop from sell price - rebuy"
            }
        
        return {"action": None}
    
    def execute_scalping_action(self, symbol: str, action_data: dict, current_price: float):
        """
        Execute scalping action and update position tracking
        """
        action = action_data["action"]
        
        if action == "PARTIAL_SELL":
            # Update position tracking
            self.scalping_positions[symbol]['partial_sold'] = action_data['amount']
            self.scalping_positions[symbol]['stop_price'] = action_data['stop_price']
            print(f"📊 Scalping: {symbol} partial sell executed - 50% sold, stop at ${action_data['stop_price']:.4f}")
            
        elif action == "REBUY":
            # Reset partial sell tracking
            self.scalping_positions[symbol]['partial_sold'] = 0
            self.scalping_positions[symbol]['stop_price'] = None
            print(f"📊 Scalping: {symbol} rebuy executed - position restored")
            
        elif action == "FULL_SELL":
            # Record sell history for potential rebuy
            self.scalping_sell_history[symbol] = {
                'sell_price': current_price,
                'sell_time': time.time(),
                'amount_sold': action_data['amount']
            }
            # Remove from scalping positions
            del self.scalping_positions[symbol]
            print(f"📊 Scalping: {symbol} full sell executed at ${current_price:.4f}")
            
        elif action == "STOP_LOSS":
            # Remove from scalping positions
            del self.scalping_positions[symbol]
            print(f"📊 Scalping: {symbol} stop loss triggered at ${current_price:.4f}")
            
        elif action == "REBUY_FROM_SELL":
            # Open new scalping position
            self.scalping_positions[symbol] = {
                'entry_price': current_price,
                'entry_time': time.time(),
                'amount': action_data['amount'],
                'partial_sold': 0,
                'stop_price': None
            }
            # Remove from sell history
            del self.scalping_sell_history[symbol]
            print(f"📊 Scalping: {symbol} rebuy from sell executed at ${current_price:.4f}")
    
    def open_scalping_position(self, symbol: str, entry_price: float, amount: float):
        """
        Open a new scalping position
        """
        self.scalping_positions[symbol] = {
            'entry_price': entry_price,
            'entry_time': time.time(),
            'amount': amount,
            'partial_sold': 0,
            'stop_price': None
        }
        print(f"📊 Scalping position opened: {symbol} at ${entry_price:.4f}, amount: {amount:.4f}")
    
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
        Save all positions to file (active, scalping, double down)
        
        :param filename: Output filename
        """
        try:
            all_positions = {
                'active_positions': self.active_positions,
                'scalping_positions': self.scalping_positions,
                'double_down_positions': self.double_down_positions,
                'stop_loss_history': self.stop_loss_history,
                'scalping_sell_history': self.scalping_sell_history
            }
            with open(filename, 'w') as f:
                json.dump(all_positions, f, indent=2)
            print(f"💾 All positions saved to {filename}")
        except Exception as e:
            print(f"❌ Error saving positions: {e}")
    
    def load_positions(self, filename: str = 'positions.json'):
        """
        Load all positions from file (active, scalping, double down)
        
        :param filename: Input filename
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
                
            # Handle both old format (just active_positions) and new format (all positions)
            if isinstance(data, dict) and 'active_positions' in data:
                # New format with all position types
                self.active_positions = data.get('active_positions', {})
                self.scalping_positions = data.get('scalping_positions', {})
                self.double_down_positions = data.get('double_down_positions', {})
                self.stop_loss_history = data.get('stop_loss_history', {})
                self.scalping_sell_history = data.get('scalping_sell_history', {})
            else:
                # Old format - just active positions
                self.active_positions = data
                self.scalping_positions = {}
                self.double_down_positions = {}
                self.stop_loss_history = {}
                self.scalping_sell_history = {}
                
            print(f"📂 All positions loaded from {filename}")
        except Exception as e:
            print(f"❌ Error loading positions: {e}")
            self.active_positions = {}
            self.scalping_positions = {}
            self.double_down_positions = {}
            self.stop_loss_history = {}
            self.scalping_sell_history = {}
