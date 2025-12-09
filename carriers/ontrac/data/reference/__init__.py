"""
Reference Data

Static reference data for rates, zones, and configuration.
"""

from .billable_weight import DIM_FACTOR, DIM_THRESHOLD, THRESHOLD_FIELD, FACTOR_FIELD
from .fuel import LIST_RATE, DISCOUNT, RATE, APPLICATION

__all__ = [
    "DIM_FACTOR",
    "DIM_THRESHOLD",
    "THRESHOLD_FIELD",
    "FACTOR_FIELD",
    "LIST_RATE",
    "DISCOUNT",
    "RATE",
    "APPLICATION",
]
