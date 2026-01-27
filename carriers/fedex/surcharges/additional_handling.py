"""
Additional Handling Surcharge - Dimensions (AHS)

Applies to Home Delivery packages that exceed dimensional thresholds
and require special handling due to their size.

Triggers when ANY of the following conditions are met:
- Length (longest side) > 48 inches
- Second longest side > 30.3 inches
- Girth (length + 2 × (width + height)) > 106 inches

Notes:
- Ground Economy is exempt from AHS
- 30.3" second longest excluded (FedEx charges only ~3.4% at this threshold)
- 106" girth threshold (105-106" borderline excluded)
- Mutually exclusive with Oversize (Oversize wins)

Side effect: Minimum billable weight of 40 lbs when triggered.
"""

import polars as pl
from shared.surcharges import Surcharge


class AHS(Surcharge):
    """
    Additional Handling Surcharge - Dimensions.

    FedEx charges AHS for packages that exceed size thresholds,
    requiring additional handling during transit.
    """

    name = "AHS"

    # -------------------------------------------------------------------------
    # PRICING
    # -------------------------------------------------------------------------
    list_price = 8.60
    discount = 0.0  # No discount

    # -------------------------------------------------------------------------
    # EXCLUSIVITY
    # -------------------------------------------------------------------------
    exclusivity_group = "dimensional"
    priority = 3  # Loses to Oversize (1) and AHS - Weight (2)

    # -------------------------------------------------------------------------
    # SIDE EFFECTS
    # -------------------------------------------------------------------------
    min_billable_weight = 40  # 40 lbs minimum when AHS triggers

    # -------------------------------------------------------------------------
    # THRESHOLDS
    # -------------------------------------------------------------------------
    LONGEST_IN = 48         # Length > 48"
    SECOND_LONGEST_IN = 30.3  # Second longest > 30.3" (30.3" borderline excluded)
    GIRTH_IN = 106          # Length + 2×(W+H) > 106" (105-106" borderline excluded)

    @classmethod
    def conditions(cls) -> pl.Expr:
        """
        Triggers when package exceeds any dimensional threshold.

        Uses length_plus_girth column which is calculated as:
        longest_side + 2 × (sum of other two sides)
        This is equivalent to: length + 2 × (width + height)

        Note: Ground Economy is exempt from AHS.
        Note: 30.3" second longest is excluded (FedEx charges only ~3.4% at this threshold).
        """
        is_home_delivery = pl.col("rate_service") == "Home Delivery"

        exceeds_dimensions = (
            (pl.col("longest_side_in") > cls.LONGEST_IN) |
            (pl.col("second_longest_in") > cls.SECOND_LONGEST_IN) |
            (pl.col("length_plus_girth") > cls.GIRTH_IN)
        )

        return is_home_delivery & exceeds_dimensions
