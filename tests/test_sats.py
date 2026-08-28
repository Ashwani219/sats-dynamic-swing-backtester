"""Unit Tests for SATS Engine"""

import numpy as np
import pytest
from src.sats_engine import SATSEngine, SATSState


class TestSATSEngine:
    """Test SATS engine implementation."""

    def test_initialization(self):
        """Test SATS engine initialization."""
        sats = SATSEngine(source="hl2")
        assert sats.trend == 1
        assert sats.atr_len == 14
        assert sats.base_mult == 2.8

    def test_hl2_source(self):
        """Test HL2 source calculation."""
        sats = SATSEngine(source="hl2")
        source = sats._get_source(high=100.0, low=90.0, close=95.0)
        assert source == 95.0  # (100 + 90) / 2

    def test_close_source(self):
        """Test close source."""
        sats = SATSEngine(source="close")
        source = sats._get_source(high=100.0, low=90.0, close=95.0)
        assert source == 95.0

    def test_hlc3_source(self):
        """Test HLC3 source."""
        sats = SATSEngine(source="hlc3")
        source = sats._get_source(high=100.0, low=90.0, close=95.0)
        assert source == pytest.approx((100 + 90 + 95) / 3)

    def test_single_bar_update(self):
        """Test update for single bar."""
        sats = SATSEngine()
        state = sats.update(high=100.0, low=90.0, close=95.0)
        
        assert state.bar_index == 0
        assert state.close == 95.0
        assert state.trend == 1
        assert not state.flip_up
        assert not state.flip_down

    def test_atr_calculation(self):
        """Test ATR is calculated (basic sanity check)."""
        sats = SATSEngine()
        
        # Add multiple bars
        for i in range(20):
            state = sats.update(high=100.0 + i, low=90.0 + i, close=95.0 + i)
        
        # ATR should be positive
        assert state.atr > 0

    def test_trend_persistence(self):
        """Test that trend persists across bars without flip."""
        sats = SATSEngine()
        
        # Add bars in uptrend
        for i in range(10):
            state = sats.update(high=100.0 + i, low=90.0 + i, close=95.0 + i)
        
        # Trend should still be bullish
        assert state.trend == 1
        assert not state.flip_up
        assert not state.flip_down

    def test_flip_detection(self):
        """Test flip detection on significant price move."""
        sats = SATSEngine()
        
        # Warmup with uptrend
        for i in range(30):
            state = sats.update(high=100.0 + i, low=90.0 + i, close=95.0 + i)
        
        assert state.trend == 1
        
        # Force downtrend (sharp drop)
        for i in range(5):
            state = sats.update(high=80.0 - i, low=70.0 - i, close=75.0 - i)
        
        # Should eventually flip to bearish
        assert state.trend == -1

    def test_multiple_bars_sequence(self):
        """Test sequence of bar updates."""
        sats = SATSEngine()
        
        prices = [
            (100, 90, 95),
            (102, 92, 98),
            (104, 94, 101),
            (106, 96, 103),
            (108, 98, 105),
        ]
        
        for high, low, close in prices:
            state = sats.update(high=high, low=low, close=close)
        
        assert state.bar_index == 4
        assert state.close == 105

    def test_history_tracking(self):
        """Test that history is tracked correctly."""
        sats = SATSEngine()
        
        for i in range(10):
            sats.update(high=100.0 + i, low=90.0 + i, close=95.0 + i)
        
        assert len(sats.history["close"]) == 10
        assert len(sats.history["high"]) == 10
        assert len(sats.history["low"]) == 10
        assert len(sats.history["trend"]) == 10
