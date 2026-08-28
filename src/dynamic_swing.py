"""Dynamic Swing Anchored VWAP Pivot Detection Engine

Exact replication of Dynamic Swing pivot detection with NO LOOKAHEAD.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum


class PivotType(Enum):
    """Pivot classification"""
    HH = "HH"  # Higher High
    HL = "HL"  # Higher Low (bullish reversal)
    LH = "LH"  # Lower High (bearish reversal)
    LL = "LL"  # Lower Low
    NONE = "NONE"


@dataclass
class SwingPivot:
    """A confirmed swing pivot"""
    bar_index: int  # bar where pivot is detected (was highest/lowest)
    confirmation_bar: int  # bar where confirmation occurred (dir changed)
    price: float
    pivot_type: PivotType
    direction: int  # 1 = uptrend now, -1 = downtrend now


class DynamicSwingEngine:
    """Dynamic Swing Pivot Detection Engine
    
    Preset parameters:
    - Swing Period: 50
    - Adaptive Price Tracking: 20
    - Adapt by ATR: False
    """

    def __init__(self, swing_period: int = 50):
        """Initialize Dynamic Swing engine.
        
        Args:
            swing_period: lookback for highest/lowest detection
        """
        self.swing_period = swing_period
        
        # State
        self.direction = 1  # 1 = uptrend, -1 = downtrend
        self.prev_direction = 1
        self.ph = np.nan  # pivot high price
        self.pl = np.nan  # pivot low price
        self.phL = 0  # bar index of pivot high
        self.plL = 0  # bar index of pivot low
        self.prev_pivot_price = np.nan  # previous cycle's pivot
        
        # History
        self.history = {
            "high": [],
            "low": [],
            "close": [],
            "direction": [],
            "pivot_high": [],
            "pivot_low": [],
        }
        
        # Confirmed pivots (only new events)
        self.confirmed_pivots: List[SwingPivot] = []
        self.last_pivot_index = -1

    def update(self, high: float, low: float, close: float) -> Optional[SwingPivot]:
        """Update Dynamic Swing state for a new bar.
        
        Returns:
            SwingPivot if a new pivot is confirmed on this bar, else None
        """
        bar_index = len(self.history["high"])
        
        # Store OHLC
        self.history["high"].append(high)
        self.history["low"].append(low)
        self.history["close"].append(close)
        
        # Check for new highest/lowest in lookback window
        highs = np.array(self.history["high"][-self.swing_period:])
        lows = np.array(self.history["low"][-self.swing_period:])
        
        highest_idx = np.argmax(highs)
        lowest_idx = np.argmin(lows)
        
        # Bars back from current (most recent bar is 0)
        bars_back_to_high = len(highs) - 1 - highest_idx
        bars_back_to_low = len(lows) - 1 - lowest_idx
        
        # Update pivot tracking
        if bars_back_to_high == 0:  # New high is at current bar
            self.ph = high
            self.phL = bar_index
        
        if bars_back_to_low == 0:  # New low is at current bar
            self.pl = low
            self.plL = bar_index
        
        # Update direction based on which pivot is more recent
        self.prev_direction = self.direction
        self.direction = 1 if self.phL > self.plL else -1
        self.history["direction"].append(self.direction)
        
        # Detect direction change (pivot confirmation)
        new_pivot = None
        if self.direction != self.prev_direction:
            # Direction changed - confirm the pivot
            if self.direction == 1:  # Now in uptrend, so low was pivot
                pivot_price = self.pl
                pivot_bar = self.plL
                
                # Classify: HL vs LL
                if np.isnan(self.prev_pivot_price):
                    pivot_type = PivotType.HL  # First pivot, assume HL
                else:
                    pivot_type = PivotType.HL if pivot_price > self.prev_pivot_price else PivotType.LL
                
                self.prev_pivot_price = self.ph  # For next cycle
            else:  # Now in downtrend, so high was pivot
                pivot_price = self.ph
                pivot_bar = self.phL
                
                # Classify: HH vs LH
                if np.isnan(self.prev_pivot_price):
                    pivot_type = PivotType.LH  # First pivot, assume LH
                else:
                    pivot_type = PivotType.HH if pivot_price > self.prev_pivot_price else PivotType.LH
                
                self.prev_pivot_price = self.pl  # For next cycle
            
            new_pivot = SwingPivot(
                bar_index=pivot_bar,
                confirmation_bar=bar_index,
                price=pivot_price,
                pivot_type=pivot_type,
                direction=self.direction,
            )
            
            self.confirmed_pivots.append(new_pivot)
            self.last_pivot_index = len(self.confirmed_pivots) - 1
        
        return new_pivot

    def get_latest_hl(self, after_bar: int = -1) -> Optional[SwingPivot]:
        """Get the latest HL (Higher Low) pivot confirmed AFTER given bar.
        
        Args:
            after_bar: only return HL confirmed at bar_index > after_bar (-1 = any)
        
        Returns:
            Latest HL or None
        """
        for pivot in reversed(self.confirmed_pivots):
            if pivot.pivot_type == PivotType.HL:
                if after_bar < 0 or pivot.confirmation_bar > after_bar:
                    return pivot
        return None

    def get_latest_hh(self, after_bar: int = -1) -> Optional[SwingPivot]:
        """Get the latest HH (Higher High) pivot confirmed AFTER given bar.
        
        Args:
            after_bar: only return HH confirmed at bar_index > after_bar (-1 = any)
        
        Returns:
            Latest HH or None
        """
        for pivot in reversed(self.confirmed_pivots):
            if pivot.pivot_type == PivotType.HH:
                if after_bar < 0 or pivot.confirmation_bar > after_bar:
                    return pivot
        return None

    def get_latest_lh(self, after_bar: int = -1) -> Optional[SwingPivot]:
        """Get the latest LH (Lower High) pivot confirmed AFTER given bar."""
        for pivot in reversed(self.confirmed_pivots):
            if pivot.pivot_type == PivotType.LH:
                if after_bar < 0 or pivot.confirmation_bar > after_bar:
                    return pivot
        return None

    def get_latest_ll(self, after_bar: int = -1) -> Optional[SwingPivot]:
        """Get the latest LL (Lower Low) pivot confirmed AFTER given bar."""
        for pivot in reversed(self.confirmed_pivots):
            if pivot.pivot_type == PivotType.LL:
                if after_bar < 0 or pivot.confirmation_bar > after_bar:
                    return pivot
        return None
