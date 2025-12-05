"""
Large Package Surcharge (LPS)

Applies to packages that exceed large package thresholds but not OML limits.
"""

import polars as pl
from .base import Surcharge


class LPS(Surcharge):
    """
    Large Package Surcharge

    Triggers when package exceeds length or cubic inch thresholds.
    Contract: 60% discount
    """

    name = "LPS"
    list_price = 260.00
    discount = 0.60
    allocation_type = "deterministic"

    priority_group = "dimensional"
    priority = 2

    min_billable_weight = 90  # OnTrac: 90, Contract: 90

    # Thresholds
    longest_threshold = 72
    cubic_threshold = 17280  # 24" x 24" x 30"

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            (pl.col("longest_side_in").round(0) > cls.longest_threshold) |
            (pl.col("cubic_in").round(0) > cls.cubic_threshold)
        )
