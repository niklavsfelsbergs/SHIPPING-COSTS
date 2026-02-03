"""
P2P US Carrier Module

Expected shipping cost calculator for P2P (Parcel Flex Advantage Plus - PFAP2).
"""

from .calculate_costs import calculate_costs
from .version import VERSION

__all__ = ["calculate_costs", "VERSION"]
