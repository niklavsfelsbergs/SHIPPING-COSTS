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
    # PRICING (2026 proposed contract)
    # -------------------------------------------------------------------------

    # Home Delivery - list prices and discount
    HD_DISCOUNT = 0.65  # 65% off all HD DAS tiers

    HD_DAS_LIST = 6.60
    HD_DAS_EXTENDED_LIST = 8.80
    HD_DAS_REMOTE_LIST = 16.75
    HD_DAS_ALASKA = 43.00      # TODO: list price unknown, storing net
    HD_DAS_HAWAII = 14.50      # TODO: list price unknown, storing net

    HD_DAS = round(HD_DAS_LIST * (1 - HD_DISCOUNT), 2)              # 2.31
    HD_DAS_EXTENDED = round(HD_DAS_EXTENDED_LIST * (1 - HD_DISCOUNT), 2)  # 3.08
    HD_DAS_REMOTE = round(HD_DAS_REMOTE_LIST * (1 - HD_DISCOUNT), 2)     # 5.86

    # Ground Economy (SmartPost) - list prices and discount
    SP_DISCOUNT = 0.50  # 50% off DAS and DAS Extended only

    SP_DAS_LIST = 6.60
    SP_DAS_EXTENDED_LIST = 8.80
    SP_DAS_ALASKA_LIST = 8.80
    SP_DAS_HAWAII_LIST = 8.80

    SP_DAS = round(SP_DAS_LIST * (1 - SP_DISCOUNT), 2)              # 3.30
    SP_DAS_EXTENDED = round(SP_DAS_EXTENDED_LIST * (1 - SP_DISCOUNT), 2)  # 4.40
    SP_DAS_ALASKA = round(SP_DAS_ALASKA_LIST, 2)                         # 8.80 (no discount)
    SP_DAS_HAWAII = round(SP_DAS_HAWAII_LIST, 2)                         # 8.80 (no discount)

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
