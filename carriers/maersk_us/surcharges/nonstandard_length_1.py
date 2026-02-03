"""
Nonstandard Length Surcharge - Tier 1 (NSL1)

Applies to packages with longest side >21".
Mutually exclusive with NSL2 - NSL2 wins when both trigger.
"""

import polars as pl
from shared.surcharges import Surcharge


class NSL1(Surcharge):
    """Nonstandard Length Tier 1 - longest side over 21"."""

    # Identity
    name = "NSL1"

    # Pricing (no discount)
    list_price = 4.00
    discount = 0.00

    # Exclusivity (length: NSL2 > NSL1)
    exclusivity_group = "length"
    priority = 2  # Lower priority than NSL2

    # Thresholds
    MIN_LENGTH_IN = 21

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("longest_side_in") > cls.MIN_LENGTH_IN
