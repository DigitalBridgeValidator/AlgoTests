"""
Simple Test Strategy for backtesting

This is a very basic strategy that:
- Goes long every X candles
- Sets a simple take profit and stop loss
- Used for testing backtesting functionality
"""

from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class SimpleTestStrategy(Strategy):

    def hyperparameters(self):
        return [
            {'name': 'entry_frequency', 'type': int, 'min': 5, 'max': 30, 'default': 10},
            {'name': 'stop_loss', 'type': float, 'min': 0.95, 'max': 0.99, 'default': 0.97},
            {'name': 'take_profit', 'type': float, 'min': 1.01, 'max': 1.10, 'default': 1.05},
        ]

    def should_long(self):
        # Enter a trade every X candles if we're not already in a position
        if self.index % self.hp['entry_frequency'] == 0:
            return True
        
        return False

    def should_short(self):
        return False

    def should_cancel_entry(self):
        return False

    def go_long(self):
        # Calculate position size (risking 2% of portfolio per trade)
        entry = self.price
        stop = entry * self.hp['stop_loss']
        qty = self.position_sizing_percent(2, entry, stop)
        
        # Enter position
        self.buy = qty, self.price
        
        # Set stop loss only (take profit will be set in on_open_position)
        self.stop_loss = qty, stop

    def go_short(self):
        pass

    def update_position(self):
        # Example of trailing stop (not used here)
        pass
        
    def on_open_position(self, order):
        """Called when a position is opened"""
        # Set take profit for spot trading
        if self.is_long:
            entry = self.position.entry_price
            self.take_profit = self.position.qty, (entry * self.hp['take_profit'])
        
    def position_sizing_percent(self, risk_percentage, entry_price, stop_price):
        """
        Calculate the quantity based on the percentage of balance to risk
        """
        # Calculate capital at risk
        capital_at_risk = self.balance * (risk_percentage / 100)
        
        # Calculate risk per unit
        risk_per_unit = abs(entry_price - stop_price)
        
        # Calculate the position size
        if risk_per_unit == 0:
            return 0
            
        return capital_at_risk / risk_per_unit