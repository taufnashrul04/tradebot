"""
bot_trade/strategies/__init__.py
"""
from .funding_scanner import FundingScanner
from .delta_neutral import DeltaNeutralStrategy
from .volume_generator import VolumeGeneratorStrategy
from .indicator_trader import IndicatorTrader, IndicatorStrategy

__all__ = [
    "FundingScanner",
    "DeltaNeutralStrategy",
    "VolumeGeneratorStrategy",
    "IndicatorTrader",
    "IndicatorStrategy",
]
