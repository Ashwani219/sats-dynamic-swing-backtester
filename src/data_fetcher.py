"""Data Fetching and Validation

Download and validate OHLCV data for backtesting.
"""

import pandas as pd
import numpy as np
from typing import Optional
import os
from datetime import datetime, timedelta


class DataFetcher:
    """Fetch OHLCV data for backtesting."""

    @staticmethod
    def load_csv(filepath: str) -> pd.DataFrame:
        """Load OHLCV data from CSV.
        
        Expected columns: timestamp, open, high, low, close, volume
        """
        df = pd.read_csv(filepath)
        
        # Validate columns
        required = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        return df


class DataValidator:
    """Validate OHLCV data quality."""

    @staticmethod
    def validate(df: pd.DataFrame, timeframe_minutes: int = 15) -> Dict[str, any]:
        """Validate data quality.
        
        Args:
            df: OHLCV DataFrame
            timeframe_minutes: expected bar interval
        
        Returns:
            validation result dictionary
        """
        issues = []
        
        # Check for duplicates
        if df['timestamp'].duplicated().any():
            n_dups = df['timestamp'].duplicated().sum()
            issues.append(f"Found {n_dups} duplicate timestamps")
        
        # Check for NaN values
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if df[col].isna().any():
                n_nans = df[col].isna().sum()
                issues.append(f"Found {n_nans} NaN values in {col}")
        
        # Check OHLC integrity
        invalid_ohlc = (df['high'] < df['low']) | \
                       (df['high'] < df['open']) | \
                       (df['high'] < df['close']) | \
                       (df['low'] > df['open']) | \
                       (df['low'] > df['close'])
        
        if invalid_ohlc.any():
            n_invalid = invalid_ohlc.sum()
            issues.append(f"Found {n_invalid} bars with invalid OHLC (high < low or out of range)")
        
        # Check for missing candles
        if len(df) > 1:
            time_diffs = df['timestamp'].diff()[1:]
            expected_delta = timedelta(minutes=timeframe_minutes)
            missing_candles = (time_diffs != expected_delta).sum()
            
            if missing_candles > 0:
                issues.append(f"Found {missing_candles} gaps in candle sequence")
        
        # Check volume
        if (df['volume'] < 0).any():
            n_neg_vol = (df['volume'] < 0).sum()
            issues.append(f"Found {n_neg_vol} bars with negative volume")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'total_bars': len(df),
            'date_range': f"{df['timestamp'].min()} to {df['timestamp'].max()}",
            'missing_candles': sum(1 for td in time_diffs if td != expected_delta) if len(df) > 1 else 0,
        }

    @staticmethod
    def print_validation_report(result: Dict):
        """Print validation report."""
        print("\n" + "="*60)
        print("DATA VALIDATION REPORT")
        print("="*60)
        print(f"Status: {'✓ VALID' if result['valid'] else '✗ INVALID'}")
        print(f"Total Bars: {result['total_bars']}")
        print(f"Date Range: {result['date_range']}")
        print(f"Missing Candles: {result['missing_candles']}")
        
        if result['issues']:
            print("\nISSUES FOUND:")
            for issue in result['issues']:
                print(f"  - {issue}")
        else:
            print("\nNo issues found.")
        print("="*60 + "\n")
