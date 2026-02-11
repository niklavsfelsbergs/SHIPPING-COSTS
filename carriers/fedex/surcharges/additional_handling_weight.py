"""
Additional Handling Surcharge - Weight (AHS - Weight)

Applies to packages that exceed weight threshold requiring special handling.

Triggers when:
- Actual weight > 50 lbs

Notes:
- Mutually exclusive with AHS - Dimensions (AHS - Weight wins as higher cost)
- Mutually exclusive with Oversize (Oversize wins)
"""

import polars as pl
from shared.surcharges import Surcharge


class AHS_Weight(Surcharge):
    """
    Additional Handling Surcharge - Weight.

    FedEx charges AHS - Weight for packages over 50 lbs,
    requiring additional handling during transit.
    """

    name = "AHS_Weight"

    # -------------------------------------------------------------------------
    # PRICING (2026 proposed contract)
    # -------------------------------------------------------------------------
    list_price = 50.25
    discount = 0.50  # 50% off

    # -------------------------------------------------------------------------
    # EXCLUSIVITY
    # -------------------------------------------------------------------------
    exclusivity_group = "dimensional"
    priority = 2  # Wins over AHS - Dimensions (priority 3), loses to Oversize (priority 1)

    # -------------------------------------------------------------------------
    # THRESHOLDS
    # -------------------------------------------------------------------------
    WEIGHT_LBS = 50  # Actual weight > 50 lbs

    @classmethod
    def conditions(cls) -> pl.Expr:
        """
        Triggers when package actual weight exceeds threshold.
        """
        return pl.col("weight_lbs") > cls.WEIGHT_LBS
