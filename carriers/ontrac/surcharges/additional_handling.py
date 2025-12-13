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
    list_price = 32.00
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

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            (pl.col("weight_lbs") > cls.WEIGHT_LBS) |
            (pl.col("longest_side_in") > cls.LONGEST_IN) |
            (pl.col("second_longest_in") > cls.SECOND_LONGEST_IN) |
            (pl.col("cubic_in") > cls.CUBIC_IN)
        )
