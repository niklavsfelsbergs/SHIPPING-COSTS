"""
Additional Handling Surcharge (AHS)

Applies to packages that require additional handling due to size or weight.
Triggers on any of:
  1. Longest side > 48"
  2. Second longest side > 30"
  3. Length + girth > 105"
  4. Billable weight > 30 lbs

When triggered by dimensional conditions (1-3), enforces 30 lb minimum billable weight.
"""

import polars as pl
from shared.surcharges import Surcharge


class AHS(Surcharge):
    """Additional Handling - requires extra handling due to size/weight."""

    # Identity
    name = "AHS"

    # Pricing (no discount)
    list_price = 29.00
    discount = 0.00

    # Not exclusive - standalone surcharge
    exclusivity_group = None
    priority = None

    # Side effects
    min_billable_weight = 30  # Applied when dimensional conditions trigger

    # Thresholds
    LONGEST_IN = 48
    SECOND_LONGEST_IN = 30
    LENGTH_PLUS_GIRTH = 105
    WEIGHT_LBS = 30

    @classmethod
    def conditions(cls) -> pl.Expr:
        """
        Triggers on any of the following:
        1. Longest side > 48"
        2. Second longest side > 30"
        3. Length + girth > 105"
        4. Billable weight > 30 lbs
        """
        return (
            (pl.col("longest_side_in") > cls.LONGEST_IN) |
            (pl.col("second_longest_in") > cls.SECOND_LONGEST_IN) |
            (pl.col("length_plus_girth") > cls.LENGTH_PLUS_GIRTH) |
            (pl.col("billable_weight_lbs") > cls.WEIGHT_LBS)
        )

    @classmethod
    def dimensional_conditions(cls) -> pl.Expr:
        """
        Only the dimensional conditions (not weight).
        Used to determine when to apply min_billable_weight side effect.
        """
        return (
            (pl.col("longest_side_in") > cls.LONGEST_IN) |
            (pl.col("second_longest_in") > cls.SECOND_LONGEST_IN) |
            (pl.col("length_plus_girth") > cls.LENGTH_PLUS_GIRTH)
        )
