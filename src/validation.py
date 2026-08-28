"""Data Validation and Quality Assurance

Validation utilities and QA checks.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from datetime import timedelta


class DataValidator:
    """Comprehensive data validation."""

    @staticmethod
    def validate_ohlcv(df: pd.DataFrame, timeframe_minutes: int = 15) -> Dict:
        """Validate OHLCV data quality.
        
        Args:
            df: DataFrame with columns: timestamp, open, high, low, close, volume
            timeframe_minutes: expected bar interval
        
        Returns:
            validation result dictionary
        """
        issues = []
        warnings = []
        
        # Check required columns
        required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing = [col for col in required if col not in df.columns]
        if missing:
            return {'valid': False, 'issues': [f"Missing columns: {missing}"]}
        
        # Check for duplicates
        if df['timestamp'].duplicated().any():
            n_dups = df['timestamp'].duplicated().sum()
            issues.append(f"Found {n_dups} duplicate timestamps")
        
        # Check for NaN values
        for col in required:
            n_nans = df[col].isna().sum()
            if n_nans > 0:
                issues.append(f"Found {n_nans} NaN values in {col}")
        
        # Check OHLC integrity
        invalid_ohlc = (df['high'] < df['low']) | \
                       (df['high'] < df['open']) | \
                       (df['high'] < df['close']) | \
                       (df['low'] > df['open']) | \
                       (df['low'] > df['close'])
        
        if invalid_ohlc.any():
            n_invalid = invalid_ohlc.sum()
            issues.append(f"Found {n_invalid} bars with invalid OHLC")
        
        # Check volume
        if (df['volume'] < 0).any():
            n_neg = (df['volume'] < 0).sum()
            issues.append(f"Found {n_neg} bars with negative volume")
        
        # Check for missing candles
        if len(df) > 1:
            df_sorted = df.sort_values('timestamp').reset_index(drop=True)
            time_diffs = df_sorted['timestamp'].diff()[1:]
            expected_delta = timedelta(minutes=timeframe_minutes)
            
            gap_count = 0
            for td in time_diffs:
                if td != expected_delta and td.total_seconds() > 0:
                    gap_count += 1
            
            if gap_count > 0:
                warnings.append(f"Found {gap_count} gaps in candle sequence")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'total_bars': len(df),
            'date_range': f"{df['timestamp'].min()} to {df['timestamp'].max()}" if len(df) > 0 else 'N/A',
        }

    @staticmethod
    def validate_trades(trades: List) -> Dict:
        """Validate trade records.
        
        Args:
            trades: list of TradeRecord objects
        
        Returns:
            validation result
        """
        issues = []
        
        if len(trades) == 0:
            return {'valid': True, 'issues': [], 'message': 'No trades to validate'}
        
        # Check entry/exit logic
        for i, trade in enumerate(trades):
            if trade.entry_bar >= trade.exit_bar:
                issues.append(f"Trade {i+1}: exit_bar ({trade.exit_bar}) <= entry_bar ({trade.entry_bar})")
            
            if trade.entry_price <= 0 or trade.exit_price <= 0:
                issues.append(f"Trade {i+1}: invalid prices (entry={trade.entry_price}, exit={trade.exit_price})")
            
            if trade.quantity <= 0:
                issues.append(f"Trade {i+1}: invalid quantity ({trade.quantity})")
        
        return {'valid': len(issues) == 0, 'issues': issues}

    @staticmethod
    def validate_equity_reconciliation(trades: List, initial_capital: float, final_equity: float) -> Dict:
        """Validate equity reconciliation.
        
        Args:
            trades: list of TradeRecord objects
            initial_capital: starting equity
            final_equity: final equity
        
        Returns:
            reconciliation result
        """
        calculated = initial_capital
        for trade in trades:
            calculated += trade.net_pnl
        
        diff = abs(calculated - final_equity)
        tolerance = 0.01  # $0.01
        
        return {
            'valid': diff <= tolerance,
            'calculated_equity': calculated,
            'actual_equity': final_equity,
            'difference': diff,
            'tolerance': tolerance,
        }


class StrategyValidator:
    """Validate strategy implementation."""

    @staticmethod
    def validate_no_lookahead(strategy_log: List) -> Dict:
        """Validate that no lookahead bias exists in signals.
        
        Args:
            strategy_log: list of signal events with confirmation_bar
        
        Returns:
            validation result
        """
        issues = []
        
        for event in strategy_log:
            # Signal should be confirmed on the same bar or later
            if 'confirmation_bar' in event:
                signal_bar = event.get('signal_bar', event.get('bar'))
                confirmation_bar = event['confirmation_bar']
                
                if confirmation_bar < signal_bar:
                    issues.append(f"Lookahead detected: signal at {signal_bar}, confirmed at {confirmation_bar}")
        
        return {'valid': len(issues) == 0, 'issues': issues}

    @staticmethod
    def validate_entry_exit_sequence(trades: List) -> Dict:
        """Validate entry/exit sequencing.
        
        Checks:
        - Entry and exit alternate properly
        - No overlapping trades
        - Proper timing
        
        Args:
            trades: list of TradeRecord objects
        
        Returns:
            validation result
        """
        issues = []
        
        if len(trades) < 2:
            return {'valid': True, 'issues': []}
        
        for i in range(len(trades) - 1):
            curr = trades[i]
            next_t = trades[i + 1]
            
            # Trades should not overlap
            if curr.exit_bar >= next_t.entry_bar:
                issues.append(f"Trades overlap: Trade {i+1} exits at {curr.exit_bar}, Trade {i+2} enters at {next_t.entry_bar}")
        
        return {'valid': len(issues) == 0, 'issues': issues}


class IndicatorValidator:
    """Validate indicator calculations."""

    @staticmethod
    def validate_atr_calculation(atr_values: np.ndarray) -> Dict:
        """Validate ATR values.
        
        Args:
            atr_values: array of ATR values
        
        Returns:
            validation result
        """
        issues = []
        
        # ATR should be positive
        if (atr_values < 0).any():
            issues.append("ATR contains negative values")
        
        # ATR should be finite
        if not np.isfinite(atr_values).all():
            n_inf = (~np.isfinite(atr_values)).sum()
            issues.append(f"ATR contains {n_inf} non-finite values")
        
        return {'valid': len(issues) == 0, 'issues': issues}

    @staticmethod
    def validate_tqi_range(tqi_values: np.ndarray) -> Dict:
        """Validate TQI is in [0, 1] range.
        
        Args:
            tqi_values: array of TQI values
        
        Returns:
            validation result
        """
        issues = []
        
        # TQI should be between 0 and 1
        if (tqi_values < 0).any() or (tqi_values > 1).any():
            out_of_range = ((tqi_values < 0) | (tqi_values > 1)).sum()
            issues.append(f"TQI has {out_of_range} values outside [0, 1]")
        
        return {'valid': len(issues) == 0, 'issues': issues}

    @staticmethod
    def validate_pivot_confirmation(pivots: List) -> Dict:
        """Validate pivot confirmations.
        
        Args:
            pivots: list of SwingPivot objects
        
        Returns:
            validation result
        """
        issues = []
        
        for i, pivot in enumerate(pivots):
            # Confirmation bar should be >= pivot bar
            if pivot.confirmation_bar < pivot.bar_index:
                issues.append(f"Pivot {i+1}: confirmation_bar < bar_index")
            
            # Price should be non-zero
            if pivot.price <= 0:
                issues.append(f"Pivot {i+1}: invalid price ({pivot.price})")
        
        return {'valid': len(issues) == 0, 'issues': issues}
