"""
Delivery Area Surcharge (DAS)

Applies to deliveries in designated remote/extended areas.
FedEx has multiple DAS tiers with service-specific pricing.

DAS zones are determined by destination ZIP code only (not origin-dependent).
"""

import polars as pl
from shared.surcharges import Surcharge


class DAS(Surcharge):
    """
    Delivery Area Surcharge - ZIP is in a DAS zone.

    Tiers (mutually exclusive):
        - DAS: Standard delivery area
        - DAS_EXTENDED: Extended delivery area
        - DAS_REMOTE: Remote residential (Home Delivery only)
        - DAS_ALASKA: Alaska delivery area
        - DAS_HAWAII: Hawaii delivery area

    The das_zone column is populated by _lookup_das_zones() in calculate_costs.py
    based on the destination ZIP code and rate_service.
    """

    name = "DAS"

    # -------------------------------------------------------------------------
    # PRICING BY TIER AND SERVICE (Q4 2025)
    # -------------------------------------------------------------------------

    # Home Delivery
    HD_DAS = 2.17
    HD_DAS_EXTENDED = 2.91
    HD_DAS_REMOTE = 5.43
    HD_DAS_ALASKA = 43.00
    HD_DAS_HAWAII = 14.50

    # Ground Economy (SmartPost)
    SP_DAS = 3.10
    SP_DAS_EXTENDED = 4.15
    SP_DAS_ALASKA = 8.30
    SP_DAS_HAWAII = 8.30

    # Base class requirements (not used - cost() handles pricing dynamically)
    list_price = 0.0
    discount = 0.0

    @classmethod
    def conditions(cls) -> pl.Expr:
        """Triggers when das_zone is set (any tier)."""
        return pl.col("das_zone").is_not_null()

    @classmethod
    def cost(cls) -> pl.Expr:
        """Returns cost based on das_zone and rate_service."""
        return (
            pl.when(pl.col("rate_service") == "Home Delivery")
            .then(
                pl.when(pl.col("das_zone") == "DAS").then(cls.HD_DAS)
                .when(pl.col("das_zone") == "DAS_EXTENDED").then(cls.HD_DAS_EXTENDED)
                .when(pl.col("das_zone") == "DAS_REMOTE").then(cls.HD_DAS_REMOTE)
                .when(pl.col("das_zone") == "DAS_ALASKA").then(cls.HD_DAS_ALASKA)
                .when(pl.col("das_zone") == "DAS_HAWAII").then(cls.HD_DAS_HAWAII)
                .otherwise(0.0)
            )
            .otherwise(  # Ground Economy
                pl.when(pl.col("das_zone") == "DAS").then(cls.SP_DAS)
                .when(pl.col("das_zone") == "DAS_EXTENDED").then(cls.SP_DAS_EXTENDED)
                .when(pl.col("das_zone") == "DAS_ALASKA").then(cls.SP_DAS_ALASKA)
                .when(pl.col("das_zone") == "DAS_HAWAII").then(cls.SP_DAS_HAWAII)
                .otherwise(0.0)
            )
        )
