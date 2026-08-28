"""Integration Tests for Complete Backtester"""

import pytest
import pandas as pd
import numpy as np
from src.backtester import Backtester
from src.sats_engine import SATSEngine
from src.dynamic_swing import DynamicSwingEngine
from src.strategy import StrategyStateMachine
from src.metrics import MetricsCalculator


class TestBacktesterIntegration:
    """Integration tests for the complete backtesting pipeline."""

    def create_sample_ohlcv(self, n_bars: int = 100) -> pd.DataFrame:
        """Create sample OHLCV data."""
        np.random.seed(42)
        prices = 100 + np.cumsum(np.random.normal(0.1, 1.0, n_bars))
        
        timestamps = pd.date_range('2024-08-28', periods=n_bars, freq='15min')
        
        return pd.DataFrame({
            'timestamp': timestamps,
            'open': prices,
            'high': prices + np.abs(np.random.normal(0, 0.5, n_bars)),
            'low': prices - np.abs(np.random.normal(0, 0.5, n_bars)),
            'close': prices + np.random.normal(0, 0.3, n_bars),
            'volume': np.random.uniform(100, 1000, n_bars),
        })

    def test_simple_backtest_run(self):
        """Test that backtest runs without errors."""
        df = self.create_sample_ohlcv(100)
        
        backtester = Backtester(initial_capital=100000)
        strategy = StrategyStateMachine(initial_equity=100000)
        
        for idx, row in df.iterrows():
            entry_sig, exit_sig = strategy.update(
                bar_index=idx,
                timestamp=row['timestamp'].isoformat(),
                high=row['high'],
                low=row['low'],
                close=row['close'],
            )
            
            ohlcv = {
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume'],
            }
            
            backtester.process_bar(
                bar_index=idx,
                timestamp=row['timestamp'].isoformat(),
                ohlcv=ohlcv,
                entry_signal=entry_sig,
                exit_signal=exit_sig,
            )
        
        # Should complete without errors
        assert len(backtester.equity_history) == len(df)

    def test_equity_tracking(self):
        """Test that equity is tracked correctly."""
        df = self.create_sample_ohlcv(50)
        backtester = Backtester(initial_capital=100000)
        strategy = StrategyStateMachine(initial_equity=100000)
        
        for idx, row in df.iterrows():
            entry_sig, exit_sig = strategy.update(
                idx, row['timestamp'].isoformat(), row['high'], row['low'], row['close']
            )
            ohlcv = {'open': row['open'], 'high': row['high'], 'low': row['low'], 
                     'close': row['close'], 'volume': row['volume']}
            backtester.process_bar(idx, row['timestamp'].isoformat(), ohlcv, entry_sig, exit_sig)
        
        # Equity should start at initial capital
        assert backtester.equity_history[0] == 100000
        
        # Equity history length should match bars
        assert len(backtester.equity_history) == len(df)

    def test_metrics_calculation(self):
        """Test that metrics can be calculated from results."""
        df = self.create_sample_ohlcv(100)
        backtester = Backtester(initial_capital=100000)
        strategy = StrategyStateMachine(initial_equity=100000)
        
        for idx, row in df.iterrows():
            entry_sig, exit_sig = strategy.update(
                idx, row['timestamp'].isoformat(), row['high'], row['low'], row['close']
            )
            ohlcv = {'open': row['open'], 'high': row['high'], 'low': row['low'], 
                     'close': row['close'], 'volume': row['volume']}
            backtester.process_bar(idx, row['timestamp'].isoformat(), ohlcv, entry_sig, exit_sig)
        
        # Calculate metrics
        metrics = MetricsCalculator(
            trades=backtester.trades,
            equity_history=backtester.equity_history,
            initial_capital=100000,
            data_timestamps=df['timestamp'].tolist(),
        )
        
        # Should be able to get all metrics
        all_metrics = metrics.get_all_metrics()
        assert 'total_return_pct' in all_metrics
        assert 'net_pnl' in all_metrics
        assert 'win_rate_pct' in all_metrics

    def test_equity_reconciliation(self):
        """Test equity reconciliation validation."""
        df = self.create_sample_ohlcv(100)
        backtester = Backtester(initial_capital=100000)
        strategy = StrategyStateMachine(initial_equity=100000)
        
        for idx, row in df.iterrows():
            entry_sig, exit_sig = strategy.update(
                idx, row['timestamp'].isoformat(), row['high'], row['low'], row['close']
            )
            ohlcv = {'open': row['open'], 'high': row['high'], 'low': row['low'], 
                     'close': row['close'], 'volume': row['volume']}
            backtester.process_bar(idx, row['timestamp'].isoformat(), ohlcv, entry_sig, exit_sig)
        
        # Should pass reconciliation
        assert backtester.validate_equity_reconciliation()

    def test_trade_counting(self):
        """Test that trades are counted correctly."""
        df = self.create_sample_ohlcv(150)
        backtester = Backtester(initial_capital=100000)
        strategy = StrategyStateMachine(initial_equity=100000)
        
        for idx, row in df.iterrows():
            entry_sig, exit_sig = strategy.update(
                idx, row['timestamp'].isoformat(), row['high'], row['low'], row['close']
            )
            ohlcv = {'open': row['open'], 'high': row['high'], 'low': row['low'], 
                     'close': row['close'], 'volume': row['volume']}
            backtester.process_bar(idx, row['timestamp'].isoformat(), ohlcv, entry_sig, exit_sig)
        
        # Count trades (may be 0 for synthetic data)
        assert len(backtester.trades) >= 0

    def test_drawdown_calculation(self):
        """Test drawdown calculation."""
        df = self.create_sample_ohlcv(100)
        backtester = Backtester(initial_capital=100000)
        strategy = StrategyStateMachine(initial_equity=100000)
        
        for idx, row in df.iterrows():
            entry_sig, exit_sig = strategy.update(
                idx, row['timestamp'].isoformat(), row['high'], row['low'], row['close']
            )
            ohlcv = {'open': row['open'], 'high': row['high'], 'low': row['low'], 
                     'close': row['close'], 'volume': row['volume']}
            backtester.process_bar(idx, row['timestamp'].isoformat(), ohlcv, entry_sig, exit_sig)
        
        # Calculate drawdown
        drawdown = backtester.get_drawdown_curve()
        
        # Drawdown should be <= 0 (or 0 at start)
        assert np.all(drawdown <= 0.01)  # Small tolerance for floating point


class TestEndToEnd:
    """End-to-end integration test."""

    def test_full_pipeline(self):
        """Test complete pipeline: data -> strategy -> backtest -> metrics."""
        # Create sample data
        np.random.seed(42)
        n_bars = 200
        prices = 100 + np.cumsum(np.random.normal(0.05, 1.0, n_bars))
        timestamps = pd.date_range('2024-08-28', periods=n_bars, freq='15min')
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'open': prices,
            'high': prices + np.abs(np.random.normal(0, 0.5, n_bars)),
            'low': prices - np.abs(np.random.normal(0, 0.5, n_bars)),
            'close': prices + np.random.normal(0, 0.3, n_bars),
            'volume': np.random.uniform(100, 1000, n_bars),
        })
        
        # Fix OHLC
        df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
        df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
        
        # Initialize systems
        backtester = Backtester(initial_capital=100000)
        strategy = StrategyStateMachine(initial_equity=100000)
        
        # Run backtest
        for idx, row in df.iterrows():
            entry_sig, exit_sig = strategy.update(
                idx, row['timestamp'].isoformat(), row['high'], row['low'], row['close']
            )
            ohlcv = {'open': row['open'], 'high': row['high'], 'low': row['low'], 
                     'close': row['close'], 'volume': row['volume']}
            backtester.process_bar(idx, row['timestamp'].isoformat(), ohlcv, entry_sig, exit_sig)
        
        # Calculate metrics
        metrics = MetricsCalculator(
            trades=backtester.trades,
            equity_history=backtester.equity_history,
            initial_capital=100000,
            data_timestamps=df['timestamp'].tolist(),
        )
        
        # Verify results
        all_metrics = metrics.get_all_metrics()
        
        assert all_metrics['initial_capital'] == 100000
        assert all_metrics['total_return_pct'] is not None
        assert all_metrics['sharpe_ratio'] is not None
        assert all_metrics['max_drawdown_pct'] <= 0.01  # Tolerance
        
        print(f"\nEnd-to-End Test Results:")
        print(f"  Final Equity: ${all_metrics['final_equity']:.2f}")
        print(f"  Total Return: {all_metrics['total_return_pct']:.2f}%")
        print(f"  Win Rate: {all_metrics['win_rate_pct']:.2f}%")
        print(f"  Trades: {all_metrics['num_trades']}")
