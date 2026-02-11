"""
Residential Surcharge

Applies to all FedEx Home Delivery shipments. Home Delivery is FedEx's
residential-specific service, so the surcharge is 100% deterministic
based on service type (not address classification).

FedEx Ground has a separate, higher residential surcharge ($5.95) for
deliveries to residential addresses, but we don't ship Ground.
"""

import polars as pl
from shared.surcharges import Surcharge


class Residential(Surcharge):
    """
    Residential Surcharge - applies to all Home Delivery shipments.

    Unlike OnTrac where residential is allocated based on address type,
    FedEx Home Delivery is inherently a residential service, so every
    shipment receives this surcharge (100% deterministic).
    """

    name = "Residential"

    # -------------------------------------------------------------------------
    # PRICING (2026 proposed contract)
    # -------------------------------------------------------------------------
    list_price = 6.45
    discount = 0.65  # 65% off

    @classmethod
    def conditions(cls) -> pl.Expr:
        """Triggers for all Home Delivery shipments."""
        return pl.col("rate_service") == "Home Delivery"

