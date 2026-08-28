"""Performance Metrics Calculator

Computes comprehensive performance statistics.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from .backtester import TradeRecord


class MetricsCalculator:
    """Calculate performance metrics from backtest results."""

    def __init__(self, trades: List[TradeRecord], equity_history: List[float],
                 initial_capital: float, data_timestamps: List[str]):
        """Initialize metrics calculator.
        
        Args:
            trades: list of TradeRecord
            equity_history: equity curve
            initial_capital: starting capital
            data_timestamps: list of bar timestamps
        """
        self.trades = trades
        self.equity = np.array(equity_history)
        self.initial_capital = initial_capital
        self.timestamps = data_timestamps

    def total_return(self) -> float:
        """Total return as percentage."""
        if len(self.equity) == 0:
            return 0.0
        final_equity = self.equity[-1]
        return ((final_equity - self.initial_capital) / self.initial_capital) * 100

    def net_pnl(self) -> float:
        """Total net P&L in dollars."""
        return self.equity[-1] - self.initial_capital if len(self.equity) > 0 else 0.0

    def num_trades(self) -> int:
        """Total number of trades."""
        return len(self.trades)

    def num_longs(self) -> int:
        """Number of long trades."""
        return sum(1 for t in self.trades if t.direction == 'long')

    def num_shorts(self) -> int:
        """Number of short trades."""
        return sum(1 for t in self.trades if t.direction == 'short')

    def winning_trades(self) -> int:
        """Number of winning trades."""
        return sum(1 for t in self.trades if t.net_pnl > 0)

    def losing_trades(self) -> int:
        """Number of losing trades."""
        return sum(1 for t in self.trades if t.net_pnl < 0)

    def win_rate(self) -> float:
        """Win rate as percentage."""
        if len(self.trades) == 0:
            return 0.0
        return (self.winning_trades() / len(self.trades)) * 100

    def average_winner(self) -> float:
        """Average profit per winning trade."""
        winners = [t.net_pnl for t in self.trades if t.net_pnl > 0]
        return np.mean(winners) if len(winners) > 0 else 0.0

    def average_loser(self) -> float:
        """Average loss per losing trade."""
        losers = [t.net_pnl for t in self.trades if t.net_pnl < 0]
        return np.mean(losers) if len(losers) > 0 else 0.0

    def largest_winner(self) -> float:
        """Largest profit."""
        if len(self.trades) == 0:
            return 0.0
        return max([t.net_pnl for t in self.trades])

    def largest_loser(self) -> float:
        """Largest loss."""
        if len(self.trades) == 0:
            return 0.0
        return min([t.net_pnl for t in self.trades])

    def profit_factor(self) -> float:
        """Ratio of gross profit to gross loss."""
        gross_profit = sum(t.gross_pnl for t in self.trades if t.gross_pnl > 0)
        gross_loss = abs(sum(t.gross_pnl for t in self.trades if t.gross_pnl < 0))
        
        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0
        return gross_profit / gross_loss

    def expectancy(self) -> float:
        """Expected value per trade in dollars."""
        if len(self.trades) == 0:
            return 0.0
        return np.mean([t.net_pnl for t in self.trades])

    def expectancy_r(self) -> float:
        """Expected value per trade in R (risk units).
        
        Simplified: uses average risk = average loss magnitude
        """
        avg_loss = self.average_loser()
        if avg_loss == 0:
            return 0.0
        risk_per_trade = abs(avg_loss)
        return self.expectancy() / risk_per_trade

    def max_drawdown(self) -> Tuple[float, int]:
        """Maximum drawdown as percentage and bars.
        
        Returns:
            (max_dd_pct, duration_bars)
        """
        peak = np.maximum.accumulate(self.equity)
        drawdown = (self.equity - peak) / peak
        max_dd = np.min(drawdown)
        max_dd_pct = max_dd * 100
        
        # Find duration of max drawdown
        dd_idx = np.argmin(drawdown)
        peak_idx = np.argmax(self.equity[:dd_idx + 1])
        duration = dd_idx - peak_idx
        
        return max_dd_pct, duration

    def sharpe_ratio(self, rf_rate: float = 0.02) -> float:
        """Sharpe ratio (annualized).
        
        Assumes daily returns and 252 trading days.
        """
        if len(self.equity) < 2:
            return 0.0
        
        returns = np.diff(self.equity) / self.equity[:-1]
        excess_returns = returns - (rf_rate / 252)
        
        if np.std(excess_returns) == 0:
            return 0.0
        
        return (np.mean(excess_returns) / np.std(excess_returns)) * np.sqrt(252)

    def sortino_ratio(self, rf_rate: float = 0.02) -> float:
        """Sortino ratio (annualized, downside only).
        
        Assumes 252 trading days.
        """
        if len(self.equity) < 2:
            return 0.0
        
        returns = np.diff(self.equity) / self.equity[:-1]
        excess_returns = returns - (rf_rate / 252)
        
        downside_returns = np.minimum(excess_returns, 0)
        downside_std = np.std(downside_returns)
        
        if downside_std == 0:
            return 0.0
        
        return (np.mean(excess_returns) / downside_std) * np.sqrt(252)

    def avg_holding_time(self) -> float:
        """Average holding time in bars."""
        if len(self.trades) == 0:
            return 0.0
        return np.mean([t.holding_bars for t in self.trades])

    def median_holding_time(self) -> float:
        """Median holding time in bars."""
        if len(self.trades) == 0:
            return 0.0
        return np.median([t.holding_bars for t in self.trades])

    def max_holding_time(self) -> int:
        """Maximum holding time in bars."""
        if len(self.trades) == 0:
            return 0
        return max([t.holding_bars for t in self.trades])

    def total_exposure(self) -> float:
        """Total bars in trades / total bars, as percentage."""
        if len(self.equity) == 0:
            return 0.0
        total_holding_bars = sum(t.holding_bars for t in self.trades)
        return (total_holding_bars / len(self.equity)) * 100

    def long_win_rate(self) -> float:
        """Win rate for long trades only."""
        longs = [t for t in self.trades if t.direction == 'long']
        if len(longs) == 0:
            return 0.0
        wins = sum(1 for t in longs if t.net_pnl > 0)
        return (wins / len(longs)) * 100

    def short_win_rate(self) -> float:
        """Win rate for short trades only."""
        shorts = [t for t in self.trades if t.direction == 'short']
        if len(shorts) == 0:
            return 0.0
        wins = sum(1 for t in shorts if t.net_pnl > 0)
        return (wins / len(shorts)) * 100

    def long_avg_pnl(self) -> float:
        """Average P&L for long trades."""
        longs = [t.net_pnl for t in self.trades if t.direction == 'long']
        return np.mean(longs) if len(longs) > 0 else 0.0

    def short_avg_pnl(self) -> float:
        """Average P&L for short trades."""
        shorts = [t.net_pnl for t in self.trades if t.direction == 'short']
        return np.mean(shorts) if len(shorts) > 0 else 0.0

    def get_all_metrics(self) -> Dict:
        """Get all metrics as dictionary."""
        max_dd, max_dd_duration = self.max_drawdown()
        
        return {
            'initial_capital': self.initial_capital,
            'final_equity': self.equity[-1] if len(self.equity) > 0 else self.initial_capital,
            'net_pnl': self.net_pnl(),
            'total_return_pct': self.total_return(),
            'num_trades': self.num_trades(),
            'num_longs': self.num_longs(),
            'num_shorts': self.num_shorts(),
            'winning_trades': self.winning_trades(),
            'losing_trades': self.losing_trades(),
            'win_rate_pct': self.win_rate(),
            'avg_winner': self.average_winner(),
            'avg_loser': self.average_loser(),
            'largest_winner': self.largest_winner(),
            'largest_loser': self.largest_loser(),
            'profit_factor': self.profit_factor(),
            'expectancy': self.expectancy(),
            'expectancy_r': self.expectancy_r(),
            'max_drawdown_pct': max_dd,
            'max_drawdown_duration_bars': max_dd_duration,
            'sharpe_ratio': self.sharpe_ratio(),
            'sortino_ratio': self.sortino_ratio(),
            'avg_holding_bars': self.avg_holding_time(),
            'median_holding_bars': self.median_holding_time(),
            'max_holding_bars': self.max_holding_time(),
            'exposure_pct': self.total_exposure(),
            'long_win_rate_pct': self.long_win_rate(),
            'short_win_rate_pct': self.short_win_rate(),
            'long_avg_pnl': self.long_avg_pnl(),
            'short_avg_pnl': self.short_avg_pnl(),
        }

    def to_dataframe(self) -> pd.DataFrame:
        """Convert trades to pandas DataFrame."""
        return pd.DataFrame([{
            'trade_id': t.trade_id,
            'direction': t.direction,
            'entry_bar': t.entry_bar,
            'entry_timestamp': t.entry_timestamp,
            'entry_price': t.entry_price,
            'exit_bar': t.exit_bar,
            'exit_timestamp': t.exit_timestamp,
            'exit_price': t.exit_price,
            'quantity': t.quantity,
            'notional': t.notional,
            'holding_bars': t.holding_bars,
            'holding_minutes': t.holding_minutes,
            'gross_pnl': t.gross_pnl,
            'commission': t.commission,
            'slippage': t.slippage,
            'net_pnl': t.net_pnl,
            'pnl_pct': t.pnl_pct,
            'return_pct': t.return_pct,
            'exit_reason': t.exit_reason,
            'exit_classification': t.exit_classification,
            'equity_after': t.equity_after,
        } for t in self.trades])
