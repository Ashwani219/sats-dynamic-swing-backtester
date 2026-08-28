"""Combined Strategy State Machine

Implements the exact SATS + Dynamic Swing strategy logic with explicit state tracking.
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple
from enum import Enum
from .sats_engine import SATSEngine, SATSState
from .dynamic_swing import DynamicSwingEngine, SwingPivot, PivotType


class StrategyState(Enum):
    """Strategy state machine states"""
    FLAT_WAIT_LONG = "FLAT_WAIT_LONG"
    LONG = "LONG"
    FLAT_WAIT_SHORT = "FLAT_WAIT_SHORT"
    SHORT = "SHORT"


class PositionDirection(Enum):
    """Position direction"""
    FLAT = 0
    LONG = 1
    SHORT = -1


@dataclass
class StrategyPosition:
    """Active trade position"""
    direction: PositionDirection
    entry_bar: int
    entry_price: float
    entry_timestamp: str
    equity_at_entry: float
    allocation_pct: float = 0.10  # 10% of equity
    quantity: float = 0.0
    notional: float = 0.0
    
    # Setup tracking
    setup_hl_bar: Optional[int] = None  # HL that created long setup
    setup_hh_bar: Optional[int] = None  # HH that created short setup
    setup_hl_price: Optional[float] = None
    setup_hh_price: Optional[float] = None
    
    # Entry signal tracking
    entry_buy_flip_bar: Optional[int] = None
    entry_sell_flip_bar: Optional[int] = None


@dataclass
class StrategyEvent:
    """Strategy event for logging"""
    bar_index: int
    timestamp: str
    event_type: str  # 'HL', 'HH', 'BUY_FLIP', 'SELL_FLIP', 'LONG_ENTRY', 'SHORT_ENTRY', 'LONG_EXIT', 'SHORT_EXIT', 'REVERSAL'
    price: float
    details: dict = field(default_factory=dict)


class StrategyStateMachine:
    """Combined SATS + Dynamic Swing strategy state machine.
    
    Entry:
    - LONG: HL (structure) → SATS BUY flip → entry at next open
    - SHORT: HH (structure) → SATS SELL flip → entry at next open
    
    Exit:
    - LONG exits on NEW HH (after entry) → check SATS state for reversal
    - SHORT exits on NEW HL (after entry) → check SATS state for reversal
    
    Reversal:
    - HH exit + SATS bearish → SHORT (next bar)
    - HL exit + SATS bullish → LONG (next bar)
    """

    def __init__(self, initial_equity: float = 100000, allocation_pct: float = 0.10):
        """Initialize strategy.
        
        Args:
            initial_equity: starting capital
            allocation_pct: % of equity per trade (default 10%)
        """
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.allocation_pct = allocation_pct
        
        # Engines
        self.sats = SATSEngine(source="hl2")
        self.swing = DynamicSwingEngine(swing_period=50)
        
        # State
        self.state = StrategyState.FLAT_WAIT_LONG
        self.position: Optional[StrategyPosition] = None
        
        # Setup tracking (for qualifying entry signals)
        self.latest_hl: Optional[SwingPivot] = None  # Latest HL pivot
        self.latest_hh: Optional[SwingPivot] = None  # Latest HH pivot
        self.latest_buy_flip_bar: int = -1  # Bar index of latest SATS BUY flip
        self.latest_sell_flip_bar: int = -1  # Bar index of latest SATS SELL flip
        
        # History
        self.events: list[StrategyEvent] = []
        self.sats_history: list[SATSState] = []
        self.swing_history: list = []

    def update(self, bar_index: int, timestamp: str, high: float, low: float, close: float) -> Tuple[Optional[dict], Optional[dict]]:
        """Update strategy for a new bar.
        
        Returns:
            (entry_signal, exit_signal) where each can be None
            entry_signal: {'direction': 'long'|'short', 'price': float, 'bar': int}
            exit_signal: {'direction': 'long'|'short', 'price': float, 'bar': int, 'reason': str}
        """
        entry_signal = None
        exit_signal = None
        
        # Update SATS
        sats_state = self.sats.update(high, low, close)
        self.sats_history.append(sats_state)
        
        # Track SATS flips
        if sats_state.flip_up:
            self.latest_buy_flip_bar = bar_index
        if sats_state.flip_down:
            self.latest_sell_flip_bar = bar_index
        
        # Update Dynamic Swing
        new_pivot = self.swing.update(high, low, close)
        if new_pivot:
            self.swing_history.append(new_pivot)
            
            # Log pivot
            self.events.append(StrategyEvent(
                bar_index=bar_index,
                timestamp=timestamp,
                event_type=new_pivot.pivot_type.value,
                price=new_pivot.price,
                details={'confirmation_bar': new_pivot.confirmation_bar}
            ))
            
            # Track latest HL/HH
            if new_pivot.pivot_type == PivotType.HL:
                self.latest_hl = new_pivot
            elif new_pivot.pivot_type == PivotType.HH:
                self.latest_hh = new_pivot
        
        # STATE MACHINE LOGIC
        
        # If position is active, check for exit
        if self.position and self.position.direction == PositionDirection.LONG:
            # LONG position: exit on NEW HH
            if self.latest_hh and self.latest_hh.confirmation_bar > self.position.entry_bar:
                # Closing LONG
                exit_signal = {
                    'direction': 'long',
                    'price': close,  # Exit at current close (will be next open in backtester)
                    'bar': bar_index,
                    'exit_bar_index': bar_index,
                    'reason': 'HH_exit',
                    'hh_price': self.latest_hh.price,
                }
                
                # Check SATS state for reversal
                if sats_state.trend == -1:  # BEARISH
                    # SHORT on next bar
                    entry_signal = {
                        'direction': 'short',
                        'price': close,
                        'bar': bar_index,
                        'reason': 'reversal_from_long_hh',
                        'sats_state': 'bearish',
                    }
                    self.state = StrategyState.SHORT
                else:  # BULLISH
                    self.state = StrategyState.FLAT_WAIT_SHORT
                    self.latest_hh = None  # Consume this HH
                
                self.position = None
        
        elif self.position and self.position.direction == PositionDirection.SHORT:
            # SHORT position: exit on NEW HL
            if self.latest_hl and self.latest_hl.confirmation_bar > self.position.entry_bar:
                # Closing SHORT
                exit_signal = {
                    'direction': 'short',
                    'price': close,
                    'bar': bar_index,
                    'exit_bar_index': bar_index,
                    'reason': 'HL_exit',
                    'hl_price': self.latest_hl.price,
                }
                
                # Check SATS state for reversal
                if sats_state.trend == 1:  # BULLISH
                    # LONG on next bar
                    entry_signal = {
                        'direction': 'long',
                        'price': close,
                        'bar': bar_index,
                        'reason': 'reversal_from_short_hl',
                        'sats_state': 'bullish',
                    }
                    self.state = StrategyState.FLAT_WAIT_LONG
                else:  # BEARISH
                    self.state = StrategyState.FLAT_WAIT_SHORT
                    self.latest_hl = None  # Consume this HL
                
                self.position = None
        
        # If no position, check for entry signals
        if not self.position:
            if self.state == StrategyState.FLAT_WAIT_LONG:
                # Waiting for HL then SATS BUY
                if self.latest_hl and self.latest_hl.confirmation_bar > (self.position.entry_bar if self.position else -1):
                    # HL confirmed, now wait for SATS BUY
                    if self.latest_buy_flip_bar > self.latest_hl.confirmation_bar:
                        # BUY flip after HL - ENTER LONG
                        entry_signal = {
                            'direction': 'long',
                            'price': close,
                            'bar': bar_index,
                            'reason': 'hl_sats_buy',
                            'hl_bar': self.latest_hl.confirmation_bar,
                            'hl_price': self.latest_hl.price,
                            'buy_flip_bar': self.latest_buy_flip_bar,
                        }
                        self.state = StrategyState.LONG
            
            elif self.state == StrategyState.FLAT_WAIT_SHORT:
                # Waiting for HH then SATS SELL
                if self.latest_hh and self.latest_hh.confirmation_bar > (self.position.entry_bar if self.position else -1):
                    # HH confirmed, now wait for SATS SELL
                    if self.latest_sell_flip_bar > self.latest_hh.confirmation_bar:
                        # SELL flip after HH - ENTER SHORT
                        entry_signal = {
                            'direction': 'short',
                            'price': close,
                            'bar': bar_index,
                            'reason': 'hh_sats_sell',
                            'hh_bar': self.latest_hh.confirmation_bar,
                            'hh_price': self.latest_hh.price,
                            'sell_flip_bar': self.latest_sell_flip_bar,
                        }
                        self.state = StrategyState.SHORT
        
        return entry_signal, exit_signal

    def open_position(self, bar_index: int, timestamp: str, direction: str, entry_price: float) -> StrategyPosition:
        """Open a new position.
        
        Args:
            direction: 'long' or 'short'
            entry_price: entry price (for next bar open)
        
        Returns:
            StrategyPosition object
        """
        pos_dir = PositionDirection.LONG if direction == 'long' else PositionDirection.SHORT
        notional = self.current_equity * self.allocation_pct
        quantity = notional / entry_price
        
        self.position = StrategyPosition(
            direction=pos_dir,
            entry_bar=bar_index,
            entry_price=entry_price,
            entry_timestamp=timestamp,
            equity_at_entry=self.current_equity,
            allocation_pct=self.allocation_pct,
            quantity=quantity,
            notional=notional,
        )
        
        self.events.append(StrategyEvent(
            bar_index=bar_index,
            timestamp=timestamp,
            event_type=f'{direction.upper()}_ENTRY',
            price=entry_price,
            details={'quantity': quantity, 'notional': notional}
        ))
        
        return self.position

    def close_position(self, bar_index: int, timestamp: str, exit_price: float, reason: str = 'structure'):
        """Close the active position.
        
        Args:
            exit_price: exit price
            reason: reason for exit
        """
        if not self.position:
            return
        
        direction_str = 'LONG' if self.position.direction == PositionDirection.LONG else 'SHORT'
        
        # Calculate P&L
        if self.position.direction == PositionDirection.LONG:
            pnl = (exit_price - self.position.entry_price) * self.position.quantity
        else:  # SHORT
            pnl = (self.position.entry_price - exit_price) * self.position.quantity
        
        self.current_equity += pnl
        
        self.events.append(StrategyEvent(
            bar_index=bar_index,
            timestamp=timestamp,
            event_type=f'{direction_str}_EXIT',
            price=exit_price,
            details={
                'pnl': pnl,
                'reason': reason,
                'entry_price': self.position.entry_price,
                'holding_bars': bar_index - self.position.entry_bar,
            }
        ))
        
        self.position = None
