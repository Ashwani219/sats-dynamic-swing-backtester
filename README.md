# SATS + Dynamic Swing Anchored VWAP Backtester

Research-grade Python backtester for the combined SATS (Self-Aware Trend System) and Dynamic Swing Anchored VWAP strategy on BTC 15-minute candles.

## Project Overview

This backtester implements a rigorous, forward-looking replication of:

1. **SATS (Self-Aware Trend System)** [WillyAlgoTrader]
   - Adaptive SuperTrend with Trend Quality Index (TQI)
   - Character-flip detection for trend reversal
   - BUY/SELL flip events for trade entry

2. **Dynamic Swing Anchored VWAP** [Zeiierman]
   - Swing pivot detection (HH, HL, LH, LL)
   - Forward-only confirmation (no lookahead)
   - Structure-based trade management

## Strategy Rules

### Entry Logic

**LONG Entry:**
1. NEW HL (Higher Low) confirmed by Dynamic Swing
2. Followed by NEW SATS BUY flip (after HL confirmation)
3. Entry at next bar OPEN

**SHORT Entry:**
1. NEW HH (Higher High) confirmed by Dynamic Swing
2. Followed by NEW SATS SELL flip (after HH confirmation)
3. Entry at next bar OPEN

### Exit Logic

**LONG Exit:**
- Closes on NEW HH confirmed after entry
- At HH, inspect CURRENT SATS trend state:
  - If BULLISH: close LONG, stay FLAT
  - If BEARISH: close LONG, open SHORT (next bar)

**SHORT Exit:**
- Closes on NEW HL confirmed after entry
- At HL, inspect CURRENT SATS trend state:
  - If BEARISH: close SHORT, stay FLAT
  - If BULLISH: close SHORT, open LONG (next bar)

### Critical Rules

- **No reuse**: Old structure events/SATS flips cannot be reused
- **No lookahead**: Confirm only on completed bars
- **No simultaneous exposure**: Close then open sequentially
- **SATS ignored in trade**: While holding position, ignore all SATS signals except at exit
- **Current state matters**: Use persistent SATS trend state for reversals, not new flips

## Position Sizing

- 10% of current equity per trade
- No fixed stop loss (Dynamic Swing structure exits)
- No fixed take profit (Dynamic Swing structure exits)

## Transaction Costs

- Commission: 0.05% per execution
- Slippage: 0.05% adverse per execution
- Applied to both entry and exit

## Data

- **Instrument**: BTC/USD (15-minute candles)
- **Period**: ~2 years (Aug 2024 - Aug 2026)
- **Source**: CCXT or verified exchange API

## Files Structure

```
sats-dynamic-swing-backtester/
├── src/
│   ├── sats_engine.py           # SATS indicator implementation
│   ├── dynamic_swing.py         # Dynamic Swing pivot detection
│   ├── strategy.py              # Combined strategy state machine
│   ├── backtester.py            # Core backtesting engine
│   ├── metrics.py               # Performance metrics & reporting
│   └── validation.py            # Unit tests & validation
├── tests/
│   ├── test_sats.py             # SATS unit tests
│   ├── test_dynamic_swing.py    # Dynamic Swing unit tests
│   ├── test_strategy.py         # Strategy state machine tests
│   └── test_backtester.py       # Integration tests
├── data/
│   ├── raw/                     # Downloaded OHLCV data
│   └── processed/               # Cleaned & validated data
├── outputs/
│   ├── trade_log.csv            # All trades with P&L
│   ├── signal_log.csv           # All signals & structure events
│   ├── equity_curve.png         # Equity progression
│   ├── drawdown.png             # Drawdown chart
│   ├── strategy_chart.png       # Price + entries/exits
│   ├── qa_chart.png             # Validation chart
│   └── research_report.md       # Final results & analysis
├── requirements.txt             # Python dependencies
└── main.py                      # Entry point

```

## Installation

```bash
git clone https://github.com/Ashwani219/sats-dynamic-swing-backtester.git
cd sats-dynamic-swing-backtester
pip install -r requirements.txt
python main.py
```

## Key Implementation Details

### SATS Engine
- Exact preset-resolved parameters (Crypto 24/7)
- Persistent trend state (stTrend)
- BUY/SELL flip events (state transitions only)
- TQI (Trend Quality Index) computation
- Character-flip detection
- No lookahead

### Dynamic Swing Engine
- Pivot detection via highest/lowest bars
- Forward-only confirmation (no backdating)
- Direction state tracking
- HH/HL/LH/LL classification
- Explicit confirmation timestamp

### Strategy State Machine
- 4 explicit states: FLAT_WAIT_LONG, LONG, FLAT_WAIT_SHORT, SHORT
- Qualifying HL/HH tracking with timestamps
- Latest SATS flip tracking with timestamps
- Entry/exit sequencing rules
- Reversal logic (current state check)
- No position overlap

### Backtester
- Bar-by-bar forward simulation
- Next-bar-open execution
- Equity accounting & reconciliation
- Cost tracking (commission + slippage)
- Trade log with full metadata
- Signal/structure event log

## Validation

- Hand-crafted test cases for all pivots
- SATS state vs TradingView comparison
- No-lookahead verification
- Execution timing tests
- Equity reconciliation checks
- Unit tests for all major components

## Research Outputs

1. **Trade Log**: entry/exit prices, P&L, costs, timing
2. **Signal Log**: all indicators, state, structure events
3. **Equity Curve**: cumulative returns over time
4. **Drawdown Analysis**: peak-to-trough and recovery
5. **Performance Metrics**: Sharpe, Sortino, win rate, etc.
6. **Research Report**: full findings and methodology

## Important Assumptions

- **Perpetual/Leverage Model**: SHORT selling is allowed (BTC perpetual equivalent)
- **No Funding Costs**: Funding rates not modeled in v1
- **Execution at OHLC**: Entry at next open, exit at next open
- **No Slippage Optimization**: Flat 0.05% adverse
- **No Optimization**: Baseline only, no parameter tuning

## Performance Metrics

Final report includes:

- Total return %
- Net P&L
- Win rate
- Profit factor
- Average winner / loser
- Sharpe ratio
- Sortino ratio
- Maximum drawdown
- Trade count (Long/Short)
- Exposure %
- Holding time analysis

## Limitations & Future Work

- No stop-loss independent of structure (by design)
- No trailing stops
- No partial exits
- No dynamic position sizing
- v1 baseline only (no optimization)

---

**Status**: Implementation in progress  
**Version**: 1.0.0  
**Author**: Ashwani219  
**License**: Research Use Only