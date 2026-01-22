"""
Additional Handling Surcharge (AHS)

Applies to packages that require additional handling due to size, weight, or shape.
"""

import polars as pl
from shared.surcharges import Surcharge


class AHS(Surcharge):
    """Additional Handling - requires extra handling due to size/weight."""

    # Identity
    name = "AHS"

    # Pricing (70% discount per Third Amendment)
    list_price = 36.00
    discount = 0.70

    # Exclusivity (dimensional: OML > LPS > AHS)
    exclusivity_group = "dimensional"
    priority = 3

    # Side effects (negotiated down from OnTrac standard of 40)
    min_billable_weight = 30

    # Thresholds
    WEIGHT_LBS = 50
    LONGEST_IN = 48
    SECOND_LONGEST_IN = 30
    CUBIC_IN = 8640  # 18" x 20" x 24"

    # Borderline allocation for second_longest near threshold
    # OnTrac charges ~50% of packages at 30.3" (PIZZA BOX 40x30x1)
    SECOND_LONGEST_BORDERLINE_MAX = 30.5
    BORDERLINE_ALLOCATION = 0.50

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            (pl.col("weight_lbs") > cls.WEIGHT_LBS) |
            (pl.col("longest_side_in") > cls.LONGEST_IN) |
            (pl.col("second_longest_in") > cls.SECOND_LONGEST_IN) |
            (pl.col("cubic_in") > cls.CUBIC_IN)
        )

    @classmethod
    def cost(cls) -> pl.Expr:
        """
        Return surcharge cost, with 50% allocation for borderline cases.

        Borderline: second_longest is in (30.0, 30.5] AND no other trigger.
        OnTrac charges these inconsistently (~50%), so we allocate 50% of cost.
        """
        base_cost = cls.list_price * (1 - cls.discount)

        # Check if ONLY triggered by borderline second_longest
        borderline_only = (
            # second_longest in borderline range
            (pl.col("second_longest_in") > cls.SECOND_LONGEST_IN) &
            (pl.col("second_longest_in") <= cls.SECOND_LONGEST_BORDERLINE_MAX) &
            # No other conditions triggered
            (pl.col("weight_lbs") <= cls.WEIGHT_LBS) &
            (pl.col("longest_side_in") <= cls.LONGEST_IN) &
            (pl.col("cubic_in") <= cls.CUBIC_IN)
        )

        return (
            pl.when(borderline_only)
            .then(pl.lit(base_cost * cls.BORDERLINE_ALLOCATION))
            .otherwise(pl.lit(base_cost))
        )
