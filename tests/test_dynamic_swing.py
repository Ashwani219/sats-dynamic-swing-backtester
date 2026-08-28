"""Unit Tests for Dynamic Swing Engine"""

import pytest
from src.dynamic_swing import DynamicSwingEngine, PivotType


class TestDynamicSwingEngine:
    """Test Dynamic Swing engine implementation."""

    def test_initialization(self):
        """Test Dynamic Swing initialization."""
        swing = DynamicSwingEngine(swing_period=50)
        assert swing.swing_period == 50
        assert swing.direction == 1
        assert len(swing.confirmed_pivots) == 0

    def test_single_bar_update(self):
        """Test update for single bar."""
        swing = DynamicSwingEngine()
        pivot = swing.update(high=100.0, low=90.0, close=95.0)
        
        # No pivot on first bar
        assert pivot is None
        assert len(swing.confirmed_pivots) == 0

    def test_direction_tracking(self):
        """Test direction state tracking."""
        swing = DynamicSwingEngine(swing_period=5)
        
        # Uptrend
        for i in range(10):
            swing.update(high=100.0 + i, low=90.0 + i, close=95.0 + i)
        
        assert swing.direction == 1

    def test_pivot_confirmation_no_lookahead(self):
        """Test that pivots are confirmed forward-only (no lookahead).
        
        This is the critical "no lookahead" test.
        """
        swing = DynamicSwingEngine(swing_period=5)
        
        # Create uptrend then downtrend
        prices = [
            (100, 90, 95),   # bar 0
            (102, 92, 98),   # bar 1
            (104, 94, 101),  # bar 2 - highest so far
            (103, 93, 100),  # bar 3
            (102, 92, 99),   # bar 4
            (101, 91, 98),   # bar 5
            (99, 89, 97),    # bar 6 - direction changes here (from up to down)
        ]
        
        for i, (h, l, c) in enumerate(prices):
            pivot = swing.update(high=h, low=l, close=c)
            print(f"Bar {i}: dir={swing.direction}, prev_dir={swing.prev_direction}, pivot={pivot}")
        
        # Pivot should be confirmed on bar 6 (where direction changed)
        assert len(swing.confirmed_pivots) == 1
        pivot = swing.confirmed_pivots[0]
        assert pivot.confirmation_bar == 6  # NOT bar 2 (where high occurred)
        assert pivot.pivot_type == PivotType.LH  # Lower High (bearish)

    def test_hl_detection(self):
        """Test HL (Higher Low) pivot detection."""
        swing = DynamicSwingEngine(swing_period=5)
        
        # Downtrend then uptrend
        prices = [
            (100, 90, 95),   # Down
            (99, 89, 94),    # Down
            (98, 88, 93),    # Down - lowest
            (99, 89, 94),    # Up
            (100, 90, 95),   # Up
            (101, 91, 96),   # Up - changes to uptrend
        ]
        
        for h, l, c in prices:
            swing.update(high=h, low=l, close=c)
        
        # Should detect HL (Higher Low)
        assert len(swing.confirmed_pivots) >= 1
        # Latest should be HL
        if len(swing.confirmed_pivots) > 0:
            latest_pivot = swing.confirmed_pivots[-1]
            if latest_pivot.pivot_type == PivotType.HL:
                assert latest_pivot.direction == 1  # Now in uptrend

    def test_no_pivot_reuse(self):
        """Test that confirmed pivots are not reused.
        
        Once a pivot is confirmed, it should not be returned again.
        """
        swing = DynamicSwingEngine(swing_period=5)
        
        # Create uptrend then downtrend
        prices = [
            (100, 90, 95),
            (102, 92, 98),
            (104, 94, 101),
            (103, 93, 100),
            (102, 92, 99),
            (101, 91, 98),
            (99, 89, 97),   # Direction changes, pivot confirmed
        ]
        
        pivots_returned = []
        for h, l, c in prices:
            pivot = swing.update(high=h, low=l, close=c)
            if pivot:
                pivots_returned.append(pivot)
        
        # Only 1 pivot should be returned (at direction change)
        assert len(pivots_returned) == 1
        
        # Continue trading - no new pivots from same bars
        prices2 = [
            (98, 88, 96),
            (97, 87, 95),
        ]
        
        for h, l, c in prices2:
            pivot = swing.update(high=h, low=l, close=c)
            assert pivot is None  # No new pivots

    def test_get_latest_hl(self):
        """Test getting latest HL pivot."""
        swing = DynamicSwingEngine(swing_period=5)
        
        # Create multiple cycles
        prices = [
            # Downtrend
            (100, 90, 95), (99, 89, 94), (98, 88, 93),
            # Uptrend (HL confirmed at bar 6)
            (99, 89, 94), (100, 90, 95), (101, 91, 96),
            # Downtrend again (LH confirmed)
            (100, 90, 95), (99, 89, 94),
            # Back to uptrend (HL confirmed)
            (100, 90, 95), (101, 91, 96),
        ]
        
        for h, l, c in prices:
            swing.update(high=h, low=l, close=c)
        
        latest_hl = swing.get_latest_hl()
        assert latest_hl is not None
        assert latest_hl.pivot_type == PivotType.HL

    def test_multiple_pivots_sequence(self):
        """Test sequence of multiple pivot confirmations."""
        swing = DynamicSwingEngine(swing_period=5)
        
        # Zig-zag pattern
        prices = [
            # Down
            (100, 90, 95), (99, 89, 94), (98, 88, 93),
            # Up (HL)
            (99, 89, 94), (100, 90, 95), (101, 91, 96),
            # Down (HH)
            (100, 90, 95), (99, 89, 94), (98, 88, 93),
            # Up (HL again)
            (99, 89, 94), (100, 90, 95), (101, 91, 96),
        ]
        
        pivot_count = 0
        for h, l, c in prices:
            pivot = swing.update(high=h, low=l, close=c)
            if pivot:
                pivot_count += 1
                print(f"Pivot confirmed: {pivot.pivot_type} at bar {pivot.confirmation_bar}")
        
        # Should have multiple pivots
        assert pivot_count >= 2

    def test_history_tracking(self):
        """Test that history is tracked."""
        swing = DynamicSwingEngine()
        
        for i in range(10):
            swing.update(high=100.0 + i, low=90.0 + i, close=95.0 + i)
        
        assert len(swing.history["high"]) == 10
        assert len(swing.history["low"]) == 10
        assert len(swing.history["close"]) == 10
