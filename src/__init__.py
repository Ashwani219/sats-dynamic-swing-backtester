"""SATS + Dynamic Swing Backtester Package"""

from .sats_engine import SATSEngine
from .dynamic_swing import DynamicSwingEngine
from .strategy import StrategyStateMachine
from .backtester import Backtester
from .metrics import MetricsCalculator

__version__ = "1.0.0"
__author__ = "Ashwani219"

__all__ = [
    "SATSEngine",
    "DynamicSwingEngine",
    "StrategyStateMachine",
    "Backtester",
    "MetricsCalculator",
]
