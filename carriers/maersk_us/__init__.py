"""
Maersk US Carrier Module

Expected shipping cost calculator for Maersk US domestic last mile delivery.
"""

from .calculate_costs import calculate_costs
from .version import VERSION

__all__ = ["calculate_costs", "VERSION"]
