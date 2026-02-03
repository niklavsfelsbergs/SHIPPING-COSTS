"""
Oversize Surcharge

Applies to packages with billable weight > 70 lbs.
"""

import polars as pl
from shared.surcharges import Surcharge


class OVERSIZE(Surcharge):
    """Oversize - billable weight over 70 lbs."""

    # Identity
    name = "OVERSIZE"

    # Pricing (no discount)
    list_price = 125.00
    discount = 0.00

    # Not exclusive - standalone surcharge
    exclusivity_group = None
    priority = None

    # Thresholds
    WEIGHT_LBS = 70

    @classmethod
    def conditions(cls) -> pl.Expr:
        return pl.col("billable_weight_lbs") > cls.WEIGHT_LBS
