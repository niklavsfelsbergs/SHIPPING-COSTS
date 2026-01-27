"""
Oversize Surcharge

Applies to Home Delivery packages that exceed size/weight limits requiring
special handling as oversized freight.

Triggers when ANY of the following conditions are met:
- Length (longest side) > 96 inches
- Length + Girth > 130 inches
- Volume > 17,280 cubic inches
- Actual weight > 110 lbs

Notes:
- Ground Economy is exempt from Oversize
- Oversize and AHS are mutually exclusive (Oversize wins)
"""

import polars as pl
from shared.surcharges import Surcharge


class Oversize(Surcharge):
    """
    Oversize Surcharge.

    FedEx charges Oversize for packages that exceed large size thresholds,
    requiring handling as oversized freight.

    Mutually exclusive with AHS - if Oversize applies, AHS does not.
    """

    name = "Oversize"

    # -------------------------------------------------------------------------
    # PRICING
    # -------------------------------------------------------------------------
    # TODO: Get actual Oversize price from contract
    list_price = 115.00  # Placeholder based on invoice data (~$131 before discount)
    discount = 0.0

    # -------------------------------------------------------------------------
    # EXCLUSIVITY
    # -------------------------------------------------------------------------
    exclusivity_group = "dimensional"
    priority = 1  # Wins over AHS (priority 2)

    # -------------------------------------------------------------------------
    # THRESHOLDS
    # -------------------------------------------------------------------------
    LONGEST_IN = 96           # Length > 96"
    LENGTH_PLUS_GIRTH_IN = 130  # Length + Girth > 130"
    CUBIC_IN = 17280          # Volume > 17,280 cubic inches
    WEIGHT_LBS = 110          # Actual weight > 110 lbs

    @classmethod
    def conditions(cls) -> pl.Expr:
        """
        Triggers when package exceeds any oversize threshold.

        Note: Ground Economy is exempt from Oversize.
        """
        is_home_delivery = pl.col("rate_service") == "Home Delivery"

        exceeds_dimensions = (
            (pl.col("longest_side_in") > cls.LONGEST_IN) |
            (pl.col("length_plus_girth") > cls.LENGTH_PLUS_GIRTH_IN) |
            (pl.col("cubic_in") > cls.CUBIC_IN) |
            (pl.col("weight_lbs") > cls.WEIGHT_LBS)
        )

        return is_home_delivery & exceeds_dimensions
