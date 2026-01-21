"""
Over Maximum Limits (OML) Surcharge

Penalty surcharge for packages exceeding maximum size/weight limits.
"""

import polars as pl
from shared.surcharges import Surcharge


class OML(Surcharge):
    """Over Maximum Limits - penalty for exceeding size/weight limits."""

    # Identity
    name = "OML"

    # Pricing (no discount - penalty surcharge)
    list_price = 1875.00
    discount = 0.00

    # Exclusivity (dimensional: OML > LPS > AHS)
    exclusivity_group = "dimensional"
    priority = 1

    # Side effects
    min_billable_weight = 150

    # Thresholds
    WEIGHT_LBS = 150
    LONGEST_IN = 108
    LENGTH_PLUS_GIRTH_IN = 165

    @classmethod
    def conditions(cls) -> pl.Expr:
        return (
            (pl.col("weight_lbs") > cls.WEIGHT_LBS) |
            (pl.col("longest_side_in") > cls.LONGEST_IN) |
            (pl.col("length_plus_girth") > cls.LENGTH_PLUS_GIRTH_IN)
        )
