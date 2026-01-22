"""
Nonstandard Length Surcharge - Tier 1 (NSL1)

Applies to packages with longest side >22" but <=30".
"""

import polars as pl
from shared.surcharges import Surcharge


class NSL1(Surcharge):
    """Nonstandard Length Tier 1 - longest side between 22" and 30"."""

    # Identity
    name = "NSL1"

    # Pricing (no discount)
    list_price = 3.00
    discount = 0.00

    # Exclusivity (length: NSL2 > NSL1)
    exclusivity_group = "length"
    priority = 2  # Lower priority than NSL2

    # Thresholds
    MIN_LENGTH_IN = 22
    MAX_LENGTH_IN = 30

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            (pl.col("longest_side_in") > cls.MIN_LENGTH_IN) &
            (pl.col("longest_side_in") <= cls.MAX_LENGTH_IN)
        )
