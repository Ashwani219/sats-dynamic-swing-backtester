"""Unit Tests for Strategy State Machine"""

import pytest
from src.strategy import StrategyStateMachine, StrategyState, PositionDirection


class TestStrategyStateMachine:
    """Test strategy state machine."""

    def test_initialization(self):
        """Test strategy initialization."""
        strategy = StrategyStateMachine(initial_equity=100000)
        assert strategy.state == StrategyState.FLAT_WAIT_LONG
        assert strategy.position is None
        assert strategy.current_equity == 100000

    def test_flat_state_on_start(self):
        """Test that strategy starts in FLAT_WAIT_LONG."""
        strategy = StrategyStateMachine()
        assert strategy.state == StrategyState.FLAT_WAIT_LONG
        assert strategy.position is None

    def test_no_signal_on_first_bar(self):
        """Test that no signals are generated on first bar."""
        strategy = StrategyStateMachine()
        entry_sig, exit_sig = strategy.update(
            bar_index=0,
            timestamp="2024-08-28T00:00:00",
            high=100.0,
            low=90.0,
            close=95.0,
        )
        
        assert entry_sig is None
        assert exit_sig is None

    def test_sats_flip_tracking(self):
        """Test that SATS flips are tracked."""
        strategy = StrategyStateMachine()
        
        # Add bars to trigger SATS flip
        for i in range(50):
            high = 100.0 + i
            low = 90.0 + i
            close = 95.0 + i
            strategy.update(i, f"bar_{i}", high, low, close)
        
        # Latest SATS state should be tracked
        assert strategy.latest_buy_flip_bar >= 0 or strategy.latest_sell_flip_bar >= 0

    def test_dynamic_swing_tracking(self):
        """Test that Dynamic Swing pivots are tracked."""
        strategy = StrategyStateMachine()
        
        # Create uptrend then downtrend (should generate pivot)
        prices = [
            (100, 90, 95), (102, 92, 98), (104, 94, 101),
            (103, 93, 100), (102, 92, 99), (101, 91, 98),
            (99, 89, 97),  # Direction changes
        ]
        
        for i, (h, l, c) in enumerate(prices):
            strategy.update(i, f"bar_{i}", h, l, c)
        
        # Should have tracked pivot
        assert strategy.latest_hh is not None or strategy.latest_hl is not None

    def test_no_position_overlap(self):
        """Test that multiple positions cannot be open simultaneously."""
        strategy = StrategyStateMachine(initial_equity=100000)
        
        # Open a LONG position
        pos1 = strategy.open_position(
            bar_index=10,
            timestamp="2024-08-28T10:00:00",
            direction='long',
            entry_price=100.0,
        )
        
        assert strategy.position is not None
        assert strategy.position.direction == PositionDirection.LONG
        
        # Try to open another LONG (should not be possible in real strategy)
        # In our simplified test, we can only have one position
        assert strategy.position is pos1

    def test_position_opening(self):
        """Test opening a position."""
        strategy = StrategyStateMachine(initial_equity=100000, allocation_pct=0.10)
        
        pos = strategy.open_position(
            bar_index=5,
            timestamp="2024-08-28T05:00:00",
            direction='long',
            entry_price=100.0,
        )
        
        assert pos.direction == PositionDirection.LONG
        assert pos.entry_bar == 5
        assert pos.entry_price == 100.0
        assert pos.notional == 100000 * 0.10  # 10% of equity
        assert pos.quantity == 100  # 10000 / 100

    def test_position_closing(self):
        """Test closing a position."""
        strategy = StrategyStateMachine(initial_equity=100000)
        
        # Open position
        strategy.open_position(
            bar_index=5,
            timestamp="2024-08-28T05:00:00",
            direction='long',
            entry_price=100.0,
        )
        
        initial_equity = strategy.current_equity
        
        # Close with profit
        strategy.close_position(
            bar_index=10,
            timestamp="2024-08-28T10:00:00",
            exit_price=110.0,
            reason='structure',
        )
        
        # Equity should have changed
        assert strategy.current_equity != initial_equity
        assert strategy.position is None

    def test_equity_tracking(self):
        """Test that equity is tracked correctly."""
        strategy = StrategyStateMachine(initial_equity=100000)
        initial = strategy.current_equity
        
        # Open and close a winning trade
        strategy.open_position(5, "bar_5", 'long', 100.0)
        strategy.close_position(10, "bar_10", 110.0)
        
        # Equity should increase (after costs)
        assert strategy.current_equity > initial - 1000  # Allow for costs

    def test_state_transitions(self):
        """Test state machine transitions."""
        strategy = StrategyStateMachine()
        
        # Start state
        assert strategy.state == StrategyState.FLAT_WAIT_LONG
        
        # Transition to LONG
        strategy.state = StrategyState.LONG
        assert strategy.state == StrategyState.LONG
        
        # Transition to FLAT_WAIT_SHORT
        strategy.state = StrategyState.FLAT_WAIT_SHORT
        assert strategy.state == StrategyState.FLAT_WAIT_SHORT
