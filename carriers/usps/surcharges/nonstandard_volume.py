"""
Nonstandard Volume Surcharge (NSV)

Applies to packages exceeding 2 cubic feet (3456 cubic inches).
"""

import polars as pl
from shared.surcharges import Surcharge


class NSV(Surcharge):
    """Nonstandard Volume - exceeds 2 cubic feet."""

    # Identity
    name = "NSV"

    # Pricing (no discount)
    list_price = 10.00
    discount = 0.00

    # No exclusivity - can stack with length surcharges
    exclusivity_group = None
    priority = None

    # Thresholds
    MAX_CUBIC_IN = 3456  # 2 cubic feet = 2 * 12^3 = 3456 cubic inches

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("cubic_in") > cls.MAX_CUBIC_IN
