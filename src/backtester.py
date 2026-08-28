"""Core Backtesting Engine

Bar-by-bar forward simulation with next-bar-open execution.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from datetime import datetime, timedelta


@dataclass
class TradeRecord:
    """Complete trade record"""
    trade_id: int
    direction: str  # 'long' or 'short'
    entry_bar: int
    entry_timestamp: str
    entry_price: float
    entry_equity: float
    quantity: float
    notional: float
    
    exit_bar: int
    exit_timestamp: str
    exit_price: float
    holding_bars: int
    holding_minutes: int
    
    gross_pnl: float
    commission: float
    slippage: float
    net_pnl: float
    pnl_pct: float
    return_pct: float
    
    exit_reason: str  # 'hl_structure', 'hh_structure', 'reversal', etc.
    exit_classification: str  # 'TP' if profitable, 'SL' if loss
    equity_after: float


class Backtester:
    """Core backtesting engine for SATS + Dynamic Swing strategy.
    
    Assumptions:
    - Entry/exit at next bar OPEN (confirmed signal on bar N, execute at bar N+1 open)
    - Commission: 0.05% per execution (entry + exit)
    - Slippage: 0.05% adverse per execution (entry + exit)
    - Position sizing: 10% of current equity per trade
    - No fixed stop loss or take profit (structure-based exits only)
    - Perpetual/leverage model (SHORT allowed)
    """

    def __init__(self, initial_capital: float = 100000, commission_pct: float = 0.05,
                 slippage_pct: float = 0.05, allocation_pct: float = 0.10):
        """Initialize backtester.
        
        Args:
            initial_capital: starting equity
            commission_pct: commission per execution (0.05 = 0.05%)
            slippage_pct: slippage per execution (0.05 = 0.05%)
            allocation_pct: allocation per trade (0.10 = 10%)
        """
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.allocation_pct = allocation_pct
        
        # State
        self.current_equity = initial_capital
        self.bar_index = 0
        
        # Trading
        self.trades: List[TradeRecord] = []
        self.trade_id = 0
        self.pending_entry: Optional[dict] = None  # Pending entry signal from previous bar
        self.pending_exit: Optional[dict] = None  # Pending exit signal from previous bar
        
        # History
        self.equity_history = [initial_capital]
        self.signal_log = []  # Detailed signal/state log

    def _apply_costs(self, nominal: float, cost_pct: float) -> float:
        """Apply commission and slippage to a trade.
        
        Args:
            nominal: nominal trade size
            cost_pct: commission + slippage %
        
        Returns:
            cost in dollars
        """
        return nominal * (cost_pct / 100.0)

    def process_bar(self, bar_index: int, timestamp: str, ohlcv: dict, 
                    entry_signal: Optional[dict], exit_signal: Optional[dict]) -> Tuple[bool, bool]:
        """Process a single bar.
        
        Args:
            bar_index: bar number
            timestamp: bar timestamp
            ohlcv: {'open', 'high', 'low', 'close', 'volume'}
            entry_signal: entry signal from strategy (or None)
            exit_signal: exit signal from strategy (or None)
        
        Returns:
            (entry_executed, exit_executed)
        """
        self.bar_index = bar_index
        open_price = ohlcv['open']
        close_price = ohlcv['close']
        
        entry_executed = False
        exit_executed = False
        
        # STEP 1: Execute pending exit from previous bar (next-bar-open)
        if self.pending_exit:
            exit_executed = self._execute_exit(timestamp, open_price, self.pending_exit)
            self.pending_exit = None
        
        # STEP 2: Execute pending entry from previous bar (next-bar-open)
        if self.pending_entry:
            entry_executed = self._execute_entry(timestamp, open_price, self.pending_entry)
            self.pending_entry = None
        
        # STEP 3: Queue exit signal for next bar
        if exit_signal and not entry_executed:  # Don't queue exit if we just entered
            self.pending_exit = exit_signal
        
        # STEP 4: Queue entry signal for next bar
        if entry_signal and not exit_executed:  # Don't queue entry if we just exited
            self.pending_entry = entry_signal
        
        # Update equity history
        self.equity_history.append(self.current_equity)
        
        return entry_executed, exit_executed

    def _execute_entry(self, timestamp: str, entry_price: float, entry_signal: dict) -> bool:
        """Execute a pending entry signal.
        
        Returns:
            True if executed
        """
        direction = entry_signal['direction']
        notional = self.current_equity * self.allocation_pct
        quantity = notional / entry_price
        
        # Apply entry costs
        entry_cost = self._apply_costs(notional, self.commission_pct + self.slippage_pct)
        self.current_equity -= entry_cost
        
        # Adjust entry price for slippage
        if direction == 'long':
            adjusted_entry = entry_price * (1.0 + self.slippage_pct / 100.0)
        else:  # short
            adjusted_entry = entry_price * (1.0 - self.slippage_pct / 100.0)
        
        # Store pending trade
        self.pending_trade = {
            'direction': direction,
            'entry_bar': entry_signal['bar'],
            'entry_timestamp': timestamp,
            'entry_price': adjusted_entry,
            'entry_equity': self.current_equity,
            'quantity': quantity,
            'notional': notional,
            'entry_cost': entry_cost,
            'entry_signal': entry_signal,
        }
        
        self.signal_log.append({
            'bar': entry_signal['bar'],
            'timestamp': timestamp,
            'event': f'{direction.upper()}_ENTRY',
            'price': adjusted_entry,
            'notional': notional,
            'reason': entry_signal.get('reason', 'signal'),
        })
        
        return True

    def _execute_exit(self, timestamp: str, exit_price: float, exit_signal: dict) -> bool:
        """Execute a pending exit signal.
        
        Returns:
            True if executed
        """
        if 'pending_trade' not in self.__dict__:
            return False
        
        trade_data = self.pending_trade
        direction = trade_data['direction']
        entry_bar = trade_data['entry_bar']
        entry_price = trade_data['entry_price']
        quantity = trade_data['quantity']
        notional = trade_data['notional']
        entry_equity = trade_data['entry_equity']
        
        # Apply exit costs
        exit_notional = exit_price * quantity
        exit_cost = self._apply_costs(exit_notional, self.commission_pct + self.slippage_pct)
        
        # Adjust exit price for slippage
        if direction == 'long':
            adjusted_exit = exit_price * (1.0 - self.slippage_pct / 100.0)
        else:  # short
            adjusted_exit = exit_price * (1.0 + self.slippage_pct / 100.0)
        
        # Calculate P&L
        if direction == 'long':
            gross_pnl = (adjusted_exit - entry_price) * quantity
        else:  # short
            gross_pnl = (entry_price - adjusted_exit) * quantity
        
        total_costs = trade_data['entry_cost'] + exit_cost
        net_pnl = gross_pnl - total_costs
        
        # Update equity
        self.current_equity += gross_pnl - exit_cost
        
        # Holding time
        holding_bars = exit_signal['exit_bar_index'] - entry_bar
        holding_minutes = holding_bars * 15  # 15-minute candles
        
        # Classification
        exit_classification = 'TP' if net_pnl > 0 else 'SL'
        if net_pnl == 0:
            exit_classification = 'BE'
        
        # Create trade record
        trade = TradeRecord(
            trade_id=len(self.trades) + 1,
            direction=direction,
            entry_bar=entry_bar,
            entry_timestamp=trade_data['entry_timestamp'],
            entry_price=entry_price,
            entry_equity=entry_equity,
            quantity=quantity,
            notional=notional,
            exit_bar=exit_signal['exit_bar_index'],
            exit_timestamp=timestamp,
            exit_price=adjusted_exit,
            holding_bars=holding_bars,
            holding_minutes=holding_minutes,
            gross_pnl=gross_pnl,
            commission=total_costs,
            slippage=exit_cost,
            net_pnl=net_pnl,
            pnl_pct=(net_pnl / notional) * 100 if notional > 0 else 0,
            return_pct=(net_pnl / entry_equity) * 100 if entry_equity > 0 else 0,
            exit_reason=exit_signal.get('reason', 'structure'),
            exit_classification=exit_classification,
            equity_after=self.current_equity,
        )
        
        self.trades.append(trade)
        
        self.signal_log.append({
            'bar': exit_signal['exit_bar_index'],
            'timestamp': timestamp,
            'event': f'{direction.upper()}_EXIT',
            'price': adjusted_exit,
            'pnl': net_pnl,
            'reason': exit_signal.get('reason', 'structure'),
            'classification': exit_classification,
        })
        
        # Clear pending trade
        del self.pending_trade
        
        return True

    def get_equity_curve(self) -> np.ndarray:
        """Get equity curve as numpy array."""
        return np.array(self.equity_history)

    def get_drawdown_curve(self) -> np.ndarray:
        """Get drawdown curve (peak-to-trough as %)."""
        equity = np.array(self.equity_history)
        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak * 100
        return drawdown

    def validate_equity_reconciliation(self) -> bool:
        """Validate that equity reconciles with trades.
        
        Returns:
            True if reconciliation passes
        """
        calculated_equity = self.initial_capital
        for trade in self.trades:
            calculated_equity += trade.net_pnl
        
        # Allow small floating point differences
        diff = abs(calculated_equity - self.current_equity)
        if diff > 0.01:  # $0.01 tolerance
            print(f"WARNING: Equity reconciliation failed. Diff: ${diff:.2f}")
            print(f"  Calculated: ${calculated_equity:.2f}")
            print(f"  Current: ${self.current_equity:.2f}")
            return False
        
        return True
