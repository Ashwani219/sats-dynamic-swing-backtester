"""CHANGELOG

## v1.0.0 - 2026-08-28

### Initial Release

**Features:**
- Complete SATS (Self-Aware Trend System) engine implementation
  - Adaptive SuperTrend with TQI (Trend Quality Index)
  - Character-flip detection for trend reversals
  - BUY/SELL flip event generation
  - Support for multiple source types (HL2, close, HLC3)
  - Efficiency ratio and volatility adaptation

- Dynamic Swing Anchored VWAP pivot detection
  - HH/HL/LH/LL pivot classification
  - Forward-only confirmation (NO lookahead)
  - Direction state tracking
  - Swing period configurable

- Combined Strategy State Machine
  - 4-state FSM (FLAT_WAIT_LONG, LONG, FLAT_WAIT_SHORT, SHORT)
  - Entry: HL + SATS BUY flip for LONG; HH + SATS SELL flip for SHORT
  - Exit: HH for LONG, HL for SHORT
  - Reversal logic: check SATS current trend state
  - Position tracking and management

- Research-Grade Backtester
  - Bar-by-bar forward simulation
  - Next-bar-open execution
  - Commission and slippage modeling (0.05% each)
  - Position sizing (10% of equity per trade)
  - Equity reconciliation validation
  - Complete trade record tracking

- Performance Metrics
  - Win rate, profit factor, expectancy
  - Sharpe ratio, Sortino ratio
  - Maximum drawdown and duration
  - Long/short breakdown
  - Holding time analysis
  - Exposure percentage

- Data Validation
  - OHLCV integrity checks
  - NaN/duplicate detection
  - Missing candle detection
  - Trade record validation
  - Equity reconciliation
  - Lookahead bias detection

- Comprehensive Unit Tests
  - SATS engine tests (flip detection, TQI, ATR)
  - Dynamic Swing tests (pivot confirmation, no lookahead)
  - Strategy state machine tests (transitions, entries, exits)
  - Data validation tests

**Assumptions:**
- Perpetual/leverage model (SHORT allowed)
- 15-minute candle timeframe
- Fixed 10% position sizing
- 0.05% commission + 0.05% slippage per execution
- Entry/exit at next bar OPEN
- No independent stop loss (structure-based exits only)

**Known Limitations:**
- v1.0 baseline only (no optimization)
- No funding costs for perpetuals
- No partial exits
- No trailing stops
- Synthetic data for demonstration

**Files:**
- src/sats_engine.py - SATS indicator
- src/dynamic_swing.py - Swing pivot detection
- src/strategy.py - Combined strategy FSM
- src/backtester.py - Backtesting engine
- src/metrics.py - Performance metrics
- src/data_fetcher.py - Data loading
- src/validation.py - QA validation
- tests/ - Comprehensive unit tests
- main.py - Entry point

---

**Next Steps:**
1. Connect to real data source (CCXT, Binance, etc.)
2. Tune preset parameters per timeframe
3. Add optimization module
4. Monte Carlo analysis
5. Walk-forward testing
