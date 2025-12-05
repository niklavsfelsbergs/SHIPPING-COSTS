"""
Additional Handling Surcharge (AHS)

Applies to packages that require additional handling due to size, weight, or shape.
"""

import polars as pl
from .base import Surcharge


class AHS(Surcharge):
    """
    Additional Handling Surcharge

    Triggers when package exceeds weight, dimension, or volume thresholds.
    Contract: 70% discount (Third Amendment)
    """

    name = "AHS"
    list_price = 32.00
    discount = 0.70
    allocation_type = "deterministic"

    priority_group = "dimensional"
    priority = 3

    min_billable_weight = 30  # OnTrac: 40, Contract: 30 (negotiated)

    # Thresholds
    weight_threshold = 50
    longest_threshold = 48
    second_longest_threshold = 30
    cubic_threshold = 8640  # 18" x 20" x 24"

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            (pl.col("weight_lbs").round(0) > cls.weight_threshold) |
            (pl.col("longest_side_in").round(0) > cls.longest_threshold) |
            (pl.col("second_longest_in").round(0) > cls.second_longest_threshold) |
            (pl.col("cubic_in").round(0) > cls.cubic_threshold)
        )
