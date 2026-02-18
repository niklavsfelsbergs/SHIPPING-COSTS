"""
PFS Nonstandard Length Surcharge

Applies to PFS packages based on longest side:
    - >22" and ≤30": $4.50
    - >30": $10.00

Uses expression-based cost (not fixed).
"""

import polars as pl
from shared.surcharges import Surcharge


class PFS_NONSTANDARD_LENGTH(Surcharge):
    """PFS Nonstandard Length - tiered by longest side."""

    name = "PFS_NSL"
    list_price = 10.00  # Max tier
    discount = 0.00

    exclusivity_group = None
    priority = None

    TIER1_THRESHOLD = 22  # >22" and ≤30" → $4.50
    TIER2_THRESHOLD = 30  # >30" → $10.00
    TIER1_COST = 4.50
    TIER2_COST = 10.00

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("longest_side_in") > cls.TIER1_THRESHOLD

    @classmethod
    def cost(cls) -> pl.Expr:
        return (
            pl.when(pl.col("longest_side_in") > cls.TIER2_THRESHOLD)
            .then(pl.lit(cls.TIER2_COST))
            .otherwise(pl.lit(cls.TIER1_COST))
        )
