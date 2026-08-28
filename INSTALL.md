# SATS + Dynamic Swing Anchored VWAP Backtester - Installation Guide

## Prerequisites

- Python 3.8+
- pip (Python package manager)
- Git

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Ashwani219/sats-dynamic-swing-backtester.git
cd sats-dynamic-swing-backtester
```

### 2. Create Virtual Environment (Recommended)

```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python -c "import numpy, pandas, matplotlib; print('All dependencies installed!')"
```

## Running the Backtester

### Quick Start (With Synthetic Data)

```bash
python main.py
```

This will:
1. Generate synthetic BTC 15-minute data
2. Run the complete backtest
3. Generate performance reports
4. Save results to `outputs/`

### Using Real Data

1. **Prepare CSV file** with columns: `timestamp, open, high, low, close, volume`
2. **Place in** `data/processed/btc_15m.csv`
3. **Run:** `python main.py`

### Data Format

```csv
timestamp,open,high,low,close,volume
2024-08-28T00:00:00,42100.50,42150.00,42050.00,42120.25,125.5
2024-08-28T00:15:00,42120.25,42180.50,42100.00,42170.75,138.2
...
```

## Running Tests

### All Tests

```bash
pytest
```

### Specific Test Suite

```bash
# SATS Engine Tests
pytest tests/test_sats.py -v

# Dynamic Swing Tests
pytest tests/test_dynamic_swing.py -v

# Strategy State Machine Tests
pytest tests/test_strategy.py -v

# Backtester Integration Tests
pytest tests/test_backtester.py -v
```

### With Coverage

```bash
pytest --cov=src tests/
```

## Project Structure

```
sats-dynamic-swing-backtester/
├── src/                    # Core implementation
│   ├── sats_engine.py     # SATS indicator
│   ├── dynamic_swing.py   # Swing pivot detection
│   ├── strategy.py        # Combined strategy FSM
│   ├── backtester.py      # Backtesting engine
│   ├── metrics.py         # Performance metrics
│   ├── data_fetcher.py    # Data loading
│   └── validation.py      # QA validation
├── tests/                 # Unit & integration tests
│   ├── test_sats.py
│   ├── test_dynamic_swing.py
│   ├── test_strategy.py
│   └── test_backtester.py
├── data/                  # Data directory
│   ├── raw/              # Raw downloaded data
│   └── processed/        # Cleaned data
├── outputs/              # Backtest results
│   ├── trade_log.csv
│   ├── equity_drawdown.png
│   └── ...
├── main.py              # Entry point
├── requirements.txt     # Dependencies
└── README.md           # This file
```

## Output Files

After running `main.py`, the following files are generated in `outputs/`:

1. **trade_log.csv** - Detailed trade history
   - Entry/exit prices, timestamps, P&L
   - Commission, slippage, return %
   - Exit reason and classification

2. **equity_drawdown.png** - Equity curve and drawdown chart
   - Equity progression over time
   - Maximum drawdown visualization

## Configuration

Modify parameters in `main.py` or indicator files:

### Backtester
```python
backtester = Backtester(
    initial_capital=100000,
    commission_pct=0.05,
    slippage_pct=0.05,
    allocation_pct=0.10,  # 10% per trade
)
```

### SATS Engine
```python
sats = SATSEngine(source="hl2")  # Options: "hl2", "close", "hlc3"
# Parameters are Crypto 24/7 preset (see src/sats_engine.py)
```

### Dynamic Swing
```python
swing = DynamicSwingEngine(swing_period=50)  # Lookback period
```

## Troubleshooting

### Import Errors

If you get `ModuleNotFoundError`, ensure:
1. Virtual environment is activated
2. All dependencies installed: `pip install -r requirements.txt`
3. You're running from project root directory

### Data Errors

If data validation fails:
1. Check CSV format matches expected columns
2. Ensure no NaN or duplicate timestamps
3. Verify OHLC logic (High >= Low)
4. Check for negative volumes

### Memory Issues

For very large datasets:
1. Process in chunks
2. Increase system RAM
3. Use lower timeframe resolution

## Performance Notes

- **Backtest speed**: ~100,000 bars/minute on modern CPU
- **Memory usage**: ~1 GB for 2 years of 15-minute data
- **Typical run time**: <30 seconds for 2-year backtest

## Next Steps

1. **Load real data** from CCXT or exchange API
2. **Analyze results** in `outputs/`
3. **Run tests** to validate implementation
4. **Customize parameters** for your market conditions
5. **Extend with optimization** (see future roadmap)

## Support & Issues

For bugs or questions:
1. Check existing issues on GitHub
2. Review CHANGELOG.md for recent changes
3. Verify data format and validation
4. Run tests to isolate problem

## License

Research Use Only - See LICENSE file

---

**Happy Backtesting!** 📈
