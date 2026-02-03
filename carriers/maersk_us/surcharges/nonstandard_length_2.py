"""
Nonstandard Length Surcharge - Tier 2 (NSL2)

Applies to packages with longest side >30".
Mutually exclusive with NSL1 - NSL2 wins when both trigger.
"""

import polars as pl
from shared.surcharges import Surcharge


class NSL2(Surcharge):
    """Nonstandard Length Tier 2 - longest side over 30"."""

    # Identity
    name = "NSL2"

    # Pricing (no discount)
    list_price = 4.00
    discount = 0.00

    # Exclusivity (length: NSL2 > NSL1)
    exclusivity_group = "length"
    priority = 1  # Highest priority, wins over NSL1

    # Thresholds
    MIN_LENGTH_IN = 30

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("longest_side_in") > cls.MIN_LENGTH_IN
