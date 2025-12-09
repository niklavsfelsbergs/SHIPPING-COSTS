"""
Large Package Surcharge (LPS)

Applies to packages that exceed large package thresholds but not OML limits.
"""

import polars as pl
from shared.surcharges import Surcharge


class LPS(Surcharge):
    """Large Package - exceeds size thresholds below OML limits."""

    # Identity
    name = "LPS"

    # Pricing (60% discount)
    list_price = 260.00
    discount = 0.60

    # Exclusivity (dimensional: OML > LPS > AHS)
    exclusivity_group = "dimensional"
    priority = 2

    # Side effects
    min_billable_weight = 90

    # Thresholds
    LONGEST_IN = 72
    CUBIC_IN = 17280  # 24" x 24" x 30"

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            (pl.col("longest_side_in").round(0) > cls.LONGEST_IN) |
            (pl.col("cubic_in").round(0) > cls.CUBIC_IN)
        )
