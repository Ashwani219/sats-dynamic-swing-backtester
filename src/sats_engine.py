"""SATS (Self-Aware Trend System) Engine Implementation

Exact replication of SATS Pine Script v6 with Crypto 24/7 preset.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional, Tuple


@dataclass
class SATSState:
    """SATS state at a given bar"""
    bar_index: int
    close: float
    trend: int  # 1 = bullish, -1 = bearish
    trend_started_bar: int  # bar where current trend started
    lower_band: float
    upper_band: float
    st_line: float
    flip_up: bool = False  # BUY flip event
    flip_down: bool = False  # SELL flip event
    tqi: float = np.nan
    er: float = np.nan
    atr: float = np.nan


class SATSEngine:
    """SATS Indicator Engine
    
    Preset: Crypto 24/7
    - ATR Length: 14
    - Base Mult: 2.8
    - Source: HL2 (High + Low) / 2
    - Adaptive ER: True
    - TQI: Enabled
    """

    def __init__(self, source: str = "hl2"):
        """Initialize SATS engine.
        
        Args:
            source: 'hl2', 'close', 'hlc3'
        """
        # Crypto 24/7 preset parameters
        self.atr_len = 14
        self.base_mult = 2.8
        self.source = source
        self.er_len = 20
        self.atr_baseline_len = 100
        self.adapt_strength = 0.5
        
        # TQI parameters
        self.use_tqi = True
        self.quality_strength = 0.4
        self.quality_curve = 1.5
        self.asym_strength = 0.5
        self.use_asym_bands = True
        self.use_eff_atr = True
        
        # Char-flip parameters
        self.use_char_flip = True
        self.char_flip_min_age = 5
        self.char_flip_high = 0.55
        self.char_flip_low = 0.25
        
        # TQI weights
        self.tqi_weight_er = 0.35
        self.tqi_weight_vol = 0.20
        self.tqi_weight_struct = 0.25
        self.tqi_weight_mom = 0.20
        self.tqi_struct_len = 20
        self.tqi_mom_len = 10
        
        # Band geometry
        self.tqi_mult_floor = 0.6
        self.tqi_mult_range = 0.8
        self.asym_tighten_max = 0.3
        self.asym_widen_max = 0.4
        
        # State
        self.trend = 1  # Start bullish
        self.trend_started_bar = 0
        self.lower_band = np.nan
        self.upper_band = np.nan
        
        # History for calculations
        self.history = {
            "close": [],
            "high": [],
            "low": [],
            "atr": [],
            "trend": [],
            "lower_band": [],
            "upper_band": [],
        }

    def _get_source(self, high: float, low: float, close: float) -> float:
        """Get source value based on configured source."""
        if self.source == "hl2":
            return (high + low) / 2.0
        elif self.source == "hlc3":
            return (high + low + close) / 3.0
        else:  # close
            return close

    def _calc_atr(self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int) -> float:
        """Calculate ATR using Wilder's smoothing."""
        if len(closes) < period:
            return np.nan
        
        tr = np.zeros(len(closes))
        tr[0] = highs[0] - lows[0]
        
        for i in range(1, len(closes)):
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
        
        # Wilder's smoothing
        atr = np.zeros(len(closes))
        atr[period - 1] = np.mean(tr[:period])
        
        for i in range(period, len(closes)):
            atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        
        return atr[-1]

    def _calc_efficiency_ratio(self, series: np.ndarray, period: int) -> float:
        """Calculate Efficiency Ratio (directional movement / volatility)."""
        if len(series) < period + 1:
            return np.nan
        
        change = abs(series[-1] - series[-period - 1])
        volatility = np.sum(np.abs(np.diff(series[-period:])))
        
        if volatility == 0:
            return 0.0
        
        return change / volatility

    def _calc_tqi(self, high: float, low: float, close: float, source: float,
                   er: float, atr: float, atr_baseline: float) -> float:
        """Calculate Trend Quality Index (0..1)."""
        if not self.use_tqi:
            return 0.5
        
        # TQI ER component
        tqi_er = np.clip(er, 0.0, 1.0)
        
        # TQI Vol component (volatility regime)
        vol_ratio = atr / atr_baseline if atr_baseline > 0 else 1.0
        tqi_vol = np.clip((vol_ratio - 0.6) / (1.8 - 0.6), 0.0, 1.0)
        
        # TQI Structure component (price position in range)
        if len(self.history["high"]) >= self.tqi_struct_len:
            struct_hi = max(self.history["high"][-self.tqi_struct_len:])
            struct_lo = min(self.history["low"][-self.tqi_struct_len:])
            struct_range = struct_hi - struct_lo
            if struct_range > 0:
                price_pos = (close - struct_lo) / struct_range
                tqi_struct = 1.0 - abs(price_pos - 0.5) * 2.0
                tqi_struct = np.clip(tqi_struct, 0.0, 1.0)
            else:
                tqi_struct = 0.5
        else:
            tqi_struct = 0.5
        
        # TQI Momentum Persistence component
        if len(self.history["close"]) >= self.tqi_mom_len:
            closes_window = self.history["close"][-self.tqi_mom_len:]
            window_change = closes_window[-1] - closes_window[0]
            up_moves = sum(1 for i in range(len(closes_window) - 1) 
                          if closes_window[i + 1] > closes_window[i])
            down_moves = self.tqi_mom_len - 1 - up_moves
            
            if window_change > 0:
                tqi_mom = up_moves / (self.tqi_mom_len - 1)
            elif window_change < 0:
                tqi_mom = down_moves / (self.tqi_mom_len - 1)
            else:
                tqi_mom = 0.0
        else:
            tqi_mom = 0.5
        
        # Weighted average
        weight_sum = self.tqi_weight_er + self.tqi_weight_vol + self.tqi_weight_struct + self.tqi_weight_mom
        tqi = (
            tqi_er * self.tqi_weight_er +
            tqi_vol * self.tqi_weight_vol +
            tqi_struct * self.tqi_weight_struct +
            tqi_mom * self.tqi_weight_mom
        ) / weight_sum
        
        return np.clip(tqi, 0.0, 1.0)

    def update(self, high: float, low: float, close: float) -> SATSState:
        """Update SATS state for a new bar.
        
        Returns:
            SATSState with current bar information and flip events
        """
        bar_index = len(self.history["close"])
        
        # Store OHLC
        self.history["close"].append(close)
        self.history["high"].append(high)
        self.history["low"].append(low)
        
        # Calculate ATR
        if bar_index < self.atr_len:
            atr = high - low  # Simple TR for warmup
        else:
            highs = np.array(self.history["high"])
            lows = np.array(self.history["low"])
            closes = np.array(self.history["close"])
            atr = self._calc_atr(highs, lows, closes, self.atr_len)
        
        self.history["atr"].append(atr)
        
        # Get source
        source = self._get_source(high, low, close)
        
        # Calculate Efficiency Ratio
        if bar_index < self.er_len:
            er = 0.5
        else:
            source_array = np.array(self.history["close"] if self.source == "close" 
                                   else [(h + l) / 2 for h, l in zip(self.history["high"], self.history["low"])])
            er = self._calc_efficiency_ratio(source_array, self.er_len)
        
        # Calculate ATR baseline
        if bar_index < self.atr_baseline_len:
            atr_baseline = atr
        else:
            atr_baseline = np.mean(self.history["atr"][-self.atr_baseline_len:])
        
        # Calculate TQI
        tqi = self._calc_tqi(high, low, close, source, er, atr, atr_baseline)
        
        # Adaptive multiplier
        vol_ratio = atr / atr_baseline if atr_baseline > 0 else 1.0
        legacy_adapt = 1.0 + self.adapt_strength * (0.5 - er)
        
        # TQI modulation
        if self.use_tqi:
            quality_deviation = (1.0 - tqi) ** self.quality_curve
            tqi_mult = 1.0 - self.quality_strength + self.quality_strength * (
                self.tqi_mult_floor + self.tqi_mult_range * quality_deviation
            )
        else:
            tqi_mult = 1.0
        
        sym_mult = self.base_mult * legacy_adapt * tqi_mult
        
        # Asymmetric bands
        if self.use_asym_bands and self.use_tqi:
            asym_tighten = 1.0 - self.asym_strength * tqi * self.asym_tighten_max
            asym_widen = 1.0 + self.asym_strength * tqi * self.asym_widen_max
            if self.trend == 1:  # bullish
                active_mult = sym_mult * asym_tighten
                passive_mult = sym_mult * asym_widen
            else:  # bearish
                active_mult = sym_mult * asym_widen
                passive_mult = sym_mult * asym_tighten
        else:
            active_mult = sym_mult
            passive_mult = sym_mult
        
        # Effective ATR
        if self.use_eff_atr:
            eff_atr = atr * (0.5 + 0.5 * er)
        else:
            eff_atr = atr
        
        # Calculate bands
        if self.trend == 1:  # bullish trend
            lower_mult = active_mult
            upper_mult = passive_mult
        else:  # bearish trend
            lower_mult = passive_mult
            upper_mult = active_mult
        
        lower_band_raw = source - lower_mult * eff_atr
        upper_band_raw = source + upper_mult * eff_atr
        
        # Ratchet logic
        if bar_index == 0:
            self.lower_band = lower_band_raw
            self.upper_band = upper_band_raw
        else:
            prev_close = self.history["close"][-2]
            prev_lower = self.history["lower_band"][-1]
            prev_upper = self.history["upper_band"][-1]
            
            if self.trend == 1:
                self.lower_band = max(lower_band_raw, prev_lower) if prev_close > prev_lower else lower_band_raw
                self.upper_band = min(upper_band_raw, prev_upper) if prev_close < prev_upper else upper_band_raw
            else:
                self.lower_band = max(lower_band_raw, prev_lower) if prev_close > prev_lower else lower_band_raw
                self.upper_band = min(upper_band_raw, prev_upper) if prev_close < prev_upper else upper_band_raw
        
        self.history["lower_band"].append(self.lower_band)
        self.history["upper_band"].append(self.upper_band)
        
        # Detect flips
        prev_trend = self.trend
        flip_up = False
        flip_down = False
        
        if bar_index > 0:
            prev_lower = self.history["lower_band"][-2]
            prev_upper = self.history["upper_band"][-2]
            
            # Price break detection
            price_flip_up = (prev_trend == -1 and close > prev_upper)
            price_flip_down = (prev_trend == 1 and close < prev_lower)
            
            # Character flip detection (TQI collapse)
            char_flip_up = False
            char_flip_down = False
            
            if self.use_char_flip and bar_index >= self.char_flip_min_age:
                trend_age = bar_index - self.trend_started_bar
                if trend_age >= self.char_flip_min_age:
                    # Check if TQI was high in window, now low
                    window_start = max(0, bar_index - self.char_flip_min_age)
                    tqi_window_high = max([self.history.get("tqi", [np.nan])[i] 
                                          for i in range(window_start, bar_index)] + [tqi])
                    
                    if tqi_window_high > self.char_flip_high and tqi < self.char_flip_low:
                        # Check if price moved against trend
                        price_then = self.history["close"][-self.char_flip_min_age - 1]
                        if prev_trend == 1 and close < price_then:
                            char_flip_down = True
                        elif prev_trend == -1 and close > price_then:
                            char_flip_up = True
            
            # Determine final flip
            final_flip_up = price_flip_up or char_flip_up
            final_flip_down = price_flip_down or char_flip_down
            
            if final_flip_up:
                self.trend = 1
                flip_up = True
                self.trend_started_bar = bar_index
            elif final_flip_down:
                self.trend = -1
                flip_down = True
                self.trend_started_bar = bar_index
        
        self.history["trend"].append(self.trend)
        
        # Determine ST line
        st_line = self.lower_band if self.trend == 1 else self.upper_band
        
        # Store TQI for history
        if "tqi" not in self.history:
            self.history["tqi"] = []
        self.history["tqi"].append(tqi)
        
        return SATSState(
            bar_index=bar_index,
            close=close,
            trend=self.trend,
            trend_started_bar=self.trend_started_bar,
            lower_band=self.lower_band,
            upper_band=self.upper_band,
            st_line=st_line,
            flip_up=flip_up,
            flip_down=flip_down,
            tqi=tqi,
            er=er,
            atr=atr,
        )
