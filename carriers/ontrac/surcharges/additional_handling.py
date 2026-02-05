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
    # Zone-based list prices (ontrac.com/surcharges, eff. March 7, 2026)
    list_price = 36.00  # Zone 2-4 default, see cost() for zone-based pricing
    discount = 0.70
    ZONE_PRICES = {2: 36.00, 3: 36.00, 4: 36.00, 5: 40.00, 6: 40.00, 7: 42.00, 8: 42.00}

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
        Return surcharge cost with zone-based pricing and borderline allocation.

        Zone pricing (eff. March 7, 2026):
        - Zone 2-4: $36.00
        - Zone 5-6: $40.00
        - Zone 7-8: $42.00

        Borderline: second_longest is in (30.0, 30.5] AND no other trigger.
        OnTrac charges these inconsistently (~50%), so we allocate 50% of cost.
        """
        # Zone-based list price
        zone_list_price = (
            pl.when(pl.col("shipping_zone").is_in([2, 3, 4]))
            .then(36.00)
            .when(pl.col("shipping_zone").is_in([5, 6]))
            .then(40.00)
            .when(pl.col("shipping_zone").is_in([7, 8]))
            .then(42.00)
            .otherwise(36.00)  # fallback for unknown zones
        )

        base_cost = zone_list_price * (1 - cls.discount)

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
            .then(base_cost * cls.BORDERLINE_ALLOCATION)
            .otherwise(base_cost)
        )
