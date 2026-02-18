"""
P2P US2 Carrier Module

Expected shipping cost calculator for P2P US2 (Parcel Flex Advantage + Standard).
Two services: PFA (light/small, ≤30 lbs) and PFS (heavier, ≤70 lbs).
"""

from .calculate_costs import calculate_costs
from .version import VERSION

__all__ = ["calculate_costs", "VERSION"]
