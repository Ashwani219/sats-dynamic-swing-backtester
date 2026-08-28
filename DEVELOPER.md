# SATS + Dynamic Swing Backtester - Developer Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│ BACKTESTER PIPELINE                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Data (OHLCV)                                              │
│       ↓                                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SATS Engine                                        │   │
│  │  ├─ Efficiency Ratio (ER)                          │   │
│  │  ├─ Trend Quality Index (TQI)                      │   │
│  │  ├─ SuperTrend Bands (asymmetric)                  │   │
│  │  ├─ Flip Detection (price + character-flip)        │   │
│  │  └─ Trend State (1 = bull, -1 = bear)             │   │
│  └─────────────────────────────────────────────────────┘   │
│       ↓                                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Dynamic Swing Engine                              │   │
│  │  ├─ Highest/Lowest Detection (50-bar window)      │   │
│  │  ├─ Direction State Tracking                       │   │
│  │  ├─ Pivot Classification (HH/HL/LH/LL)           │   │
│  │  └─ Forward-Only Confirmation (NO LOOKAHEAD)     │   │
│  └─────────────────────────────────────────────────────┘   │
│       ↓                                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Strategy State Machine                             │   │
│  │  ├─ 4-State FSM                                    │   │
│  │  │  ├─ FLAT_WAIT_LONG  (HL → SATS BUY)            │   │
│  │  │  ├─ LONG            (HH exit)                   │   │
│  │  │  ├─ FLAT_WAIT_SHORT (HH → SATS SELL)           │   │
│  │  │  └─ SHORT           (HL exit)                   │   │
│  │  ├─ Entry/Exit Logic                               │   │
│  │  └─ Reversal Detection (SATS state check)          │   │
│  └─────────────────────────────────────────────────────┘   │
│       ↓                                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Backtester                                         │   │
│  │  ├─ Bar-by-Bar Simulation                          │   │
│  │  ├─ Next-Bar-Open Execution                        │   │
│  │  ├─ Commission & Slippage (0.05% each)            │   │
│  │  ├─ Equity Tracking & Reconciliation              │   │
│  │  └─ Trade Record Generation                        │   │
│  └─────────────────────────────────────────────────────┘   │
│       ↓                                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Metrics Calculator                                 │   │
│  │  ├─ Win Rate, Profit Factor                        │   │
│  │  ├─ Sharpe, Sortino Ratios                         │   │
│  │  ├─ Max Drawdown & Duration                        │   │
│  │  └─ Long/Short Breakdown                           │   │
│  └─────────────────────────────────────────────────────┘   │
│       ↓                                                      │
│  Output: Trade Log, Charts, Metrics Report                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Module Documentation

### 1. SATS Engine (`src/sats_engine.py`)

**Purpose**: Implement SATS indicator with exact Pine Script replication

**Key Classes**:
- `SATSState`: Dataclass for SATS state at a bar
  - `trend`: 1 (bullish) or -1 (bearish)
  - `flip_up`, `flip_down`: BUY/SELL flip events
  - `tqi`: Trend Quality Index (0..1)
  - `lower_band`, `upper_band`: SuperTrend bands

- `SATSEngine`: Main SATS implementation
  - Preset: Crypto 24/7 (ATR=14, BaseMult=2.8)
  - TQI calculation (4 weighted factors)
  - Asymmetric band logic
  - Character-flip detection

**Key Methods**:
```python
update(high, low, close) -> SATSState
```
Process one bar, return current state and flip flags.

**Critical Behaviors**:
- Trend persists until flip
- Flip requires either price break OR character-flip (TQI collapse)
- Bands have ratchet logic (non-retracing upper band in bull, lower in bear)
- TQI modulates band width: high TQI = tight bands, low TQI = wide bands

---

### 2. Dynamic Swing Engine (`src/dynamic_swing.py`)

**Purpose**: Detect swing pivots (HH/HL/LH/LL) with NO lookahead

**Key Classes**:
- `PivotType`: Enum for HH, HL, LH, LL

- `SwingPivot`: Confirmed pivot
  - `bar_index`: Bar where pivot was formed
  - `confirmation_bar`: Bar where pivot was confirmed (dir changed)
  - `pivot_type`: HH/HL/LH/LL classification

- `DynamicSwingEngine`: Pivot detection
  - Tracks direction (1 = uptrend, -1 = downtrend)
  - Confirms pivots on direction change ONLY
  - No backdating or lookahead

**Key Methods**:
```python
update(high, low, close) -> Optional[SwingPivot]
get_latest_hl(after_bar=-1) -> Optional[SwingPivot]
get_latest_hh(after_bar=-1) -> Optional[SwingPivot]
```

**Critical Behaviors**:
- Pivot is confirmed (returned) ONLY when direction changes
- Pivot price is the extreme from the previous trend
- Classification (HH/HL/LH/LL) based on comparison with prior cycle
- `after_bar` parameter prevents reuse of old pivots
- NO historical lookback (forward-only)

---

### 3. Strategy State Machine (`src/strategy.py`)

**Purpose**: Combine SATS + Dynamic Swing into trading rules

**Key Classes**:
- `StrategyState`: 4-state enum
  - FLAT_WAIT_LONG: waiting for HL + SATS BUY
  - LONG: holding long position
  - FLAT_WAIT_SHORT: waiting for HH + SATS SELL
  - SHORT: holding short position

- `StrategyPosition`: Active trade
  - entry_bar, entry_price, quantity, notional
  - Tracks setup events (HL/HH confirmation bars)
  - Tracks entry signal (SATS flip bars)

- `StrategyStateMachine`: FSM controller
  - Embeds SATS + Dynamic Swing engines
  - State transitions based on signals
  - Entry/exit signal generation

**Key Methods**:
```python
update(bar_index, timestamp, high, low, close) -> (entry_signal, exit_signal)
open_position(bar_index, timestamp, direction, entry_price) -> StrategyPosition
close_position(bar_index, timestamp, exit_price, reason)
```

**Critical Logic**:

**LONG Entry**:
1. Wait for NEW HL confirmation (confirmed_bar > prior bars)
2. Wait for NEW SATS BUY flip (flip_bar > HL confirmation_bar)
3. Enter at next bar OPEN

**LONG Exit**:
1. Monitor for NEW HH confirmation (after entry_bar)
2. On HH:
   - Check SATS current trend (persistent state, not new flip)
   - If BEARISH: close LONG, reverse to SHORT (next bar)
   - If BULLISH: close LONG, stay FLAT_WAIT_SHORT

**Similar logic for SHORT**.

---

### 4. Backtester (`src/backtester.py`)

**Purpose**: Execute strategy bar-by-bar with accurate accounting

**Key Classes**:
- `TradeRecord`: Complete trade record
  - OHLC entry/exit, P&L breakdown
  - Commission, slippage, net P&L
  - Holding time, exit reason

- `Backtester`: Simulation engine
  - Tracks equity, positions, pending signals
  - Next-bar-open execution (signal on bar N, execute on N+1 open)
  - Commission + slippage modeling
  - Equity reconciliation

**Key Methods**:
```python
process_bar(bar_index, timestamp, ohlcv, entry_signal, exit_signal) -> (bool, bool)
validate_equity_reconciliation() -> bool
get_equity_curve() -> np.ndarray
get_drawdown_curve() -> np.ndarray
```

**Critical Logic**:

1. **Signal Queueing**: Signals from bar N are executed at bar N+1 OPEN
2. **Exit Priority**: Exit is processed before entry (no simultaneous exposure)
3. **Cost Application**: Commission + slippage on notional, applied to equity
4. **Slippage Direction**: 
   - LONG entry: price increases (adverse)
   - LONG exit: price decreases (adverse)
   - SHORT entry: price decreases (adverse)
   - SHORT exit: price increases (adverse)

---

### 5. Metrics Calculator (`src/metrics.py`)

**Purpose**: Compute performance statistics

**Key Methods**:
```python
total_return() -> float
win_rate() -> float
profit_factor() -> float
sharpe_ratio(rf_rate=0.02) -> float
max_drawdown() -> Tuple[float, int]
get_all_metrics() -> Dict
```

**Metrics Computed**:
- Win rate, avg winner/loser, profit factor
- Sharpe/Sortino ratios (annualized, 252 days)
- Max drawdown (peak-to-trough %)
- Holding time analysis
- Long/short breakdown
- Exposure %

---

## Testing Strategy

### Unit Tests

1. **test_sats.py**
   - ER, TQI calculations
   - Flip detection (price + character)
   - Trend persistence
   - ATR ratchet logic

2. **test_dynamic_swing.py**
   - Pivot confirmation (no lookahead)
   - HH/HL/LH/LL classification
   - Direction state tracking
   - Pivot reuse prevention

3. **test_strategy.py**
   - State transitions
   - Entry/exit logic
   - Position tracking
   - Equity updates

4. **test_backtester.py**
   - Bar-by-bar processing
   - Equity reconciliation
   - Trade counting
   - Drawdown calculation

### Integration Tests

- **test_backtester.py::TestEndToEnd**
  - Full pipeline: data → strategy → backtest → metrics
  - Validation of results
  - End-to-end correctness

## Data Flow

```
bar N:
  ├─ SATS.update(H, L, C)
  │  └─ flip_up or flip_down?
  ├─ DynamicSwing.update(H, L, C)
  │  └─ pivot confirmed?
  ├─ Strategy.update(...)
  │  └─ entry_signal or exit_signal?
  └─ (signals queued for bar N+1)

bar N+1:
  ├─ Backtester.process_bar(..., entry_signal, exit_signal)
  │  ├─ Execute pending exit at open (N+1)
  │  ├─ Execute pending entry at open (N+1)
  │  ├─ Queue new signals for bar N+2
  │  └─ Update equity history
  └─ Continue to bar N+2
```

## Key Design Decisions

1. **No Lookahead**: All confirmations use bar N or later, never N-1
2. **Next-Bar-Open**: Execute signals at next bar open (typical trading model)
3. **Fixed Allocation**: 10% of equity per trade (simple, reproducible)
4. **Flat Costs**: 0.05% commission + 0.05% slippage (conservative estimates)
5. **No Independent SL**: Structure (HL/HH) defines exits, not fixed stops
6. **Reversal Logic**: Check SATS current state (persistent), not new flip

## Extending the Backtester

### Adding New Indicators

1. Create new class in `src/`
2. Implement `update(...)` method returning state
3. Add to strategy state machine
4. Write unit tests

### Changing Position Sizing

Modify in `src/backtester.py`:
```python
notional = self.current_equity * self.allocation_pct
```

### Adding Stop Loss Logic

Add to `src/strategy.py` in `update()` method:
```python
if position and close < entry_price - max_loss:
    exit_signal = {...}
```

### Monte Carlo / Walk-Forward

Create wrapper in `main.py` to:
1. Split data into train/test windows
2. Re-run backtest for each window
3. Compare results across periods

---

## Performance Profiling

```bash
python -m cProfile -s cumtime main.py
```

Expected bottlenecks:
1. ATR calculation (O(n) per bar)
2. TA library calls (numpy operations)
3. Matplotlib rendering (charts)

---

**Happy Development!** 🚀
