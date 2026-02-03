"""
Nonstandard Dimensions Surcharge (NSD)

Applies to packages with volume >3456 cubic inches (2 cubic feet).
Can stack with NSL surcharges.
"""

import polars as pl
from shared.surcharges import Surcharge


class NSD(Surcharge):
    """Nonstandard Dimensions - volume over 2 cubic feet."""

    # Identity
    name = "NSD"

    # Pricing (no discount)
    list_price = 18.00
    discount = 0.00

    # Not exclusive - can stack with NSL surcharges
    exclusivity_group = None
    priority = None

    # Thresholds
    MAX_CUBIC_IN = 3456  # 2 cubic feet (12*12*24 = 3456)

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("cubic_in") > cls.MAX_CUBIC_IN
