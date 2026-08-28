"""Main Entry Point for SATS + Dynamic Swing Backtester

Runs the complete backtest pipeline.
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.sats_engine import SATSEngine
from src.dynamic_swing import DynamicSwingEngine
from src.strategy import StrategyStateMachine
from src.backtester import Backtester
from src.metrics import MetricsCalculator
from src.data_fetcher import DataFetcher, DataValidator


def create_sample_data():
    """Create sample BTC 15-minute data for demonstration.
    
    Since we don't have real data yet, create synthetic data with realistic patterns.
    """
    print("Creating sample synthetic BTC 15-minute data...")
    
    # Create date range: 2 years back from today
    start_date = pd.Timestamp('2024-08-28')
    end_date = pd.Timestamp('2026-08-28')
    timestamps = pd.date_range(start_date=start_date, end=end_date, freq='15min')
    
    # Generate synthetic price data with trend and volatility
    n = len(timestamps)
    np.random.seed(42)
    
    # Brownian motion with drift
    drift = 0.0001
    volatility = 0.002
    returns = np.random.normal(drift, volatility, n)
    prices = 42000 * np.exp(np.cumsum(returns))
    
    # Add some structure: create swings
    for i in range(0, n, 100):
        trend_direction = np.random.choice([-1, 1])
        for j in range(i, min(i + 50, n)):
            prices[j] *= (1 + trend_direction * 0.0001)
    
    # Generate OHLCV
    df = pd.DataFrame({
        'timestamp': timestamps,
        'open': prices,
        'high': prices * (1 + np.random.uniform(0, 0.005, n)),
        'low': prices * (1 - np.random.uniform(0, 0.005, n)),
        'close': prices * (1 + np.random.normal(0, 0.002, n)),
        'volume': np.random.uniform(100, 1000, n),
    })
    
    # Fix OHLC logic
    df['high'] = df[['open', 'high', 'low', 'close']].max(axis=1)
    df['low'] = df[['open', 'high', 'low', 'close']].min(axis=1)
    
    return df


def run_backtest(df: pd.DataFrame, initial_capital: float = 100000):
    """Run the backtest on provided OHLCV data.
    
    Args:
        df: DataFrame with columns: timestamp, open, high, low, close, volume
        initial_capital: starting capital in USD
    """
    print(f"\n{'='*70}")
    print("SATS + DYNAMIC SWING BACKTESTER")
    print(f"{'='*70}")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Data Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Total Bars: {len(df)}")
    print()
    
    # Validate data
    validator = DataValidator()
    validation_result = validator.validate(df, timeframe_minutes=15)
    validator.print_validation_report(validation_result)
    
    if not validation_result['valid']:
        print("WARNING: Data validation failed. Proceeding anyway...\n")
    
    # Initialize backtester and strategy
    backtester = Backtester(initial_capital=initial_capital)
    strategy = StrategyStateMachine(initial_equity=initial_capital)
    
    print("Running backtest...")
    
    # Main simulation loop
    for idx, row in df.iterrows():
        bar_index = idx
        timestamp = row['timestamp'].isoformat()
        ohlcv = {
            'open': row['open'],
            'high': row['high'],
            'low': row['low'],
            'close': row['close'],
            'volume': row['volume'],
        }
        
        # Update strategy (get signals)
        entry_signal, exit_signal = strategy.update(
            bar_index=bar_index,
            timestamp=timestamp,
            high=row['high'],
            low=row['low'],
            close=row['close'],
        )
        
        # Process bar in backtester
        entry_executed, exit_executed = backtester.process_bar(
            bar_index=bar_index,
            timestamp=timestamp,
            ohlcv=ohlcv,
            entry_signal=entry_signal,
            exit_signal=exit_signal,
        )
        
        # Show progress
        if (idx + 1) % 1000 == 0:
            print(f"  Processed {idx + 1}/{len(df)} bars...")
    
    print(f"\nBacktest complete! Processed {len(df)} bars.")
    print(f"Total trades: {len(backtester.trades)}")
    print()
    
    # Validate equity reconciliation
    if backtester.validate_equity_reconciliation():
        print("✓ Equity reconciliation PASSED")
    else:
        print("✗ Equity reconciliation FAILED")
    print()
    
    return backtester, strategy


def generate_reports(backtester: Backtester, df: pd.DataFrame, output_dir: str = 'outputs'):
    """Generate reports and charts.
    
    Args:
        backtester: completed backtester instance
        df: original OHLCV data
        output_dir: output directory path
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*70}")
    print("GENERATING REPORTS")
    print(f"{'='*70}")
    
    # Calculate metrics
    metrics = MetricsCalculator(
        trades=backtester.trades,
        equity_history=backtester.equity_history,
        initial_capital=backtester.initial_capital,
        data_timestamps=df['timestamp'].tolist(),
    )
    
    all_metrics = metrics.get_all_metrics()
    
    # Print metrics
    print("\nPERFORMANCE METRICS:")
    print("-" * 70)
    print(f"Initial Capital:        ${all_metrics['initial_capital']:>15,.2f}")
    print(f"Final Equity:           ${all_metrics['final_equity']:>15,.2f}")
    print(f"Net P&L:                ${all_metrics['net_pnl']:>15,.2f}")
    print(f"Total Return:           {all_metrics['total_return_pct']:>15.2f}%")
    print()
    print(f"Total Trades:           {all_metrics['num_trades']:>15}")
    print(f"  Long Trades:          {all_metrics['num_longs']:>15}")
    print(f"  Short Trades:         {all_metrics['num_shorts']:>15}")
    print(f"Winning Trades:         {all_metrics['winning_trades']:>15}")
    print(f"Losing Trades:          {all_metrics['losing_trades']:>15}")
    print(f"Win Rate:               {all_metrics['win_rate_pct']:>15.2f}%")
    print()
    print(f"Avg Winner:             ${all_metrics['avg_winner']:>15,.2f}")
    print(f"Avg Loser:              ${all_metrics['avg_loser']:>15,.2f}")
    print(f"Largest Winner:         ${all_metrics['largest_winner']:>15,.2f}")
    print(f"Largest Loser:          ${all_metrics['largest_loser']:>15,.2f}")
    print(f"Profit Factor:          {all_metrics['profit_factor']:>15.2f}")
    print()
    print(f"Expectancy (\$):        ${all_metrics['expectancy']:>15,.2f}")
    print(f"Expectancy (R):         {all_metrics['expectancy_r']:>15.2f}R")
    print(f"Max Drawdown:           {all_metrics['max_drawdown_pct']:>15.2f}%")
    print(f"Max DD Duration:        {all_metrics['max_drawdown_duration_bars']:>15} bars")
    print()
    print(f"Sharpe Ratio:           {all_metrics['sharpe_ratio']:>15.2f}")
    print(f"Sortino Ratio:          {all_metrics['sortino_ratio']:>15.2f}")
    print(f"Avg Holding Time:       {all_metrics['avg_holding_bars']:>15.0f} bars")
    print(f"Median Holding Time:    {all_metrics['median_holding_bars']:>15.0f} bars")
    print(f"Exposure:               {all_metrics['exposure_pct']:>15.2f}%")
    print()
    print(f"Long Win Rate:          {all_metrics['long_win_rate_pct']:>15.2f}%")
    print(f"Short Win Rate:         {all_metrics['short_win_rate_pct']:>15.2f}%")
    print(f"Long Avg P&L:           ${all_metrics['long_avg_pnl']:>15,.2f}")
    print(f"Short Avg P&L:          ${all_metrics['short_avg_pnl']:>15,.2f}")
    print()
    
    # Export trade log
    trade_df = metrics.to_dataframe()
    trade_log_path = os.path.join(output_dir, 'trade_log.csv')
    trade_df.to_csv(trade_log_path, index=False)
    print(f"✓ Trade log saved to: {trade_log_path}")
    
    # Generate equity curve chart
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    equity = np.array(backtester.equity_history)
    bars = np.arange(len(equity))
    
    axes[0].plot(bars, equity, label='Equity', linewidth=2, color='blue')
    axes[0].axhline(y=backtester.initial_capital, color='gray', linestyle='--', label='Initial Capital')
    axes[0].fill_between(bars, backtester.initial_capital, equity, alpha=0.3)
    axes[0].set_title('Equity Curve', fontsize=14, fontweight='bold')
    axes[0].set_ylabel('Equity ($)', fontsize=12)
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    # Drawdown chart
    drawdown = backtester.get_drawdown_curve()
    axes[1].fill_between(bars, drawdown, 0, alpha=0.5, color='red', label='Drawdown')
    axes[1].plot(bars, drawdown, color='darkred', linewidth=1)
    axes[1].set_title('Drawdown Curve', fontsize=14, fontweight='bold')
    axes[1].set_xlabel('Bar Index', fontsize=12)
    axes[1].set_ylabel('Drawdown (%)', fontsize=12)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    chart_path = os.path.join(output_dir, 'equity_drawdown.png')
    plt.tight_layout()
    plt.savefig(chart_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"✓ Equity chart saved to: {chart_path}")
    
    return all_metrics


def main():
    """Main entry point."""
    print("\n" + "="*70)
    print("SATS + DYNAMIC SWING ANCHORED VWAP BACKTESTER")
    print("Research-Grade Implementation")
    print("="*70 + "\n")
    
    # Load or create data
    data_file = 'data/processed/btc_15m.csv'
    if os.path.exists(data_file):
        print(f"Loading data from {data_file}...")
        df = DataFetcher.load_csv(data_file)
    else:
        print("Creating sample synthetic data for demonstration...")
        df = create_sample_data()
    
    # Run backtest
    backtester, strategy = run_backtest(df, initial_capital=100000)
    
    # Generate reports
    metrics = generate_reports(backtester, df)
    
    print("\n" + "="*70)
    print("BACKTEST COMPLETE")
    print("="*70)
    print(f"\nResults saved to: outputs/")
    print("  - trade_log.csv")
    print("  - equity_drawdown.png")
    print()


if __name__ == "__main__":
    main()
