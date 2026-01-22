"""
Demand Additional Handling Surcharge (DEM_AHS)

Seasonal surcharge applied when AHS triggers during peak period.
"""

import polars as pl
from shared.surcharges import Surcharge, in_period


class DEM_AHS(Surcharge):
    """Demand Additional Handling - seasonal surcharge when AHS applies."""

    # Identity
    name = "DEM_AHS"

    # Pricing (0% discount per Fourth Amendment)
    list_price = 11.00
    discount = 0.00

    # Dependencies
    depends_on = "AHS"
    period_start = (9, 27)   # Sept 27
    period_end = (1, 16)     # Jan 16

    # Borderline allocation (same as AHS)
    # Import thresholds from AHS to stay in sync
    BORDERLINE_ALLOCATION = 0.50

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("surcharge_ahs") & in_period(cls.period_start, cls.period_end)

    @classmethod
    def cost(cls) -> pl.Expr:
        """
        Return surcharge cost, with 50% allocation for borderline AHS cases.

        Mirrors AHS borderline logic - if AHS was triggered only by borderline
        second_longest (30.0-30.5"), apply 50% allocation to DEM_AHS as well.
        """
        from .additional_handling import AHS

        base_cost = cls.list_price * (1 - cls.discount)

        # Check if AHS was triggered ONLY by borderline second_longest
        borderline_only = (
            (pl.col("second_longest_in") > AHS.SECOND_LONGEST_IN) &
            (pl.col("second_longest_in") <= AHS.SECOND_LONGEST_BORDERLINE_MAX) &
            (pl.col("weight_lbs") <= AHS.WEIGHT_LBS) &
            (pl.col("longest_side_in") <= AHS.LONGEST_IN) &
            (pl.col("cubic_in") <= AHS.CUBIC_IN)
        )

        return (
            pl.when(borderline_only)
            .then(pl.lit(base_cost * cls.BORDERLINE_ALLOCATION))
            .otherwise(pl.lit(base_cost))
        )
